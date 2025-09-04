import discord
from discord.ext import commands

class Clean(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="clean",
        help="Cleanup the bot responses.\n\n**Usage:** `?clean [count]`"
    )
    @commands.has_permissions(manage_messages=True)
    async def clean(self, ctx, count: int = 5):
        guild_id = str(ctx.guild.id)

        # 🔒 Block if command is disabled
        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return

        # 🔒 Additional check: silent block if member has no mod permissions
        if not ctx.author.guild_permissions.manage_messages:
            return

        # ✅ Clamp count between 1 and 100
        count = max(1, min(count, 100))

        # ⏳ Fetch recent messages and filter bot's messages
        messages = [msg async for msg in ctx.channel.history(limit=100)]
        bot_msgs = [msg for msg in messages if msg.author == self.bot.user]

        if not bot_msgs:
            embed = discord.Embed(
                description=":GhostError: I couldn't find any messages to clean.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        to_delete = bot_msgs[:count]
        await ctx.channel.delete_messages(to_delete)

        embed = discord.Embed(
            description=f":GhostSuccess: Cleaned `{len(to_delete)}` bot message(s).",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, delete_after=4)

    @clean.error
    async def clean_error(self, ctx, error):
        # Only show error if it's a real mod
        if ctx.author.guild_permissions.manage_messages:
            if isinstance(error, commands.MissingPermissions):
                await ctx.send(":GhostError: You need `Manage Messages` permission.", delete_after=6)
            else:
                await ctx.send(f":GhostError: {str(error)}", delete_after=6)
        else:
            return  # Silent for members

async def setup(bot):
    await bot.add_cog(Clean(bot))
