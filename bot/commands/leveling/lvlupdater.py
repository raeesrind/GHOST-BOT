import discord 
from discord.ext import commands
from discord import app_commands
from bot.database.database import database

def get_xp_for_level(level: int) -> int:
    return int(5 / 6 * level * (2 * level**2 + 27 * level + 91))

class LevelAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin():
        async def predicate(interaction: discord.Interaction):
            return interaction.user.guild_permissions.administrator
        return app_commands.check(predicate)

    # 🎯 Hybrid givelevel command
    @commands.hybrid_command(name="givelvl", description="Add levels to a user.")
    @app_commands.describe(user="User to add levels to", level="Number of levels to add")
    @is_admin()
    async def givelvl(self, ctx: commands.Context, user: discord.Member, level: int):
        if level < 1 or level > 600:
            return await self._send(ctx, "❌ Level must be between 1 and 600.")

        guild_id = str(ctx.guild.id)
        user_id = str(user.id)

        data = await database.get_xp(guild_id, user_id)
        current_xp = data["xp"] if data else 0

        current_level = 0
        while get_xp_for_level(current_level + 1) <= current_xp:
            current_level += 1

        new_level = min(current_level + level, 600)
        target_xp = get_xp_for_level(new_level)
        additional_xp = target_xp - current_xp

        if additional_xp > 0:
            await database.set_user_custom_xp(guild_id, user_id, additional_xp)

        await self._send(
            ctx,
            f"✅ Added **{level}** levels to {user.mention} (from level {current_level} → {new_level})",
            ephemeral=True
        )

    # 🎯 Hybrid remlvl command (fixed)
    @commands.hybrid_command(name="remlvl", description="Remove levels from a user or reset XP.")
    @app_commands.describe(user="User to remove levels from", levels="Number of levels to remove (optional)")
    @is_admin()
    async def remlvl(self, ctx: commands.Context, user: discord.Member, levels: int = None):
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)

        if levels is None:
            await database.reset_user(guild_id, user_id)
            return await self._send(ctx, f"🗑️ Fully reset XP data for {user.mention}.", ephemeral=True)

        if levels < 1 or levels > 600:
            return await self._send(ctx, "❌ Levels to remove must be between 1 and 600.", ephemeral=True)

        data = await database.get_xp(guild_id, user_id)
        current_xp = data["xp"] if data else 0

        current_level = 0
        while get_xp_for_level(current_level + 1) <= current_xp:
            current_level += 1

        new_level = max(0, current_level - levels)
        new_target_xp = get_xp_for_level(new_level)
        xp_to_remove = current_xp - new_target_xp

        if xp_to_remove > 0:
            await database.remove_user_custom_xp(guild_id, user_id, xp_to_remove)

        await self._send(
            ctx,
            f"🔻 Removed **{levels}** levels from {user.mention} (from level {current_level} → {new_level})",
            ephemeral=True
        )

    # Internal helper for slash/prefix response
    async def _send(self, ctx, msg, ephemeral=False):
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(msg, ephemeral=ephemeral)
        else:
            await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(LevelAdmin(bot))
