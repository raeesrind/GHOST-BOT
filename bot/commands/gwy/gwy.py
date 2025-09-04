import re
import datetime as dt
from typing import Optional, Literal
import random

import discord
from discord import app_commands
from discord.ext import commands

from bot.database.gwydb import GwyDB
from bot.utils.gwymanager import GiveawayManager, JOIN_EMOJI, UTC

# ---------------------- duration parsing ----------------------
DUR_RE = re.compile(r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$", re.I)
DURATION_HINT = "Examples: 30m, 2h, 1d12h"

def parse_duration_to_seconds(s: str) -> Optional[int]:
    s = s.strip().lower()
    m = DUR_RE.match(s)
    if not m:
        return None
    d, h, m_, s_ = (int(x) if x else 0 for x in m.groups())
    total = d * 86400 + h * 3600 + m_ * 60 + s_
    return total or None

# ---------------------- Giveaway Cog ----------------------
class GiveawayCog(commands.Cog):
    """
    Professional giveaway cog with slash commands, listeners, and manager role checks.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = GwyDB()
        self.manager = GiveawayManager(bot, self.db)

    # ---------------------- Cog lifecycle ----------------------
    async def cog_load(self):
        await self.db.setup()
        await self.manager.load_giveaways()

    async def cog_unload(self):
        for task in list(self.manager._tasks.values()):
            task.cancel()
        self.manager._tasks.clear()

    # ---------------------- Utilities ----------------------
    async def _require_manager_role(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("Guild-only command.", ephemeral=True)
            return False

        role_id = await self.db.get_manager_role(guild.id)
        if role_id:
            role = guild.get_role(int(role_id))
            if role and role in getattr(interaction.user, "roles", []):
                return True

        if interaction.user.guild_permissions.administrator:
            return True

        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ You don't have permission. Set a manager role with `/gsetrole`.",
                ephemeral=True,
            )
        return False

    @staticmethod
    def _fmt_time(ts: int) -> str:
        return f"<t:{ts}:F> (<t:{ts}:R>)"

    async def _update_requirement(
        self,
        interaction: discord.Interaction,
        g: dict,
        rtype: Literal["role", "min_messages", "min_invites"],
        value: str,
    ):
        if rtype == "role":
            try:
                rid = int(re.sub(r"[^\d]", "", value))
            except ValueError:
                return await interaction.response.send_message(
                    "Provide a valid role mention or ID.", ephemeral=True
                )
            await self.db.update_requirements(int(g["message_id"]), required_role_id=rid)

        elif rtype == "min_messages":
            try:
                num = int(value)
            except ValueError:
                return await interaction.response.send_message(
                    "Value must be a number.", ephemeral=True
                )
            await self.db.update_requirements(int(g["message_id"]), min_messages=num)

        elif rtype == "min_invites":
            try:
                num = int(value)
            except ValueError:
                return await interaction.response.send_message(
                    "Value must be a number.", ephemeral=True
                )
            await self.db.update_requirements(int(g["message_id"]), min_invites=num)
        else:
            return await interaction.response.send_message(
                "Unknown requirement type.", ephemeral=True
            )

        await interaction.response.send_message("✅ Requirement updated.", ephemeral=True)

    # ---------------------- Slash Commands ----------------------
    @app_commands.command(name="gstart", description="Start a giveaway in this channel.")
    @app_commands.describe(
        duration=f"Duration of giveaway ({DURATION_HINT})",
        winners="Number of winners (1-50)",
        prize="Prize for the giveaway",
    )
    async def gstart(
        self, interaction: discord.Interaction, duration: str, winners: app_commands.Range[int,1,50], prize: str
    ):
        if not await self._require_manager_role(interaction):
            return

        secs = parse_duration_to_seconds(duration)
        if not secs:
            return await interaction.response.send_message(
                f"❌ Invalid duration. {DURATION_HINT}", ephemeral=True
            )

        # Defer the ephemeral confirmation first
        await interaction.response.defer(ephemeral=True, thinking=False)

        # Post the giveaway publicly in the channel
        channel = interaction.channel  # TextChannel
        msg = await self.manager.start_giveaway(channel, int(secs), int(winners), prize)

        # Send ephemeral confirmation to the user
        await interaction.followup.send(
            f"✅ Giveaway started in {channel.mention} (ID: `{msg.id}`)", ephemeral=True
        )

    @app_commands.command(name="gdel", description="Delete a giveaway by message ID.")
    @app_commands.describe(message_id="Giveaway message ID")
    async def gdel(self, interaction: discord.Interaction, message_id: str):
        if not await self._require_manager_role(interaction):
            return
        try: mid = int(message_id)
        except ValueError: return await interaction.response.send_message("Invalid message ID.", ephemeral=True)

        g = await self.db.get_giveaway(mid)
        if not g: return await interaction.response.send_message("Giveaway not found.", ephemeral=True)

        guild = interaction.guild
        if guild:
            channel = guild.get_channel(int(g["channel_id"]))
            if isinstance(channel, discord.TextChannel):
                try: msg = await channel.fetch_message(mid); await msg.delete()
                except: pass

        await self.db.delete_giveaway(mid)
        await interaction.response.send_message("🗑️ Giveaway deleted.", ephemeral=True)

    @app_commands.command(name="gend", description="End a running giveaway now.")
    @app_commands.describe(message_id="Giveaway message ID")
    async def gend(self, interaction: discord.Interaction, message_id: str):
        if not await self._require_manager_role(interaction):
            return
        try: mid = int(message_id)
        except ValueError: return await interaction.response.send_message("Invalid message ID.", ephemeral=True)

        g = await self.db.get_giveaway(mid)
        if not g: return await interaction.response.send_message("Giveaway not found.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        try: await self.manager.end_giveaway(g)
        except: await self.db.delete_giveaway(mid)
        await interaction.followup.send("⏹️ Giveaway ended.", ephemeral=True)

    @app_commands.command(name="greroll", description="Reroll winners for a giveaway.")
    @app_commands.describe(message_id="Giveaway message ID")
    async def greroll(self, interaction: discord.Interaction, message_id: str):
        if not await self._require_manager_role(interaction):
            return
        try: mid = int(message_id)
        except ValueError: return await interaction.response.send_message("Invalid message ID.", ephemeral=True)

        g = await self.db.get_giveaway(mid)
        if not g: return await interaction.response.send_message("Giveaway not found.", ephemeral=True)

        entries = await self.db.get_entries(mid)
        if not entries: return await interaction.response.send_message("No entries to reroll.", ephemeral=True)

        random.shuffle(entries)
        winners = entries[: int(g["winners"])]
        guild = interaction.guild
        channel = guild.get_channel(int(g["channel_id"])) if guild else None
        if isinstance(channel, discord.TextChannel):
            mentions = " ".join(f"<@{w}>" for w in winners)
            await channel.send(f"🔁 Reroll winners for **{g['prize']}**: {mentions}")

        await interaction.response.send_message("✅ Winners rerolled.", ephemeral=True)

    @app_commands.command(name="glist", description="List running giveaways.")
    async def glist(self, interaction: discord.Interaction):
        if not await self._require_manager_role(interaction):
            return
        running = await self.db.get_all_giveaways()
        if not running: return await interaction.response.send_message("No running giveaways.", ephemeral=True)
        lines = [f"- **{g['prize']}** in <#{g['channel_id']}> — ends {self._fmt_time(int(g['end_time']))} — msgID `{g['message_id']}`" for g in running]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @app_commands.command(name="ginfo", description="Show info about a giveaway.")
    @app_commands.describe(message_id="Giveaway message ID")
    async def ginfo(self, interaction: discord.Interaction, message_id: str):
        try: mid = int(message_id)
        except ValueError: return await interaction.response.send_message("Invalid message ID.", ephemeral=True)
        g = await self.db.get_giveaway(mid)
        if not g: return await interaction.response.send_message("Giveaway not found.", ephemeral=True)

        entries = await self.db.get_entries(mid)
        reqs = []
        if g.get("required_role_id"): reqs.append(f"Role: <@&{int(g['required_role_id'])}>")
        if int(g.get("min_messages") or 0) > 0: reqs.append(f"Messages ≥ {int(g['min_messages'])}")
        if int(g.get("min_invites") or 0) > 0: reqs.append(f"Invites ≥ {int(g['min_invites'])}")
        reqs_str = ", ".join(reqs) if reqs else "None"

        embed = discord.Embed(
            title="Giveaway Info",
            color=discord.Color.blurple(),
            timestamp=dt.datetime.now(UTC),
        )
        embed.add_field(name="Prize", value=str(g["prize"]), inline=False)
        embed.add_field(name="Winners", value=str(g["winners"]), inline=True)
        embed.add_field(name="Status", value="Running", inline=True)
        embed.add_field(name="Ends", value=self._fmt_time(int(g["end_time"])), inline=False)
        embed.add_field(name="Channel", value=f"<#{g['channel_id']}>", inline=True)
        embed.add_field(name="Message ID", value=str(g["message_id"]), inline=True)
        embed.add_field(name="Entries", value=str(len(entries)), inline=True)
        embed.add_field(name="Requirements", value=reqs_str, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="gsetrequirement", description="Set a requirement for a running giveaway.")
    @app_commands.describe(message_id="Giveaway message ID", type="Requirement type", value="Value (role mention/ID or number)")
    @app_commands.choices(type=[
        app_commands.Choice(name="Role", value="role"),
        app_commands.Choice(name="Min Messages", value="min_messages"),
        app_commands.Choice(name="Min Invites", value="min_invites")
    ])
    async def gsetrequirement(self, interaction: discord.Interaction, message_id: str, type: app_commands.Choice[str], value: str):
        if not await self._require_manager_role(interaction):
            return
        try: mid = int(message_id)
        except ValueError: return await interaction.response.send_message("Invalid message ID.", ephemeral=True)
        g = await self.db.get_giveaway(mid)
        if not g: return await interaction.response.send_message("Giveaway not found.", ephemeral=True)
        await self._update_requirement(interaction, g, type.value, value)

    @app_commands.command(name="gsetrole", description="Set the Giveaway Manager role.")
    @app_commands.describe(role="Role that can manage giveaways")
    async def gsetrole(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Only admins can set the manager role.", ephemeral=True)
        await self.db.set_manager_role(interaction.guild_id, role.id)
        await interaction.response.send_message(f"✅ Manager role set to {role.mention}.", ephemeral=True)

    # ---------------------- Reaction Listeners ----------------------
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != JOIN_EMOJI or payload.user_id == self.bot.user.id:
            return
        g = await self.db.get_giveaway(payload.message_id)
        if not g: return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        try: member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
        except: return

        # Check requirements
        if g.get("required_role_id") and not discord.utils.get(member.roles, id=int(g["required_role_id"])):
            await self._remove_reaction(payload)
            return
        if await self.db.get_messages(guild.id, member.id) < int(g.get("min_messages") or 0):
            await self._remove_reaction(payload)
            return
        if await self.db.get_invites(guild.id, member.id) < int(g.get("min_invites") or 0):
            await self._remove_reaction(payload)
            return

        await self.db.add_entry(int(g["message_id"]), member.id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != JOIN_EMOJI or payload.user_id == self.bot.user.id:
            return
        g = await self.db.get_giveaway(payload.message_id)
        if not g: return
        await self.db.remove_entry(int(g["message_id"]), int(payload.user_id))

    async def _remove_reaction(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        channel = guild.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel): return
        try:
            msg = await channel.fetch_message(payload.message_id)
            user = guild.get_member(payload.user_id)
            if user: await msg.remove_reaction(JOIN_EMOJI, user)
        except: pass

# ---------------------- Setup ----------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayCog(bot))
