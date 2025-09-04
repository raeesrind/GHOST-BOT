import discord  
from discord.ext import commands
from discord import app_commands
from bot.database.database import database
import csv
import os
from datetime import datetime

# ✅ Allowed user IDs (edit this list as needed)
ALLOWED_USER_IDS = {1117037767831072891, 876949915870302309, 601256111764668426, 1130498969844334774}  # Replace with actual IDs

# ✅ Custom check for both slash and prefix commands
def is_allowed_user():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id in ALLOWED_USER_IDS
    return app_commands.check(predicate)

def is_allowed_user_prefix():
    def predicate(ctx: commands.Context):
        return ctx.author.id in ALLOWED_USER_IDS
    return commands.check(predicate)

class SendXPData(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✅ Prefix command: ?senddata @user
    @commands.command(name="senddata", help="Export this server's XP data to a file and DM it to the mentioned user.")
    @is_allowed_user_prefix()
    async def senddata_prefix(self, ctx, member: discord.Member = None):
        if not member:
            return await ctx.send("❌ Please mention a user. Example: `?senddata @owner`")

        await self._export_and_send(ctx.guild, member, ctx)

    # ✅ Slash command: /senddata user:@user
    @app_commands.command(name="senddata", description="Export this server's XP data and DM it to the mentioned user.")
    @is_allowed_user()
    async def senddata_slash(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        await self._export_and_send(interaction.guild, user, interaction)

    # ✅ Shared logic
    async def _export_and_send(self, guild, member, origin):
        guild_id = str(guild.id)  
        guild_name = guild.name.replace(" ", "_")
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = f"ghost_xp_{guild_name}_{timestamp}.csv"
        filepath = f"data/{filename}"

        try:
            os.makedirs("data", exist_ok=True)

            async with database.db.execute("""
                SELECT user_id, xp FROM user_xp
                WHERE guild_id = ?
                ORDER BY xp DESC
            """, (guild_id,)) as cursor:
                rows = await cursor.fetchall()

            if not rows:
                msg = "📭 No XP data found for this server."
                if isinstance(origin, discord.Interaction):
                    await origin.followup.send(msg, ephemeral=True)
                else:
                    await origin.send(msg)
                return

            with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Rank", "User ID", "XP"])
                for i, row in enumerate(rows, start=1):
                    writer.writerow([i, row["user_id"], row["xp"]])

            await member.send(
                content=f"📁 XP Export for **{guild.name}** — {len(rows)} users",
                file=discord.File(filepath)
            )

            msg = f"✅ XP data exported and sent to {member.mention} via DM."
            if isinstance(origin, discord.Interaction):
                await origin.followup.send(msg, ephemeral=True)
            else:
                await origin.send(msg)

        except Exception as e:
            error_msg = f"❌ Failed to send data: `{e}`"
            if isinstance(origin, discord.Interaction):
                await origin.followup.send(error_msg, ephemeral=True)
            else:
                await origin.send(error_msg)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    # 🧩 Error handler for slash commands
    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, (app_commands.errors.MissingPermissions, app_commands.errors.CheckFailure)):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Error: `{error}`", ephemeral=True)

# 🔄 Load cog
async def setup(bot):
    await bot.add_cog(SendXPData(bot))
