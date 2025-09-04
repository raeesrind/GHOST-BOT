import aiosqlite
from pathlib import Path

DB_PATH = Path("data/ghost.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

class Database:
    def __init__(self):
        self.db: aiosqlite.Connection = None

    async def connect(self):
        self.db = await aiosqlite.connect(DB_PATH)
        self.db.row_factory = aiosqlite.Row
        await self.db.execute("PRAGMA foreign_keys = ON")
        await self.create_tables()
        await self.run_migrations()

    async def create_tables(self):
        await self.db.executescript("""
        CREATE TABLE IF NOT EXISTS user_xp (
            guild_id TEXT,
            user_id TEXT,
            xp INTEGER DEFAULT 0,
            xp_user INTEGER DEFAULT 0,
            last_message_ts INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS level_roles (
            guild_id TEXT,
            level INTEGER,
            role_id TEXT,
            PRIMARY KEY (guild_id, level)
        );

        CREATE TABLE IF NOT EXISTS xp_multipliers (
            guild_id TEXT,
            target_id TEXT,
            type TEXT CHECK(type IN ('channel', 'role')),
            multiplier REAL,
            PRIMARY KEY (guild_id, target_id, type)
        );

        CREATE TABLE IF NOT EXISTS no_xp_channels (
            guild_id TEXT,
            channel_id TEXT,
            PRIMARY KEY (guild_id, channel_id)
        );

        CREATE TABLE IF NOT EXISTS config (
            guild_id TEXT PRIMARY KEY,
            leveling_enabled INTEGER DEFAULT 1,
            xp_cooldown_seconds INTEGER DEFAULT 60,
            global_multiplier REAL DEFAULT 1.0,
            rankup_mode TEXT DEFAULT 'channel',
            rankup_channel TEXT,
            role_mode TEXT DEFAULT 'highest'
        );

        CREATE TABLE IF NOT EXISTS xp_settings (
            guild_id TEXT PRIMARY KEY,
            leveling_enabled INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS claimed_xp (
            guild_id TEXT,
            user_id TEXT,
            claimed INTEGER DEFAULT 1,
            PRIMARY KEY (guild_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS leaderboard_data (
            guild_id TEXT NOT NULL,
            username TEXT NOT NULL,
            level INTEGER NOT NULL,
            xp INTEGER NOT NULL
        );
        """)
        await self.db.commit()

    async def run_migrations(self):
        # Ensure xp_user column exists
        async with self.db.execute("PRAGMA table_info(user_xp)") as cursor:
            columns = [row["name"] async for row in cursor]
        if "xp_user" not in columns:
            await self.db.execute("ALTER TABLE user_xp ADD COLUMN xp_user INTEGER DEFAULT 0")
            await self.db.commit()

        # Ensure role_mode column exists in xp_settings
        async with self.db.execute("PRAGMA table_info(xp_settings)") as cursor:
            columns = [row["name"] async for row in cursor]
        if "role_mode" not in columns:
            await self.db.execute("ALTER TABLE xp_settings ADD COLUMN role_mode TEXT DEFAULT 'highest'")
            await self.db.commit()

    async def update_xp(self, guild_id, user_id, xp, ts):
        existing = await self.get_xp(guild_id, user_id)
        if existing:
            await self.db.execute("""
                UPDATE user_xp SET xp = xp + ?, last_message_ts = ?
                WHERE guild_id = ? AND user_id = ?
            """, (xp, ts, guild_id, user_id))
        else:
            await self.db.execute("""
                INSERT INTO user_xp (guild_id, user_id, xp, last_message_ts)
                VALUES (?, ?, ?, ?)
            """, (guild_id, user_id, xp, ts))
        await self.db.commit()

    async def get_xp(self, guild_id, user_id):
        async with self.db.execute("""
            SELECT xp, xp_user, last_message_ts FROM user_xp
            WHERE guild_id = ? AND user_id = ?
        """, (guild_id, user_id)) as cursor:
            return await cursor.fetchone()

    async def set_user_custom_xp(self, guild_id, user_id, xp_amount):
        existing = await self.get_xp(guild_id, user_id)
        if existing:
            await self.db.execute("""
                UPDATE user_xp SET 
                    xp = xp + ?, 
                    xp_user = xp_user + ?
                WHERE guild_id = ? AND user_id = ?
            """, (xp_amount, xp_amount, guild_id, user_id))
        else:
            await self.db.execute("""
                INSERT INTO user_xp (guild_id, user_id, xp, xp_user)
                VALUES (?, ?, ?, ?)
            """, (guild_id, user_id, xp_amount, xp_amount))
        await self.db.commit()

    async def remove_user_custom_xp(self, guild_id, user_id, xp_amount):
        existing = await self.get_xp(guild_id, user_id)
        if existing:
            new_xp = max(0, existing["xp"] - xp_amount)
            new_xp_user = max(0, existing["xp_user"] - xp_amount)
            await self.db.execute("""
                UPDATE user_xp SET 
                    xp = ?, 
                    xp_user = ?
                WHERE guild_id = ? AND user_id = ?
            """, (new_xp, new_xp_user, guild_id, user_id))
            await self.db.commit()

    async def get_leaderboard(self, guild_id, limit=10):
        async with self.db.execute("""
            SELECT user_id, xp FROM user_xp
            WHERE guild_id = ? 
            ORDER BY xp DESC LIMIT ?
        """, (guild_id, limit)) as cursor:
            return await cursor.fetchall()

    async def reset_user(self, guild_id, user_id):
        await self.db.execute("""
            DELETE FROM user_xp WHERE guild_id = ? AND user_id = ?
        """, (guild_id, user_id))
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()

# ✅ Singleton instance
database = Database()
