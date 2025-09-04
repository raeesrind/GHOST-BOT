import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

class Case(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="case", help="Retrieve details of a moderation case by its number.")
    @commands.has_permissions(manage_messages=True)
    async def case(self, ctx, case_number: int = None):
        guild_id = str(ctx.guild.id)

        # ✅ Block if command is disabled for this guild
        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return  # Silent block

        # ✅ Additional protection: Ignore non-mod users silently
        if not ctx.author.guild_permissions.manage_messages:
            return  # Silent block

        if case_number is None:
            embed = discord.Embed(
                title="Missing Case Number",
                description="Please provide a case number.\n\n**Usage:** `?case <case_number>`",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        logs_ref = db.collection("moderation").document(guild_id).collection("logs")

        try:
            for doc in logs_ref.stream():
                data = doc.to_dict()
                if str(data.get("case")) == str(case_number) or str(data.get("case_number")) == str(case_number):
                    timestamp = data.get("timestamp")
                    time_str = datetime.utcfromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M") if timestamp else "Unknown"

                    embed = discord.Embed(
                        title=f"Case #{case_number} | {data.get('action').capitalize()}",
                        color=discord.Color.purple()
                    )
                    embed.add_field(name="User", value=f"{data.get('user_tag')} (`{data.get('user_id')}`)", inline=False)
                    embed.add_field(name="Moderator", value=f"<@{data.get('moderator_id')}>", inline=False)
                    embed.add_field(name="Reason", value=data.get("reason") or "No reason provided", inline=False)
                    embed.set_footer(text=f"{time_str}")

                    return await ctx.send(embed=embed)

            embed = discord.Embed(
                description=f"No case with number `#{case_number}` found.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Failed to retrieve case: `{e}`",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Case(bot))
