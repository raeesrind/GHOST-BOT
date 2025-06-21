# bot/commands/utility/ping.py

import discord
from discord.ext import commands

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)  # convert to ms
        await ctx.send(f"Pong! {latency}ms")

# ✅ ASYNC setup required in discord.py 2.0+
async def setup(bot):
    await bot.add_cog(Ping(bot))
