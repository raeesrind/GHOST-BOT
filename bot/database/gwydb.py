# bot/database/gwydb.py
import aiosqlite
from typing import Any, Dict, List, Optional


class GwyDB:
    def __init__(self, db_path: str = "giveaways.db"):
        self.db_path = db_path

    async def setup(self):
        """Create necessary tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Giveaways
            await db.execute("""
                CREATE TABLE IF NOT EXISTS giveaways (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER UNIQUE NOT NULL,
                    channel_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    prize TEXT NOT NULL,
                    winners INTEGER NOT NULL,
                    end_time INTEGER NOT NULL,
                    host_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'running',
                    required_role_id INTEGER DEFAULT NULL,
                    min_messages INTEGER DEFAULT 0,
                    min_invites INTEGER DEFAULT 0
                )
            """)

            # Entries
            await db.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    message_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    PRIMARY KEY (message_id, user_id)
                )
            """)

            # Manager role
            await db.execute("""
                CREATE TABLE IF NOT EXISTS giveaway_manager_role (
                    guild_id INTEGER PRIMARY KEY,
                    role_id INTEGER NOT NULL
                )
            """)

            # Invite tracker (for requirement)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS invites (
                    guild_id INTEGER,
                    user_id INTEGER,
                    invites INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)

            # Message tracker (for requirement)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    guild_id INTEGER,
                    user_id INTEGER,
                    message_count INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)

            await db.commit()

    # ---------------- Giveaways ----------------
    async def add_giveaway(
        self, message_id: int, channel_id: int, guild_id: int,
        prize: str, winners: int, end_time: int, host_id: int,
        required_role_id: Optional[int] = None,
        min_messages: int = 0,
        min_invites: int = 0
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO giveaways 
                (message_id, channel_id, guild_id, prize, winners, end_time, host_id, required_role_id, min_messages, min_invites)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (message_id, channel_id, guild_id, prize, winners, end_time, host_id, required_role_id, min_messages, min_invites))
            await db.commit()

    async def get_giveaway(self, message_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM giveaways WHERE message_id = ?", (message_id,))
            row = await cursor.fetchone()
            if row:
                keys = [d[0] for d in cursor.description]
                return dict(zip(keys, row))
            return None

    async def get_giveaway_by_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        return await self.get_giveaway(message_id)

    async def delete_giveaway(self, message_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM giveaways WHERE message_id = ?", (message_id,))
            await db.execute("DELETE FROM entries WHERE message_id = ?", (message_id,))
            await db.commit()

    async def get_all_giveaways(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM giveaways")
            rows = await cursor.fetchall()
            keys = [d[0] for d in cursor.description]
            return [dict(zip(keys, row)) for row in rows]

    async def get_active_giveaways(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM giveaways WHERE status = 'running'")
            rows = await cursor.fetchall()
            keys = [d[0] for d in cursor.description]
            return [dict(zip(keys, row)) for row in rows]

    async def update_status(self, message_id: int, status: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE giveaways SET status = ? WHERE message_id = ?", (status, message_id))
            await db.commit()

    async def update_requirements(
        self,
        message_id: int,
        required_role_id: Optional[int] = None,
        min_messages: Optional[int] = None,
        min_invites: Optional[int] = None
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            query_parts = []
            params = []
            if required_role_id is not None:
                query_parts.append("required_role_id = ?")
                params.append(required_role_id)
            if min_messages is not None:
                query_parts.append("min_messages = ?")
                params.append(min_messages)
            if min_invites is not None:
                query_parts.append("min_invites = ?")
                params.append(min_invites)
            params.append(message_id)
            if query_parts:
                await db.execute(f"UPDATE giveaways SET {', '.join(query_parts)} WHERE message_id = ?", params)
                await db.commit()

    # ---------------- Entries ----------------
    async def add_entry(self, message_id: int, user_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO entries (message_id, user_id) VALUES (?, ?)",
                (message_id, user_id)
            )
            await db.commit()

    async def remove_entry(self, message_id: int, user_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM entries WHERE message_id = ? AND user_id = ?", (message_id, user_id))
            await db.commit()

    async def get_entries(self, message_id: int) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM entries WHERE message_id = ?", (message_id,))
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    # ---------------- Manager Role ----------------
    async def set_manager_role(self, guild_id: int, role_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO giveaway_manager_role (guild_id, role_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id
            """, (guild_id, role_id))
            await db.commit()

    async def get_manager_role(self, guild_id: int) -> Optional[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT role_id FROM giveaway_manager_role WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            return row[0] if row else None

    # ---------------- Requirements helpers ----------------
    async def get_messages(self, guild_id: int, user_id: int) -> int:
        """Fetch message count from messages table."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT message_count FROM messages WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_invites(self, guild_id: int, user_id: int) -> int:
        """Fetch invite count from invites table."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT invites FROM invites WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
