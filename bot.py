import discord
import os
from dotenv import load_dotenv
from discord.ext import commands

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

def bot_startup():
    load_dotenv()
    DISCORD_KEY = os.getenv("DISCORD_PUBLIC_KEY")
    try:
        bot.run(DISCORD_KEY)
    except discord.errors.LoginFailure:
        print("\n[ERROR] Invalid Token detected. Please check your DISCORD_TOKEN.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred while running the bot: {e}")


