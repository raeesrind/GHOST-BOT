import discord
from discord.ext import commands
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

    @commands.command(name="lock", help="Lock a channel optionally for a time.\n\n**Usage:** `?lock [channel] [duration] [reason]`\n**Example:** `?lock #general 10m Spamming`")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def lock(self, ctx, channel: discord.TextChannel = None, time: str = None, *, reason: str = "No reason provided"):
        guild_id = str(ctx.guild.id)

        # 🔒 Skip if command is disabled
        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return

        # ✅ Permission check
        if not (ctx.author.guild_permissions.administrator or await self.bot.is_owner(ctx.author)):
            embed = discord.Embed(
                title=":GhostError: Access Denied",
                description="You must be an administrator or the bot owner to use this command.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        # 📍 Use current channel if none specified
        if channel is None:
            channel = ctx.channel
            if time is None:
                embed = discord.Embed(
                    title="🔒 Command: ?lock",
                    description=(
                        "**Description:** Lock a channel (optionally with a timer).\n"
                        "**Usage:** `?lock [channel] [time] [reason]`\n"
                        "**Examples:**\n"
                        "`?lock #chat 5m Spamming`\n"
                        "`?lock 10m Rule violation`\n"
                        "`?lock #general`"
                    ),
                    color=discord.Color.orange()
                )
                return await ctx.send(embed=embed)

        # ⏳ Check if valid time
        duration_seconds = self.parse_time(time) if time else None
        if time and not duration_seconds:
            reason = f"{time} {reason}".strip()  # Treat time as part of reason
            duration_seconds = None

        # 🔐 Lock channel
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
                embed.add_field(name="Auto-Unlock", value=f"In `{time}`", inline=False)
            embed.set_footer(text=f"Locked by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

            # 🕒 Schedule unlock
            if duration_seconds:
                await asyncio.sleep(duration_seconds)
                overwrite.send_messages = None  # Reset permission
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason="Auto-unlock")

                unlock_embed = discord.Embed(
                    title="🔓 Channel Unlocked",
                    description=f"{channel.mention} has been auto-unlocked after `{time}`.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=unlock_embed)

        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(
                title=":GhostError: Missing Permissions",
                description="I don’t have permission to lock this channel.",
                color=discord.Color.red()
            ))
        except Exception as e:
            await ctx.send(f":GhostError: `{e}`")

async def setup(bot):
    await bot.add_cog(ChannelModeration(bot))
