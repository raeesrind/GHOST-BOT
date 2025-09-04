import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database  # Make sure this is your aiosqlite manager

class SetRoleMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute("SELECT leveling_enabled FROM xp_settings WHERE guild_id = ?", (str(guild_id),)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

    @commands.command(name="setrolemode", help="Set how level roles are assigned: 'highest' or 'all'.")
    @commands.has_permissions(administrator=True)
    async def setrolemode_prefix(self, ctx, mode: str = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send("❌ Leveling is disabled in this server.")

        if mode not in ["highest", "all"]:
            return await ctx.send("❌ Please choose a valid mode: `highest` or `all`\nExample: `?setrolemode highest`")

        await self.set_mode(ctx.guild.id, mode)
        await ctx.send(f"🔧 Role assignment mode set to `{mode}`.")

    @app_commands.command(name="setrolemode", description="Set how level roles are assigned: 'highest' or 'all'.")
    @app_commands.describe(mode="Choose 'highest' or 'all'")
    @app_commands.checks.has_permissions(administrator=True)
    async def setrolemode_slash(self, interaction: discord.Interaction, mode: str):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message("❌ Leveling is disabled in this server.", ephemeral=True)

        if mode not in ["highest", "all"]:
            return await interaction.response.send_message(
                "❌ Invalid mode. Choose either `highest` or `all`.", ephemeral=True
            )

        await self.set_mode(interaction.guild.id, mode)
        await interaction.response.send_message(f"🔧 Role assignment mode set to `{mode}`.", ephemeral=True)

    async def set_mode(self, guild_id, mode):
        await database.db.execute("""
            INSERT INTO xp_settings (guild_id, role_mode)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET role_mode = excluded.role_mode
        """, (str(guild_id), mode))
        await database.db.commit()

async def setup(bot):
    await bot.add_cog(SetRoleMode(bot))
