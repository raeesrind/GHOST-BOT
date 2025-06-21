import discord
from discord.ext import commands

class Clean(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clean", help="Cleanup the bot responses.\nUsage: ?clean [count]")
    @commands.has_permissions(manage_messages=True)
    async def clean(self, ctx, count: int = 5):
        # Limit count between 1 and 100
        count = max(1, min(count, 100))

        # Fetch messages using async for (no .flatten in discord.py 2.x)
        messages = [msg async for msg in ctx.channel.history(limit=100)]
        bot_msgs = [msg for msg in messages if msg.author == self.bot.user]

        if not bot_msgs:
            embed = discord.Embed(
                description=":dynoError: I couldn't find any messages to clean.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        # Select only the number of messages requested
        to_delete = bot_msgs[:count]
        await ctx.channel.delete_messages(to_delete)

        await ctx.send(
            embed=discord.Embed(
                description=f"✅ Cleaned `{len(to_delete)}` bot message(s).",
                color=discord.Color.green()
            ),
            delete_after=4
        )

    @clean.error
    async def clean_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need `Manage Messages` permission.", delete_after=6)
        else:
            await ctx.send(f"⚠️ Error: {str(error)}", delete_after=6)

async def setup(bot):
    await bot.add_cog(Clean(bot))
