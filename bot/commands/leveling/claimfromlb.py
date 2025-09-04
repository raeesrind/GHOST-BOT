import discord
from discord.ext import commands
import re
from bot.database.database import database
from typing import List, Dict

class LeaderboardProcessor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.currently_processing = False

    @commands.command(name="processleaderboard")
    @commands.has_permissions(administrator=True)
    async def process_leaderboard(self, ctx: commands.Context):
        if self.currently_processing:
            return await ctx.send("⚠️ Already processing a leaderboard. Please wait.")

        self.currently_processing = True
        try:
            await ctx.typing()

            if not ctx.message.reference:
                self.currently_processing = False
                return await ctx.send("❌ Please reply to the leaderboard message with `?processleaderboard`.")

            referenced_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)

            processed_data = await self.process_all_pages(ctx)
            if not processed_data:
                self.currently_processing = False
                return await ctx.send("❌ No valid leaderboard data found. Make sure you're replying to the leaderboard.")

            await self.store_leaderboard_data(ctx.guild, processed_data)
            await ctx.send(f"✅ Successfully processed {len(processed_data)} leaderboard entries!")

        except Exception as e:
            await ctx.send(f"❌ Error processing leaderboard: {str(e)}")
        finally:
            self.currently_processing = False

    async def process_all_pages(self, ctx: commands.Context) -> List[Dict]:
        all_entries = []
        current_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        processed_pages = set()

        while current_msg:
            if current_msg.id in processed_pages:
                break

            processed_pages.add(current_msg.id)

            content = current_msg.content or (current_msg.embeds[0].description if current_msg.embeds else "")
            entries = self.extract_entries_from_message(content)
            if not entries:
                break

            all_entries.extend(entries)

            next_page_msg = await self.find_next_page(ctx, current_msg)
            if not next_page_msg:
                break

            current_msg = next_page_msg

        return all_entries

    def extract_entries_from_message(self, content: str) -> List[Dict]:
        entries = []
        if not content or "Level" not in content or "xp" not in content:
            return entries

        pattern = r"\*\*([^*]+)\*\*\s+Level\s+(\d+)\s+\(([^)]+)\s*xp\)"
        matches = list(re.finditer(pattern, content))

        for match in matches:
            try:
                username = match.group(1).strip()
                level = int(match.group(2))
                xp_str = match.group(3).strip()
                entries.append({
                    'username': username,
                    'level': level,
                    'xp': self.convert_xp_string(xp_str)
                })
            except Exception:
                continue

        return entries

    def convert_xp_string(self, xp_str: str) -> int:
        xp_str = xp_str.lower().strip()
        multipliers = {'k': 1000, 'm': 1_000_000, 'b': 1_000_000_000}
        if xp_str[-1] in multipliers:
            try:
                return int(float(xp_str[:-1]) * multipliers[xp_str[-1]])
            except ValueError:
                return 0
        try:
            return int(xp_str)
        except ValueError:
            return 0

    async def find_next_page(self, ctx, current_msg):
        try:
            async for message in ctx.channel.history(limit=20, after=current_msg):
                content = message.content or (message.embeds[0].description if message.embeds else "")
                if message.author.bot and "Level" in content and "xp" in content:
                    return message
        except Exception:
            return None
        return None

    async def store_leaderboard_data(self, guild: discord.Guild, entries: List[Dict]):
        await guild.chunk()
        guild_id_str = str(guild.id)

        for entry in entries:
            username = entry['username'].lower()
            xp = entry['xp']

            matched_member = discord.utils.find(
                lambda m: m.name.lower() == username or (m.nick and m.nick.lower() == username),
                guild.members
            )

            if matched_member:
                user_id = str(matched_member.id)
                await database.db.execute(
                    """
                    INSERT INTO user_xp (guild_id, user_id, xp)
                    VALUES (?, ?, ?)
                    ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    xp = excluded.xp
                    """,
                    (guild_id_str, user_id, xp)
                )
            else:
                print(f"⚠️ Could not match username: {username}")

        await database.db.commit()

async def setup(bot):
    await bot.add_cog(LeaderboardProcessor(bot))
