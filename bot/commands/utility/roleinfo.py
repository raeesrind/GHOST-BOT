import discord
from discord.ext import commands
from discord import app_commands
from firebase_admin import firestore
from discord.utils import utcnow

db = firestore.client()

class RoleInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 🔹 Log who created the role in Firestore
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        try:
            async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
                if entry.target.id == role.id:
                    creator_id = entry.user.id
                    guild_id = str(role.guild.id)

                    db.collection("roles") \
                      .document(guild_id) \
                      .collection("role_creators") \
                      .document(str(role.id)) \
                      .set({
                          "creator_id": creator_id,
                          "created_at": role.created_at.isoformat(),
                          "guild_id": guild_id,
                          "role_name": role.name
                      })
        except Exception as e:
            # 🔥 Log silently in console, or forward to your error channel if you want
            print(f"Error saving role creator: {e}")

    # 🔹 Roleinfo command
    @commands.hybrid_command(name="roleinfo", description="Get detailed information about a role")
    @commands.guild_only()
    async def roleinfo(self, ctx: commands.Context, role: discord.Role):
        guild_id = str(ctx.guild.id)

        # Default creator text
        creator_text = "Unknown"

        # Fetch Firestore creator data
        doc = db.collection("roles") \
                .document(guild_id) \
                .collection("role_creators") \
                .document(str(role.id)) \
                .get()

        if doc.exists:
            data = doc.to_dict()
            creator = ctx.guild.get_member(data.get("creator_id"))
            if creator:
                creator_text = creator.mention
            else:
                creator_text = f"<@{data.get('creator_id')}> (not in server)"
        else:
            # 🔹 Fallback: fetch audit logs live if not in Firestore
            try:
                async for entry in ctx.guild.audit_logs(limit=5, action=discord.AuditLogAction.role_create):
                    if entry.target.id == role.id:
                        creator = ctx.guild.get_member(entry.user.id)
                        if creator:
                            creator_text = creator.mention
                        else:
                            creator_text = f"<@{entry.user.id}> (not in server)"
                        # Save it to Firestore for next time
                        db.collection("roles") \
                          .document(guild_id) \
                          .collection("role_creators") \
                          .document(str(role.id)) \
                          .set({
                              "creator_id": entry.user.id,
                              "created_at": role.created_at.isoformat(),
                              "guild_id": guild_id,
                              "role_name": role.name
                          })
                        break
            except Exception as e:
                print(f"Error fetching audit logs in roleinfo: {e}")

        # Key Permissions
        key_perms = []
        perms = role.permissions
        if perms.administrator: key_perms.append("Administrator")
        if perms.manage_guild: key_perms.append("Manage Server")
        if perms.manage_roles: key_perms.append("Manage Roles")
        if perms.manage_channels: key_perms.append("Manage Channels")
        if perms.manage_messages: key_perms.append("Manage Messages")
        if perms.kick_members: key_perms.append("Kick Members")
        if perms.ban_members: key_perms.append("Ban Members")
        if perms.mention_everyone: key_perms.append("Mention Everyone")
        if perms.manage_webhooks: key_perms.append("Manage Webhooks")
        if perms.manage_nicknames: key_perms.append("Manage Nicknames")

        key_perm_text = ", ".join(key_perms) if key_perms else "None"

        # Members with role
        member_count = sum(1 for m in ctx.guild.members if role in m.roles)

        # Embed
        embed = discord.Embed(
            title=f"Role Info - {role.name}",
            color=role.color if role.color.value else discord.Color.blurple()
        )

        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="Name", value=role.name, inline=True)
        embed.add_field(name="Color", value=str(role.color) if role.color.value else "None", inline=True)
        embed.add_field(name="Mention", value=role.mention, inline=False)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="Position", value=role.position, inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Managed", value="Yes" if role.managed else "No", inline=True)

        embed.add_field(name="Key Permissions", value=key_perm_text, inline=False)
        embed.add_field(name="Members with this Role", value=str(member_count), inline=False)
        embed.add_field(name="Role Created", value=role.created_at.strftime("%d/%m/%Y %H:%M"), inline=False)

        # 🔹 Always add Created by
        embed.add_field(name="Created by", value=creator_text, inline=False)

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RoleInfo(bot))
