import discord
from discord.ext import commands
import aiosqlite

# Shared database path used across purrbot modules
DATABASE = "media.db"

class PurrSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setship", help="Set the ship channel for this server")
    @commands.has_permissions(manage_guild=True)
    async def set_ship_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        async with aiosqlite.connect(DATABASE) as db:
            # Create table if it doesn't exist
            await db.execute("""
                CREATE TABLE IF NOT EXISTS purrbot_settings (
                    guild_id INTEGER PRIMARY KEY,
                    ship_channel_id INTEGER
                )
            """)
            # Insert or update the channel
            await db.execute(
                "INSERT OR REPLACE INTO purrbot_settings (guild_id, ship_channel_id) VALUES (?, ?)",
                (ctx.guild.id, channel.id),
            )
            await db.commit()

        await ctx.send(f"✅ Ship channel set to {channel.mention}")

async def setup(bot):
    await bot.add_cog(PurrSetup(bot))
