import discord
from discord.ext import commands
from discord import app_commands
import os
import sys

# List of allowed user IDs (besides the guild owner)
ALLOWED_USER_IDS = [1117037767831072891, 1130498969844334774]  # Replace with actual IDs

def is_guild_owner_or_allowed():
    async def predicate(ctx: commands.Context):
        return (
            ctx.author.id in ALLOWED_USER_IDS
            or (ctx.guild and ctx.author.id == ctx.guild.owner_id)
        )
    return commands.check(predicate)

class CogManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_all_cogs(self):
        commands_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
        suggestions = []

        for root, dirs, files in os.walk(commands_path):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    path = os.path.relpath(os.path.join(root, file), commands_path)
                    module = path.replace(os.sep, ".")[:-3]
                    suggestions.append(module)
        return suggestions

    @commands.hybrid_command(name="reload", description="Reload a cog/module and sync commands.")
    @is_guild_owner_or_allowed()
    async def reload(self, ctx: commands.Context, cog: str):
        module = f"bot.commands.{cog}"
        try:
            await self.bot.reload_extension(module)
            await self.bot.tree.sync(guild=ctx.guild)
            await ctx.reply(f"🔄 Reloaded `{module}` and synced slash commands.", ephemeral=False)
        except Exception as e:
            await ctx.reply(f"❌ Error reloading `{module}`: `{e}`", ephemeral=False)

    @reload.autocomplete('cog')
    async def reload_autocomplete(self, interaction: discord.Interaction, current: str):
        return [      app_commands.Choice(name=mod, value=mod)
            for mod in self.get_all_cogs()
            if current.lower() in mod.lower()
        ][:20]

    @commands.hybrid_command(name="load", description="Load a cog/module and sync commands.")
    @is_guild_owner_or_allowed()
    async def load(self, ctx: commands.Context, cog: str):
        module = f"bot.commands.{cog}"
        try:
            await self.bot.load_extension(module)
            await self.bot.tree.sync(guild=ctx.guild)
            await ctx.reply(f"📥 Loaded `{module}` and synced slash commands.", ephemeral=False)
        except Exception as e:
            await ctx.reply(f"❌ Error loading `{module}`: `{e}`", ephemeral=False)

    @load.autocomplete('cog')
    async def load_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=mod, value=mod)
            for mod in self.get_all_cogs()
            if current.lower() in mod.lower()
        ][:20]

    @commands.hybrid_command(name="unload", description="Unload a cog/module.")
    @is_guild_owner_or_allowed()
    async def unload(self, ctx: commands.Context, cog: str):
        module = f"bot.commands.{cog}"
        try:
            await self.bot.unload_extension(module)
            await ctx.reply(f"🗑️ Unloaded `{module}`.", ephemeral=False)
        except Exception as e:
            await ctx.reply(f"❌ Error unloading `{module}`: `{e}`", ephemeral=False)

    @unload.autocomplete('cog')
    async def unload_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name=mod, value=mod)
            for mod in self.get_all_cogs()
            if current.lower() in mod.lower()
        ][:20]

    @commands.hybrid_command(name="restart", description="Restart the bot process.")
    @is_guild_owner_or_allowed()
    async def restart(self, ctx: commands.Context):
        await ctx.reply("♻️ Restarting bot...", ephemeral=False)
        await self.bot.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

async def setup(bot):
    await bot.add_cog(CogManager(bot))
