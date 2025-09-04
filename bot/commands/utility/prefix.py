import discord
from discord.ext import commands
from firebase_admin import firestore

db = firestore.client()

class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="prefix", help="View or change the command prefix.")
    @commands.has_permissions(administrator=True)
    async def prefix(self, ctx, *, new_prefix: str = None):
        guild_id = str(ctx.guild.id)
        prefix_ref = db.collection("settings").document(guild_id)

        if new_prefix:
            if len(new_prefix) > 5:
                embed = discord.Embed(
                    title="<:GhostError:1387033531221413959> Prefix Too Long",
                    description="Please use a prefix with **5 characters or fewer.**",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)

            prefix_ref.set({"prefix": new_prefix}, merge=True)
            embed = discord.Embed(
                title="<:GhostSuccess:1387033552809492682> Prefix Updated",
                description=f"The new prefix is now set to `{new_prefix}` for this server.",
                color=discord.Color.green()
            )
            return await ctx.send(embed=embed)

        # Show current prefix
        doc = prefix_ref.get()
        current = doc.to_dict().get("prefix") if doc.exists else "?"
        embed = discord.Embed(
            title="ℹ️ Current Prefix",
            description=f"The command prefix for this server is `{current}`.\n\nTo change it:\n`?prefix <new_prefix>`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @prefix.error
    async def prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="<:GhostError:1387033531221413959> Missing Permissions",
                description="You need **Administrator** permission to change the prefix.",
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
    await bot.add_cog(Prefix(bot))
