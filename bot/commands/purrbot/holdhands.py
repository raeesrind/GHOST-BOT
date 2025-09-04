import random
import aiosqlite
import discord
from discord.ext import commands

DATABASE = "media.db"

class Handholds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="holdhand", help="Hold hands with someone (with permission 🤝)")
    async def handholds(self, ctx: commands.Context, *, arg: str = None):
        # ✅ Restrict to the configured ship channel
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

        # Check if replied message
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
            await ctx.reply("❌ Please mention someone or reply to their message to hold hands.")
            return

        if member.bot:
            consent = True
        else:
            embed = discord.Embed(
                title=f"Hey {member.display_name} 🤝",
                description=(
                    f"**{ctx.author.display_name}** wants to hold your hands. Do you want that too?\n"
                    f"Click on ✅ to accept or ❌ to deny the request.\n\n"
                    f"> **This Request will time out after 1 Minute!**"
                ),
                color=discord.Color.blurple()
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
                    await ctx.reply(
                        f"**{member.display_name}** doesn't wanna hold your hands.\n"
                        f"**God gave you two hands, you can hold your own hand.**"
                    )
                    return
            except:
                await ctx.reply(
                    f" Your request timed out.\n{ctx.author.mention} **{member.display_name}** don't have time for you."
                )
                return

        # Get random gif from correct category
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT url FROM media WHERE category = 'holdhands'")
            results = await cursor.fetchall()

        if not results:
            await ctx.reply("❌ No holdhands gifs found in database.")
            return

        gif_url = random.choice(results)[0]

        embed = discord.Embed(
            description=f"**{ctx.author.display_name}** holds hands with **{member.display_name}** 🤝",
            color=discord.Color.blurple()
        )
        embed.set_image(url=gif_url)

        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(Handholds(bot))
