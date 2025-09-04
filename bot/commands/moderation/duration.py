import discord
from discord.ext import commands
from firebase_admin import firestore
from discord.utils import utcnow
import asyncio

from bot.utils.taskmanager import task_manager  # ✅ Task scheduler

db = firestore.client()

class Duration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="duration", help="Update duration of mute/ban.\n\n**Usage:** `?duration <case_number> <new_duration>`")
    @commands.has_permissions(manage_roles=True)
    async def duration(self, ctx, case_number: int = None, new_duration: str = None):
        guild_id = str(ctx.guild.id)

        # 🔒 Silently ignore if disabled or non-mod uses
        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return
        if not ctx.author.guild_permissions.manage_roles:
            return

        if case_number is None or new_duration is None:
            embed = discord.Embed(
                title="Command: ?duration",
                description=(
                    "**Update the duration for a mute or ban case.**\n\n"
                    "**Usage:** `?duration <case_number> <time>`\n"
                    "**Examples:** `?duration 101 2d`, `?duration 5 30m`"
                ),
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        try:
            logs_ref = db.collection("moderation").document(guild_id).collection("logs")
            matched_doc = None

            for doc in logs_ref.stream():
                data = doc.to_dict()
                if data.get("case") == case_number:
                    matched_doc = doc
                    break

            if not matched_doc:
                embed = discord.Embed(
                    title="Case Not Found",
                    description=f"Case `#{case_number}` does not exist in the database.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)

            data = matched_doc.to_dict()
            action = data.get("action", "").lower()

            if action not in ["mute", "ban"]:
                embed = discord.Embed(
                    title=f"Unsupported Action: {action}",
                    description="Only `mute` and `ban` cases can have durations changed.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
                return await ctx.send(embed=embed)

            old_duration = data.get("duration", "Unknown")
            data["duration"] = new_duration
            matched_doc.reference.set(data)

            try:
                unit = new_duration[-1].lower()
                value = int(new_duration[:-1])
                seconds = {"s": value, "m": value * 60, "h": value * 3600, "d": value * 86400}.get(unit)

                if seconds:
                    timestamp = data.get("timestamp")
                    elapsed = int(utcnow().timestamp()) - int(timestamp)
                    remaining = seconds - elapsed

                    if remaining > 0:
                        async def delayed_unpunish():
                            await asyncio.sleep(remaining)
                            guild = ctx.guild
                            if action == "ban":
                                try:
                                    user = await self.bot.fetch_user(data["user_id"])
                                    await guild.unban(user, reason="Auto-unban (duration updated)")
                                except Exception as e:
                                    print(f"[AutoUnban Fail] Case #{case_number} → {e}")
                            elif action == "mute":
                                member = guild.get_member(data["user_id"])
                                if member:
                                    muted_role = discord.utils.get(guild.roles, name="Muted")
                                    if muted_role and muted_role in member.roles:
                                        try:
                                            await member.remove_roles(muted_role, reason="Auto-unmute (duration updated)")
                                        except Exception as e:
                                            print(f"[AutoUnmute Fail] Case #{case_number} → {e}")

                        task_manager.schedule(case_number, delayed_unpunish())

            except Exception as e:
                print(f"[Duration Update Error] Case #{case_number}: {e}")

            embed = discord.Embed(
                title=f"Duration Updated - Case #{case_number}",
                color=discord.Color.green()
            )
            embed.add_field(name="Old Duration", value=old_duration, inline=True)
            embed.add_field(name="New Duration", value=new_duration, inline=True)
            embed.set_footer(text=f"Updated by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="Failed to Update Duration",
                description=f"Error: `{e}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Duration(bot))
