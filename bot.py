import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from utils import collect_league_data

# API Keys
load_dotenv()
DISCORD_KEY = os.getenv("DISCORD_PUBLIC_KEY")
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

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

@bot.event
async def on_command_error(ctx, error):
    #handles errors that occur when running a command
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Sorry, I don't know that command")
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


