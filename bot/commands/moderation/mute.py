import discord
from discord.ext import commands
from discord import app_commands
from firebase_admin import firestore
from discord.utils import utcnow
from bot.utils.taskmanager import task_manager
from bot.utils.casecounter import get_next_case_number
import asyncio
import traceback

db = firestore.client()

class Mute(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_duration(self, s):
        try:
            s = s.lower()
            if s.isdigit():
                return int(s) * 60
            unit = s[-1]
            value = int(s[:-1])
            return value * {"s": 1, "m": 60, "h": 3600, "d": 86400}.get(unit, 0)
        except:
            return None

    async def get_or_create_muted_role(self, ctx):
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if role:
            return role
        try:
            role = await ctx.guild.create_role(name="Muted", reason="Mute role for muting users")
            for channel in ctx.guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
            return role
        except Exception as e:
            await ctx.send(f"❌ Failed to create Muted role: `{e}`")
            return None

    @commands.hybrid_command(name="mute", help="Mute a user with optional duration and reason.")
    @app_commands.describe(
        target="User or ID to mute",
        duration="Duration (e.g. 10m, 2h, 1d)",
        reason="Reason for the mute"
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def mute(self, ctx, target: str = None, duration: str = None, *, reason: str = None):
        guild_id = str(ctx.guild.id)

        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return

        config_ref = db.collection("server_config").document(guild_id)
        config_data = config_ref.get().to_dict() or {}
        allowed_roles = [r.lower() for r in config_data.get("mute_roles", ["admin", "moderator", "senior mod"])]
        has_allowed_role = any(role.name.lower() in allowed_roles for role in ctx.author.roles)
        perms = ctx.author.guild_permissions
        has_permission = perms.manage_messages or perms.administrator

        if not (has_allowed_role or has_permission):
            return await ctx.send("🚫 You don't have permission to use this command.")

        if not target:
            embed = discord.Embed(
                title=":GhostError: Mute Command Help",
                description="**Usage:**\n"
                            "`?mute [user/@mention/user_id] [limit] [reason]`\n\n"
                            "**Examples:**\n"
                            "`?mute @User 10m spamming`\n"
                            "`?mute 1234567890 2d rule violation`\n"
                            "`?mute @User being rude` (permanent)",
                color=discord.Color.purple()
            )
            return await ctx.send(embed=embed)

        if ctx.message:
            try:
                await ctx.message.delete()
            except:
                pass

        member = None
        try:
            member = await commands.MemberConverter().convert(ctx, target)
        except:
            member = None

        if not member:
            embed = discord.Embed(description=":GhostError: Invalid user or ID.", color=discord.Color.red())
            return await ctx.send(embed=embed)

        if member == ctx.author or member.bot or ctx.guild.owner_id == member.id:
            return await ctx.send(embed=discord.Embed(description=":GhostError: Invalid mute target.", color=discord.Color.red()))
        if member.guild_permissions.administrator or member.guild_permissions.manage_messages:
            return await ctx.send(embed=discord.Embed(description=":GhostError: That user is protected.", color=discord.Color.red()))

        duration_seconds = self.parse_duration(duration) if duration else None
        final_reason = (reason or "No reason provided") if duration_seconds else f"{duration or ''} {reason or ''}".strip()
        duration_label = duration if duration_seconds else "permanent"

        muted_role = await self.get_or_create_muted_role(ctx)
        if not muted_role:
            return

        try:
            await member.add_roles(muted_role, reason=final_reason)
        except Exception as e:
            embed = discord.Embed(description=f":GhostError: Failed to add Muted role: `{e}`", color=discord.Color.red())
            return await ctx.send(embed=embed)

        try:
            await member.send(
                f"🔇 You were muted in **{ctx.guild.name}**.\n"
                f"**Reason:** {final_reason}\n"
                f"**Duration:** {duration_label}"
            )
        except:
            pass

        await ctx.send(embed=discord.Embed(
            description=f":GhostSuccess: **{member.name}** was muted.\n**Reason:** {final_reason}",
            color=discord.Color.blue()
        ))

        try:
            logs_ref = db.collection("moderation") \
                         .document(guild_id) \
                         .collection("logs") \
                         .document()

            case_number = await get_next_case_number(ctx.guild.id)

            logs_ref.set({
                "case": case_number,
                "user_id": member.id,
                "user_tag": str(member),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": final_reason,
                "action": "mute",
                "duration": duration_label,
                "timestamp": int(utcnow().timestamp())
            })

            if duration_seconds:
                async def unmute_later():
                    await asyncio.sleep(duration_seconds)
                    try:
                        await member.remove_roles(muted_role, reason="Temporary mute expired.")
                        try:
                            await member.send(f"🔊 You have been unmuted in **{ctx.guild.name}**.")
                        except:
                            pass
                    except Exception as e:
                        print(f"[AutoUnmute Fail] Case #{case_number} → {e}")

                task_manager.schedule(case_number, unmute_later())

        except Exception as e:
            embed = discord.Embed(description=f":GhostError: Firestore error: `{e}`", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Silently ignore unknown commands
        if isinstance(error, commands.CommandNotFound):
            return

        # Only handle errors that occurred in this cog
        if ctx.command and ctx.command.cog_name != self.__class__.__name__:
            return

        # Optional: You can still print error to console (or remove this)
        print(f"Ignored Error: {type(error).__name__}: {error}")


async def setup(bot):
    await bot.add_cog(Mute(bot))
