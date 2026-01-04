import contextlib
import os
import sys
import urllib.parse

import aiohttp
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from firebase_admin import firestore
from google.cloud.firestore import FieldFilter

from database import GUILD_CONFIG_COLLECTION, TRACKED_USERS_COLLECTION, database_startup
from logger_config import logger
from sentry_config import setup_sentry
from utils import (
    RateLimitError,
    RiotAPIError,
    UserNotFoundError,
    extract_match_info,
    get_puuid,
    get_ranked_info,
    get_recent_match_info,
    parse_riot_id,
)

# API Keys

load_dotenv()
DISCORD_KEY = os.getenv("DISCORD_PUBLIC_KEY")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# Sentry Initialization

setup_sentry()

# Sorting Helpers

TIER_ORDER = {
    "CHALLENGER": 9,
    "GRANDMASTER": 8,
    "MASTER": 7,
    "DIAMOND": 6,
    "EMERALD": 5,
    "PLATINUM": 4,
    "GOLD": 3,
    "SILVER": 2,
    "BRONZE": 1,
    "IRON": 0,
    "UNRANKED": -1,
}
RANK_ORDER = {"I": 4, "II": 3, "III": 2, "IV": 1, "": 0}

# Database Startup

db = database_startup()
if not db:
    logger.error("❌ ERROR: Database did not properly initialize")
    sys.exit(1)

# Bot Startup

BOT_PREFIX = "!"

class MyHelp(commands.MinimalHelpCommand):
    def add_bot_commands_formatting(self, commands, _heading):
        """This replaces the category heading with an 'Available Commands' label."""
        if commands:
            self.paginator.add_line("**Available Commands:**")
            for command in commands:
                self.add_subcommand_formatting(command)

    async def send_bot_help(self, mapping):
        self.paginator.add_line(
            "⚠️ **DISCLAIMER**: This bot is a personal project and is not " \
            "affiliated with Riot Games.",
        )
        self.paginator.add_line(
            "**NOTE**: By default, the bot will not send live ranked updates until " \
            "the `!updateshere` command is used",
        )
        self.paginator.add_line()
        await super().send_bot_help(mapping)

    def get_ending_note(self):
        """Adds a blank space before the 'Type !help command for more info' message."""
        return f"\n{super().get_ending_note()}"

    def get_opening_note(self):
        """Only returns the 'help [command]' instruction, removing the category line."""
        command_name = f"{self.context.clean_prefix}{self.invoked_with}"
        return f"Use `{command_name} [command]` for more info on a command."

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Watching The Rift - !help",
        )
        super().__init__(
            command_prefix=BOT_PREFIX,
            intents=intents,
            activity=activity,
        )
        self.session = None  # placeholder

    async def setup_hook(self):
        # runs when the bot starts up.
        self.session = aiohttp.ClientSession()
        logger.info("✅ Persistent HTTP Session created.")
        if not self.background_update_task.is_running():
            self.background_update_task.start()
            logger.info("✅ Background update task started.")

    async def close(self):
        # runs when the bot shuts down.
        if self.session:
            await self.session.close()
            logger.info("🛑 HTTP Session closed.")
        await super().close()

    # Background Task

    @tasks.loop(minutes=10)
    async def background_update_task(self):
        try:
            logger.info("♻️ Starting background update loop")
            docs = db.collection(TRACKED_USERS_COLLECTION).stream()
            doc_list = list(docs)
            for doc in doc_list:
                old_tier = doc.get("tier")
                old_rank = doc.get("rank")
                old_lp = doc.get("LP")
                puuid = doc.get("puuid")
                data = await get_ranked_info(bot.session, puuid, RIOT_API_KEY)
                new_tier = data.get("tier")
                new_rank = data.get("rank")
                new_lp = data.get("LP")
                doc.reference.update(data)
                if old_tier == new_tier and old_rank == new_rank and old_lp == new_lp:
                    continue
                guild_ids = doc.get("guild_ids")
                for guild in guild_ids:
                    channel = None
                    try:
                        config_ref = (
                            db.collection(GUILD_CONFIG_COLLECTION).document(guild)
                        )
                        config = config_ref.get()
                        if config.exists:
                            channel_id = config.get("channel_id")
                            channel = bot.get_channel(channel_id)
                    except Exception as e:
                        logger.exception(
                            f"❌ ERROR: fetching config for guild {guild}: {e}",
                        )
                    if channel:
                        riot_id = doc.get("riot_id")
                        match_info = await get_recent_match_info(
                            bot.session,
                            puuid,
                            RIOT_API_KEY,
                        )
                        processed_match_info = extract_match_info(match_info, puuid)
                        ranked_data = {
                            "old_tier": old_tier,
                            "old_rank": old_rank,
                            "old_lp": old_lp,
                            "new_tier": new_tier,
                            "new_rank": new_rank,
                            "new_lp": new_lp,
                        }
                        view = MatchDetailsView(
                            processed_match_info,
                            ranked_data,
                            riot_id,
                            puuid,
                        )
                        initial_embed = view.create_minimized_embed()
                        message = await channel.send(embed=initial_embed, view=view)
                        view.message = message
        except Exception as e:
            logger.exception(f"❌ ERROR: {e}")


    @background_update_task.before_loop
    async def before_background_task(self):
        await self.wait_until_ready()


