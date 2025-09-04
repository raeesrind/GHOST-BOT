import discord 
from discord.ext import commands
from firebase_admin import firestore
from discord.utils import utcnow
from bot.utils.casecounter import get_next_case_number  # :GhostSuccess: Added import

db = firestore.client()

class Unban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="unban",
        help="Unban a user by their ID and log the action.",
        brief="Unban a user and log it to modlogs."
    )
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int = None, *, reason: str = None):
        await ctx.message.delete()
        if user_id is None:
            usage = (
                "**Usage:** `?unban <user_id> [reason]`\n"
                "**Example:** `?unban 123456789012345678 Apologized`\n\n"
                "This command removes a user's ban from the server and logs the action."
            )
            return await ctx.send(embed=discord.Embed(description=usage, color=discord.Color.purple()))

        reason = reason or "No reason provided"

        try:
            user = await self.bot.fetch_user(user_id)

            # :GhostSuccess: Async-safe way to check if user is banned
            banned_user = None
            async for ban_entry in ctx.guild.bans(limit=None):
                if ban_entry.user.id == user.id:
                    banned_user = ban_entry
                    break

            if banned_user is None:
                return await ctx.send(":GhostError: That user is not banned.")

            await ctx.guild.unban(user, reason=reason)

            # 📩 Try to DM the user
            try:
                await user.send(f"🔓 You have been unbanned from **{ctx.guild.name}**.\n**Reason:** {reason}")
            except discord.Forbidden:
                pass

            # :GhostSuccess: Confirmation message
            embed = discord.Embed(
                description=f"🔓 *{user} was unbanned.*",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            await ctx.send(embed=embed)

            # 🗃️ Firestore Logging (modlogs)
            guild_id = str(ctx.guild.id)
            case_number = await get_next_case_number(guild_id)

            db.collection("moderation") \
              .document(guild_id) \
              .collection("logs") \
              .document(str(case_number)) \
              .set({
                  "case": case_number,  # :GhostSuccess: Changed from case_number to case for consistency
                  "user_id": user.id,
                  "user_tag": str(user),
                  "moderator_id": ctx.author.id,
                  "moderator_tag": str(ctx.author),
                  "reason": reason,
                  "action": "unban",
                  "duration": "n/a",
                  "timestamp": int(utcnow().timestamp())
              })

        except discord.NotFound:
            await ctx.send(":GhostError: User not found.")
        except discord.Forbidden:
            await ctx.send(":GhostError: I don't have permission to unban this user.")
        except Exception as e:
            await ctx.send(f":GhostError: Unban failed: {e}")

async def setup(bot):
    await bot.add_cog(Unban(bot))
