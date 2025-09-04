import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database  # ✅ Points to your aiosqlite setup


class RoleXPMultiplier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute(
            "SELECT leveling_enabled FROM config WHERE guild_id = ?", (str(guild_id),)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

    def usage_embed(self):
        return discord.Embed(
            title="📘 Usage: ?rolexpmultiplier",
            description=(
                "Sets XP multiplier for a role.\n\n"
                "**Example:** `?rolexpmultiplier @VIP 10`\n"
                "**Range:** `1x` to `100x`\n"
                "**Permission:** Administrator"
            ),
            color=discord.Color.blue()
        )

    def remove_usage_embed(self):
        return discord.Embed(
            title="📘 Usage: ?removerolexpmultiplier",
            description=(
                "Removes XP multiplier from a role.\n\n"
                "**Example:** `?removerolexpmultiplier @VIP`\n"
                "**Permission:** Administrator"
            ),
            color=discord.Color.blue()
        )

    def success_embed(self, message):
        return discord.Embed(description=f"✅ {message}", color=discord.Color.green())

    def error_embed(self, message):
        return discord.Embed(description=f"❌ {message}", color=discord.Color.red())

    # ====== SET MULTIPLIER ======
    @commands.command(name="rolexpmultiplier", help="Set XP multiplier for a role (1x to 100x).")
    @commands.has_permissions(administrator=True)
    async def prefix_cmd(self, ctx, role: discord.Role = None, multiplier: float = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send(embed=self.error_embed("Leveling is currently disabled on this server."))
        if role is None or multiplier is None:
            return await ctx.send(embed=self.usage_embed())
        if not (1 <= multiplier <= 100):
            return await ctx.send(embed=self.error_embed("Multiplier must be between **1x and 100x**."))
        await self.save(ctx.guild.id, role.id, multiplier)
        await ctx.send(embed=self.success_embed(f"Set XP multiplier `{multiplier}x` for {role.mention}"))

    @app_commands.command(name="rolexpmultiplier", description="Set XP multiplier for a role (1x to 100x).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Target role", multiplier="XP multiplier (e.g. 2, 10, 50)")
    async def slash_cmd(self, interaction: discord.Interaction, role: discord.Role, multiplier: float):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message(embed=self.error_embed("Leveling is currently disabled."), ephemeral=True)
        if not (1 <= multiplier <= 100):
            return await interaction.response.send_message(embed=self.error_embed("Multiplier must be between **1x and 100x**."), ephemeral=True)
        await self.save(interaction.guild.id, role.id, multiplier)
        await interaction.response.send_message(embed=self.success_embed(f"Set XP multiplier `{multiplier}x` for {role.mention}"), ephemeral=True)

    # ====== REMOVE MULTIPLIER ======
    @commands.command(name="removerolexpmultiplier", help="Remove XP multiplier for a role.")
    @commands.has_permissions(administrator=True)
    async def remove_prefix_cmd(self, ctx, role: discord.Role = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send(embed=self.error_embed("Leveling is currently disabled on this server."))
        if role is None:
            return await ctx.send(embed=self.remove_usage_embed())
        await self.remove(ctx.guild.id, role.id)
        await ctx.send(embed=self.success_embed(f"Removed XP multiplier for {role.mention}"))

    @app_commands.command(name="removerolexpmultiplier", description="Remove XP multiplier for a role.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_slash_cmd(self, interaction: discord.Interaction, role: discord.Role):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message(embed=self.error_embed("Leveling is currently disabled."), ephemeral=True)
        await self.remove(interaction.guild.id, role.id)
        await interaction.response.send_message(embed=self.success_embed(f"Removed XP multiplier for {role.mention}"), ephemeral=True)

    # ====== DB ======
    async def save(self, guild_id, role_id, multiplier):
        await database.db.execute("""
            INSERT INTO xp_multipliers (guild_id, target_id, type, multiplier)
            VALUES (?, ?, 'role', ?)
            ON CONFLICT(guild_id, target_id, type)
            DO UPDATE SET multiplier = excluded.multiplier
        """, (str(guild_id), str(role_id), multiplier))
        await database.db.commit()

    async def remove(self, guild_id, role_id):
        await database.db.execute("""
            DELETE FROM xp_multipliers
            WHERE guild_id = ? AND target_id = ? AND type = 'role'
        """, (str(guild_id), str(role_id)))
        await database.db.commit()


async def setup(bot):
    await bot.add_cog(RoleXPMultiplier(bot))
