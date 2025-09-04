import random
import aiosqlite
import discord
from discord.ext import commands

DATABASE = "media.db"

class Kiss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="kiss", help="Kiss someone with their permission 💋")
    async def kiss(self, ctx: commands.Context, *, arg: str = None):
        # ✅ Restrict to ship channel if set
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
            await ctx.reply("❌ Please mention someone or reply to their message to kiss.")
            return

        if member.bot:
            consent = True  # auto-accept for bots
        else:
            embed = discord.Embed(
                title=f"Hey {member.display_name} 👀",
                description=(
                    f"**{ctx.author.display_name}** wants to kiss you. Do you want to accept it?\n"
                    f"Click on ✅ to accept or ❌ to deny the request.\n\n"
                    f"> **This request will time out after 1 minute!**"
                ),
                color=discord.Color.pink()
            )

            prompt = await ctx.reply(embed=embed)
            await prompt.add_reaction("✅")
            await prompt.add_reaction("❌")

            def check(reaction, user):
                return (
                    user.id == member.id and 
                    str(reaction.emoji) in ["✅", "❌"] and 
                    reaction.message.id == prompt.id
                )

            try:
                reaction, _ = await ctx.bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "✅":
                    consent = True
                else:
                    await ctx.reply(f"**{member.display_name}** doesn't want kiss from you **<@{ctx.author.id}>** **DIE SINGLE**")
                    return
            except:
                await ctx.reply(
                    f" Your request timed out.\n**{member.display_name}** doesn't have time for you. "
                )
                return

        # Get gif
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT url FROM media WHERE category = 'kiss'")
            results = await cursor.fetchall()

        if not results:
            await ctx.reply("❌ No kiss gifs found in database.")
            return

        gif_url = random.choice(results)[0]

        embed = discord.Embed(
            description=f"**{ctx.author.display_name}** Kisses You **{member.display_name}** 💋",
            color=discord.Color.pink()
        )
        embed.set_image(url=gif_url)

        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Kiss(bot))
