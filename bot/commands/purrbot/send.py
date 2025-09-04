import random
import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands

DATABASE = "media.db"

class GifSendCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="sendgif", description="Send a random GIF from a given category")
    @app_commands.describe(category="Category name (e.g. kiss, slap, hug)")
    async def send_gif(self, ctx: commands.Context, category: str = None):
        if not category:
            await ctx.reply("Usage (prefix): `sendgif <category>`\nUsage (slash): `/sendgif category:<name>`")
            return

        category = category.strip().lower()

        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT url FROM media WHERE category = ?",
                (category,)
            )
            results = await cursor.fetchall()

        if not results:
            await ctx.reply(f"❌ No media found for category `{category}`.")
            return

        url = random.choice(results)[0]
        await ctx.send(url)

async def setup(bot):
    await bot.add_cog(GifSendCog(bot))
