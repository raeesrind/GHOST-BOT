import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

class EditWarn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="editwarn")
    @commands.has_permissions(manage_messages=True)
    async def editwarn(self, ctx, member: discord.Member = None, warn_number: int = None, *, new_reason: str = None):
        if not member or not warn_number or not new_reason:
            embed = discord.Embed(
                title="✏️ Edit Warning",
                description="Edit a user's previous warning reason.\n\n"
                            "**Usage:**\n"
                            "`?editwarn @user <warn_number> <new_reason>`\n\n"
                            "**Example:**\n"
                            "`?editwarn @nakibingariya 2 Apologized and promised to follow rules`",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        warnings_ref = db.collection("infractions").document(guild_id).collection("users").document(user_id)

        try:
            doc = warnings_ref.get()
            if not doc.exists or "warnings" not in doc.to_dict():
                return await ctx.send(f"⚠️ No warnings found for {member.mention}.")

            warnings = doc.to_dict()["warnings"]

            index = warn_number - 1  # 1-based indexing

            if index < 0 or index >= len(warnings):
                return await ctx.send(f"❌ Warning #{warn_number} does not exist for {member.mention}.")

            old_reason = warnings[index]["reason"]
            warnings[index]["reason"] = new_reason
            warnings[index]["edited_at"] = datetime.utcnow().isoformat()

            warnings_ref.set({"warnings": warnings}, merge=True)

            embed = discord.Embed(
                title="⚠️ Warning Edited",
                color=discord.Color.orange()
            )
            embed.add_field(name="User", value=member.mention, inline=True)
            embed.add_field(name="Warning #", value=warn_number, inline=True)
            embed.add_field(name="Old Reason", value=old_reason, inline=False)
            embed.add_field(name="New Reason", value=new_reason, inline=False)
            embed.set_footer(text=f"Edited by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

            try:
                await member.send(
                    f"⚠️ Your warning #{warn_number} in **{ctx.guild.name}** has been edited.\n"
                    f"**New Reason:** {new_reason}"
                )
            except discord.Forbidden:
                pass

        except Exception as e:
            await ctx.send(f"❌ Firestore error: {e}")

async def setup(bot):
    await bot.add_cog(EditWarn(bot))
