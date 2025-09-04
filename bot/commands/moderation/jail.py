import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

GHOST_SUCCESS = "<:GhostSuccess:1387033552809492682>"
GHOST_ERROR = "<:GhostError:1387033531221413959>"

class Jail(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "data/jail.db"

    async def cog_load(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jailed_users (
                    guild_id INTEGER,
                    user_id INTEGER,
                    roles TEXT,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS jail_settings (
                    guild_id INTEGER PRIMARY KEY,
                    jail_role_id INTEGER,
                    log_channel_id INTEGER
                )
            """)
            await db.commit()

    # ----------------- DB HELPERS -----------------
    async def get_settings(self, guild: discord.Guild):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT jail_role_id, log_channel_id FROM jail_settings WHERE guild_id = ?", (guild.id,)
            ) as cursor:
                row = await cursor.fetchone()
        if row:
            return (guild.get_role(row[0]) if row[0] else None,
                    guild.get_channel(row[1]) if row[1] else None)
        return None, None

    async def set_jail_role_db(self, guild_id: int, role_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO jail_settings (guild_id, jail_role_id, log_channel_id)
                VALUES (?, ?, COALESCE((SELECT log_channel_id FROM jail_settings WHERE guild_id = ?), NULL))
                ON CONFLICT(guild_id) DO UPDATE SET jail_role_id=excluded.jail_role_id
            """, (guild_id, role_id, guild_id))
            await db.commit()

    async def set_log_channel_db(self, guild_id: int, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO jail_settings (guild_id, jail_role_id, log_channel_id)
                VALUES (?, COALESCE((SELECT jail_role_id FROM jail_settings WHERE guild_id = ?), NULL), ?)
                ON CONFLICT(guild_id) DO UPDATE SET log_channel_id=excluded.log_channel_id
            """, (guild_id, guild_id, channel_id))
            await db.commit()

    # ----------------- CORE ACTIONS -----------------
    async def jail_user_core(self, guild, executor, member, reason):
        if member.guild_permissions.administrator:
            return False, discord.Embed(title=f"{GHOST_ERROR} Cannot Jail Admin",
                                        description=f"{member.mention} is an administrator and cannot be jailed.",
                                        color=discord.Color.red())
        if member == executor:
            return False, discord.Embed(title=f"{GHOST_ERROR} Invalid Action",
                                        description="You cannot jail yourself.",
                                        color=discord.Color.red())

        jail_role, log_channel = await self.get_settings(guild)
        if not jail_role:
            return False, discord.Embed(title=f"{GHOST_ERROR} Jail Role Not Set",
                                        description="Please set a jail role first.",
                                        color=discord.Color.red())
        try:
            # ✅ Save original roles (excluding @everyone and jail role)
            original_roles = [role.id for role in member.roles if role != guild.default_role and role != jail_role]

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("INSERT OR REPLACE INTO jailed_users (guild_id, user_id, roles) VALUES (?, ?, ?)",
                                 (guild.id, member.id, ",".join(map(str, original_roles))))
                await db.commit()

            # ✅ Keep booster role(s) intact
            booster_roles = [r for r in member.roles if r.is_premium_subscriber()]
            new_roles = [jail_role] + booster_roles

            await member.edit(roles=new_roles, reason=f"Jailed by {executor} | {reason}")

            if log_channel:
                embed_log = discord.Embed(title=f"{GHOST_ERROR} User Jailed", color=discord.Color.red())
                embed_log.add_field(name="User", value=member.mention, inline=True)
                embed_log.add_field(name="By", value=executor.mention, inline=True)
                embed_log.add_field(name="Reason", value=reason, inline=False)
                embed_log.set_thumbnail(url=member.display_avatar.url)
                await log_channel.send(embed=embed_log)

            return True, discord.Embed(title=f"{GHOST_SUCCESS} User Jailed",
                                       description=f"{member.mention} has been jailed for: **{reason}**",
                                       color=discord.Color.orange())
        except discord.Forbidden:
            return False, discord.Embed(title=f"{GHOST_ERROR} Permission Error",
                                        description="I do not have permission to edit this user's roles.",
                                        color=discord.Color.red())
        except Exception as e:
            return False, discord.Embed(title=f"{GHOST_ERROR} Unexpected Error",
                                        description=f"An error occurred: {e}",
                                        color=discord.Color.red())

    async def unjail_user_core(self, guild, executor, member):
        jail_role, log_channel = await self.get_settings(guild)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT roles FROM jailed_users WHERE guild_id=? AND user_id=?", (guild.id, member.id)) as cursor:
                row = await cursor.fetchone()
            if not row:
                return False, discord.Embed(title=f"{GHOST_ERROR} Not Jailed",
                                            description="This user is not currently jailed.",
                                            color=discord.Color.red())
            role_ids = [int(r) for r in row[0].split(",") if r]
            roles = [guild.get_role(r) for r in role_ids if guild.get_role(r)]

            # ✅ Restore booster role(s) too
            booster_roles = [r for r in member.roles if r.is_premium_subscriber()]
            roles = roles + booster_roles

            # ✅ Remove duplicates (fix for Bad Request 50035)
            roles = list({r.id: r for r in roles if r is not None}.values())

            await db.execute("DELETE FROM jailed_users WHERE guild_id=? AND user_id=?", (guild.id, member.id))
            await db.commit()

        await member.edit(roles=roles, reason=f"Unjailed by {executor}")
        if log_channel:
            embed_log = discord.Embed(title=f"{GHOST_SUCCESS} User Unjailed", color=discord.Color.green())
            embed_log.add_field(name="User", value=member.mention, inline=True)
            embed_log.add_field(name="By", value=executor.mention, inline=True)
            embed_log.set_thumbnail(url=member.display_avatar.url)
            await log_channel.send(embed=embed_log)
        return True, discord.Embed(title=f"{GHOST_SUCCESS} User Unjailed",
                                   description=f"{member.mention} has been unjailed and their roles restored.",
                                   color=discord.Color.green())

    # ----------------- COMMANDS -----------------
    # Prefix commands
    @commands.command(name="jailrole")
    @commands.has_permissions(administrator=True)
    async def prefix_set_jail_role(self, ctx, role: discord.Role):
        await self.set_jail_role_db(ctx.guild.id, role.id)
        await ctx.send(embed=discord.Embed(description=f"{GHOST_SUCCESS} Jail role set to {role.mention}", color=discord.Color.green()))

    @commands.command(name="jailsetlog")
    @commands.has_permissions(administrator=True)
    async def prefix_set_log_channel(self, ctx, channel: discord.TextChannel):
        await self.set_log_channel_db(ctx.guild.id, channel.id)
        await ctx.send(embed=discord.Embed(description=f"{GHOST_SUCCESS} Jail log channel set to {channel.mention}", color=discord.Color.green()))

    @commands.command(name="jail")
    @commands.has_permissions(administrator=True)
    async def prefix_jail(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        success, embed = await self.jail_user_core(ctx.guild, ctx.author, member, reason)
        await ctx.send(embed=embed)

    @commands.command(name="unjail")
    @commands.has_permissions(administrator=True)
    async def prefix_unjail(self, ctx, member: discord.Member):
        success, embed = await self.unjail_user_core(ctx.guild, ctx.author, member)
        await ctx.send(embed=embed)

    # Slash commands
    @app_commands.command(name="jailrole", description="Set the jail role")
    @app_commands.default_permissions(administrator=True)
    async def slash_set_jail_role(self, interaction: discord.Interaction, role: discord.Role):
        await self.set_jail_role_db(interaction.guild.id, role.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"{GHOST_SUCCESS} Jail role set to {role.mention}", color=discord.Color.green()), ephemeral=True)

    @app_commands.command(name="jailsetlog", description="Set the jail log channel")
    @app_commands.default_permissions(administrator=True)
    async def slash_set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.set_log_channel_db(interaction.guild.id, channel.id)
        await interaction.response.send_message(embed=discord.Embed(description=f"{GHOST_SUCCESS} Jail log channel set to {channel.mention}", color=discord.Color.green()), ephemeral=True)

    @app_commands.command(name="jail", description="Jail a user")
    @app_commands.default_permissions(administrator=True)
    async def slash_jail(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        success, embed = await self.jail_user_core(interaction.guild, interaction.user, member, reason)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unjail", description="Unjail a user")
    @app_commands.default_permissions(administrator=True)
    async def slash_unjail(self, interaction: discord.Interaction, member: discord.Member):
        success, embed = await self.unjail_user_core(interaction.guild, interaction.user, member)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Jail(bot))
