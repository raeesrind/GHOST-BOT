import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import timedelta
from discord.utils import utcnow
import asyncio

from bot.utils.casecounter import get_next_case_number  # ✅ Added import


db = firestore.client()

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_duration(self, s):
        try:
            unit = s[-1].lower()
            value = int(s[:-1])
            if unit == 's':
                return value
            elif unit == 'm':
                return value * 60
            elif unit == 'h':
                return value * 3600
            elif unit == 'd':
                return value * 86400
        except:
            return None

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def ban(self, ctx, target=None, maybe_duration=None, *, rest: str = None):
        await ctx.message.delete()
        if not target:
            embed = discord.Embed(
                title="Ban Command Help",
                description="**Command:** ?ban\n"
                            "**Description:** Ban a member or user ID from the server.\n"
                            "**Cooldown:** 3 seconds\n\n"
                            "**Usage:**\n"
                            "?ban [user/@mention/user_id] [limit] [reason]\n\n"
                            "**Examples:**\n"
                            "?ban @NoobLance 10 Spamming\n"
                            "?ban 123456789012345678 1d Alt account\n"
                            "?ban @NoobLance\n"
                            "?ban @NoobLance spamming memes",
                color=discord.Color.purple()
            )
            return await ctx.send(embed=embed)

        member = None
        user = None
        try:
            member = await commands.MemberConverter().convert(ctx, target)
            user = member
        except:
            try:
                user = await self.bot.fetch_user(int(target))
            except:
                return await ctx.send("❌ Invalid user or user ID.")

        # ⛔ Self/owner/bot protection
        if member and member == ctx.author:
            return await ctx.send("❌ You can't ban yourself.")
        if member and member.bot:
            return await ctx.send("❌ You can't ban bots.")
        if member and ctx.guild.owner_id == member.id:
            return await ctx.send("❌ You can't ban the server owner.")

        # 🔒 Protected user check (admin or mod)
        if member and (member.guild_permissions.administrator or member.guild_permissions.manage_messages):
            embed = discord.Embed(
                description="❌ That user is protected, I can't do that.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        # Parse duration and reason
        duration_seconds = self.parse_duration(maybe_duration)
        if duration_seconds is None:
            reason = f"{maybe_duration or ''} {rest or ''}".strip()
            duration_label = "permanent"
        else:
            reason = rest or "No reason provided"
            duration_label = maybe_duration

        # DM embed
        try:
            dm_embed = discord.Embed(
                title=f"You've been banned from {ctx.guild.name}",
                description=f"**Reason:** {reason or 'No reason provided'}\n"
                            f"**Duration:** {duration_label}",
                color=discord.Color.red()
            )
            await user.send(embed=dm_embed)
        except:
            pass  # DM failed

        # Ban action
        try:
            await ctx.guild.ban(user, reason=reason)
        except Exception as e:
            return await ctx.send(f"❌ Failed to ban user: {e}")

        # Confirmation
        response_embed = discord.Embed(
            description=f"✅ *{user.name} was banned.* | {reason or 'No reason provided'}",
            color=discord.Color.red()
        )
        await ctx.send(embed=response_embed)

        # Firestore logging
        try:
            logs_ref = db.collection("moderation") \
                         .document(str(ctx.guild.id)) \
                         .collection("logs") \
                         .document()
            
            case_number = await get_next_case_number(ctx.guild.id)  # ✅ Fetch case number
            
            logs_ref.set({
                "case": case_number,  # ✅ Store the case number
                "user_id": user.id,
                "user_tag": str(user),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": reason or "No reason provided",
                "action": "ban",
                "duration": duration_label,
                "timestamp": int(utcnow().timestamp())
            })
        except Exception as e:
            await ctx.send(f"❌ Firestore error: {e}")

        # ⏱️ Schedule auto-unban
        if duration_seconds:
            async def unban_later():
                await asyncio.sleep(duration_seconds)
                try:
                    await ctx.guild.unban(user, reason="Temporary ban expired.")
                    # Optional: notify log channel or moderator
                except:
                    pass  # Already unbanned or failed

            asyncio.create_task(unban_later())

async def setup(bot):
    await bot.add_cog(Ban(bot))


