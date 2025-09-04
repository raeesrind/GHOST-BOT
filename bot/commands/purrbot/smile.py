import random
import aiosqlite
import discord
from discord.ext import commands

DATABASE = "media.db"

class Smile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="smile", help="Smile solo or at someone using a random gif 😊")
    async def smile(self, ctx: commands.Context, *, arg: str = None):
        # ✅ Restrict to ship channel
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT ship_channel_id FROM purrbot_settings WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    allowed_channel_id = row[0]
                    if ctx.channel.id != allowed_channel_id:
                        return #await ctx.send("❌ You can only use this command in the configured ship channel.")
                else:
                    return await ctx.send("❌ No ship channel set. Use `?setship #channel` first.")

        member = None

        # Check reply
        ref = ctx.message.reference
        if ref:
            try:
                replied_msg = await ctx.channel.fetch_message(ref.message_id)
                member = replied_msg.author
            except:
                pass

        # Or mention
        if not member and ctx.message.mentions:
            member = ctx.message.mentions[0]

        # Fetch random gif from 'smile' category
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT url FROM media WHERE category = 'smile'")
            results = await cursor.fetchall()

        if not results:
            await ctx.reply("❌ No smile gifs found in database.")
            return

        gif_url = random.choice(results)[0]

        # Description
        desc = f"**{ctx.author.display_name}** is smiling "

        embed = discord.Embed(
            description=desc,
            color=discord.Color.green()
        )
        embed.set_image(url=gif_url)

        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Smile(bot))
