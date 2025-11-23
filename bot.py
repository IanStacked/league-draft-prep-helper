import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from firebase_admin import firestore

# Self Contained Imports
from database import database_startup
from database import TRACKED_USERS_COLLECTION
from utils import collect_league_data
from utils import get_puuid

# API Keys
load_dotenv()
DISCORD_KEY = os.getenv("DISCORD_PUBLIC_KEY")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

# Database Startup
db = database_startup()

# Bot Information
BOT_PREFIX = "!"
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

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
    else:
        print(f"An unexpected error occured: {error}")

# Command Definitions
@bot.command(name="hello", help="Greets the user back.")
async def hello(ctx):
    user_name = ctx.author.display_name
    await ctx.send(f"Hello {user_name}")

@bot.command(name="scout", help="Finds information on league player given riotid")
async def scout(ctx, *, riot_id):
    riot_id_tuple = parse_riot_id(riot_id)
    if not riot_id_tuple:
        await ctx.send("Invalid input, please ensure syntax is: !scout username#tagline")
        return
    player_info = collect_league_data(RIOT_API_KEY, riot_id_tuple[0], riot_id_tuple[1])
    for champ in player_info[0]["sorted_champions_played"]:
        await ctx.send(champ)

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
    try:
        puuid = get_puuid(username, tagline, RIOT_API_KEY)
    except Exception as e:
        return await ctx.send(e)
    #DB handling
    user_data = {
        "riot_id": f"{username}#{tagline}",
        "puuid": puuid,
        "tier": "",
        "rank": "",
        "LP": 0,
        "Added By": ctx.author.display_name
    }
    try:
        db.collection(TRACKED_USERS_COLLECTION).document(doc_id).set(user_data)
        await ctx.send(f"{doc_id} is now being tracked!")
    except Exception as e:
        raise e
    
    
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
    return (username,tagline)
        

def bot_startup():
    try:
        bot.run(DISCORD_KEY)
    except discord.errors.LoginFailure:
        print("\n[ERROR] Invalid Token detected. Please check your DISCORD_TOKEN.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred while running the bot: {e}")