bot = MyBot()
bot.help_command = MyHelp()

# Ranked Update Class

class MatchDetailsView(discord.ui.View):
    """A view that toggles between a simple rank update and a full match summary."""
    def __init__(self, match_data, ranked_data, riot_id, puuid, timeout=259200):
        super().__init__(timeout=timeout)
        self.match_data = match_data
        self.ranked_data = ranked_data
        self.riot_id = riot_id
        self.is_expanded = False
        self.message = None
        self.puuid = puuid
        self.minimized_embed = self.create_minimized_embed()
        self.maximized_embed = self.create_maximized_embed()
        self.create_profile_buttons()

    def create_profile_buttons(self):
        try:
            link_riot_id = self.riot_id.replace("#","-")
            encoded_riot_id = urllib.parse.quote(link_riot_id)
            opgg_url = f"https://op.gg/lol/summoners/na/{encoded_riot_id}"
            deeplol_url = f"https://www.deeplol.gg/summoner/na/{encoded_riot_id}"
            self.add_item(
                discord.ui.Button(
                    label="OP.GG",
                    url=opgg_url,
                    style=discord.ButtonStyle.link,
                ),
            )
            self.add_item(
                discord.ui.Button(
                    label="DeepLol",
                    url=deeplol_url,
                    style=discord.ButtonStyle.link,
                ),
            )
        except Exception as e:
            logger.error(f"Failed to add profile buttons: {e}")

    def create_minimized_embed(self):
        """Creates the minimized embed with information only on the target player."""
        partial_description = extract_minimized_embed_description(
            self.ranked_data,
            self.riot_id,
        )
        if self.match_data.get("win"):
            color = discord.Color.green()
        else:
            color = discord.Color.red()
        description = partial_description + (
            f"\n{self.match_data.get('target_champion')}"
            f" ({self.match_data.get('target_kda')})"
        )
        embed = discord.Embed(
            title="Rank Update",
            description=description,
            color=color,
        )
        return embed

    def create_maximized_embed(self):
        """Creates the maximized embed with information on all players."""
        participants = self.match_data.get("participants")
        role_order = {
            "TOP": 0, #Top
            "JUNGLE": 1, #Jungle
            "MIDDLE": 2, #Mid
            "BOTTOM": 3, #ADC
            "UTILITY": 4, #Support
        }
        sorted_participants = sorted(
            participants,
            key=lambda p: (
                p["teamId"],
                role_order.get(p.get("teamPosition",""), 5),
            ),
        )
        blue_team = []
        red_team = []
        for p in sorted_participants:
            champion = p.get("championName")
            kda = f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}"
            game_name = p.get('riotIdGameName')
            tag_line = p.get('riotIdTagline')
            line = f"**{(game_name + '#' + tag_line):<10}** - {champion} ({kda})"
            if p['teamId'] == 100:
                blue_team.append(line)
            else:
                red_team.append(line)
        embed = discord.Embed(
            title="Match Summary",
            color=discord.Color.purple(),
        )
        embed.add_field(
            name="🟦 Blue Team",
            value="\n".join(blue_team),
            inline=False,
        )
        embed.add_field(
            name="🟥 Red Team",
            value="\n".join(red_team),
            inline=False,
        )
        return embed

    @discord.ui.button(
        label="Show Match Details",
        style=discord.ButtonStyle.secondary,
    )
    async def toggle_details(self, interaction, button):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            embed = self.maximized_embed
            button.label = "Show Minimized View"
        else:
            embed = self.minimized_embed
            button.label = "Show Match Summary"
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            if (
                isinstance(
                    item,
                    discord.ui.Button,
                ) and item.style != discord.ButtonStyle.link
            ):
                item.disabled = True
        if self.message:
            with contextlib.suppress(
                discord.HTTPException,
                discord.NotFound,
                discord.Forbidden,
                ):
                await self.message.edit(view=self)
        self.stop()


