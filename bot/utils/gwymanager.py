import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Union

import discord
from discord.ext import commands
from bot.database.gwydb import GwyDB  # adjust path as needed

# Constants
JOIN_EMOJI = "🎉"
UTC = timezone.utc


class GiveawayManager:
    """
    Handles creation, tracking, rerolling, and ending giveaways.
    Fully async, persistent via GwyDB.
    """

    def __init__(self, bot: commands.Bot, db: Optional[GwyDB] = None):
        self.bot = bot
        self.db = db or GwyDB()
        self._tasks: Dict[int, asyncio.Task] = {}
        self._failsafe_task: Optional[asyncio.Task] = None

    async def load_giveaways(self):
        """Load ongoing giveaways from DB and start timers."""
        giveaways = await self.db.get_all_giveaways()
        now_ts = datetime.now(UTC).timestamp()
        for g in giveaways:
            # Only schedule for still-running ones (row exists == running)
            end_time = datetime.fromtimestamp(int(g["end_time"]), UTC)
            remaining = (end_time - datetime.now(UTC)).total_seconds()
            if remaining > 0:
                # schedule to end at the right time
                self._tasks[int(g["message_id"])] = asyncio.create_task(
                    self._end_giveaway(int(g["message_id"]), remaining)
                )
            else:
                # already expired -> end ASAP
                asyncio.create_task(self._end_giveaway(int(g["message_id"]), 0))

        # Start failsafe loop once
        if not self._failsafe_task:
            self._failsafe_task = asyncio.create_task(self._failsafe_loop())

    async def _failsafe_loop(self):
        """Checks every 60s for expired giveaways that didn't end."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.now(UTC).timestamp()
            giveaways = await self.db.get_all_giveaways()
            for g in giveaways:
                mid = int(g["message_id"])
                if int(g["end_time"]) <= now and mid not in self._tasks:
                    asyncio.create_task(self._end_giveaway(mid, 0))
            await asyncio.sleep(60)

    async def start_giveaway(
        self,
        ctx: Union[commands.Context, discord.Interaction, discord.TextChannel],
        duration: int,
        winners: int,
        prize: str,
        # keep signature extensible; requirements are configured later via commands
        requirements: Optional[str] = None
    ) -> discord.Message:
        """Start a new giveaway and schedule its end; returns the created message."""
        end_time = datetime.now(UTC) + timedelta(seconds=duration)

        author = getattr(ctx, "author", getattr(ctx, "user", None))
        channel = getattr(ctx, "channel", ctx)
        guild = getattr(ctx, "guild", getattr(channel, "guild", None))

        embed = discord.Embed(
            title="🎉 Giveaway Started! 🎉",
            description=(
                f"**Prize:** {prize}\n"
                f"**Hosted by:** {author.mention}\n"
                f"**Ends:** <t:{int(end_time.timestamp())}:R>"
            ),
            color=discord.Color.blurple()
        )
        if requirements:
            # purely informational; enforced reqs are stored & checked elsewhere
            embed.add_field(name="Requirements", value=requirements, inline=False)

        embed.set_footer(text=f"{winners} winner(s) • React with {JOIN_EMOJI} to join!")

        # ---- FIXED INTERACTION HANDLING ----
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                # already deferred
                message = await ctx.followup.send(embed=embed)
            else:
                await ctx.response.send_message(embed=embed)
                message = await ctx.original_response()
        else:
            message = await channel.send(embed=embed)
        # ------------------------------------

        try:
            await message.add_reaction(JOIN_EMOJI)
        except discord.HTTPException:
            pass

        # Persist in DB (defaults: required_role_id=None, min_messages=0, min_invites=0)
        await self.db.add_giveaway(
            message_id=message.id,
            channel_id=channel.id,
            guild_id=guild.id,
            prize=prize,
            winners=int(winners),
            end_time=int(end_time.timestamp()),
            host_id=author.id,
        )

        # Schedule end
        self._tasks[message.id] = asyncio.create_task(
            self._end_giveaway(message.id, duration)
        )

        return message

    async def _end_giveaway(self, message_id: int, delay: float):
        """Ends a giveaway after a delay."""
        if delay > 0:
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return

        giveaway = await self.db.get_giveaway(message_id)
        if not giveaway:
            # already ended/removed
            return

        await self.end_giveaway(giveaway)

    async def end_giveaway(self, giveaway: dict):
        """Immediately ends a giveaway (public method)."""
        message_id = int(giveaway["message_id"])
        channel = self.bot.get_channel(int(giveaway["channel_id"]))
        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.VoiceChannel)):
            await self.db.delete_giveaway(message_id)
            return

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await self.db.delete_giveaway(message_id)
            return

        entries = await self.db.get_entries(message_id)
        if not entries:
            embed = discord.Embed(
                title="🎉 Giveaway Ended 🎉",
                description=f"**Prize:** {giveaway['prize']}\nNo valid entries 😢",
                color=discord.Color.red()
            )
            try:
                await message.edit(embed=embed)
            except discord.HTTPException:
                pass
            await self.db.delete_giveaway(message_id)
            self._tasks.pop(message_id, None)
            return

        winners = random.sample(entries, min(len(entries), int(giveaway["winners"])))
        mentions = ", ".join(f"<@{uid}>" for uid in winners)

        embed = discord.Embed(
            title="🎉 Giveaway Ended 🎉",
            description=f"**Prize:** {giveaway['prize']}\n**Winner(s):** {mentions}",
            color=discord.Color.green()
        )
        try:
            await message.edit(embed=embed)
        except discord.HTTPException:
            pass
        try:
            await channel.send(f"🎉 Congratulations {mentions}! You won **{giveaway['prize']}**!")
        except discord.HTTPException:
            pass

        await self.db.delete_giveaway(message_id)
        task = self._tasks.pop(message_id, None)
        if task:
            task.cancel()

    async def reroll(self, ctx, message_id: int):
        """Reroll winners for a finished giveaway or running one (uses current entries)."""
        giveaway = await self.db.get_giveaway(message_id)
        if not giveaway:
            return await ctx.send("❌ No giveaway found with that message ID.")

        entries = await self.db.get_entries(message_id)
        if not entries:
            return await ctx.send("❌ No valid entries to reroll.")

        winners = random.sample(entries, min(len(entries), int(giveaway["winners"])))
        mentions = ", ".join(f"<@{uid}>" for uid in winners)
        await ctx.send(f"🎉 Reroll Results! 🎉\nNew winner(s): {mentions}\nPrize: **{giveaway['prize']}**")

    async def delete_giveaway(self, ctx, message_id: int):
        """Delete a giveaway immediately (message + DB row)."""
        giveaway = await self.db.get_giveaway(message_id)
        if not giveaway:
            return await ctx.send("❌ No giveaway found with that message ID.")

        channel = self.bot.get_channel(int(giveaway["channel_id"]))
        if channel:
            try:
                msg = await channel.fetch_message(message_id)
                await msg.delete()
            except discord.NotFound:
                pass
            except discord.HTTPException:
                pass

        await self.db.delete_giveaway(message_id)
        task = self._tasks.pop(message_id, None)
        if task:
            task.cancel()
        await ctx.send("✅ Giveaway deleted successfully.")
