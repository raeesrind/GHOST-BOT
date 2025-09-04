import discord
import asyncio
from discord.ext import commands
from discord import app_commands

class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.used = False  # one-time lock

    # Prefix Command
    @commands.command(name="bday")
    @commands.is_owner()  # only bot owner can use
    async def bday(self, ctx, member: discord.Member = None):
        if self.used:
            return await ctx.send("🎂 This command was already used to wish someone!")

        try:
            await ctx.message.delete()  # delete command immediately
        except discord.Forbidden:
            pass

        if not member:
            return await ctx.send("❌ Please mention a user: `?bday @username`")

        # Elegant animation
        animation = [
            "✦ Preparing a special message…",
            "✦ Gathering wishes from the community…",
            "✦ Wrapping everything with gratitude & respect…",
            f"✨ **Happy Birthday, {member.mention}!** ✨"
        ]

        async with ctx.typing():
            for line in animation:
                await ctx.send(line)
                await asyncio.sleep(1.5)

        # Professional Embed
        embed = discord.Embed(
            title="🌟 A Special Birthday Tribute 🌟",
            description=(
                f"Dear {member.mention},\n\n"
                "On behalf of the entire community, I want to extend heartfelt wishes "
                "for your birthday. 🎉\n\n"
                "Your vision, dedication, and leadership are the pillars that keep "
                "this community thriving. May this year bring you immense success, "
                "personal growth, and memorable moments.\n\n"
                "Thank you for building and guiding this space we celebrate not just "
                "your birthday, but also the positive impact you’ve made on all of us.\n\n"
                "Cheers to health, happiness, and new milestones ahead! 🥂"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"With respect and best wishes • From {ctx.author}")

        await ctx.send(embed=embed)
        self.used = True

    # Slash Command
    @app_commands.command(name="bday", description="Send a classy birthday tribute to someone")
    @app_commands.describe(member="The user you want to wish a happy birthday")
    async def bday_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ Only the bot owner can use this.", ephemeral=True)

        if self.used:
            return await interaction.response.send_message("🎂 This command was already used to wish someone!", ephemeral=True)

        if not member:
            return await interaction.response.send_message("❌ Please mention a user to wish!", ephemeral=True)

        await interaction.response.defer(thinking=True)

        animation = [
            "✦ Preparing a special message…",
            "✦ Gathering wishes from the community…",
            "✦ Wrapping everything with gratitude & respect…",
            f"✨ **Happy Birthday, {member.mention}!** ✨"
        ]

        for line in animation:
            await interaction.followup.send(line)
            await asyncio.sleep(1.5)

        embed = discord.Embed(
            title="🌟 A Special Birthday Tribute 🌟",
            description=(
                f"Dear {member.mention},\n\n"
                "On behalf of the entire community, I want to extend heartfelt wishes "
                "for your birthday. 🎉\n\n"
                "Your vision, dedication, and leadership are the pillars that keep "
                "this community thriving. May this year bring you immense success, "
                "personal growth, and memorable moments.\n\n"
                "Thank you for building and guiding this space—we celebrate not just "
                "your birthday, but also the positive impact you’ve made on all of us.\n\n"
                "Cheers to health, happiness, and new milestones ahead! 🥂"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"With respect and best wishes • From {interaction.user}")

        await interaction.followup.send(embed=embed)
        self.used = True


async def setup(bot):
    await bot.add_cog(Birthday(bot))
