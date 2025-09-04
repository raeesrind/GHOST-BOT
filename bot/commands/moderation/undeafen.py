import discord
from discord.ext import commands
from firebase_admin import firestore
from discord.utils import utcnow
from bot.utils.casecounter import get_next_case_number

db = firestore.client()

class VoiceModeration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="undeafen",
        help="Un-deafen a user so they can hear in voice chat again.\n\n**Usage:** `?undeafen @user [reason]`\n**Example:** `?undeafen @User mistake ban`",
        brief="Un-deafen a user in VC."
    )
    @commands.has_permissions(deafen_members=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def undeafen(self, ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
        if not member:
            embed = discord.Embed(
                title="Command: ?undeafen",
                description=(
                    "**Description:** Un-deafen a member in voice chat.\n"
                    "**Cooldown:** 3 seconds\n\n"
                    "**Usage:**\n"
                    "`?undeafen [user]`\n"
                    "**Example:**\n"
                    "`?undeafen @User`"
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
            await member.edit(deafen=False, reason=reason)
            embed = discord.Embed(
                title="🔊 Member Un-Deafened",
                description=f"{member.mention} has been un-deafened.\n**Reason:** {reason}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"By {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

            # Firestore log
            case_number = await get_next_case_number(ctx.guild.id)
            logs_ref = db.collection("moderation").document(str(ctx.guild.id)).collection("logs").document()
            logs_ref.set({
                "case": case_number,
                "user_id": member.id,
                "user_tag": str(member),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": reason,
                "action": "undeafen",
                "timestamp": int(utcnow().timestamp())
            })

        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(
                title=":GhostError: Permission Denied",
                description="I don't have permission to un-deafen this member.",
                color=discord.Color.red()
            ))

async def setup(bot):
    await bot.add_cog(VoiceModeration(bot))
