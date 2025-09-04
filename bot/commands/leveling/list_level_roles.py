import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database

class ListLevelRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute("SELECT leveling_enabled FROM xp_settings WHERE guild_id = ?", (str(guild_id),)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

    @commands.command(name="listlevelroles", help="List all level-based roles for this server.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def listlevelroles_prefix(self, ctx):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send("❌ Leveling is currently disabled on this server.")
        await self._send_roles(ctx.guild, ctx)

    @app_commands.command(name="listlevelroles", description="List all level-based roles for this server.")
    async def listlevelroles_slash(self, interaction: discord.Interaction):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message("❌ Leveling is currently disabled on this server.", ephemeral=True)
        await self._send_roles(interaction.guild, interaction)

    async def _send_roles(self, guild, destination):
        guild_id = str(guild.id)
        async with database.db.execute(
            "SELECT level, role_id FROM level_roles WHERE guild_id = ? ORDER BY level ASC",
            (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            msg = "📭 No level roles have been set yet."
            if isinstance(destination, discord.Interaction):
                return await destination.response.send_message(msg, ephemeral=True)
            return await destination.send(msg)

        embed = discord.Embed(
            title=f"📊 Level Roles for {guild.name}",
            color=discord.Color.blue()
        )

        for level, role_id in rows:
            role = guild.get_role(int(role_id))
            mention = role.mention if role else f"`{role_id}` (deleted role)"
            embed.add_field(name=f"Level {level}", value=mention, inline=False)

        if isinstance(destination, discord.Interaction):
            await destination.response.send_message(embed=embed, ephemeral=True)
        else:
            await destination.send(embed=embed)

    @listlevelroles_prefix.error
    async def on_prefix_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait {error.retry_after:.1f} seconds before reusing this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    @listlevelroles_slash.error
    async def on_slash_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ListLevelRoles(bot))
