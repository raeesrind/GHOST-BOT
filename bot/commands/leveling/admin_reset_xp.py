import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database


class AdminResetXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute(
            "SELECT leveling_enabled FROM xp_settings WHERE guild_id = ?", (str(guild_id),)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

    # 📘 Prefix Command
    @commands.command(name="resetxp", help="Reset XP for a user or all users.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def resetxp_prefix(self, ctx, target: str = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send(embed=self.error_embed("Leveling is currently disabled on this server."))

        if not target:
            return await ctx.send(embed=self.help_embed("?resetxp", "@user or `all`"))

        if target.lower() == "all":
            await self.reset_all(ctx.guild.id)
            return await ctx.send(embed=self.success_embed("⚠️ All users' XP has been reset."))

        # Try to get a member from mention or name
        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, target)
            except Exception:
                return await ctx.send(embed=self.error_embed(f"User `{target}` not found."))

        await self.reset_user(ctx.guild.id, member.id)
        await ctx.send(embed=self.success_embed(f"✅ XP reset for {member.mention}."))

    # 📘 Slash Command
    @app_commands.command(name="resetxp", description="Reset XP for a user or all users.")
    @app_commands.describe(user="User to reset XP for", all="Reset XP for everyone?")
    @app_commands.checks.has_permissions(administrator=True)
    async def resetxp_slash(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None,
        all: bool = False
    ):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message(
                embed=self.error_embed("Leveling is currently disabled on this server."), ephemeral=True
            )

        if all:
            await self.reset_all(interaction.guild.id)
            return await interaction.response.send_message(
                embed=self.success_embed("⚠️ All users' XP has been reset."), ephemeral=True
            )

        if not user:
            return await interaction.response.send_message(
                embed=self.help_embed("/resetxp", "Choose a user or enable `all:true`."), ephemeral=True
            )

        await self.reset_user(interaction.guild.id, user.id)
        await interaction.response.send_message(
            embed=self.success_embed(f"✅ XP reset for {user.mention}."), ephemeral=True
        )

    # 💾 Database Methods
    async def reset_user(self, guild_id, user_id):
        await database.db.execute(
            "DELETE FROM user_xp WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        )
        await database.db.commit()

    async def reset_all(self, guild_id):
        await database.db.execute(
            "DELETE FROM user_xp WHERE guild_id = ?",
            (str(guild_id),)
        )
        await database.db.commit()

    # ✅ Embeds
    def success_embed(self, msg):
        return discord.Embed(
            title="✅ Success",
            description=msg,
            color=discord.Color.green()
        )

    def error_embed(self, msg):
        return discord.Embed(
            title="❌ Error",
            description=msg,
            color=discord.Color.red()
        )

    def help_embed(self, command, usage_hint):
        return discord.Embed(
            title=f"📘 Usage: {command}",
            description=f"Reset XP for a user or all users.\n\n**Example:** `{command} {usage_hint}`\n**Permissions:** Administrator",
            color=discord.Color.blurple()
        )

    # ❗ Error Handlers
    @resetxp_prefix.error
    async def on_prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=self.error_embed("You need **Administrator** permission to use this command."))
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=self.error_embed(f"⏳ Wait {error.retry_after:.1f}s before using this again."))
        else:
            await ctx.send(embed=self.error_embed(f"Unexpected error: {error}"))

    @resetxp_slash.error
    async def on_slash_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=self.error_embed("You need **Administrator** permission."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=self.error_embed(f"Unexpected error: {error}"), ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(AdminResetXP(bot))
