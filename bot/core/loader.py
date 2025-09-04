import os
import asyncio

async def load_cogs(bot):
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../commands")
    base_path = os.path.abspath(base_path)
    print(f"📁 Loading cogs from: {base_path}")

    for folder in os.listdir(base_path):
        folder_path = os.path.join(base_path, folder)
        if os.path.isdir(folder_path):
            for filename in os.listdir(folder_path):
                if filename.endswith(".py") and not filename.startswith("__"):
                    module = f"bot.commands.{folder}.{filename[:-3]}"
                    
                    if module in bot.extensions:
                        print(f"⚠️  Skipping duplicate load: {module} (already loaded)")
                        continue
                    
                    try:
                        await bot.load_extension(module)
                        print(f"✅ Loaded: {module}")
                    except Exception as e:
                        print(f"❌ Failed to load {module} → {e}")

    print("\n🧠 [COG DEBUG] Loaded Cogs:")
    for cog_name in bot.cogs:
        print(f"  - {cog_name}")

    print("\n🧠 [COMMAND DEBUG] Loaded Commands:")
    for cmd in bot.commands:
        print(f"  - {cmd.name}  ({type(cmd).__name__})")

    print(
        f"\n✅ All cogs loaded → total cogs: {len(bot.cogs)} | "
        f"total commands: {len(bot.commands)}"
    )
