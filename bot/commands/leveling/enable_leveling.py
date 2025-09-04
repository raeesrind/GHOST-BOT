import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database  # Make sure this path matches your project

class ToggleLeveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Enable leveling (prefix)
    @commands.command(name="enableleveling", help="Enable leveling in this server.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def enableleveling_prefix(self, ctx):
        await self._set_leveling(ctx.guild.id, True)
        await ctx.send(embed=self._success_embed(enabled=True))

    # Disable leveling (prefix)
    @commands.command(name="disableleveling", help="Disable leveling in this server.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def disableleveling_prefix(self, ctx):
        await self._set_leveling(ctx.guild.id, False)
        await ctx.send(embed=self._success_embed(enabled=False))

    # Enable leveling (slash)
    @app_commands.command(name="enableleveling", description="Enable leveling in this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def enableleveling_slash(self, interaction: discord.Interaction):
        await self._set_leveling(interaction.guild.id, True)
        await interaction.response.send_message(embed=self._success_embed(enabled=True), ephemeral=True)

    # Disable leveling (slash)
    @app_commands.command(name="disableleveling", description="Disable leveling in this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def disableleveling_slash(self, interaction: discord.Interaction):
        await self._set_leveling(interaction.guild.id, False)
        await interaction.response.send_message(embed=self._success_embed(enabled=False), ephemeral=True)

    async def _set_leveling(self, guild_id, enabled: bool):
        await database.db.execute("""
            INSERT INTO xp_settings (guild_id, leveling_enabled)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET leveling_enabled = excluded.leveling_enabled
        """, (str(guild_id), int(enabled)))
        await database.db.commit()

    def _success_embed(self, enabled: bool):
        return discord.Embed(
            title="✅ Leveling Enabled" if enabled else "⚠️ Leveling Disabled",
            description="Users can now earn XP and level up!" if enabled else "Users will no longer earn XP or level up.",
            color=discord.Color.green() if enabled else discord.Color.red()
        )

    # Prefix error handlers
    @enableleveling_prefix.error
    async def on_enable_prefix_error(self, ctx, error):
        await self._handle_prefix_error(ctx, error)

    @disableleveling_prefix.error
    async def on_disable_prefix_error(self, ctx, error):
        await self._handle_prefix_error(ctx, error)

    async def _handle_prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permission to use this command.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait {error.retry_after:.1f} seconds before reusing this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    # Slash error handlers
    @enableleveling_slash.error
    async def on_enable_slash_error(self, interaction: discord.Interaction, error):
        await self._handle_slash_error(interaction, error)

    @disableleveling_slash.error
    async def on_disable_slash_error(self, interaction: discord.Interaction, error):
        await self._handle_slash_error(interaction, error)

    async def _handle_slash_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ToggleLeveling(bot))
