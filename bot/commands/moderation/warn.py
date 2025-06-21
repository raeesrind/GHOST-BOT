import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime
from bot.utils.casecounter import get_next_case_number  # ✅ Added import

db = firestore.client()

class Warn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member = None, *, reason: str = None):
        await ctx.message.delete()
        if member is None or reason is None:
            usage = (
                "**Usage:** ?warn @user <reason>\n"
                "Example: ?warn @John Spamming in chat\n\n"
                "This command will send a DM to the user and log the warning."
            )
            return await ctx.send(embed=discord.Embed(description=usage, color=discord.Color.purple()))

        if member == ctx.author:
            return await ctx.send("❌ You can't warn yourself.")
        if member.bot:
            return await ctx.send("❌ You can't warn bots.")
        if ctx.guild.owner_id == member.id:
            return await ctx.send("❌ You can't warn the server owner.")

        guild_id = str(ctx.guild.id)
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
                    f"You were warned in **{ctx.guild.name}** 🌍 for **{reason}**\n"
                    f"Message from server: **{ctx.guild.name}**"
                )
            except discord.Forbidden:
                pass  # User has DMs off

            embed = discord.Embed(
                description=f"✅ *{member.name} has been warned.*",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

            # ✅ Store log in proper moderation logs collection
            logs_ref = db.collection("moderation").document(guild_id).collection("logs").document()
            case_number = await get_next_case_number(guild_id)  # ✅ Fix: Provide guild_id
            logs_ref.set({
                "case": case_number,  # ✅ Add case number
                "user_id": member.id,
                "user_tag": str(member),
                "moderator_id": ctx.author.id,
                "moderator_tag": str(ctx.author),
                "reason": reason,
                "action": "warn",
                "timestamp": int(datetime.utcnow().timestamp())  # Unix timestamp
            })

        except Exception as e:
            await ctx.send(f"❌ Firestore error: {e}")

async def setup(bot):
    if not bot.get_cog("Warn"):
        await bot.add_cog(Warn(bot))
