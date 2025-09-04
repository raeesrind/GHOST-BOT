import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime, timedelta

db = firestore.client()

class ModStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="modstats",
        help="📊 Shows moderation stats for you or a specific moderator.\n"
             "❌ Skips if command is disabled for the server.",
        brief="Check your or another mod's moderation activity."
    )
    async def modstats(self, ctx, member: discord.Member = None):
        # ❌ Skip if command is disabled
        if ctx.command.name.lower() in self.bot.disabled_commands.get(str(ctx.guild.id), []):
            return

        # ✅ Allow access to mods / admins / owners
        is_mod = ctx.author.guild_permissions.manage_messages
        is_admin = ctx.author.guild_permissions.administrator
        is_owner = await self.bot.is_owner(ctx.author)
        if not (is_mod or is_admin or is_owner):
            return await ctx.message.add_reaction("⛔")

        target = member or ctx.author
        guild_id = str(ctx.guild.id)
        logs_ref = db.collection("moderation").document(guild_id).collection("logs")

        try:
            docs = logs_ref.stream()
        except Exception as e:
            return await ctx.send(f":GhostError: Firestore error: {e}")

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

        mod_id = str(target.id)

        for doc in docs:
            data = doc.to_dict()
            action = data.get("action")
            timestamp = data.get("timestamp")
            moderator_id = str(data.get("moderator_id"))

            if action not in counts or not timestamp:
                continue
            if moderator_id != mod_id:
                continue

            try:
                timestamp_dt = datetime.utcfromtimestamp(timestamp)
            except Exception:
                continue

            counts[action]["all"] += 1
            if timestamp_dt >= last_30_days:
                counts[action]["30d"] += 1
            if timestamp_dt >= last_7_days:
                counts[action]["7d"] += 1

        total_7d = sum(counts[a]["7d"] for a in counts)
        total_30d = sum(counts[a]["30d"] for a in counts)
        total_all = sum(counts[a]["all"] for a in counts)

        embed = discord.Embed(
            title=f"{target.display_name}'s Moderation Statistics",
            color=discord.Color.purple(),
            timestamp=now
        )

        embed.add_field(name="Mutes (7d)", value=counts['mute']['7d'], inline=True)
        embed.add_field(name="Mutes (30d)", value=counts['mute']['30d'], inline=True)
        embed.add_field(name="Mutes (all)", value=counts['mute']['all'], inline=True)

        embed.add_field(name="Bans (7d)", value=counts['ban']['7d'], inline=True)
        embed.add_field(name="Bans (30d)", value=counts['ban']['30d'], inline=True)
        embed.add_field(name="Bans (all)", value=counts['ban']['all'], inline=True)

        embed.add_field(name="Kicks (7d)", value=counts['kick']['7d'], inline=True)
        embed.add_field(name="Kicks (30d)", value=counts['kick']['30d'], inline=True)
        embed.add_field(name="Kicks (all)", value=counts['kick']['all'], inline=True)

        embed.add_field(name="Warns (7d)", value=counts['warn']['7d'], inline=True)
        embed.add_field(name="Warns (30d)", value=counts['warn']['30d'], inline=True)
        embed.add_field(name="Warns (all)", value=counts['warn']['all'], inline=True)

        embed.add_field(name="Total (7d)", value=total_7d, inline=True)
        embed.add_field(name="Total (30d)", value=total_30d, inline=True)
        embed.add_field(name="Total (all)", value=f":GhostSuccess: {total_all}", inline=True)

        embed.set_footer(text=f"Moderator ID: {target.id} • Snapshot at {now.strftime('%H:%M UTC')}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ModStats(bot))
