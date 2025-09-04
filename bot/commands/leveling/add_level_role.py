import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database
from discord.ext.commands import Context
from typing import Optional

class AddLevelRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_command_enabled(self, guild_id):
        return True  # Placeholder for future toggle

    async def get_prefix(self, guild_id):
        return "?"  # Customize if needed

    def success_embed(self, role, level):
        return discord.Embed(
            title="✅ Level Role Set",
            description=f"{role.mention} will be awarded at level **{level}**.",
            color=discord.Color.green()
        )

    def help_embed(self, prefix):
        return discord.Embed(
            title="📘 Usage: Add Level Role",
            description=(
                f"**Command:** `{prefix}addlevelrole`\n"
                "**Description:** Assign a role at a specific level.\n\n"
                "**Usage:**\n"
                f"`{prefix}addlevelrole @role <level>`\n\n"
                "**Example:**\n"
                f"`{prefix}addlevelrole @Member 10`"
            ),
            color=discord.Color.blurple()
        )

    def error_embed(self, msg):
        return discord.Embed(description=f"❌ {msg}", color=discord.Color.red())

    # Prefix command
    @commands.command(name="addlevelrole", help="Assign a role at a specific level.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def addlevelrole_prefix(self, ctx: Context, role: Optional[discord.Role] = None, level: Optional[int] = None):
        if not await self.is_command_enabled(ctx.guild.id):
            return await ctx.send(embed=self.error_embed("The leveling system is currently disabled."))

        prefix = await self.get_prefix(ctx.guild.id)

        if role is None or level is None:
            return await ctx.send(embed=self.help_embed(prefix))

        await self.save_role(str(ctx.guild.id), str(role.id), level)
        await ctx.send(embed=self.success_embed(role, level))

    # Slash command
    @app_commands.command(name="addlevelrole", description="Assign a role at a specific level.")
    @app_commands.checks.has_permissions(administrator=True)
    async def addlevelrole_slash(self, interaction: discord.Interaction, role: discord.Role, level: int):
        if not await self.is_command_enabled(interaction.guild.id):
            return await interaction.response.send_message(
                embed=self.error_embed("The leveling system is currently disabled."), ephemeral=True
            )

        await self.save_role(str(interaction.guild.id), str(role.id), level)
        await interaction.response.send_message(embed=self.success_embed(role, level), ephemeral=True)

    async def save_role(self, guild_id, role_id, level):
        await database.db.execute("""
            INSERT INTO level_roles (guild_id, level, role_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, level) DO UPDATE SET role_id = excluded.role_id
        """, (guild_id, level, role_id))
        await database.db.commit()

    # Prefix error handler
    @addlevelrole_prefix.error
    async def on_prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=self.error_embed("You need Administrator permission to use this command."))
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=self.error_embed(f"⏳ Please wait {error.retry_after:.1f}s before reusing this command."))
        else:
            await ctx.send(embed=self.error_embed(f"An error occurred: `{error}`"))

    # Slash error handler
    @addlevelrole_slash.error
    async def on_slash_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=self.error_embed("You need Administrator permission to use this command."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=self.error_embed(f"An error occurred: `{error}`"), ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(AddLevelRole(bot))