# Event Handlers


@bot.event
async def on_ready():
    # called when bot initially connects
    logger.info(f"✅ Bot connected as {bot.user.name} (ID: {bot.user.id})")
    if db is None:
        logger.warning("Database is not connected")


# Global Error Handler


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, I don't know that command")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"Missing arguments. Usage: !{ctx.command} '{ctx.command.signature}'",
        )
    else:
        actual_error = getattr(error, "original", error)
        if isinstance(actual_error, UserNotFoundError):
            await ctx.send(f"User Not Found: {actual_error}")
        elif isinstance(actual_error, RateLimitError):
            await ctx.send(f"Bot is busy, try again in a minute: {actual_error}")
        elif isinstance(actual_error, RiotAPIError):
            await ctx.send(f"Riot API issue: {actual_error}")
        else:
            logger.error(
                f"❌ ERROR: {actual_error}",
                exc_info=actual_error,
            )
            await ctx.send("An unexpected error occurred.")


# Command Definitions

@bot.command()
async def track(ctx, *, riot_id):
    """Adds a user to the list of users tracked by the bot.

    Usage: !track <riotid>
    Given a riotid, the bot will attempt to add the user to the bot's database,
    "tracking" the user.
    """
    if db is None:
        return await ctx.send("Database Error")
    parsed = parse_riot_id(riot_id)
    if not parsed:
        return await ctx.send(
            "Invalid input, please ensure syntax is: !track username#tagline",
        )
    username = parsed[0]
    tagline = parsed[1]
    doc_id = f"{username}#{tagline}"
    # API handling
    puuid = await get_puuid(bot.session, username, tagline, RIOT_API_KEY)
    # DB handling
    guild_id_str = str(ctx.guild.id)
    doc_ref = db.collection(TRACKED_USERS_COLLECTION).document(doc_id)
    ranked_data = await get_ranked_info(bot.session, puuid, RIOT_API_KEY)
    try:
        doc_ref.set(
            {
                "riot_id": f"{username}#{tagline}",
                "puuid": puuid,
                "tier": f"{ranked_data.get('tier')}",
                "rank": f"{ranked_data.get('rank')}",
                "LP": ranked_data.get("LP"),
                "guild_ids": firestore.ArrayUnion([guild_id_str]),
                f"server_info.{guild_id_str}": {"added_by": ctx.author.id},
            },
            merge=True,
        )
        await ctx.send(f"{doc_id} is now being tracked!")
    except Exception as e:
        logger.exception(f"❌ ERROR: tracking: {e}")
        await ctx.send("Database write failed.")
        raise e


