import discord
from discord.ext import commands
from firebase_admin import firestore
from discord.utils import utcnow
from bot.utils.casecounter import get_next_case_number

db = firestore.client()

class VoiceDeafen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="deafen",
        help="Deafen a user in voice chat so they can't hear.\n\n"
             "**Usage:** `?deafen @user [reason]`\n"
             "**Example:** `?deafen @User Spamming in VC`",
        brief="Deafen a user in VC."
    )
    @commands.has_permissions(deafen_members=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def deafen(self, ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
        guild_id = str(ctx.guild.id)

        # 🔒 Block if command is disabled in server
        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return

        # 🔒 Silent block if user lacks permission
        if not ctx.author.guild_permissions.deafen_members:
            return

        if not member:
            embed = discord.Embed(
                title="Command: ?deafen",
                description=(
                    "**Description:** Deafen a member in voice chat.\n"
                    "**Cooldown:** 3 seconds\n\n"
                    "**Usage:**\n"
                    "`?deafen [user] [reason]`\n"
                    "**Example:**\n"
                    "`?deafen @User Being disruptive`"
                ),
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        if not member.voice or not member.voice.channel:
            return await ctx.send(embed=discord.Embed(
                title=":GhostError: User Not in Voice Channel",
                description=f"{member.mention} is not connected to any voice channel.",
                color=discord.Color.red()
            ))

        try:
            await member.edit(deafen=True, reason=reason)

            embed = discord.Embed(
                title="🔇 Member Deafened",
                description=f"{member.mention} has been deafened.\n**Reason:** {reason}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"By {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

            # Firestore logging
            case_number = await get_next_case_number(ctx.guild.id)
            logs_ref = db.collection("moderation").document(guild_id).collection("logs").document()
            logs_ref.set({
                "case": case_number,
                "user_id": member.id,
                "user_tag": str(member),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": reason,
                "action": "deafen",
                "timestamp": int(utcnow().timestamp())
            })

        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(
                title=":GhostError: Permission Denied",
                description="I don't have permission to deafen this member.",
                color=discord.Color.red()
            ))

async def setup(bot):
    await bot.add_cog(VoiceDeafen(bot))
