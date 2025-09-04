import discord 
from discord.ext import commands
from discord import app_commands
from firebase_admin import firestore
from typing import Optional
import io

db = firestore.client()

GHOST_SUCCESS = "<:GhostSuccess:1387033552809492682>"
GHOST_ERROR = "<:GhostError:1387033531221413959>"

class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_limit_ref(self, guild_id):
        return db.collection("settings").document(str(guild_id))

    async def get_purge_limit(self, guild_id: int):
        doc = self.get_limit_ref(guild_id).get()
        if doc.exists:
            return doc.to_dict().get("purge_limit", 100)
        return 100

    async def set_purge_limit(self, guild_id: int, limit: int):
        self.get_limit_ref(guild_id).set({"purge_limit": limit}, merge=True)

    async def get_log_channel_id(self, guild_id: int):
        doc = self.get_limit_ref(guild_id).get()
        if doc.exists:
            return doc.to_dict().get("purge_log_channel")
        return None

    async def log_purge(self, guild: discord.Guild, messages: list[discord.Message]):
        if not messages:
            return

        channel_id = await self.get_log_channel_id(guild.id)
        if not channel_id:
            return

        log_channel = guild.get_channel(channel_id)
        if not log_channel:
            return

        content = ""
        for msg in reversed(messages):
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author = f"{msg.author} ({msg.author.id})"
            content += f"[{timestamp}] {author}: {msg.content}\n"

        file = discord.File(io.BytesIO(content.encode()), filename="purge_log.txt")
        await log_channel.send(file=file, content=f"{GHOST_SUCCESS} Purge log from #{messages[0].channel.name}")

    # 🔁 Prefix Command: ?purge
    @commands.command(name="purge", help="Delete messages in bulk.\n\n**Usage:** `?purge <amount>`")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: Optional[int] = None):
        if amount is None:
            return await ctx.send(embed=discord.Embed(
                title="Command: ?purge",
                description="Delete messages in bulk.\n\n**Usage:** `?purge <amount>`",
                color=discord.Color.orange()
            ))

        max_limit = await self.get_purge_limit(ctx.guild.id)

        if amount < 1 or amount > max_limit:
            return await ctx.send(f"{GHOST_ERROR} You can only purge between 1 and {max_limit} messages.")

        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"{GHOST_SUCCESS} Purged {len(deleted)-1} messages.", delete_after=5)
        await self.log_purge(ctx.guild, deleted)

    # 🔁 Prefix Command: ?setpurgenumber <number>
    @commands.command(name="setpurgenumber", help="Set the max purge limit.\n\n**Usage:** `?setpurgenumber <number>`")
    @commands.has_permissions(administrator=True)
    async def set_purge_limit_cmd(self, ctx, limit: Optional[int] = None):
        if limit is None or limit < 1 or limit > 1000:
            return await ctx.send(f"{GHOST_ERROR} Please provide a valid number (1–1000).")

        await self.set_purge_limit(ctx.guild.id, limit)
        await ctx.send(f"{GHOST_SUCCESS} Max purge limit set to `{limit}`.")

    # 🧩 Slash Command: /purge
    @app_commands.command(name="purge", description="Delete messages in bulk.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def slash_purge(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 1000]):
        max_limit = await self.get_purge_limit(interaction.guild.id)

        if amount > max_limit:
            return await interaction.response.send_message(
                f"{GHOST_ERROR} Max allowed: `{max_limit}` messages.",
                ephemeral=True
            )

        deleted = await interaction.channel.purge(limit=amount + 1)
        await interaction.response.send_message(f"{GHOST_SUCCESS} Purged {len(deleted)-1} messages.", ephemeral=True)
        await self.log_purge(interaction.guild, deleted)

    # 🧩 Slash Command: /setpurgenumber
    @app_commands.command(name="setpurgenumber", description="Set max purge limit.")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_set_limit(self, interaction: discord.Interaction, limit: app_commands.Range[int, 1, 1000]):
        await self.set_purge_limit(interaction.guild.id, limit)
        await interaction.response.send_message(f"{GHOST_SUCCESS} Max purge limit set to `{limit}`.", ephemeral=True)

    # ✅ NEW Slash Command: /setuppurgechannel
    @app_commands.command(name="setuppurgechannel", description="Set the purge logging channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def setup_purge_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        ref = self.get_limit_ref(interaction.guild.id)
        ref.set({"purge_log_channel": channel.id}, merge=True)
        await interaction.response.send_message(f"{GHOST_SUCCESS} Set purge log channel to {channel.mention}.", ephemeral=True)

    # 🔒 Handle missing permissions
    @purge.error
    @set_purge_limit_cmd.error
    async def perm_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"{GHOST_ERROR} You lack permission to use this command.")

    @slash_purge.error
    @slash_set_limit.error
    @setup_purge_channel.error
    async def slash_perm_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                f"{GHOST_ERROR} You lack permission to use this command.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Purge(bot))
