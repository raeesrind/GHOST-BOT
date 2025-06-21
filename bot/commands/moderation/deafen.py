import discord
from discord.ext import commands

class VoiceModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="deafen")
    @commands.has_permissions(deafen_members=True)
    async def deafen(self, ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
        """Deafen a member in a voice channel."""
        # Help embed if user not mentioned
        if not member:
            embed = discord.Embed(
                title="Command: ?deafen",
                description=(
                    "**Description:** Deafen a member\n"
                    "**Cooldown:** 3 seconds\n\n"
                    "**Usage:**\n"
                    "`?deafen [user]`\n"
                    "**Example:**\n"
                    "`?deafen @NoobLance`"
                ),
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        # Check if the target user is in a voice channel
        if not member.voice or not member.voice.channel:
            return await ctx.send(embed=discord.Embed(
                title="❌ User Not in Voice Channel",
                description=f"{member.mention} is not connected to any voice channel.",
                color=discord.Color.red()
            ))

        # Allow bot owner and admins to bypass permissions check
        if not ctx.author.guild_permissions.deafen_members:
            app = await ctx.bot.application_info()
            if ctx.author.id != app.owner.id and not ctx.author.guild_permissions.administrator:
                return await ctx.send(embed=discord.Embed(
                    title="⛔ You don't have permission to use this command.",
                    color=discord.Color.red()
                ))

        # Try to deafen the user
        try:
            await member.edit(deafen=True, reason=reason)
            embed = discord.Embed(
                title="🔇 Member Deafened",
                description=f"{member.mention} has been deafened.\n**Reason:** {reason}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"By {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(
                title="⛔ Permission Denied",
                description="I don't have permission to deafen this member.",
                color=discord.Color.red()
            ))

async def setup(bot):
    await bot.add_cog(VoiceModeration(bot))
