import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime, timedelta, timezone

db = firestore.client()

class Moderations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="moderations")
    async def moderations(self, ctx):
        guild_id = str(ctx.guild.id)
        logs_ref = db.collection("moderation").document(guild_id).collection("logs")

        # Fetch only mute/ban entries with valid duration
        docs = logs_ref.stream()
        now = datetime.now(timezone.utc)
        active_moderations = []

        for doc in docs:
            data = doc.to_dict()
            if data["action"] not in ["mute", "ban"]:
                continue
            duration = data.get("duration")
            if not duration or duration in ["n/a", "permanent"]:
                continue
            timestamp = data.get("timestamp")
            if timestamp is None:
                continue
            start_time = datetime.fromtimestamp(timestamp, timezone.utc)

            # Parse duration
            try:
                unit = duration[-1]
                num = int(duration[:-1])
                if unit == "s":
                    delta = timedelta(seconds=num)
                elif unit == "m":
                    delta = timedelta(minutes=num)
                elif unit == "h":
                    delta = timedelta(hours=num)
                elif unit == "d":
                    delta = timedelta(days=num)
                else:
                    continue
            except:
                continue

            end_time = start_time + delta
            if end_time > now:
                remaining = end_time - now
                active_moderations.append((data["user_tag"], data["action"].capitalize(), str(remaining).split('.')[0]))

        if not active_moderations:
            embed = discord.Embed(
            description="✅ **No active timed moderations.**",
            color=discord.Color.green()
            )
            return await ctx.send(embed=embed)


        # Format output
        description = "**Active Moderations**\n"
        for i, (user_tag, action, remaining) in enumerate(active_moderations, start=1):
            description += f"{i}. {user_tag}\n{action} | ⏳ Time Remaining: {remaining}\n"

        description += f"{len(active_moderations)} active moderations"

        embed = discord.Embed(description=description, color=discord.Color.orange())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderations(bot))
