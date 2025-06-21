from discord.ext import commands

class Balance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.balances = {}

    @commands.command()
    async def balance(self, ctx):
        user_id = str(ctx.author.id)
        balance = self.balances.get(user_id, 100)  # Default: 100
        await ctx.send(f"💰 {ctx.author.display_name}, your balance is ${balance}")

async def setup(bot):
    await bot.add_cog(Balance(bot))
