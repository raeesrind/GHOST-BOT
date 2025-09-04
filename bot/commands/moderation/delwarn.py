import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

class DelWarn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="delwarn", help="Delete a specific warning by its index.\n\n**Usage:** `?delwarn @user <number>`")
    @commands.has_permissions(manage_messages=True)
    async def delwarn(self, ctx, member: discord.Member = None, index: int = None):
        guild_id = str(ctx.guild.id)

        # 🔒 Silently ignore if disabled or non-mod uses
        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return
        if not ctx.author.guild_permissions.manage_messages:
            return

        if member is None or index is None:
            usage_embed = discord.Embed(
                title="Command: ?delwarn",
                description=(
                    "**Delete a specific warning for a user by number.**\n\n"
                    "**Usage:** `?delwarn @user <number>`\n"
                    "**Example:** `?delwarn @John 2`\n"
                    "Use `?warnings @user` to view warning numbers."
                ),
                color=discord.Color.orange()
            )
            return await ctx.send(embed=usage_embed)

        user_id = str(member.id)
        warnings_ref = db.collection("infractions").document(guild_id).collection("users").document(user_id)
        doc = warnings_ref.get()

        if not doc.exists:
            return await ctx.send(f":GhostError: {member.mention} has no warnings.")

        warnings = doc.to_dict().get("warnings", [])

        if index < 1 or index > len(warnings):
            return await ctx.send(
                f":GhostError: Invalid index. Use `?warnings {member.mention}` to view their warning list."
            )

        removed = warnings.pop(index - 1)
        warnings_ref.set({"warnings": warnings}, merge=True)

        embed = discord.Embed(
            title=":GhostSuccess: Warning Removed",
            description=(
                f"**User:** {member.mention}\n"
                f"**Removed By:** {ctx.author.mention}\n"
                f"**Reason:** {removed.get('reason', 'No reason')}"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

        try:
            await member.send(
                f"A warning was removed from your record in **{ctx.guild.name}**.\n"
                f"**Removed Reason:** {removed.get('reason', 'No reason')}"
            )
        except discord.Forbidden:
            pass

        # Audit log
        logs_ref = db.collection("logs").document(guild_id).collection("moderation").document()
        logs_ref.set({
            "user_id": member.id,
            "user_tag": str(member),
            "moderator_id": ctx.author.id,
            "moderator_tag": str(ctx.author),
            "reason": removed.get('reason', 'No reason'),
            "action": "delwarn",
            "timestamp": datetime.utcnow().isoformat()
        })

async def setup(bot):
    await bot.add_cog(DelWarn(bot))
