import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database


class ChannelXPMultiplier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_command_enabled(self, guild_id):
        return True  # Placeholder for toggle logic

    async def get_prefix(self, guild_id):
        return "?"  # Customize if needed

    def help_embed(self, prefix):
        return discord.Embed(
            title="📘 Usage: Channel XP Multiplier",
            description=(
                f"**Command:** `{prefix}channelxpmultiplier`\n"
                "**Description:** Set XP multiplier for a specific channel.\n\n"
                "**Usage:**\n"
                f"`{prefix}channelxpmultiplier #channel <multiplier>`\n\n"
                "**Example:**\n"
                f"`{prefix}channelxpmultiplier #general 1.5`"
            ),
            color=discord.Color.blurple()
        )

    def remove_help_embed(self, prefix):
        return discord.Embed(
            title="📘 Usage: Remove Channel XP Multiplier",
            description=(
                f"**Command:** `{prefix}removechannelxpmultiplier`\n"
                "**Description:** Remove the XP multiplier from a channel.\n\n"
                "**Usage:**\n"
                f"`{prefix}removechannelxpmultiplier #channel`"
            ),
            color=discord.Color.blurple()
        )

    def success_embed(self, channel: discord.TextChannel, multiplier: float):
        return discord.Embed(
            title="✅ XP Multiplier Set",
            description=f"XP multiplier of **{multiplier}x** has been set for {channel.mention}.",
            color=discord.Color.green()
        )

    def removed_embed(self, channel: discord.TextChannel):
        return discord.Embed(
            title="✅ XP Multiplier Removed",
            description=f"The XP multiplier for {channel.mention} has been removed.",
            color=discord.Color.green()
        )

    def error_embed(self, msg: str):
        return discord.Embed(description=f"❌ {msg}", color=discord.Color.red())

    # ======================= SET MULTIPLIER =======================

    @commands.command(name="channelxpmultiplier", help="Set XP multiplier for a channel.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prefix_cmd(self, ctx, channel: discord.TextChannel = None, multiplier: float = None):
        if not await self.is_command_enabled(ctx.guild.id):
            return await ctx.send(embed=self.error_embed("The leveling system is currently disabled."))

        prefix = await self.get_prefix(ctx.guild.id)

        if channel is None or multiplier is None:
            return await ctx.send(embed=self.help_embed(prefix))

        await self.save(str(ctx.guild.id), str(channel.id), multiplier)
        await ctx.send(embed=self.success_embed(channel, multiplier))

    @app_commands.command(name="channelxpmultiplier", description="Set XP multiplier for a channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel, multiplier: float):
        if not await self.is_command_enabled(interaction.guild.id):
            return await interaction.response.send_message(
                embed=self.error_embed("The leveling system is currently disabled."), ephemeral=True
            )

        await self.save(str(interaction.guild.id), str(channel.id), multiplier)
        await interaction.response.send_message(embed=self.success_embed(channel, multiplier), ephemeral=True)

    # ======================= REMOVE MULTIPLIER =======================

    @commands.command(name="removechannelxpmultiplier", help="Remove XP multiplier for a channel.")
    @commands.has_permissions(administrator=True)
    async def remove_prefix_cmd(self, ctx, channel: discord.TextChannel = None):
        if not await self.is_command_enabled(ctx.guild.id):
            return await ctx.send(embed=self.error_embed("The leveling system is currently disabled."))

        prefix = await self.get_prefix(ctx.guild.id)

        if channel is None:
            return await ctx.send(embed=self.remove_help_embed(prefix))

        await self.remove(str(ctx.guild.id), str(channel.id))
        await ctx.send(embed=self.removed_embed(channel))

    @app_commands.command(name="removechannelxpmultiplier", description="Remove XP multiplier for a channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_slash_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.is_command_enabled(interaction.guild.id):
            return await interaction.response.send_message(
                embed=self.error_embed("The leveling system is currently disabled."), ephemeral=True
            )

        await self.remove(str(interaction.guild.id), str(channel.id))
        await interaction.response.send_message(embed=self.removed_embed(channel), ephemeral=True)

    # ======================= DATABASE =======================

    async def save(self, guild_id, channel_id, multiplier):
        await database.db.execute("""
            INSERT INTO xp_multipliers (guild_id, target_id, type, multiplier)
            VALUES (?, ?, 'channel', ?)
            ON CONFLICT(guild_id, target_id, type) DO UPDATE SET multiplier = excluded.multiplier
        """, (guild_id, channel_id, multiplier))
        await database.db.commit()

    async def remove(self, guild_id, channel_id):
        await database.db.execute("""
            DELETE FROM xp_multipliers WHERE guild_id = ? AND target_id = ? AND type = 'channel'
        """, (guild_id, channel_id))
        await database.db.commit()

    # ======================= ERRORS =======================

    @prefix_cmd.error
    @remove_prefix_cmd.error
    async def on_prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=self.error_embed("You need Administrator permission to use this command."))
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=self.error_embed(f"⏳ Wait {error.retry_after:.1f}s before using this again."))
        else:
            await ctx.send(embed=self.error_embed(f"An error occurred: `{error}`"))

    @slash_cmd.error
    @remove_slash_cmd.error
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
    await bot.add_cog(ChannelXPMultiplier(bot))
