# bot/database/afkdb.py

import aiosqlite

AFK_DB = "data/afk_data.db"

async def init_afk_db():
    async with aiosqlite.connect(AFK_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS afk (
                guild_id TEXT,
                user_id TEXT,
                reason TEXT,
                original_nick TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await db.commit()

async def set_afk(guild_id, user_id, reason, original_nick):
    async with aiosqlite.connect(AFK_DB) as db:
        await db.execute("""
            INSERT OR REPLACE INTO afk (guild_id, user_id, reason, original_nick)
            VALUES (?, ?, ?, ?)
        """, (str(guild_id), str(user_id), reason, original_nick))
        await db.commit()

async def get_afk(guild_id, user_id):
    async with aiosqlite.connect(AFK_DB) as db:
        async with db.execute("""
            SELECT reason, original_nick FROM afk
            WHERE guild_id = ? AND user_id = ?
        """, (str(guild_id), str(user_id))) as cursor:
            row = await cursor.fetchone()
            return row if row else (None, None)

async def remove_afk(guild_id, user_id):
    async with aiosqlite.connect(AFK_DB) as db:
        await db.execute("""
            DELETE FROM afk WHERE guild_id = ? AND user_id = ?
        """, (str(guild_id), str(user_id)))
        await db.commit()
