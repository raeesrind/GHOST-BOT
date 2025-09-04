# msg_tracker.py

import discord
from discord.ext import commands
import aiosqlite


class MessageTracker(commands.Cog):
    """
    Tracks user messages across guilds.
    Stores message counts in SQLite for giveaway requirements.
    """

    def __init__(self, bot):
        self.bot = bot
        self.db_path = "giveaways.db"

    async def cog_load(self):
        """Ensure table exists when cog loads."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    guild_id INTEGER,
                    user_id INTEGER,
                    message_count INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            await db.commit()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Increment message count for each user message."""
        if message.author.bot or not message.guild:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO messages (guild_id, user_id, message_count)
                VALUES (?, ?, 1)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    message_count = message_count + 1
                """,
                (message.guild.id, message.author.id),
            )
            await db.commit()

    async def get_message_count(self, guild_id: int, user_id: int) -> int:
        """Return the total number of messages a user has sent in the guild."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT message_count FROM messages WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0


async def setup(bot):
    await bot.add_cog(MessageTracker(bot))
