import discord
from discord.ext import commands
from firebase_admin import firestore
from discord.utils import utcnow
from bot.utils.casecounter import get_next_case_number  # ✅ Added import

db = firestore.client()

class Kickuser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def resolve_member(self, ctx, arg):
        try:
            return await commands.MemberConverter().convert(ctx, arg)
        except:
            for member in ctx.guild.members:
                if member.name.lower() == arg.lower() or f"{member.name}#{member.discriminator}" == arg:
                    return member
        return None

    @commands.command(name="kickuser")
    @commands.has_permissions(kick_members=True)
    async def kickuser(self, ctx, member_arg: str = None, *, reason="No reason provided"):
        guild_id = str(ctx.guild.id)

        # 🔒 Silent ignore if disabled or no perms
        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return
        if not ctx.author.guild_permissions.kick_members:
            return

        await ctx.message.delete()

        if not member_arg:
            embed = discord.Embed(
                title="Command: ?kickuser",
                description=(
                    "**Usage:** `?kickuser @user [reason]`\n"
                    "**Example:** `?kickuser @John Spamming in general`\n\n"
                    "This command kicks the user from the server and logs the action."
                ),
                color=discord.Color.purple()
            )
            embed.set_footer(text="Kickuser Command Help")
            return await ctx.send(embed=embed)

        member = await self.resolve_member(ctx, member_arg)

        if not member:
            return await ctx.send(embed=discord.Embed(
                title=":GhostError: User Not Found",
                description="I couldn't find that user in this server.",
                color=discord.Color.red()
            ))

        # ✅ Kick checks
        if member == ctx.author:
            return await ctx.send(":GhostError: You can't kick yourself.")
        if member.bot:
            return await ctx.send(":GhostError: You can't kick bots.")
        if ctx.guild.owner_id == member.id:
            return await ctx.send(":GhostError: You can't kick the server owner.")
        if member.guild_permissions.manage_messages or member.guild_permissions.administrator:
            return await ctx.send(embed=discord.Embed(
                description=":GhostError: That user is protected, I can't do that.",
                color=discord.Color.red()
            ))

        # 📩 Try DM
        try:
            await member.send(f"You were **kicked** from **{ctx.guild.name}** for: {reason}")
        except discord.Forbidden:
            pass

        # 🦵 Kick
        try:
            await member.kick(reason=reason)
        except Exception as e:
            return await ctx.send(f":GhostError: Failed to kick user: {e}")

        # ✅ Confirmation
        embed = discord.Embed(
            description=f":GhostSuccess: *{member.name} was kicked.* | {reason}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

        # 📝 Log to Firestore
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
                "action": "kick",
                "duration": "N/A",
                "timestamp": int(utcnow().timestamp())
            })

        except Exception as e:
            await ctx.send(f":GhostError: Firestore error: {e}")

async def setup(bot):
    await bot.add_cog(Kickuser(bot))
