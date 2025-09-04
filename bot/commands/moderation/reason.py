import discord
from discord.ext import commands
from firebase_admin import firestore

db = firestore.client()

class Reason(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="reason",
        help="✏️ Change the reason for a moderation case.\n❌ Skips if command is disabled for the server.",
        brief="Edit a moderation case reason."
    )
    @commands.has_permissions(manage_messages=True)
    async def reason(self, ctx, case_number: int = None, *, new_reason: str = None):
        # 🔇 Silent skip if command is disabled
        if ctx.command.name.lower() in self.bot.disabled_commands.get(str(ctx.guild.id), []):
            return

        # ❌ Validate inputs
        if case_number is None or new_reason is None:
            embed = discord.Embed(
                title="Command: ?reason",
                description=(
                    "**Description:** Change the reason for any moderation case.\n"
                    "**Cooldown:** 60 seconds\n\n"
                    "**Usage:**\n`?reason [case ID] [new reason]`\n"
                    "**Example:**\n`?reason 42 Apologized and warned privately.`"
                ),
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        try:
            guild_id = str(ctx.guild.id)
            logs_ref = db.collection("moderation").document(guild_id).collection("logs")
            matched_doc = None

            for doc in logs_ref.stream():
                data = doc.to_dict()
                if data.get("case") == case_number:
                    matched_doc = doc
                    break

            if not matched_doc:
                return await ctx.send(f":GhostError: Case #{case_number} not found.")

            data = matched_doc.to_dict()
            old_reason = data.get("reason", "No previous reason")

            data["reason"] = new_reason
            matched_doc.reference.set(data)

            embed = discord.Embed(
                title=f":GhostSuccess: Reason Updated for Case #{case_number}",
                color=discord.Color.green()
            )
            embed.add_field(name="Old Reason", value=old_reason, inline=False)
            embed.add_field(name="New Reason", value=new_reason, inline=False)
            embed.set_footer(text=f"Updated by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f":GhostError: Failed to update reason: `{e}`")

async def setup(bot):
    await bot.add_cog(Reason(bot))
