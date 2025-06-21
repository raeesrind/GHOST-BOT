import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import timedelta
from discord.utils import utcnow
from bot.utils.casecounter import get_next_case_number  # ✅ Added import

db = firestore.client()

class Mute(commands.Cog):
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

    async def resolve_member(self, ctx, arg):
        # Try mention or ID
        try:
            member = await commands.MemberConverter().convert(ctx, arg)
            return member
        except:
            pass

        # Try to find by username
        for member in ctx.guild.members:
            if member.name.lower() == arg.lower() or f"{member.name}#{member.discriminator}" == arg:
                return member

        return None

    @commands.command(name="mute")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def mute(self, ctx, member_arg: str = None, maybe_duration: str = None, *, rest: str = None):
        await ctx.message.delete()
        if not member_arg:
            embed = discord.Embed(
                title="Mute Command Help",
                description="**Command:** ?mute\n"
                            "**Description:** Mute a member so they cannot type.\n"
                            "**Cooldown:** 3 seconds\n\n"
                            "**Usage:**\n"
                            "?mute [user] [limit] [reason]\n\n"
                            "**Examples:**\n"
                            "?mute @User 10m spamming\n"
                            "?mute 1234567890 being rude\n"
                            "?mute username#1234 5h excessive pinging\n"
                            "?mute @User spamming (perm mute)",
                color=discord.Color.purple()
            )
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, member_arg)

        if not member:
            embed = discord.Embed(
                title="❌ User Not Found",
                description="I couldn't find that user in this server.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return await ctx.send("❌ User not found or not in the server.")  # ✅ PRESERVED

        if member.guild_permissions.manage_messages or member.guild_permissions.administrator:
            embed = discord.Embed(
                description="❌ That user is protected, I can't do that.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        if member == ctx.author:
            return await ctx.send("❌ You can't mute yourself.")
        if member.bot:
            return await ctx.send("❌ You can't mute bots.")
        if ctx.guild.owner_id == member.id:
            return await ctx.send("❌ You can't mute the server owner.")

        duration_seconds = self.parse_duration(maybe_duration)

        if duration_seconds is None:
            reason = f"{maybe_duration or ''} {rest or ''}".strip()
            until = None
            duration_label = "permanent"
        else:
            reason = rest or "No reason provided"
            until = utcnow() + timedelta(seconds=duration_seconds)
            duration_label = maybe_duration

        try:
            await member.timeout(until, reason=reason)
        except Exception as e:
            return await ctx.send(f"❌ Failed to mute: {e}")

        try:
            await member.send(
                f"You were muted in **{ctx.guild.name}** for **{reason}**\n"
                f"Duration: **{duration_label}**"
            )
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            description=f"✅ *{member.name} was muted.* | {reason}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

        try:
            logs_ref = db.collection("moderation") \
                         .document(str(ctx.guild.id)) \
                         .collection("logs") \
                         .document()

            case_number = await get_next_case_number(ctx.guild.id)

            logs_ref.set({
                "case": case_number,
                "user_id": member.id,
                "user_tag": str(member),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": reason,
                "action": "mute",
                "duration": duration_label,
                "timestamp": int(utcnow().timestamp())
            })
        except Exception as e:
            await ctx.send(f"❌ Firestore error: {e}")

async def setup(bot):
    await bot.add_cog(Mute(bot))
