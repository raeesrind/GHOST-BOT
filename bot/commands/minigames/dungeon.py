import discord
from discord.ext import commands
from discord import app_commands
import random
import aiosqlite
import asyncio
from datetime import datetime, timedelta

DATABASE = "data/player.db"

RANKS = {
    "E": (0, 300),
    "D": (300, 500),
    "C": (500, 700),
    "B": (700, 2000),
    "A": (2000, 10000),
    "S": (10000, 50000),
    "Monarch": (50000, float('inf'))
}

DUNGEONS = {
    "E": {"exp_range": (10, 50), "gold_range": (50, 150), "completion_time": 30, "failure_chance": 0.1},
    "D": {"exp_range": (25, 80), "gold_range": (100, 300), "completion_time": 60, "failure_chance": 0.2},
    "C": {"exp_range": (45, 100), "gold_range": (250, 500), "completion_time": 120, "failure_chance": 0.3},
    "B": {"exp_range": (75, 120), "gold_range": (400, 800), "completion_time": 120, "failure_chance": 0.4},
    "A": {"exp_range": (100, 180), "gold_range": (700, 1200), "completion_time": 180, "failure_chance": 0.5},
    "S": {"exp_range": (150, 550), "gold_range": (1000, 2000), "completion_time": 180, "failure_chance": 0.6},
    "Monarch": {"exp_range": (150, 1050), "gold_range": (1000, 2000), "completion_time": 30, "failure_chance": 0.8}
}

ITEMS = {
    "E": ["Wooden Sword", "Leather Armor", "Health Potion"],
    "D": ["Iron Sword", "Chain Mail", "Mana Potion"],
    "C": ["Steel Sword", "Steel Armor", "Enhancement Stone"],
    "B": ["Mithril Sword", "Mithril Armor", "Ancient Scroll"],
    "A": ["Dragon Sword", "Dragon Armor", "Legendary Stone"],
    "S": ["Divine Weapon", "Divine Armor", "Immortality Potion"],
    "Monarch": ["Shadow Army", "Heavenly devil", "GOD TITLE"]
}

