import discord
from discord.ext import commands
from discord import app_commands
from firebase_admin import firestore
from discord.utils import utcnow
from bot.utils.taskmanager import task_manager
from bot.utils.casecounter import get_next_case_number
import asyncio
import traceback

ERROR_LOG_CHANNEL_ID = 1398974738579198082

db = firestore.client()

class Ban(commands.Cog):
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

    @commands.hybrid_command(name="ban", help="Ban a user with optional duration and reason.")
    @app_commands.describe(
        target="User or ID to ban",
        duration="Time duration (e.g. 10m, 2h, 1d)",
        reason="Reason for the ban"
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def ban(self, ctx, target: str = None, duration: str = None, *, reason: str = None):
        guild_id = str(ctx.guild.id)

        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return

        config_ref = db.collection("server_config").document(guild_id)
        config_data = config_ref.get().to_dict() or {}
        allowed_roles = [r.lower() for r in config_data.get("ban_roles", ["admin", "moderator", "senior mod"])]
        has_allowed_role = any(role.name.lower() in allowed_roles for role in ctx.author.roles)
        perms = ctx.author.guild_permissions
        has_permission = perms.ban_members or perms.administrator

        if not (has_allowed_role or has_permission):
            return await ctx.send("🚫 You don't have permission to use this command.")

        if not target:
            embed = discord.Embed(
                title=":GhostError: Ban Command Help",
                description="**Usage:**\n"
                            "`?ban [user/@mention/user_id] [limit] [reason]`\n\n"
                            "**Examples:**\n"
                            "`?ban @User 10m spamming`\n"
                            "`?ban 1234567890 2d rule violation`\n"
                            "`?ban @User being rude` (permanent)",
                color=discord.Color.purple()
            )
            return await ctx.send(embed=embed)

        # ✅ Delete the command message (e.g. ",ban ...")
        if ctx.message:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass

        member = None
        user = None

        try:
            member = await commands.MemberConverter().convert(ctx, target)
            user = member
        except commands.errors.BadArgument:
            try:
                user = await self.bot.fetch_user(int(target))
            except (discord.NotFound, discord.HTTPException, ValueError):
                embed = discord.Embed(description=":GhostError: Invalid user or ID provided.", color=discord.Color.red())
                return await ctx.send(embed=embed)

        if member:
            if member == ctx.author:
                return await ctx.send(embed=discord.Embed(description=":GhostError: You can't ban yourself.", color=discord.Color.red()))
            if member.bot:
                return await ctx.send(embed=discord.Embed(description=":GhostError: You can't ban bots.", color=discord.Color.red()))
            if member.guild_permissions.administrator or member.guild_permissions.manage_messages:
                return await ctx.send(embed=discord.Embed(description=":GhostError: That user is protected.", color=discord.Color.red()))
            if ctx.guild.owner_id == member.id:
                return await ctx.send(embed=discord.Embed(description=":GhostError: You can't ban the server owner.", color=discord.Color.red()))

        duration_seconds = self.parse_duration(duration) if duration else None
        final_reason = (reason or "No reason provided") if duration_seconds else f"{duration or ''} {reason or ''}".strip()
        duration_label = duration if duration_seconds else "permanent"

        try:
            await user.send(embed=discord.Embed(
                title=f"You've been banned from {ctx.guild.name}",
                description=f"**Reason:** {final_reason}\n**Duration:** {duration_label}",
                color=discord.Color.red()
            ))
        except:
            pass

        try:
            await ctx.guild.ban(user, reason=final_reason)
        except Exception as e:
            log_channel = self.bot.get_channel(ERROR_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(
                   f":GhostError: Failed to ban user `{user}` by `{ctx.author}` in `{ctx.guild.name}`\n"
                   f"```py\n{e}\n```"
                )
            embed = discord.Embed(description=":GhostError: Failed to ban user. A log has been sent.", color=discord.Color.red())
            return await ctx.send(embed=embed)

        confirm = discord.Embed(
            description=f":GhostSuccess: **{user.name}** was banned.\n**Reason:** {final_reason}",
            color=discord.Color.red()
        )
        await ctx.send(embed=confirm)

        try:
            logs_ref = db.collection("moderation") \
                         .document(guild_id) \
                         .collection("logs") \
                         .document()

            case_number = await get_next_case_number(ctx.guild.id)

            logs_ref.set({
                "case": case_number,
                "user_id": user.id,
                "user_tag": str(user),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": final_reason,
                "action": "ban",
                "duration": duration_label,
                "timestamp": int(utcnow().timestamp())
            })

            if duration_seconds:
                async def unban_later():
                    await asyncio.sleep(duration_seconds)
                    try:
                        await ctx.guild.unban(user, reason="Temporary ban expired.")
                        invite = None
                        for channel in ctx.guild.text_channels:
                            if channel.permissions_for(ctx.guild.me).create_instant_invite:
                                invite = await channel.create_invite(max_uses=1, unique=True)
                                break
                        if invite:
                            try:
                                await user.send(
                                    f"🔓 You have been unbanned from **{ctx.guild.name}**.\n"
                                    f"Here is your invite link to rejoin: {invite.url}"
                                )
                            except:
                                pass
                    except Exception as e:
                        log_channel = self.bot.get_channel(ERROR_LOG_CHANNEL_ID)
                        if log_channel:
                            await log_channel.send(f":GhostError: Auto-unban failed\n```py\n{e}```")

                task_manager.schedule(case_number, unban_later())

        except Exception as e:
            log_channel = self.bot.get_channel(ERROR_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f":GhostError: Firestore logging failed\n```py\n{e}```")
            embed = discord.Embed(description=":GhostError: Firestore error. Logged to error channel.", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if ctx.command and ctx.command.cog_name != self.__class__.__name__:
            return


async def setup(bot):
    await bot.add_cog(Ban(bot))
