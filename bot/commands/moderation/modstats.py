import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime, timedelta

db = firestore.client()

class ModStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="modstats")
    @commands.has_permissions(administrator=True)
    async def modstats(self, ctx):
        guild_id = str(ctx.guild.id)
        logs_ref = db.collection("moderation").document(guild_id).collection("logs")
        
        try:
            docs = logs_ref.stream()
        except Exception as e:
            return await ctx.send(f"❌ Firestore error: {e}")

        now = datetime.utcnow()
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)

        # Action counters
        counts = {
            "warn": {"7d": 0, "30d": 0, "all": 0},
            "mute": {"7d": 0, "30d": 0, "all": 0},
            "ban": {"7d": 0, "30d": 0, "all": 0},
            "kick": {"7d": 0, "30d": 0, "all": 0}
        }

        for doc in docs:
            data = doc.to_dict()
            action = data.get("action")
            timestamp = data.get("timestamp")

            if action not in counts or not timestamp:
                continue

            try:
                timestamp_dt = datetime.utcfromtimestamp(timestamp)
            except Exception:
                continue

            # All time
            counts[action]["all"] += 1
            if timestamp_dt >= last_30_days:
                counts[action]["30d"] += 1
            if timestamp_dt >= last_7_days:
                counts[action]["7d"] += 1

        # Build embed
        def fmt(label, value): return f"{label}:\n`{value}`"
        total_7d = sum(counts[a]["7d"] for a in counts)
        total_30d = sum(counts[a]["30d"] for a in counts)
        total_all = sum(counts[a]["all"] for a in counts)

        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Moderation Statistics",
            color=discord.Color.purple()
        )

        embed.add_field(name="Mutes (last 7 days)", value=counts['mute']['7d'], inline=True)
        embed.add_field(name="Mutes (last 30 days)", value=counts['mute']['30d'], inline=True)
        embed.add_field(name="Mutes (all time)", value=counts['mute']['all'], inline=True)

        embed.add_field(name="Bans (last 7 days)", value=counts['ban']['7d'], inline=True)
        embed.add_field(name="Bans (last 30 days)", value=counts['ban']['30d'], inline=True)
        embed.add_field(name="Bans (all time)", value=counts['ban']['all'], inline=True)

        embed.add_field(name="Kicks (last 7 days)", value=counts['kick']['7d'], inline=True)
        embed.add_field(name="Kicks (last 30 days)", value=counts['kick']['30d'], inline=True)
        embed.add_field(name="Kicks (all time)", value=counts['kick']['all'], inline=True)

        embed.add_field(name="Warns (last 7 days)", value=counts['warn']['7d'], inline=True)
        embed.add_field(name="Warns (last 30 days)", value=counts['warn']['30d'], inline=True)
        embed.add_field(name="Warns (all time)", value=counts['warn']['all'], inline=True)

        embed.add_field(name="Total (last 7 days)", value=total_7d, inline=True)
        embed.add_field(name="Total (last 30 days)", value=total_30d, inline=True)
        embed.add_field(name="Total (all time)", value=total_all, inline=True)

        embed.set_footer(text=f"ID: {ctx.author.id} • Today at {now.strftime('%H:%M')}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ModStats(bot))
