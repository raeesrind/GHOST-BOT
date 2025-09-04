import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database


class XPAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute("SELECT leveling_enabled FROM xp_settings WHERE guild_id = ?", (str(guild_id),)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

    async def get_prefix(self, guild_id):
        return "?"

    def error_embed(self, msg: str):
        return discord.Embed(description=f"❌ {msg}", color=discord.Color.red())

    def success_embed(self, member: discord.Member, xp: int, action: str):
        action_verb = "given" if action == "give" else "removed"
        return discord.Embed(
            title=f"✅ XP {action_verb.capitalize()}",
            description=f"{xp:,} XP has been {action_verb} for {member.mention}.",
            color=discord.Color.green()
        )

    def help_embed(self, prefix: str, command: str):
        if command == "givexp":
            return discord.Embed(
                title="📘 Usage: Give XP",
                description=(
                    f"**Command:** `{prefix}givexp`\n"
                    "**Description:** Give a specific amount of XP to a user.\n\n"
                    "**Usage:**\n"
                    f"`{prefix}givexp @user <amount>`\n\n"
                    "**Example:**\n"
                    f"`{prefix}givexp @John 150`"
                ),
                color=discord.Color.blurple()
            )
        elif command == "removexp":
            return discord.Embed(
                title="📘 Usage: Remove XP",
                description=(
                    f"**Command:** `{prefix}removexp`\n"
                    "**Description:** Remove a specific amount of XP from a user.\n\n"
                    "**Usage:**\n"
                    f"`{prefix}removexp @user <amount>`\n\n"
                    "**Example:**\n"
                    f"`{prefix}removexp @John 150`"
                ),
                color=discord.Color.blurple()
            )

    # ===================== PREFIX COMMANDS =====================

    @commands.command(name="givexp", help="Give XP to a user.")
    @commands.has_permissions(administrator=True)
    async def give_prefix(self, ctx, member: discord.Member = None, amount: int = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send(embed=self.error_embed("Leveling system is disabled."))

        prefix = await self.get_prefix(ctx.guild.id)

        if member is None or amount is None:
            return await ctx.send(embed=self.help_embed(prefix, "givexp"))

        await self.modify_xp(str(ctx.guild.id), str(member.id), amount)
        await ctx.send(embed=self.success_embed(member, amount, "give"))

    @commands.command(name="removexp", help="Remove XP from a user.")
    @commands.has_permissions(administrator=True)
    async def remove_prefix(self, ctx, member: discord.Member = None, amount: int = None):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send(embed=self.error_embed("Leveling system is disabled."))

        prefix = await self.get_prefix(ctx.guild.id)

        if member is None or amount is None:
            return await ctx.send(embed=self.help_embed(prefix, "removexp"))

        await self.modify_xp(str(ctx.guild.id), str(member.id), -amount)
        await ctx.send(embed=self.success_embed(member, amount, "remove"))

    # ===================== SLASH COMMANDS =====================

    @app_commands.command(name="givexp", description="Give XP to a user.")
    @app_commands.checks.has_permissions(administrator=True)
    async def give_slash(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message(embed=self.error_embed("Leveling system is disabled."), ephemeral=True)

        await self.modify_xp(str(interaction.guild.id), str(member.id), amount)
        await interaction.response.send_message(embed=self.success_embed(member, amount, "give"), ephemeral=True)

    @app_commands.command(name="removexp", description="Remove XP from a user.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_slash(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message(embed=self.error_embed("Leveling system is disabled."), ephemeral=True)

        await self.modify_xp(str(interaction.guild.id), str(member.id), -amount)
        await interaction.response.send_message(embed=self.success_embed(member, amount, "remove"), ephemeral=True)

    # ===================== DATABASE =====================

    async def modify_xp(self, guild_id: str, user_id: str, xp_change: int):
        async with database.db.execute("SELECT xp FROM user_xp WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
            row = await cursor.fetchone()
        current = row[0] if row else 0
        new_xp = max(current + xp_change, 0)

        await database.db.execute("""
            INSERT INTO user_xp (guild_id, user_id, xp)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = ?
        """, (guild_id, user_id, new_xp, new_xp))
        await database.db.commit()

    # ===================== ERROR HANDLERS =====================

    @give_prefix.error
    @remove_prefix.error
    async def on_prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=self.error_embed("You need Administrator permission to use this command."))
        else:
            await ctx.send(embed=self.error_embed(f"An error occurred: `{error}`"))

    @give_slash.error
    @remove_slash.error
    async def on_slash_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=self.error_embed("You need Administrator permission to use this command."), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=self.error_embed(f"An error occurred: `{error}`"), ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(XPAdmin(bot))
