import discord
from discord.ext import commands
from firebase_admin import firestore
from discord.utils import utcnow

db = firestore.client()

class Duration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="duration")
    @commands.has_permissions(manage_roles=True)
    async def duration(self, ctx, case_number: int = None, new_duration: str = None):
        if case_number is None or new_duration is None:
            embed = discord.Embed(
                title="Command: ?duration",
                description=(
                    "**Aliases:** ?undefined\n"
                    "**Description:** Change the duration of a mute/ban\n"
                    "**Cooldown:** 60 seconds\n\n"
                    "**Usage:**\n`?duration [modlog ID] [limit]`\n"
                    "**Example:**\n`?duration 69 420m`"
                ),
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        try:
            guild_id = str(ctx.guild.id)
            logs_ref = db.collection("moderation") \
                         .document(guild_id) \
                         .collection("logs")
            matched_doc = None

            # Search using the correct field
            for doc in logs_ref.stream():
                data = doc.to_dict()
                if data.get("case") == case_number:
                    matched_doc = doc
                    break

            if not matched_doc:
                return await ctx.send(f"❌ Case #{case_number} not found.")

            data = matched_doc.to_dict()
            action_type = data.get("action", "").lower()

            if action_type not in ["mute", "ban"]:
                embed = discord.Embed(
                    title=f"⛔ Cannot Edit Duration for Case #{case_number}",
                    description=(
                        f"That case is of type **{action_type}**, which does not support duration editing.\n"
                        "Only `mute` and `ban` cases can have durations changed."
                    ),
                    color=discord.Color.orange()
                )
                embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
                return await ctx.send(embed=embed)

            old_duration = data.get("duration", "unknown")

            data["duration"] = new_duration
            matched_doc.reference.set(data)

            embed = discord.Embed(
                title=f"✅ Duration Updated for Case #{case_number}",
                color=discord.Color.green()
            )
            embed.add_field(name="Old Duration", value=old_duration, inline=True)
            embed.add_field(name="New Duration", value=new_duration, inline=True)
            embed.set_footer(text=f"Updated by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ Failed to update duration: `{e}`")

async def setup(bot):
    await bot.add_cog(Duration(bot))
