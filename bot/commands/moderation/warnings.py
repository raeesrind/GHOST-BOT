import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime
import humanize

db = firestore.client()

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="warnings",
        help="View all warnings issued to a member.\n\n**Usage:** `?warnings @user`\n**Example:** `?warnings @User`",
        brief="View a user's warnings"
    )
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member = None):
        if member is None:
            usage = (
                "**Usage:** `?warnings @user`\n"
                "Example: `?warnings @John`\n\n"
                "This command will display all active warnings issued to the user."
            )
            return await ctx.send(embed=discord.Embed(description=usage, color=discord.Color.red()))

        try:
            guild_id = str(ctx.guild.id)
            user_id = str(member.id)
            warnings_ref = db.collection("infractions").document(guild_id).collection("users").document(user_id)
            doc = warnings_ref.get()

            if not doc.exists or "warnings" not in doc.to_dict() or len(doc.to_dict()["warnings"]) == 0:
                embed = discord.Embed(
                    description=f":GhostSuccess: **{member.mention} has no warnings.**",
                    color=discord.Color.green()
                )
                return await ctx.send(embed=embed)

            warnings_list = doc.to_dict()["warnings"]
            embed = discord.Embed(
                title=f"⚠️ Warnings for {member}",
                color=discord.Color.orange()
            )

            for i, warn in enumerate(warnings_list, 1):
                timestamp = datetime.fromisoformat(warn["timestamp"])
                time_ago = humanize.naturaltime(datetime.utcnow() - timestamp)
                moderator = warn.get("moderator_name", f"<@{warn['moderator_id']}>") or "Unknown"

                embed.add_field(
                    name=f"#{i} • {time_ago}",
                    value=f"**Reason:** {warn['reason']}\n**Moderator:** {moderator}",
                    inline=False
                )

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f":GhostError: Error retrieving warnings: `{e}`")

async def setup(bot):
    await bot.add_cog(Warnings(bot))
