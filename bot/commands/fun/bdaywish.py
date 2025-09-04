import discord
from discord.ext import commands
import random

class Wish(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Hybrid Command (works as both prefix + slash)
    @commands.hybrid_command(name="spamwish", description="Spam HBD wishes (Owner only)")
    @commands.is_owner()
    async def spamwish(self, ctx, member: discord.Member):
        # Delete invoking message if it's a prefix command
        if ctx.message:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass  # if bot can't delete

        # Spam wishes 10–20 times
        times = random.randint(10, 20)
        for _ in range(times):
            await ctx.send(f"🎉 Happy Birthday {member.mention}! 🥳")

async def setup(bot):
    await bot.add_cog(Wish(bot))
