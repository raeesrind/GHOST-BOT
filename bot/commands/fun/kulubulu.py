import discord
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import Context
from typing import Optional
import random

class Kulubulu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ✨ Embed generator
    def fun_embed(self):
        meanings = [
            "**Kulubulu** means *pookie* (sometimes), depending on the sentence. 😌",
            "**Kulubulu** is a vibe. It’s cute, mysterious — invented by GHOST 👻",
            "**Kulubulu**? It's like saying *aww* but with chaos... kinda. Ask GHOST.",
            "**Kulubulu** = pookie energy 💜 Word by the one and only GHOST.",
        ]
        embed = discord.Embed(
            title="🔮 What is Kulubulu?",
            description=random.choice(meanings),
            color=discord.Color.purple()
        )
        embed.set_footer(text="Word crafted by GHOST 😈")
        return embed

    # Prefix Command
    @commands.command(name="kulubulu", help="Find out what kulubulu means!")
    async def kulubulu_prefix(self, ctx: Context):
        await ctx.send(embed=self.fun_embed())

    # Slash Command
    @app_commands.command(name="kulubulu", description="Find out what kulubulu means!")
    async def kulubulu_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self.fun_embed(), ephemeral=False)

    # Prefix Error
    @kulubulu_prefix.error
    async def on_prefix_error(self, ctx, error):
        await ctx.send("❌ Something went wrong while processing the kulubulu command.")

    # Slash Error
    @kulubulu_slash.error
    async def on_slash_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message("❌ An error occurred while running the kulubulu command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Kulubulu(bot))
