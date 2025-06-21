# bot/main.py

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from bot.core.loader import load_cogs
from firebase.config import init_firebase
import asyncio

load_dotenv(dotenv_path="./config/.env")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=os.getenv("BOT_PREFIX", "?"), intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

async def main():
    db = init_firebase()         # ✅ Initialize Firebase
    bot.db = db                  # ✅ Attach Firestore db instance to bot

    await load_cogs(bot)         # ✅ Load all modular cogs

    try:
        await bot.start(os.getenv("DISCORD_TOKEN"))
    finally:
        await bot.close()

def run_bot():
    asyncio.run(main())
