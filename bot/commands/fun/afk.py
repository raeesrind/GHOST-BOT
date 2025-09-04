import discord
from discord import app_commands
from discord.ext import commands
from bot.database.afkdb import init_afk_db, set_afk, remove_afk, get_afk
from datetime import datetime, timedelta
import re  # Import moved to top

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.processing_afk_users = set()
        self.afk_timestamps = {}  # { "guildid-userid": datetime }

    @app_commands.command(name="afk", description="Set your AFK status.")
    async def afk(self, interaction: discord.Interaction, reason: str = "AFK"):
        member = interaction.user
        guild = interaction.guild
        key = f"{guild.id}-{member.id}"
        
        await interaction.response.defer(ephemeral=False)
    
        # 🚫 Block role mentions in reason
        if (
            "@everyone" in reason
            or "@here" in reason
            or re.search(r"<@&\d+>", reason)
        ):
            await interaction.followup.send(
                f"{member.mention}, your AFK reason cannot contain role mentions.",
                allowed_mentions=discord.AllowedMentions.none()
            )
            return

        # Prevent race condition
        if member.id in self.processing_afk_users:
            return

        self.processing_afk_users.add(member.id)

        prev_reason, prev_nick = await get_afk(guild.id, member.id)
        now = datetime.utcnow()
        last_afk_time = self.afk_timestamps.get(key)

        # If already AFK, prevent spamming the command again within 10 seconds
        if prev_reason:
            if last_afk_time and now - last_afk_time < timedelta(seconds=10):
                await interaction.followup.send(
                    f"{member.mention}, a little too quick there."
                )
                self.processing_afk_users.discard(member.id)
                return

        self.afk_timestamps[key] = now

        # Set AFK nickname (optional "[AFK]" tag can be added if you want)
        original_nick = member.nick or member.name
        afk_nick = f"{original_nick}"

        try:
            await member.edit(nick=afk_nick)
        except discord.Forbidden:
            pass

        # Save AFK info
        if not prev_reason:
            await set_afk(guild.id, member.id, reason, original_nick)
        else:
            await set_afk(guild.id, member.id, reason, prev_nick)

        # Publicly announce AFK
        if member.guild_permissions.manage_messages or member.guild_permissions.administrator:
            await interaction.followup.send(
                f"{member.mention}, you are now AFK: **{reason}**"
            )
        else:
            await interaction.followup.send(
                f"[AFK] {member.display_name}, I set your AFK: **{reason}**"
            )

        self.processing_afk_users.discard(member.id)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        member = message.author
        key = f"{guild_id}-{member.id}"

        # Remove AFK status if the user sends a normal message
        reason, original_nick = await get_afk(guild_id, member.id)
        if reason:
            try:
                if member.nick and member.nick.startswith("[AFK] "):
                    if original_nick and member.nick != original_nick:
                        await member.edit(nick=original_nick)
            except discord.Forbidden:
                pass

            await remove_afk(guild_id, member.id)
            self.afk_timestamps.pop(key, None)
            await message.channel.send(
                f"Welcome back {member.mention}, your AFK was removed",
                delete_after=9
            )

        # Notify if any AFK user is mentioned
        for mention in message.mentions:
            afk_reason, _ = await get_afk(guild_id, mention.id)
            if afk_reason:
                await message.channel.send(
                    f"💤 {mention.display_name} is AFK: **{afk_reason}**",
                    delete_after=9
                )

async def setup(bot):
    await init_afk_db()
    await bot.add_cog(AFK(bot))
