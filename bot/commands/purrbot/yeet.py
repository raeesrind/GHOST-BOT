import random
import aiosqlite
import discord
from discord.ext import commands

DATABASE = "media.db"

class Yeet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="yeet", help="Yeet someone using a random gif 🌀")
    async def yeet(self, ctx: commands.Context, *, arg: str = None):
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

        # Get member from reply
        ref = ctx.message.reference
        if ref:
            try:
                replied_msg = await ctx.channel.fetch_message(ref.message_id)
                member = replied_msg.author
            except:
                pass

        # Or from mention
        if not member and ctx.message.mentions:
            member = ctx.message.mentions[0]

        if not member:
            await ctx.reply("❌ Please mention someone or reply to their message to yeet.")
            return

        # Get gif from 'yeet' category
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT url FROM media WHERE category = 'yeet'")
            results = await cursor.fetchall()

        if not results:
            await ctx.reply("❌ No yeet gifs found in database.")
            return

        gif_url = random.choice(results)[0]

        embed = discord.Embed(
            description=f"**{ctx.author.display_name}** Yeets you **{member.display_name}** ",
            color=discord.Color.teal()
        )
        embed.set_image(url=gif_url)

        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Yeet(bot))
