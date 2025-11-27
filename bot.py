import discord
import os
import aiohttp
from dotenv import load_dotenv
from discord.ext import commands
from firebase_admin import firestore

# Self Contained Imports
from database import database_startup
from database import TRACKED_USERS_COLLECTION
from utils import RateLimitError, RiotAPIError, UserNotFound
from utils import get_puuid

# API Keys
load_dotenv()
DISCORD_KEY = os.getenv("DISCORD_PUBLIC_KEY")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# Database Startup
db = database_startup()

# Bot Startup
BOT_PREFIX = "!"
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default() 
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix=BOT_PREFIX, intents=intents)
        self.session = None #placeholder
    async def setup_hook(self):
        #Runs once when the bot starts up.
        self.session = aiohttp.ClientSession()
        print("✅ Persistent HTTP Session created.")
    async def close(self):
        #Runs when the bot shuts down.
        if self.session:
            await self.session.close()
            print("🛑 HTTP Session closed.")
        await super().close()

bot = MyBot()

# Event Handlers
@bot.event
async def on_ready():
    #called when bot initially connects
    print(f"Bot connected as {bot.user.name} (ID: {bot.user.id}")
    if db is None:
        print("WARNING: Database is not connected")

# Global Error Handler
@bot.event
async def on_command_error(ctx, error):
    # Command not found
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, I don't know that command")
    # Missing arguments
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing arguments. Usage: '{ctx.command.signature}'")
    elif isinstance(error, commands.CommandInvokeError):
        original = error.original
        if isinstance(original, UserNotFound):
            await ctx.send(f"User Not Found: {original}")
        elif isinstance(original, RateLimitError):
            await ctx.send(f"Bot is busy, try again in a minute: {original}")
        elif isinstance(original, RiotAPIError):
            await ctx.send(f"Riot API issue: {original}")
        else:
            print(f"[CRITICAL ERROR] {original}")
            await ctx.send("An unexpected error occurred.")
    else:
        print(f"Error: {error}")

# Command Definitions
@bot.command(name="hello", help="Greets the user back.")
async def hello(ctx):
    user_name = ctx.author.display_name
    await ctx.send(f"Hello {user_name}")

@bot.command(name="track", help="Adds player to list of players tracked by bot given riotid")
async def track(ctx, *, riot_id):
    if db is None:
        return await ctx.send("Database Error")
    parsed = parse_riot_id(riot_id)
    if not parsed:
        return await ctx.send("Invalid input, please ensure syntax is: !track username#tagline")
    username = parsed[0]
    tagline = parsed[1]
    doc_id = f"{username}#{tagline}" 
    #API handling
    puuid = await get_puuid(bot.session, username, tagline, RIOT_API_KEY)
    if not puuid:
        return
    #DB handling
    guild_id_str = str(ctx.guild.id)
    doc_ref = db.collection(TRACKED_USERS_COLLECTION).document(doc_id)
    try:
        doc_ref.set({
            "riot_id": f"{username}#{tagline}",
            "puuid": puuid,
            "tier": "",
            "rank": "",
            "LP": 0,
            "guild_ids": firestore.ArrayUnion([guild_id_str]),
            f"server_info.{guild_id_str}": {
                "added_by": ctx.author.id
            }
        }, merge=True)
        await ctx.send(f"{doc_id} is now being tracked!")
    except Exception as e:
        print(f"Error tracking: {e}")
        await ctx.send("Database write failed.")
        raise e

@bot.command(name="untrack", help="Removes player from list of players tracked by bot given riotid")
async def untrack(ctx, *, riot_id):
    if db is None:
        return await ctx.send("Database Error")
    parsed = parse_riot_id(riot_id)
    if not parsed:
        return await ctx.send("Invalid input, please ensure syntax is: !untrack username#tagline")
    username = parsed[0]
    tagline = parsed[1]
    doc_id = f"{username}#{tagline}" 
    #DB handling
    guild_id_str = str(ctx.guild.id)
    doc_ref = db.collection(TRACKED_USERS_COLLECTION).document(doc_id)
    try:
        #READ
        doc = doc_ref.get()
        if not doc.exists:
            return await ctx.send(f"{doc_id} is not in the database.")
        data = doc.to_dict()
        guild_list = data.get("guild_ids",[])
        if guild_id_str not in guild_list:
            return await ctx.send(f"{doc_id} is not being tracked in this server.")
        #LOGIC
        guild_list.remove(guild_id_str)
        if not guild_list:
            #We were the only server left, delete whole file
            doc_ref.delete()
            await ctx.send(f"{doc_id} is no longer tracked")
        else:
            data["guild_ids"] = guild_list
            del data[f"server_info.{guild_id_str}"]
            doc_ref.set(data)
            await ctx.send(f"{doc_id} is no longer tracked")
    except Exception as e:
        print(f"Error untracking: {e}")
        await ctx.send("Database update failed")
        
# Helper Functions
def parse_riot_id(unclean_riot_id):
    clean_riot_id = unclean_riot_id.strip()
    if "#" not in clean_riot_id:
        return None
    parts = clean_riot_id.split("#",1)
    username = parts[0]
    tagline = parts[1]
    if not username or not tagline:
        return None
    return (username,tagline.lower()) #tagline.lower() because taglines are not case sensitive, this gaurentees we dont handle the same riotid differently
        

def bot_startup():
    try:
        bot.run(DISCORD_KEY)
    except discord.errors.LoginFailure:
        print("\n[ERROR] Invalid Token detected. Please check your DISCORD_TOKEN.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred while running the bot: {e}")