async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER,
                guild_id INTEGER,
                exp INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                inventory TEXT DEFAULT '',
                current_dungeon TEXT DEFAULT '',
                rank TEXT DEFAULT 'E',
                last_dungeon REAL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                guild_id INTEGER PRIMARY KEY,
                dungeon_channel_id INTEGER
            )
        ''')
        await db.commit()

class Dungeon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_player(self, user_id: int, guild_id: int):
        await init_db()
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT * FROM players WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            player = await cursor.fetchone()
            if not player:
                await db.execute("INSERT INTO players (user_id, guild_id) VALUES (?, ?)", (user_id, guild_id))
                await db.commit()
                return (user_id, guild_id, 0, 0, '', '', 'E', 0)
            return player

    async def update_player(self, user_id: int, guild_id: int, **kwargs):
        if not kwargs:
            return
        columns = []
        values = []
        for key, value in kwargs.items():
            columns.append(f"{key} = ?")
            values.append(value)
        values.extend([user_id, guild_id])
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute(f"UPDATE players SET {', '.join(columns)} WHERE user_id = ? AND guild_id = ?", tuple(values))
            await db.commit()

    async def get_dungeon_channel(self, guild_id: int):
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT dungeon_channel_id FROM settings WHERE guild_id = ?", (guild_id,))
            row = await cursor.fetchone()
            return row[0] if row else None

    def update_rank(self, exp: int):
        for r, (min_exp, max_exp) in RANKS.items():
            if min_exp <= exp < max_exp:
                return r
        return "E"

    @commands.hybrid_command(name="dungset", description="Set the allowed dungeon channel.")
    @commands.has_permissions(administrator=True)
    async def dungset(self, ctx: commands.Context, channel: discord.TextChannel = None):
        if not channel:
            channel = ctx.channel
        await init_db()
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("""
                INSERT INTO settings (guild_id, dungeon_channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET dungeon_channel_id = excluded.dungeon_channel_id
            """, (ctx.guild.id, channel.id))
            await db.commit()
        await ctx.reply(f"✅ Dungeon commands locked to {channel.mention}")

    @commands.hybrid_command(name="dungprofile", description="View a hunter profile")
    @app_commands.describe(user="Mention a user to view their profile")
    async def profile(self, ctx: commands.Context, user: discord.User = None):
        if ctx.guild:
            allowed_channel_id = await self.get_dungeon_channel(ctx.guild.id)
            if allowed_channel_id and ctx.channel.id != allowed_channel_id:
                return
        user = user or ctx.author
        player = await self.get_player(user.id, ctx.guild.id)
        _, _, exp, gold, inventory, current_dungeon, rank, _ = player
        inv = inventory.split(',') if inventory else []

        embed = discord.Embed(title=f"{user.name}'s Hunter Profile", color=discord.Color.blue())
        embed.add_field(name="🏅 Rank", value=rank, inline=True)
        embed.add_field(name="🌟 EXP", value=exp, inline=True)
        embed.add_field(name="💰 Gold", value=gold, inline=True)
        embed.add_field(name="📦 Inventory", value="\n".join(inv) if inv else "Empty", inline=False)
        embed.add_field(name="🗜️ Current Dungeon", value=current_dungeon or "None", inline=False)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="dungleaderboard", description="View the top hunters")
    async def leaderboard(self, ctx: commands.Context):
        if ctx.guild:
            allowed_channel_id = await self.get_dungeon_channel(ctx.guild.id)
            if allowed_channel_id and ctx.channel.id != allowed_channel_id:
                return

        await init_db()
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute(
                "SELECT user_id, exp, gold, rank FROM players WHERE guild_id = ? ORDER BY exp DESC, gold DESC LIMIT 10",
                (ctx.guild.id,)
            )
            top_players = await cursor.fetchall()

        embed = discord.Embed(title="🏆 Top Hunters Leaderboard", color=discord.Color.gold())
        for i, (uid, exp, gold, rank) in enumerate(top_players, 1):
            try:
                user = await self.bot.fetch_user(uid)
                name = user.name
            except:
                name = f"Unknown ({uid})"
            embed.add_field(name=f"{i}. {name}", value=f"Rank: {rank} | EXP: {exp} | Gold: {gold}", inline=False)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="dungeon", description="Enter a dungeon of specified rank")
    @app_commands.describe(rank="Dungeon rank: E, D, C, B, A, S, Monarch")
    async def dungeon(self, ctx: commands.Context, rank: str = None):
        if ctx.guild:
            allowed_channel_id = await self.get_dungeon_channel(ctx.guild.id)
            if allowed_channel_id and ctx.channel.id != allowed_channel_id:
                return

        player = await self.get_player(ctx.author.id, ctx.guild.id)
        user_id, _, exp, gold, inventory, current_dungeon, current_rank, last_dungeon = player
        if current_dungeon:
            return await ctx.reply("⚠️ You are already in a dungeon!")

        if rank is None or rank.upper() not in DUNGEONS:
            return await ctx.reply("Please specify a valid dungeon rank (E, D, C, B, A, S, Monarch).")

        rank = rank.upper()
        if exp < RANKS[rank][0]:
            return await ctx.reply(f"❌ You don't have enough EXP to enter a Rank {rank} dungeon.")

        cooldown = datetime.utcnow() - datetime.utcfromtimestamp(last_dungeon)
        if cooldown.total_seconds() < 60:
            return await ctx.reply("⏳ You must wait before entering another dungeon!")

        await ctx.reply(f"🛡️ You entered a Rank {rank} dungeon! Hold tight...")
        await self.update_player(user_id, ctx.guild.id, current_dungeon=rank)

        await asyncio.sleep(DUNGEONS[rank]["completion_time"])
        success = random.random() > DUNGEONS[rank]["failure_chance"]
        items = []

        if success:
            gained_exp = random.randint(*DUNGEONS[rank]["exp_range"])
            gained_gold = random.randint(*DUNGEONS[rank]["gold_range"])
            if random.random() < 0.3:
                item = random.choice(ITEMS[rank])
                items.append(item)
                inventory = (inventory + "," + item).strip(",")

            new_exp = exp + gained_exp
            new_rank = self.update_rank(new_exp)

            await self.update_player(user_id, ctx.guild.id,
                                     exp=new_exp,
                                     gold=gold + gained_gold,
                                     inventory=inventory,
                                     current_dungeon='',
                                     rank=new_rank,
                                     last_dungeon=datetime.utcnow().timestamp())

            embed = discord.Embed(title=f"✅ Dungeon Cleared - Rank {rank}", color=discord.Color.green())
            embed.add_field(name="EXP Gained", value=str(gained_exp))
            embed.add_field(name="Gold Earned", value=str(gained_gold))
            if items:
                embed.add_field(name="Item Found", value=", ".join(items))
        else:
            penalty = int(gold * 0.1)
            await self.update_player(user_id, ctx.guild.id,
                                     gold=gold - penalty,
                                     current_dungeon='',
                                     last_dungeon=datetime.utcnow().timestamp())
            embed = discord.Embed(title=f"❌ Dungeon Failed - Rank {rank}", color=discord.Color.red())
            embed.add_field(name="Penalty", value=f"Lost {penalty} gold.")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Dungeon(bot))
