import discord
from discord.ext import commands
from firebase_admin import firestore
from discord.utils import utcnow
from bot.utils.casecounter import get_next_case_number

db = firestore.client()

class Unmute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="unmute",
        help="Unmute a member by removing timeout and muted role.\n\n**Usage:** `?unmute @user [reason]`\n**Example:** `?unmute @User Apologized`",
        brief="Unmute a member in the server."
    )
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member = None, *, reason: str = None):
        await ctx.message.delete()
        if member is None:
            usage = (
                "**Usage:** `?unmute @user [reason]`\n"
                "**Example:** `?unmute @John Apologized for spamming`\n\n"
                "This command removes both timeout and muted role, then logs the action."
            )
            return await ctx.send(embed=discord.Embed(description=usage, color=discord.Color.purple()))

        if member == ctx.author:
            return await ctx.send(":GhostError: You can't unmute yourself.")
        if member.bot:
            return await ctx.send(":GhostError: You can't unmute bots.")
        if ctx.guild.owner_id == member.id:
            return await ctx.send(":GhostError: You can't unmute the server owner.")

        guild_id = str(ctx.guild.id)
        reason = reason or "No reason provided"

        # 🔧 Get mute role from Firestore
        guild_doc = db.collection("settings").document(guild_id)
        guild_data = guild_doc.get().to_dict() if guild_doc.get().exists else {}
        mute_role_id = guild_data.get("mute_role_id")
        mute_role = ctx.guild.get_role(int(mute_role_id)) if mute_role_id else None

        try:
            # Step 1: Remove timeout
            if member.timed_out_until:
                try:
                    await member.timeout(None, reason=reason)
                except discord.Forbidden:
                    await ctx.send("⚠️ Could not remove timeout (missing permissions).")

            # Step 2: Remove mute role
            if mute_role and mute_role in member.roles:
                try:
                    await member.remove_roles(mute_role, reason=reason)
                except discord.Forbidden:
                    await ctx.send("⚠️ Could not remove mute role (missing permissions).")

            # Step 3: DM user
            try:
                dm_embed = discord.Embed(
                    title=f"You have been unmuted in {ctx.guild.name}",
                    description=f"**Reason:** {reason}",
                    color=discord.Color.green()
                )
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass

            # Step 4: Confirmation in server
            response_embed = discord.Embed(
                description=f"🔊 *{member.mention} was unmuted.*",
                color=discord.Color.green()
            )
            response_embed.add_field(name="Reason", value=reason, inline=False)
            await ctx.send(embed=response_embed)

            # :GhostSuccess: Step 5: Log to Firestore with correct case field
            case_number = await get_next_case_number(guild_id)
            db.collection("moderation").document(guild_id).collection("logs").document().set({
                "case": case_number,
                "user_id": member.id,
                "user_tag": str(member),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": reason,
                "action": "unmute",
                "duration": "n/a",
                "timestamp": int(utcnow().timestamp())
            })

        except Exception as e:
            await ctx.send(f":GhostError: Unmute failed: {e}")

async def setup(bot):
    await bot.add_cog(Unmute(bot))
