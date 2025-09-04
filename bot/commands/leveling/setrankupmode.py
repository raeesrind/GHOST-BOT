import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database  # SQLite wrapper module

class SetRankupMode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    valid_modes = ["dm", "channel", "silent", "specific"]

    @commands.command(name="setrankupmode", help="Set how rank-up messages are sent. Modes: dm, channel, silent, specific")
    @commands.has_permissions(administrator=True)
    async def setrankupmode_prefix(self, ctx, mode: str = None, channel: discord.TextChannel = None):
        if mode is None:
            return await ctx.send(embed=self.usage_embed())

        result = await self.handle_mode(ctx.guild.id, mode, channel)
        if isinstance(result, str):
            return await ctx.send(result)
        await ctx.send(embed=self.success_embed(mode, channel))

    @app_commands.command(name="setrankupmode", description="Set how rank-up messages are sent.")
    @app_commands.describe(mode="Mode: dm, channel, silent, or specific", channel="Channel for 'specific' mode")
    @app_commands.checks.has_permissions(administrator=True)
    async def setrankupmode_slash(self, interaction: discord.Interaction, mode: str, channel: discord.TextChannel = None):
        result = await self.handle_mode(interaction.guild.id, mode, channel)
        if isinstance(result, str):
            return await interaction.response.send_message(result, ephemeral=True)
        await interaction.response.send_message(embed=self.success_embed(mode, channel), ephemeral=True)

    async def handle_mode(self, guild_id, mode, channel):
        mode = mode.lower()
        if mode not in self.valid_modes:
            return "❌ Invalid mode. Choose from: `dm`, `channel`, `silent`, or `specific`."

        if mode == "specific":
            if not channel:
                return "❌ Please provide a channel for `specific` mode."
            await database.db.execute("""
                INSERT INTO config (guild_id, rankup_mode, rankup_channel)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET rankup_mode = excluded.rankup_mode, rankup_channel = excluded.rankup_channel
            """, (str(guild_id), mode, str(channel.id)))
        else:
            await database.db.execute("""
                INSERT INTO config (guild_id, rankup_mode, rankup_channel)
                VALUES (?, ?, NULL)
                ON CONFLICT(guild_id) DO UPDATE SET rankup_mode = excluded.rankup_mode, rankup_channel = NULL
            """, (str(guild_id), mode))

        await database.db.commit()
        return True

    def success_embed(self, mode, channel):
        descriptions = {
            "dm": "📬 Users will receive level-up notifications via direct message.",
            "channel": "💬 Notifications will be sent in the channel where the user messages.",
            "silent": "🔇 Level-up notifications are disabled.",
            "specific": f"📢 Notifications will be sent in {channel.mention}." if channel else "📢 Notifications will be sent in the specific channel."
        }
        return discord.Embed(
            title="✅ Rank-up Notification Mode Set",
            description=descriptions.get(mode.lower(), "Rank-up mode updated."),
            color=discord.Color.green()
        )

    def usage_embed(self):
        return discord.Embed(
            title="📘 Usage: ?setrankupmode",
            description=(
                "**Set how users are notified when they level up.**\n\n"
                "**Modes:**\n"
                "`dm` → Direct message to the user\n"
                "`channel` → Sent in the same channel\n"
                "`silent` → No message\n"
                "`specific` → Sent in a specified channel\n\n"
                "**Examples:**\n"
                "`?setrankupmode dm`\n"
                "`?setrankupmode channel`\n"
                "`?setrankupmode silent`\n"
                "`?setrankupmode specific #rankup-channel`"
            ),
            color=discord.Color.blurple()
        )

async def setup(bot):
    await bot.add_cog(SetRankupMode(bot))
