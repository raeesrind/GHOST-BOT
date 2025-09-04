import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database  # ✅ Make sure your aiosqlite db instance is set here

class RemoveLevelRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute("SELECT leveling_enabled FROM xp_settings WHERE guild_id = ?", (str(guild_id),)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

    @commands.command(name="removelevelrole", help="Remove a role assigned to a specific level.")
    @commands.has_permissions(administrator=True)
    async def removelevelrole_prefix(self, ctx, level: int = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send("❌ Leveling is disabled on this server.")
        if level is None:
            return await ctx.send("❌ Please specify a level to remove. Example: `?removelevelrole 10`")

        removed = await self.remove_role(ctx.guild.id, level)
        if removed:
            await ctx.send(f"✅ Removed level role for Level {level}.")
        else:
            await ctx.send(f"⚠️ No level role was set for Level {level}.")

    @app_commands.command(name="removelevelrole", description="Remove a role assigned to a specific level.")
    @app_commands.checks.has_permissions(administrator=True)
    async def removelevelrole_slash(self, interaction: discord.Interaction, level: int):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message("❌ Leveling is disabled on this server.", ephemeral=True)

        removed = await self.remove_role(interaction.guild.id, level)
        if removed:
            await interaction.response.send_message(f"✅ Removed level role for Level {level}.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ No level role was set for Level {level}.", ephemeral=True)

    async def remove_role(self, guild_id, level):
        async with database.db.execute("SELECT 1 FROM level_roles WHERE guild_id = ? AND level = ?", (str(guild_id), level)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False

        await database.db.execute("DELETE FROM level_roles WHERE guild_id = ? AND level = ?", (str(guild_id), level))
        await database.db.commit()
        return True

async def setup(bot):
    await bot.add_cog(RemoveLevelRole(bot))
