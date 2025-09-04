import discord
from discord.ext import commands
from firebase_admin import firestore

db = firestore.client()

class CommandToggle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="command",
        help="⚙️ Enable or disable a command (Admins only).",
        description="Enable or disable a command for this server.\nUsage: `?command <command_name>`"
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def command(self, ctx, command_name: str = None):
        if not command_name:
            embed = discord.Embed(
                title="⚙️ Command: ?command",
                description="**Enable/disable a command per server.**\n\n"
                            "**Usage:** `?command <command>`\n"
                            "**Example:** `?command ban`",
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            return await ctx.send(embed=embed)

        command_name = command_name.lower()
        command = self.bot.get_command(command_name)

        if not command:
            return await ctx.send(embed=discord.Embed(
                title="<:GhostError:1387033531221413959> Command Not Found",
                description=f"No command named `{command_name}` exists.",
                color=discord.Color.red()
            ))

        if command_name in ["command", "help", "prefix"]:
            return await ctx.send(embed=discord.Embed(
                title="⚠️ Protected Command",
                description=f"`{command_name}` is protected and cannot be disabled.",
                color=discord.Color.orange()
            ))

        guild_id = str(ctx.guild.id)
        settings_ref = db.collection("settings").document(guild_id)
        doc = settings_ref.get()
        current = doc.to_dict().get("disabled_commands", []) if doc.exists else []

        if command_name in current:
            current.remove(command_name)
            status = "<:GhostSuccess:1387033552809492682> Enabled"
            color = discord.Color.green()
        else:
            current.append(command_name)
            status = "🚫 Disabled"
            color = discord.Color.red()

        # 🔄 Update Firestore
        settings_ref.set({"disabled_commands": current}, merge=True)

        # 🔄 Update memory cache (case-insensitive)
        self.bot.disabled_commands[guild_id] = [cmd.lower() for cmd in current]

        embed = discord.Embed(
            title="⚙️ Command Toggled",
            description=f"Command `{command_name}` has been **{status}**.",
            color=color
        )
        embed.set_footer(text=f"Managed by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @command.error
    async def command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="<:GhostError:1387033531221413959> Missing Permissions",
                description="You need **Administrator** permission to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ Error",
                description=str(error),
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CommandToggle(bot))
