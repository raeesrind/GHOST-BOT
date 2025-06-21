import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

class Case(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="case")
    @commands.has_permissions(manage_messages=True)
    async def case(self, ctx, case_number: int = None):
        if case_number is None:
            return await ctx.send("❌ Usage: `?case <case_number>`")

        guild_id = str(ctx.guild.id)
        logs_ref = db.collection("moderation").document(guild_id).collection("logs")

        try:
            # Search for the case
            for doc in logs_ref.stream():
                data = doc.to_dict()
                if str(data.get("case")) == str(case_number) or str(data.get("case_number")) == str(case_number):
                    # Format timestamp
                    timestamp = data.get("timestamp")
                    time_str = datetime.utcfromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M") if timestamp else "Unknown"

                    # Build styled embed
                    embed = discord.Embed(
                        description=(
                            f"**User**\n{data.get('user_tag')}\n\n"
                            f"**Moderator**\n<@{data.get('moderator_id')}>\n\n"
                            f"**Reason**\n{data.get('reason')}"
                        ),
                        color=discord.Color.purple()
                    )

                    embed.set_author(name=f"Case {case_number} | {data.get('action').capitalize()} | {data.get('user_tag')}")
                    embed.set_footer(text=f"ID: {data.get('user_id')} • {time_str}")

                    return await ctx.send(embed=embed)

            return await ctx.send(f"❌ Case #{case_number} not found.")

        except Exception as e:
            return await ctx.send(f"❌ Failed to retrieve case: `{e}`")

async def setup(bot):
    await bot.add_cog(Case(bot))
