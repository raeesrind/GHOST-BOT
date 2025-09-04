import discord
from discord.ext import commands

class Lockdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.guild_settings = {
            123456789012345678: {
                "lockdown_channels": [
                    987654321098765432,
                    876543210987654321
                ],
                "default_lockdown_reason": "🚨 Server lockdown activated by Admin"
            }
        }

    @commands.command(
        name="lockdown",
        help="🔒 Lock all channels defined in moderation settings.",
        description="Locks multiple channels defined in your server's dashboard or moderation settings. "
                    "Use an optional reason to display in the lockdown message.\n\n"
                    "**Usage:** `?lockdown [optional reason]`\n"
                    "**Example:** `?lockdown Spam wave in #general`"
    )
    async def lockdown(self, ctx, *, reason: str = None):
        """Lock multiple channels defined in dashboard settings, with an optional reason."""

        # ❌ Skip if command is disabled
        if ctx.command.name.lower() in self.bot.disabled_commands.get(str(ctx.guild.id), []):
            return

        # 👮 Member protection (Admin or Bot Owner required)
        is_admin = ctx.author.guild_permissions.administrator
        is_owner = await self.bot.is_owner(ctx.author)
        if not (is_admin or is_owner):
            return await ctx.message.add_reaction("⛔")

        guild_id = ctx.guild.id
        settings = self.guild_settings.get(guild_id)

        if not settings or not settings.get("lockdown_channels"):
            return await ctx.send(embed=discord.Embed(
                title="⚠️ Lockdown Failed",
                description="No lockdown channels are configured for this server.",
                color=discord.Color.orange()
            ))

        lockdown_channels = settings["lockdown_channels"]
        default_reason = settings.get("default_lockdown_reason", "🔒 Lockdown in progress")
        final_reason = reason or default_reason

        locked = []
        failed = []

        for channel_id in lockdown_channels:
            channel = ctx.guild.get_channel(channel_id)
            if not channel:
                failed.append(f"<#{channel_id}> *(not found)*")
                continue

            try:
                overwrite = channel.overwrites_for(ctx.guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite, reason=final_reason)
                locked.append(channel.mention)
            except discord.Forbidden:
                failed.append(channel.mention)

        embed = discord.Embed(
            title="🛑 Lockdown Activated",
            description=f"**Reason:** `{final_reason}`",
            color=discord.Color.dark_red()
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else discord.Embed.Empty)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/463/463612.png")

        embed.add_field(name="✅ Locked Channels", value="\n".join(locked) if locked else "*None*", inline=False)

        if failed:
            embed.add_field(name="⚠️ Failed to Lock", value="\n".join(failed), inline=False)

        embed.set_footer(text=f"Triggered by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Lockdown(bot))