@bot.command()
async def untrack(ctx, *, riot_id):
    """Removes a user from the list of users tracked by the bot.

    Usage: !untrack <riotid>
    Given a riotid, the bot will attempt to remove the user from the bot's database,
    "untracking" the user.
    """
    if db is None:
        return await ctx.send("Database Error")
    parsed = parse_riot_id(riot_id)
    if not parsed:
        return await ctx.send(
            "Invalid input, please ensure syntax is: !untrack username#tagline",
        )
    username = parsed[0]
    tagline = parsed[1]
    doc_id = f"{username}#{tagline}"
    # DB handling
    guild_id_str = str(ctx.guild.id)
    doc_ref = db.collection(TRACKED_USERS_COLLECTION).document(doc_id)
    try:
        doc = doc_ref.get()
        if not doc.exists:
            return await ctx.send(f"{doc_id} is not in the database.")
        data = doc.to_dict()
        guild_list = data.get("guild_ids", [])
        if guild_id_str not in guild_list:
            return await ctx.send(f"{doc_id} is not being tracked in this server.")
        guild_list.remove(guild_id_str)
        if not guild_list:
            # We are the only server left, delete the whole file
            doc_ref.delete()
            await ctx.send(f"{doc_id} is no longer tracked")
        else:
            data["guild_ids"] = guild_list
            del data[f"server_info.{guild_id_str}"]
            doc_ref.set(data)
            await ctx.send(f"{doc_id} is no longer tracked")
    except Exception as e:
        logger.exception(f"❌ ERROR: untracking: {e}")
        await ctx.send("Database update failed")


@bot.command()
async def update(ctx):
    """Manually updates ranked information of tracked users in this server.

    Usage: !update
    Triggers ranked updates for all users in the server where this command is called
    """
    if db is None:
        return await ctx.send("Database Error")
    guild_id_str = str(ctx.guild.id)
    docs = (
        db.collection(TRACKED_USERS_COLLECTION)
        .where(filter=FieldFilter("guild_ids", "array_contains", guild_id_str))
        .stream()
    )
    doc_list = list(docs)
    if not doc_list:
        return await ctx.send("No users tracked in this server. Use !track.")
    for doc in doc_list:
        old_tier = doc.get("tier")
        old_rank = doc.get("rank")
        old_lp = doc.get("LP")
        puuid = doc.get("puuid")
        data = await get_ranked_info(bot.session, puuid, RIOT_API_KEY)
        new_tier = data.get("tier")
        new_rank = data.get("rank")
        new_lp = data.get("LP")
        doc.reference.update(data)
        if old_tier == new_tier and old_rank == new_rank and old_lp == new_lp:
            continue
        riot_id = doc.get("riot_id")
        match_info = await get_recent_match_info(bot.session, puuid, RIOT_API_KEY)
        processed_match_info = extract_match_info(match_info, puuid)
        ranked_data = {
            "old_tier": old_tier,
            "old_rank": old_rank,
            "old_lp": old_lp,
            "new_tier": new_tier,
            "new_rank": new_rank,
            "new_lp": new_lp,
        }
        view = MatchDetailsView(processed_match_info, ranked_data, riot_id, puuid)
        initial_embed = view.create_minimized_embed()
        message = await ctx.send(embed=initial_embed, view=view)
        view.message = message
    return await ctx.send("Ranked information has been updated")


