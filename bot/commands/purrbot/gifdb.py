import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands

DATABASE = "media.db"
VALID_EXTENSIONS = (".gif", ".mp4", ".png", ".jpg", ".jpeg")

class GifCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def init_db(self):
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    url TEXT NOT NULL,
                    filetype TEXT NOT NULL
                );
            """)
            await db.commit()
        print("[✓] media table created or already exists.")

    async def __cog_load__(self):
        await self.init_db()

    @commands.hybrid_command(name="extractgifs", description="Store media links from a replied message under a category")
    @commands.is_owner()
    @app_commands.describe(category="Category name (e.g. kiss, hug, slap)")
    async def extract_gifs(self, ctx: commands.Context, category: str = None):
        if not category:
            await ctx.reply("Usage (prefix): `extractgifs <category>`\nUsage (slash): `/extractgifs category:<name>`")
            return

        category = category.strip().lower()
        expected_channel_name = f"{category}-gifs"
        if ctx.channel.name != expected_channel_name:
            await ctx.reply(f"❌ This command must be used in the `#{expected_channel_name}` channel.")
            return

        # Grab the message being replied to
        ref_msg = ctx.message.reference
        if not ref_msg:
            await ctx.reply("❌ Please reply to a message that has media files to extract.")
            return

        try:
            target_msg = await ctx.channel.fetch_message(ref_msg.message_id)
        except:
            await ctx.reply("❌ Failed to fetch the replied message.")
            return

        attachments = target_msg.attachments
        if not attachments:
            await ctx.reply("❌ The replied message has no media attachments.")
            return

        files_added = 0
        async with aiosqlite.connect(DATABASE) as db:
            for att in attachments:
                ext = att.filename.split('.')[-1].lower()
                if not att.filename.lower().endswith(VALID_EXTENSIONS):
                    continue

                # Avoid duplicates
                cursor = await db.execute("SELECT 1 FROM media WHERE url = ?", (att.url,))
                if await cursor.fetchone():
                    continue

                await db.execute(
                    "INSERT INTO media (category, url, filetype) VALUES (?, ?, ?)",
                    (category, att.url, ext)
                )
                files_added += 1

            await db.commit()

        await ctx.reply(f"✅ Stored `{files_added}` media links under `{category}` category.")

async def setup(bot):
    await bot.add_cog(GifCog(bot))
