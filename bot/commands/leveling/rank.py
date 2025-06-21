from discord.ext import commands

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.levels = {}

    @commands.command()
    async def rank(self, ctx):
        user_id = str(ctx.author.id)
        level = self.levels.get(user_id, 1)
        await ctx.send(f"📈 {ctx.author.display_name}, you are at level {level}!")

async def setup(bot):
    await bot.add_cog(Rank(bot))
