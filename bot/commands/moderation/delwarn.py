import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

class DelWarn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="delwarn")
    @commands.has_permissions(manage_messages=True)
    async def delwarn(self, ctx, member: discord.Member = None, index: int = None):
        # If required arguments are missing, show usage guide
        if member is None or index is None:
            usage_embed = discord.Embed(
                title="❗ DelWarn Command Usage",
                description=(
                    "**Usage:** `?delwarn @user <warning number>`\n"
                    "Example: `?delwarn @John 2`\n\n"
                    "Use `?warnings @user` to view the list of warnings and their numbers."
                ),
                color=discord.Color.red()
            )
            return await ctx.send(embed=usage_embed)

        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        warnings_ref = db.collection("infractions").document(guild_id).collection("users").document(user_id)

        doc = warnings_ref.get()

        if not doc.exists:
            return await ctx.send(f"❌ No warnings found for {member.mention}.")

        warnings = doc.to_dict().get("warnings", [])

        if index < 1 or index > len(warnings):
            return await ctx.send(f"❌ Invalid warning index. Use `?warnings {member.mention}` to see available warnings.")

        # Remove the specific warning (1-based index)
        removed_warning = warnings.pop(index - 1)
        warnings_ref.set({"warnings": warnings}, merge=True)

        # Confirmation embed
        embed = discord.Embed(
            title="⚠️ Warning Removed",
            description=(
                f"**User:** {member.mention}\n"
                f"**Moderator:** {ctx.author.mention}\n"
                f"**Removed Warning Reason:** {removed_warning['reason']}"
            ),
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

        # Try to DM the user
        try:
            await member.send(
                f"A warning has been removed from your record in **{ctx.guild.name}**.\n"
                f"**Removed Reason:** {removed_warning['reason']}"
            )
        except discord.Forbidden:
            pass

        # Log the removal to audit logs
        logs_ref = db.collection("logs").document(guild_id).collection("moderation").document()
        logs_ref.set({
            "user_id": member.id,
            "user_tag": str(member),
            "moderator_id": ctx.author.id,
            "moderator_tag": str(ctx.author),
            "reason": removed_warning['reason'],
            "action": "delwarn",
            "timestamp": datetime.utcnow().isoformat()
        })

async def setup(bot):
    await bot.add_cog(DelWarn(bot))
