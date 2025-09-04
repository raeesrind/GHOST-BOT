import discord 
from discord.ext import commands
import time
from bot.database.database import database

class XPAuto(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # {(guild_id, user_id): last_timestamp}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        channel_id = str(message.channel.id)

        # ✅ Load XP Config
        async with database.db.execute("SELECT * FROM config WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            await database.db.execute("""
                INSERT INTO config (guild_id, leveling_enabled, rankup_mode, rankup_channel)
                VALUES (?, ?, ?, ?)
            """, (guild_id, 1, "channel", None))
            await database.db.commit()
            config = {
                "leveling_enabled": 1,
                "xp_cooldown_seconds": 60,
                "rankup_mode": "channel",
                "rankup_channel": None,
            }
        else:
            config = dict(row)

        if config.get("leveling_enabled") != 1:
            return

        # ✅ Cooldown per user per guild
        cooldown = config.get("xp_cooldown_seconds", 60)
        now = time.time()
        last_time = self.cooldowns.get((guild_id, user_id), 0)
        if now - last_time < cooldown:
            return
        self.cooldowns[(guild_id, user_id)] = now

        # ✅ Ignore XP in blocked channels
        async with database.db.execute(
            "SELECT 1 FROM no_xp_channels WHERE guild_id = ? AND channel_id = ?",
            (guild_id, channel_id)
        ) as cursor:
            if await cursor.fetchone():
                return

        # ✅ XP = based on message length (5 chars = 1 XP, capped at 25 XP)
                # Determine if message contains something
        has_content = message.content.strip() or message.attachments or message.stickers or message.embeds

        if not has_content:
            return  # Ignore empty messages

        # Detect if it's a "simple" non-text (emoji, GIF, sticker, etc.)
        is_simple_media = (
            message.stickers
            or message.attachments
            or message.embeds
            or (
                len(message.content.strip()) <= 20
                and any(domain in message.content for domain in ["tenor.com", "giphy.com"])
            )
        )

        if is_simple_media:
            base_xp = 3
        else:
            # Calculate XP normally for real messages
            message_length = len(message.content.strip())
            base_xp = max(min(message_length, 25), 5)
            base_xp = max(base_xp, 5)  # Minimum 5 XP for valid text


        multiplier = 1.0

        # ✅ Channel XP multiplier
        async with database.db.execute(
            "SELECT multiplier FROM xp_multipliers WHERE guild_id = ? AND target_id = ? AND type = 'channel'",
            (guild_id, channel_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                multiplier *= float(row["multiplier"])

        # ✅ Role XP multiplier (use highest)
        user_roles = [str(role.id) for role in message.author.roles]
        if user_roles:
            placeholders = ",".join("?" * len(user_roles))
            query = f"""
                SELECT multiplier FROM xp_multipliers
                WHERE guild_id = ? AND target_id IN ({placeholders}) AND type = 'role'
            """
            async with database.db.execute(query, (guild_id, *user_roles)) as cursor:
                multipliers = [float(r["multiplier"]) async for r in cursor]
                if multipliers:
                    multiplier *= max(multipliers)

        earned_xp = int(base_xp * multiplier)

        # ✅ Update DB
        await database.db.execute("""
            INSERT INTO user_xp (guild_id, user_id, xp, last_message_ts)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, user_id)
            DO UPDATE SET xp = xp + excluded.xp, last_message_ts = excluded.last_message_ts
        """, (guild_id, user_id, earned_xp, int(message.created_at.timestamp())))
        await database.db.commit()

        # ✅ Check level-up
        async with database.db.execute(
            "SELECT xp FROM user_xp WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id)
        ) as cursor:
            xp_row = await cursor.fetchone()
        if not xp_row:
            return

        total_xp = xp_row["xp"]
        new_level = self.calculate_level(total_xp)
        old_level = self.calculate_level(total_xp - earned_xp)

        if new_level > old_level:
            await self.send_rankup_notice(message, new_level, config)
            await self.assign_level_roles(message.author, message.guild, new_level, config)

    async def send_rankup_notice(self, message, level, config):
        msg = f"🎉 {message.author.mention} leveled up to **Level {level}**!"
        mode = (config.get("rankup_mode") or "channel").lower()
        channel_id = config.get("rankup_channel")

        if mode in ["none", "silent"]:
            return
        elif mode == "dm":
            try:
                await message.author.send(msg)
            except discord.Forbidden:
                pass
        elif mode == "specific" and channel_id:
            channel = message.guild.get_channel(int(channel_id))
            if channel:
                await channel.send(msg)
            else:
                await message.channel.send(msg)  # fallback
        else:
            await message.channel.send(msg)

    async def assign_level_roles(self, member, guild, level, config):
        guild_id = str(guild.id)
        role_mode = config.get("role_mode", "highest")

        async with database.db.execute(
            "SELECT level, role_id FROM level_roles WHERE guild_id = ?", (guild_id,)
        ) as cursor:
            all_roles = await cursor.fetchall()

        matched_roles = [int(r["role_id"]) for r in all_roles if r["level"] <= level]
        if not matched_roles:
            return

        if role_mode == "highest":
            matched_roles = [max(matched_roles)]

        for role_id in matched_roles:
            role = guild.get_role(role_id)
            if role and role not in member.roles:
                try:
                    await member.add_roles(role, reason="Level-up reward")
                except discord.Forbidden:
                    pass

    def get_xp_for_level(self, level):
        return int(5 / 6 * level * (2 * level ** 2 + 27 * level + 91))

    def calculate_level(self, xp):
        level = 0
        while self.get_xp_for_level(level + 1) <= xp:
            level += 1
        return level

async def setup(bot):
    await bot.add_cog(XPAuto(bot))
