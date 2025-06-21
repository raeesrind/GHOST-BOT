import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

class ClearWarn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clearwarn")
    @commands.has_permissions(manage_messages=True)
    async def clearwarn(self, ctx, member: discord.Member = None):
        if member is None:
            usage = (
                "**Usage:** `?clearwarn @user`\n"
                "Example: `?clearwarn @John`\n\n"
                "This will delete all stored warnings for the mentioned user."
            )
            return await ctx.send(embed=discord.Embed(description=usage, color=discord.Color.red()))

        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        warnings_ref = db.collection("infractions").document(guild_id).collection("users").document(user_id)

        try:
            doc = warnings_ref.get()
            if not doc.exists or not doc.to_dict().get("warnings"):
                return await ctx.send(embed=discord.Embed(
                    description=f"⚠️ **{member.mention} has no warnings to clear.**",
                    color=discord.Color.orange()
                ))

            # Clear all warnings
            warnings_ref.set({"warnings": []}, merge=True)

            # Confirmation embed
            embed = discord.Embed(
                description=f"✅ **All warnings for {member.mention} have been cleared.**",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

            # Log the action
            logs_ref = db.collection("logs").document(guild_id).collection("moderation").document()
            logs_ref.set({
                "user_id": member.id,
                "user_tag": str(member),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": "All warnings cleared",
                "action": "clearwarn",
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            await ctx.send(f"❌ Firestore error: {e}")

async def setup(bot):
    await bot.add_cog(ClearWarn(bot))
