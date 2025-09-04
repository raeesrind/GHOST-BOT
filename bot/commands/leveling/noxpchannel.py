import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database

class NoXPChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute("SELECT leveling_enabled FROM xp_settings WHERE guild_id = ?", (str(guild_id),)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

    # -------------------- BLOCK XP --------------------
    @commands.command(name="noxpchannel", help="Add a channel where XP is not earned.")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def prefix_cmd(self, ctx, channel: discord.TextChannel = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send("❌ Leveling is currently disabled on this server.")

        if channel is None:
            return await ctx.send(embed=self.usage_embed("?noxpchannel", "Add a channel where XP is not earned."))

        await self.save_block(ctx.guild.id, channel.id)
        embed = discord.Embed(
            title="🚫 XP Blocked",
            description=f"Users will **not** earn XP in {channel.mention}.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @app_commands.command(name="noxpchannel", description="Add a channel where XP is not earned.")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message("❌ Leveling is currently disabled on this server.", ephemeral=True)

        await self.save_block(interaction.guild.id, channel.id)
        embed = discord.Embed(
            title="🚫 XP Blocked",
            description=f"Users will **not** earn XP in {channel.mention}.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------- REMOVE BLOCK --------------------
    @commands.command(name="remnoxpchannel", help="Remove a no-XP channel restriction.")
    @commands.has_permissions(administrator=True)
    async def rem_prefix_cmd(self, ctx, channel: discord.TextChannel = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send("❌ Leveling is currently disabled on this server.")

        if channel is None:
            return await ctx.send(embed=self.usage_embed("?remnoxpchannel", "Remove XP block from a channel."))

        await self.remove_block(ctx.guild.id, channel.id)
        embed = discord.Embed(
            title="✅ XP Enabled",
            description=f"Users will now earn XP in {channel.mention}.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @app_commands.command(name="remnoxpchannel", description="Remove XP block from a channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def rem_slash_cmd(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message("❌ Leveling is currently disabled on this server.", ephemeral=True)

        await self.remove_block(interaction.guild.id, channel.id)
        embed = discord.Embed(
            title="✅ XP Enabled",
            description=f"Users will now earn XP in {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------- LIST BLOCKED CHANNELS --------------------
    @commands.command(name="listnoxpchannels", help="List all channels where XP is disabled.")
    @commands.has_permissions(administrator=True)
    async def list_prefix_cmd(self, ctx):
        blocked = await self.fetch_blocked(ctx.guild)
        if not blocked:
            return await ctx.send("✅ No channels are currently blocked from earning XP.")
        channel_list = "\n".join(f"<#{cid}>" for cid in blocked)
        embed = discord.Embed(
            title="🚫 No XP Channels",
            description=channel_list,
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @app_commands.command(name="listnoxpchannels", description="List all channels where XP is disabled.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_slash_cmd(self, interaction: discord.Interaction):
        blocked = await self.fetch_blocked(interaction.guild)
        if not blocked:
            return await interaction.response.send_message("✅ No channels are currently blocked from earning XP.", ephemeral=True)
        channel_list = "\n".join(f"<#{cid}>" for cid in blocked)
        embed = discord.Embed(
            title="🚫 No XP Channels",
            description=channel_list,
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------- HELP & ERROR HANDLING --------------------
    def usage_embed(self, cmd, desc):
        return discord.Embed(
            title=f"📘 Usage: {cmd}",
            description=f"**Description:** {desc}\n\n**Example:** `{cmd} #channel`\n**Permission Required:** Administrator",
            color=discord.Color.blurple()
        )

    @prefix_cmd.error
    @rem_prefix_cmd.error
    @list_prefix_cmd.error
    async def on_prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need Administrator permission to use this command.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait {error.retry_after:.1f}s before reusing this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    @slash_cmd.error
    @rem_slash_cmd.error
    @list_slash_cmd.error
    async def on_slash_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need Administrator permission.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)

    # -------------------- DB Helpers --------------------
    async def save_block(self, guild_id, channel_id):
        await database.db.execute("""
            INSERT OR IGNORE INTO no_xp_channels (guild_id, channel_id)
            VALUES (?, ?)
        """, (str(guild_id), str(channel_id)))
        await database.db.commit()

    async def remove_block(self, guild_id, channel_id):
        await database.db.execute("""
            DELETE FROM no_xp_channels
            WHERE guild_id = ? AND channel_id = ?
        """, (str(guild_id), str(channel_id)))
        await database.db.commit()

    async def fetch_blocked(self, guild):
        async with database.db.execute("""
            SELECT channel_id FROM no_xp_channels WHERE guild_id = ?
        """, (str(guild.id),)) as cursor:
            rows = await cursor.fetchall()
        return [int(row["channel_id"]) for row in rows]

async def setup(bot):
    await bot.add_cog(NoXPChannel(bot))
