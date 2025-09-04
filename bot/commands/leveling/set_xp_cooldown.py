import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database  # your aiosqlite wrapper

class SetXPCooldown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setxpcooldown", help="Set XP cooldown in seconds (min: 3, default: 60).")
    @commands.has_permissions(administrator=True)
    async def setxpcooldown_prefix(self, ctx, seconds: int = None):
        if seconds is None:
            return await ctx.send(embed=self.usage_embed())

        if seconds < 3:
            return await ctx.send("❌ Cooldown must be **at least 3 seconds**.")

        await self.set_cooldown(ctx.guild.id, seconds)
        await ctx.send(embed=self.success_embed(seconds))

    @app_commands.command(name="setxpcooldown", description="Set XP cooldown in seconds (minimum 3)")
    @app_commands.describe(seconds="Cooldown time in seconds (min: 3)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setxpcooldown_slash(self, interaction: discord.Interaction, seconds: int):
        if seconds < 3:
            return await interaction.response.send_message("❌ Cooldown must be **at least 3 seconds**.", ephemeral=True)

        await self.set_cooldown(interaction.guild.id, seconds)
        await interaction.response.send_message(embed=self.success_embed(seconds), ephemeral=True)

    async def set_cooldown(self, guild_id, seconds):
        await database.db.execute("""
            INSERT INTO config (guild_id, xp_cooldown_seconds)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET xp_cooldown_seconds = excluded.xp_cooldown_seconds
        """, (str(guild_id), seconds))
        await database.db.commit()

    def success_embed(self, seconds):
        return discord.Embed(
            title="⏱️ XP Cooldown Set",
            description=f"Users will now earn XP **once every {seconds} seconds**.",
            color=discord.Color.green()
        )

    def usage_embed(self):
        return discord.Embed(
            title="📘 Usage: ?setxpcooldown",
            description=(
                "Set how often users can earn XP by chatting.\n\n"
                "**Example:** `?setxpcooldown 60`\n"
                "**Minimum:** 3 seconds\n"
                "**Permission:** Administrator"
            ),
            color=discord.Color.blue()
        )

async def setup(bot):
    await bot.add_cog(SetXPCooldown(bot))
