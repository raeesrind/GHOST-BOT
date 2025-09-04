from discord.ext import commands
import discord 

class hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hello(self, ctx):
        await ctx.send(f"👋🏻 hello jaan,{ctx.author.display_name}!")

async def setup(bot):
    await bot.add_cog(hello(bot))