@bot.command(name="leaderboard", help="Prints the servers leaderboard of tracked users")
async def leaderboard(ctx):
    """Prints the servers leaderboard.

    Usage: !leaderboard
    Prints out the tracked users in order of rank from highest to lowest
    """
    if db is None:
        return await ctx.send("Database Error")
    guild_id_str = str(ctx.guild.id)
    # DB handling
    docs = (
        db.collection(TRACKED_USERS_COLLECTION)
        .where(filter=FieldFilter("guild_ids", "array_contains", guild_id_str))
        .stream()
    )
    doc_list = list(docs)
    if not doc_list:
        return await ctx.send("No users tracked in this server. Use !track.")
    leaderboard_data = []
    for doc in doc_list:
        data = doc.to_dict()
        leaderboard_data.append(
            {
                "name": data.get("riot_id"),
                "tier": data.get("tier", "UNRANKED"),
                "rank": data.get("rank", ""),
                "lp": data.get("LP", 0),
            },
        )
    leaderboard_data.sort(
        key=lambda x: (
            TIER_ORDER.get(x["tier"].upper(), -1),
            RANK_ORDER.get(x["rank"], 0),
            x["lp"],
        ),
        reverse=True,
    )
    embed = discord.Embed(
        title=f"🏆 Leaderboard for {ctx.guild.name}",
        color=discord.Color.gold(),
    )
    description = ""
    for i, player in enumerate(leaderboard_data, 1):
        if i == 1:
            rank_prefix = "🥇"
        elif i == 2:
            rank_prefix = "🥈"
        elif i == 3:
            rank_prefix = "🥉"
        else:
            rank_prefix = f"**{i}.**"
        description += (
            f"{rank_prefix} **{player['name']}** - "
            f"{player['tier']} {player['rank']} ({player['lp']} LP)\n"
        )
    embed.description = description
    await ctx.send(embed=embed)


@bot.command()
async def set_update_channel(ctx):
    """Defaults automatic rank updates to post in this channel.

    Usage: !updateshere
    Automatic rank updates will post in the channel where this bot is used.
    If this command is not used, by default the bot will simply not post
    live ranked updates.
    """
    if db is None:
        return await ctx.send("Database Error")
    doc_ref = db.collection(GUILD_CONFIG_COLLECTION).document(str(ctx.guild.id))
    try:
        doc_ref.set({"channel_id": ctx.channel.id}, merge=True)
        await ctx.send("Rank updates will now be posted in this channel")
    except Exception as e:
        logger.exception(f"❌ ERROR: setting guild config: {e}")
        await ctx.send("Database write failed.")
        raise e


# Helper Functions


def extract_minimized_embed_description(ranked_data, riot_id):
    old_tier = ranked_data.get("old_tier")
    old_rank = ranked_data.get("old_rank")
    old_lp = ranked_data.get("old_lp")
    new_tier = ranked_data.get("new_tier")
    new_rank = ranked_data.get("new_rank")
    new_lp = ranked_data.get("new_lp")
    if TIER_ORDER.get(old_tier) > TIER_ORDER.get(new_tier):
        return f"{riot_id} has DEMOTED from {old_tier} to {new_tier}"
    elif TIER_ORDER.get(old_tier) < TIER_ORDER.get(new_tier):
        return f"{riot_id} has PROMOTED from {old_tier} to {new_tier}"
    elif RANK_ORDER.get(old_rank) > RANK_ORDER.get(new_rank):
        return (
            f"{riot_id} has DEMOTED from {old_tier} {old_rank} to {new_tier} {new_rank}"
        )
    elif RANK_ORDER.get(old_rank) < RANK_ORDER.get(new_rank):
        return (
            f"{riot_id} has PROMOTED from "
            f"{old_tier} {old_rank} to {new_tier} {new_rank}"
        )
    elif old_lp > new_lp:
        return f"{riot_id} lost {old_lp - new_lp} LP"
    elif old_lp < new_lp:
        return f"{riot_id} gained {new_lp - old_lp} LP"
    else:
        # this case only happens when both old and new ranked information are identical
        return "This update should not have happened, WHOOPS!"

def bot_startup():
    try:
        bot.run(DISCORD_KEY)
    except discord.errors.LoginFailure:
        logger.exception(
            "❌ ERROR: Invalid Token detected. Please check your DISCORD_TOKEN.",
        )
    except Exception as e:
        logger.exception(f"❌ ERROR: occurred while running the bot: {e}")
