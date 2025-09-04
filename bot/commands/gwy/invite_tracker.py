# invite_tracker.py
import discord
from discord.ext import commands
import aiosqlite

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}

    async def cog_load(self):
        # Load DB table
        async with aiosqlite.connect("giveaways.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS invites (
                    guild_id INTEGER,
                    user_id INTEGER,
                    invites INTEGER,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.commit()

        # Cache invites
        for guild in self.bot.guilds:
            self.invites[guild.id] = await guild.invites()

    async def add_invite(self, guild_id: int, user_id: int):
        async with aiosqlite.connect("giveaways.db") as db:
            await db.execute("""
                INSERT INTO invites (guild_id, user_id, invites) 
                VALUES (?, ?, 1)
                ON CONFLICT(guild_id, user_id) 
                DO UPDATE SET invites = invites + 1
            """, (guild_id, user_id))
            await db.commit()

    async def remove_invite(self, guild_id: int, user_id: int):
        async with aiosqlite.connect("giveaways.db") as db:
            await db.execute("""
                UPDATE invites
                SET invites = CASE 
                    WHEN invites > 0 THEN invites - 1 
                    ELSE 0 
                END
                WHERE guild_id = ? AND user_id = ?
            """, (guild_id, user_id))
            await db.commit()

    async def get_invites(self, guild_id: int, user_id: int):
        async with aiosqlite.connect("giveaways.db") as db:
            cursor = await db.execute("SELECT invites FROM invites WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
            row = await cursor.fetchone()
            return row[0] if row else 0

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        new_invites = await guild.invites()
        old_invites = self.invites[guild.id]

        inviter = None
        for invite in new_invites:
            for old in old_invites:
                if invite.code == old.code and invite.uses > old.uses:
                    inviter = invite.inviter
                    break

        self.invites[guild.id] = new_invites

        if inviter:
            await self.add_invite(guild.id, inviter.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        # Optional: remove one invite from inviter if member leaves
        # (can be debated; some servers don't reduce invites)
        # self.remove_invite(guild.id, inviter_id) if tracked

    @commands.hybrid_command(name="invites", description="Check your invite count.")
    async def invites_command(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        count = await self.get_invites(ctx.guild.id, member.id)
        await ctx.send(f"🎟️ {member.mention} has **{count}** invites.")

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))
