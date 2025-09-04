import os
import discord
from discord.ext import commands

class FileSender(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="givefile")
    async def givefile(self, ctx, filepath: str):
        """Send a single file from the given path"""
        if not os.path.isfile(filepath):
            return await ctx.send("❌ File not found!")

        if not filepath.endswith(".py"):
            return await ctx.send("❌ Only `.py` files are allowed!")

        try:
            await ctx.send(file=discord.File(filepath))
        except Exception as e:
            await ctx.send(f"⚠️ Error: {e}")

    @commands.command(name="givefol")
    async def givefol(self, ctx, folderpath: str):
        """Send all .py files in a folder as separate messages"""
        if not os.path.isdir(folderpath):
            return await ctx.send("❌ Folder not found!")

        py_files = [f for f in os.listdir(folderpath) if f.endswith(".py")]
        if not py_files:
            return await ctx.send("❌ No `.py` files found in this folder.")

        for file in py_files:
            filepath = os.path.join(folderpath, file)
            try:
                await ctx.send(file=discord.File(filepath))
            except Exception as e:
                await ctx.send(f"⚠️ Error sending `{file}`: {e}")

async def setup(bot):
    await bot.add_cog(FileSender(bot))

