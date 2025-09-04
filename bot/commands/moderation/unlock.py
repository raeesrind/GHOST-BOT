import discord
from discord.ext import commands

class UnlockChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="unlock",
        help="Unlocks a text channel for @everyone.",
        brief="Unlock a locked text channel."
    )
    async def unlock(self, ctx, channel: discord.TextChannel = None, *, reason: str = "No reason provided"):
        """Unlock a text channel."""

        # Permission check
        is_admin = ctx.author.guild_permissions.administrator
        is_owner = await self.bot.is_owner(ctx.author)
        if not (is_admin or is_owner):
            embed = discord.Embed(
                title=":GhostError: Access Denied",
                description="You must be a server administrator or the bot owner to use this command.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        # Use current channel if none provided
        if channel is None:
            channel = ctx.channel
            if ctx.message.content.strip() == "?unlock":
                embed = discord.Embed(
                    title="🔓 Command: ?unlock",
                    description=(
                        "**Description:** Unlock a channel\n"
                        "**Cooldown:** 3 seconds\n\n"
                        "**Usage:**\n"
                        "`?unlock [channel] (reason)`\n"
                        "**Example:**\n"
                        "`?unlock #general Spamming stopped`\n"
                        "`?unlock Resolved`"
                    ),
                    color=discord.Color.orange()
                )
                return await ctx.send(embed=embed)

        # Unlock the channel
        try:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = None  # Reset to default
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=reason)

            embed = discord.Embed(
                title=":GhostSuccess: Channel Unlocked",
                description=f"{channel.mention} has been unlocked.",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text=f"Unlocked by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(
                title=":GhostError: Permission Error",
                description="I don't have permission to unlock this channel.",
                color=discord.Color.red()
            ))

async def setup(bot):
    await bot.add_cog(UnlockChannel(bot))
