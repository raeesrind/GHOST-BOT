import random
import aiosqlite
import discord
from discord.ext import commands

DATABASE = "media.db"

class Dance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dance", help="Dance solo or with someone using a random gif 💃🕺")
    async def dance(self, ctx: commands.Context, *, arg: str = None):
        # ✅ Restrict to the configured ship channel
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT ship_channel_id FROM purrbot_settings WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    allowed_channel_id = row[0]
                    if ctx.channel.id != allowed_channel_id:
                        return# await ctx.send("❌ You can only use this command in the configured ship channel.")
                else:
                    return await ctx.send("❌ No ship channel set. Use `?setship #channel` first.")

        member = None

        # Check if message is a reply
        ref = ctx.message.reference
        if ref:
            try:
                replied_msg = await ctx.channel.fetch_message(ref.message_id)
                member = replied_msg.author
            except:
                pass

        # Or get from mention
        if not member and ctx.message.mentions:
            member = ctx.message.mentions[0]

        # Get random gif from 'dance' category
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT url FROM media WHERE category = 'dance'")
            results = await cursor.fetchall()

        if not results:
            await ctx.reply("❌ No dance gifs found in database.")
            return

        gif_url = random.choice(results)[0]

        # Message (always solo style for simplicity)
        desc = f"**{ctx.author.display_name}** is dancing "

        embed = discord.Embed(
            description=desc,
            color=discord.Color.orange()
        )
        embed.set_image(url=gif_url)

        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Dance(bot))
