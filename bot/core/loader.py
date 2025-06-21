# bot/core/loader.py
import os
import asyncio

async def load_cogs(bot):
    base_path = "bot/commands"
    for folder in os.listdir(base_path):
        folder_path = os.path.join(base_path, folder)
        if os.path.isdir(folder_path):
            for filename in os.listdir(folder_path):
                if filename.endswith(".py"):
                    module = f"bot.commands.{folder}.{filename[:-3]}"
                    try:
                        await bot.load_extension(module)  # ✅ Now properly awaited
                        print(f"✅ Loaded: {module}")
                    except Exception as e:
                        print(f"❌ Failed to load {module} → {e}")