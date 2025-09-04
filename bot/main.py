# bot/main.py 

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from bot.core.loader import load_cogs
from firebase.config import init_firebase
from bot.database.database import database  # ✅ Added for SQLite
import asyncio

# ✅ Load environment variables from config/.env
load_dotenv(dotenv_path="config/.env")

intents = discord.Intents.all()

# ✅ Dynamic prefix from Firestore
async def get_prefix(bot, message):
    if not message.guild:
        return "?"
    try:
        doc = bot.db.collection("settings").document(str(message.guild.id)).get()
        if doc.exists:
            return doc.to_dict().get("prefix", "?")
    except:
        pass
    return "?"

# ✅ Create bot instance
bot = commands.Bot(
    command_prefix=get_prefix,
    help_command=None,
    intents=intents
)

# ✅ Store disabled commands in memory per guild
bot.disabled_commands = {}  # {guild_id: [command names]}

# ✅ Global check to block disabled commands per server
@bot.check
async def global_command_toggle_check(ctx):
    if not ctx.guild:
        return True  # Allow in DMs

    guild_id = str(ctx.guild.id)
    command_name = ctx.command.name.lower() if ctx.command else None
    disabled = bot.disabled_commands.get(guild_id, [])

    return command_name not in disabled  # Case-insensitive check

# ✅ Error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # ✅ Silently ignore unknown commands (your request)

    if isinstance(error, commands.CheckFailure):
        return  # ✅ Silently ignore blocked commands (disabled ones)

    embed = discord.Embed(
        title="⚠️ Error",
        description=str(error),
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

# ✅ Load disabled commands when bot starts
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

    for guild in bot.guilds:
        guild_id = str(guild.id)
        doc = bot.db.collection("settings").document(guild_id).get()
        if doc.exists:
            data = doc.to_dict()
            disabled = data.get("disabled_commands", [])
            bot.disabled_commands[guild_id] = [cmd.lower() for cmd in disabled]
            print(f"🔧 {guild.name} disabled: {disabled}")
        else:
            bot.disabled_commands[guild_id] = []
            print(f"ℹ️ No disabled_commands found for {guild.name}")

    synced = await bot.tree.sync()
    print(f"🔄 Synced {len(synced)} global slash commands.")

# ✅ Main entry point
async def main():
    db = init_firebase()
    bot.db = db

    await database.connect()  # ✅ SQLite database connection here
    print("✅ Connected to ghost.db")

    await load_cogs(bot)

    try:
        await bot.start(os.getenv("DISCORD_TOKEN"))
    finally:
        await database.close()  # ✅ Clean shutdown
        await bot.close()

# ✅ Run bot
def run_bot():
    asyncio.run(main())
