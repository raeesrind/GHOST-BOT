import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime
from bot.utils.casecounter import get_next_case_number

db = firestore.client()

class Warn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="warn",
        help="Warn a member and log the reason in Firestore.\n\n"
             "**Usage:** `?warn @user <reason>`\n"
             "**Example:** `?warn @User Spamming`",
        brief="Warn a member and log it."
    )
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member = None, *, reason: str = None):
        guild_id = str(ctx.guild.id)

        # ✅ Absolute silent block if disabled in this guild
        if ctx.command.name in self.bot.disabled_commands.get(guild_id, []):
            return  # No response

        await ctx.message.delete()

        # ✅ Missing arguments
        if member is None or reason is None:
            usage = discord.Embed(
                title="❓ Missing Arguments",
                description="**Usage:** `?warn @user <reason>`\n"
                            "**Example:** `?warn @John Spamming in chat`\n\n"
                            "This command warns a user and logs it in the database.",
                color=discord.Color.purple()
            )
            return await ctx.send(embed=usage)

        # ✅ Invalid targets
        if member == ctx.author:
            return await ctx.send(embed=discord.Embed(
                description=":GhostError: You can't warn yourself.",
                color=discord.Color.red()
            ))
        if member.bot:
            return await ctx.send(embed=discord.Embed(
                description=":GhostError: You can't warn bots.",
                color=discord.Color.red()
            ))
        if ctx.guild.owner_id == member.id:
            return await ctx.send(embed=discord.Embed(
                description=":GhostError: You can't warn the server owner.",
                color=discord.Color.red()
            ))

        user_id = str(member.id)
        warnings_ref = db.collection("infractions").document(guild_id).collection("users").document(user_id)

        try:
            doc = warnings_ref.get()
            warnings = doc.to_dict().get("warnings", []) if doc.exists else []

            warning_data = {
                "moderator_id": ctx.author.id,
                "moderator_name": str(ctx.author),
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            warnings.append(warning_data)
            warnings_ref.set({"warnings": warnings}, merge=True)

            try:
                await member.send(
                    f"You were warned in **{ctx.guild.name}** 🌍 for **{reason}**"
                )
            except discord.Forbidden:
                pass  # DMs disabled

            embed = discord.Embed(
                description=f":GhostSuccess: **{member.mention} has been warned.**",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"By {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

            # ✅ Log in mod logs
            logs_ref = (
                db.collection("moderation")
                .document(guild_id)
                .collection("logs")
                .document()
            )
            case_number = await get_next_case_number(guild_id)
            logs_ref.set({
                "case": case_number,
                "user_id": member.id,
                "user_tag": str(member),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": reason,
                "action": "warn",
                "timestamp": int(datetime.utcnow().timestamp())
            })

        except Exception as e:
            await ctx.send(embed=discord.Embed(
                description=f":GhostError: Firestore error: `{e}`",
                color=discord.Color.red()
            ))

async def setup(bot):
    if not bot.get_cog("Warn"):
        await bot.add_cog(Warn(bot))
