import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database  # your aiosqlite-compatible wrapper

class SetGlobalXPMultiplier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute("SELECT leveling_enabled FROM config WHERE guild_id = ?", (str(guild_id),)) as cursor:
            row = await cursor.fetchone()
            return row is None or row["leveling_enabled"] == 1

    @commands.command(name="setglobalxpmultiplier", help="Set global XP multiplier for the server.")
    @commands.has_permissions(administrator=True)
    async def prefix_cmd(self, ctx, multiplier: float = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send("❌ Leveling is disabled in this server.")

        if multiplier is None:
            return await ctx.send(embed=self.usage_embed())

        if multiplier <= 0:
            return await ctx.send("❌ Multiplier must be **greater than 0**.")

        await self.save(ctx.guild.id, multiplier)
        await ctx.send(embed=self.success_embed(multiplier))

    @app_commands.command(name="setglobalxpmultiplier", description="Set global XP multiplier for the server.")
    @app_commands.describe(multiplier="XP multiplier (e.g., 1.5 for 150% XP)")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_cmd(self, interaction: discord.Interaction, multiplier: float):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message("❌ Leveling is disabled.", ephemeral=True)
        if multiplier <= 0:
            return await interaction.response.send_message("❌ Multiplier must be **greater than 0**.", ephemeral=True)

        await self.save(interaction.guild.id, multiplier)
        await interaction.response.send_message(embed=self.success_embed(multiplier), ephemeral=True)

    async def save(self, guild_id, multiplier):
        await database.db.execute("""
            INSERT INTO config (guild_id, global_multiplier)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET global_multiplier = excluded.global_multiplier
        """, (str(guild_id), multiplier))
        await database.db.commit()

    def success_embed(self, multiplier):
        return discord.Embed(
            title="🌐 Global XP Multiplier Updated",
            description=f"XP is now multiplied by **{multiplier}x** across the server.",
            color=discord.Color.green()
        )

    def usage_embed(self):
        return discord.Embed(
            title="📘 Usage: ?setglobalxpmultiplier",
            description=(
                "Sets the global XP multiplier for all members.\n\n"
                "**Example:**\n"
                "`?setglobalxpmultiplier 2`\n\n"
                "**Note:** Multiplier must be greater than 0.\n"
                "Default is `1x` (no boost)."
            ),
            color=discord.Color.blurple()
        )

async def setup(bot):
    await bot.add_cog(SetGlobalXPMultiplier(bot))
