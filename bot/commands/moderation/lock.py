import discord
from discord.ext import commands, tasks
import asyncio
import re

class ChannelModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_time(self, text):
        match = re.fullmatch(r"(\d+)([smh])", text.lower())
        if not match:
            return None
        value, unit = match.groups()
        multiplier = {"s": 1, "m": 60, "h": 3600}
        return int(value) * multiplier[unit]

    @commands.command(name="lock")
    async def lock(self, ctx, channel: discord.TextChannel = None, time: str = None, *, reason: str = "No reason provided"):
        """Lock a channel with optional time auto-unlock."""

        # Check permission
        is_admin = ctx.author.guild_permissions.administrator
        is_owner = await self.bot.is_owner(ctx.author)
        if not (is_admin or is_owner):
            embed = discord.Embed(
                title="⛔ Access Denied",
                description="You must be a server administrator or the bot owner to use this command.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        # If no channel given, use current one
        if channel is None:
            channel = ctx.channel
            # If only ?lock used → show help
            if time is None:
                embed = discord.Embed(
                    title="🔒 Command: ?lock",
                    description=(
                        "**Description:** Lock a channel (optionally for a time)\n"
                        "**Cooldown:** 3 seconds\n\n"
                        "**Usage:**\n"
                        "`?lock [channel] (time) (reason)`\n"
                        "**Example:**\n"
                        "`?lock #general 10m Spamming`\n"
                        "`?lock 5m Breaking rules`"
                    ),
                    color=discord.Color.orange()
                )
                return await ctx.send(embed=embed)

        # Check if time is valid
        duration_seconds = None
        if time:
            duration_seconds = self.parse_time(time)
            if duration_seconds:
                reason = reason or "No reason provided"
            else:
                # Shift `time` into `reason` if not valid time
                reason = f"{time} {reason}".strip()
                duration_seconds = None

        # Lock the channel
        try:
            overwrite = channel.overwrites_for(ctx.guild.default_role)
            overwrite.send_messages = False
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=reason)

            embed = discord.Embed(
                title="🔒 Channel Locked",
                description=f"{channel.mention} has been locked.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason, inline=False)

            if duration_seconds:
                embed.add_field(name="Auto-Unlock", value=f"In {time}", inline=False)

            embed.set_footer(text=f"Locked by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

            # Schedule unlock if timed
            if duration_seconds:
                await asyncio.sleep(duration_seconds)
                overwrite.send_messages = None  # Reset to default
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason="Auto-unlock")
                unlock_embed = discord.Embed(
                    title="🔓 Channel Unlocked",
                    description=f"{channel.mention} has been auto-unlocked after {time}.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=unlock_embed)

        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(
                title="⛔ Permission Error",
                description="I don't have permission to lock this channel.",
                color=discord.Color.red()
            ))

async def setup(bot):
    await bot.add_cog(ChannelModeration(bot))
