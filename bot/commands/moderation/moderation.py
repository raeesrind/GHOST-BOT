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
        # ❌ Skip if command is disabled for this server
        if ctx.command.name.lower() in self.bot.disabled_commands.get(str(ctx.guild.id), []):
            return

        # 👮 Allow mods (manage_messages), admins, or bot owner
        is_mod = ctx.author.guild_permissions.manage_messages
        is_admin = ctx.author.guild_permissions.administrator
        is_owner = await self.bot.is_owner(ctx.author)
        if not (is_mod or is_admin or is_owner):
            return await ctx.message.add_reaction("⛔")

        guild_id = str(ctx.guild.id)
        logs_ref = db.collection("moderation").document(guild_id).collection("logs")

        docs = logs_ref.stream()
        now = datetime.now(timezone.utc)
        active_moderations = []

        for doc in docs:
            data = doc.to_dict()
            if data["action"] not in ["mute", "ban"]:
                continue
            duration = data.get("duration")
            if not duration or duration.lower() in ["n/a", "permanent"]:
                continue
            timestamp = data.get("timestamp")
            if timestamp is None:
                continue
            start_time = datetime.fromtimestamp(timestamp, timezone.utc)

            # Parse duration
            try:
                unit = duration[-1].lower()
                num = int(duration[:-1])
                delta = {
                    "s": timedelta(seconds=num),
                    "m": timedelta(minutes=num),
                    "h": timedelta(hours=num),
                    "d": timedelta(days=num)
                }.get(unit)
                if not delta:
                    continue
            except:
                continue

            end_time = start_time + delta
            if end_time > now:
                remaining = end_time - now
                active_moderations.append((data["user_tag"], data["action"].capitalize(), str(remaining).split('.')[0]))

        if not active_moderations:
            embed = discord.Embed(
                description=":GhostSuccess: **No active timed moderations.**",
                color=discord.Color.green()
            )
            return await ctx.send(embed=embed)

        # Format output
        description = "**Active Moderations**\n"
        for i, (user_tag, action, remaining) in enumerate(active_moderations, start=1):
            description += f"{i}. {user_tag}\n{action} | ⏳ Time Remaining: {remaining}\n"

        description += f"\n`{len(active_moderations)}` active moderation(s)."

        embed = discord.Embed(description=description, color=discord.Color.orange())
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderations(bot))
