import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

class ModLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="modlogs")
    @commands.has_permissions(manage_messages=True)
    async def modlogs(self, ctx, *, user: str = None):
        if not user:
            return await ctx.send(embed=discord.Embed(
                title="❌ Missing User",
                description="Please mention a user or provide their username or ID.\n\n**Usage:** `?modlogs @user [page]`",
                color=discord.Color.red()
            ))

        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        else:
            user = user.strip()
            if user.isdigit():
                member = ctx.guild.get_member(int(user))
            else:
                member = ctx.guild.get_member_named(user)

        if not member:
            return await ctx.send(embed=discord.Embed(
                title="❌ User Not Found",
                description=(
                    f"Could not find any member matching `{user}`.\n\n"
                    "Please try again using:\n"
                    "- A proper `@mention`\n"
                    "- Their exact username or `username#1234`\n"
                    "- Their user ID (numbers only)"
                ),
                color=discord.Color.red()
            ))

        guild_id = str(ctx.guild.id)
        user_id = str(member.id)

        logs_ref = db.collection("moderation").document(guild_id).collection("logs")

        try:
            docs = logs_ref.stream()
            logs = [doc.to_dict() for doc in docs if str(doc.to_dict().get("user_id")) == user_id]
            logs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        except Exception as e:
            return await ctx.send(f"❌ Failed to fetch logs: `{e}`")

        if not logs:
            return await ctx.send(f"✅ No moderation logs found for {member.mention}.")

        logs_per_page = 10
        total_pages = (len(logs) + logs_per_page - 1) // logs_per_page

        page = 1
        if len(ctx.message.content.split()) > 2:
            try:
                page = int(ctx.message.content.split()[2])
            except ValueError:
                page = 1

        if page > total_pages:
            return await ctx.send(f"❌ Page {page} doesn't exist. {member.mention} has only {total_pages} page(s).")

        page = max(1, page)
        start = (page - 1) * logs_per_page
        end = start + logs_per_page
        paginated_logs = logs[start:end]

        log_text = ""
        for entry in paginated_logs:
            case_number = entry.get("case", "?")
            timestamp = datetime.utcfromtimestamp(entry["timestamp"]).strftime("%b %d %Y %H:%M:%S")
            reason = entry.get("reason", "No reason provided")
            moderator = entry.get("moderator_tag", "Unknown Moderator")
            action = entry.get("action", "Unknown").capitalize()
            duration = entry.get("duration")
            length_line = f"Length: {duration}\n" if duration else ""

            log_text += (
                f"**Case {case_number}**\n"
                f"Type: {action}\n"
                f"User: ({entry['user_id']}) {entry['user_tag']}\n"
                f"Moderator: {moderator}\n"
                f"{length_line}"
                f"Reason: {reason} - {timestamp}\n\n"
            )

        embed = discord.Embed(
            title=f"Modlogs for {member} (Page {page} of {total_pages})",
            description=log_text,
            color=discord.Color.orange()
        )
        embed.set_footer(text="Use ?modlogs @user [page] to view other pages.")
        await ctx.send(embed=embed)

async def setup(bot):
    if not bot.get_cog("ModLogs"):
        await bot.add_cog(ModLogs(bot))
