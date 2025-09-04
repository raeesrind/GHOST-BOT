import discord
from discord.ext import commands
from discord import app_commands
import os
import random
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, firestore


class Motivate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # GPT client
        self.gpt = OpenAI(
            base_url="https://models.github.ai/inference",
            api_key=os.getenv("GITHUB_TOKEN")
        )

        # Firebase init (safe check)
        if not firebase_admin._apps:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()
        self.collection = self.db.collection("motivational_responses")

    async def generate_motivation(self):
        try:
            res = self.gpt.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a motivational coach."},
                    {"role": "user", "content": "Give me one short motivational quote."}
                ]
            )
            message = res.choices[0].message.content.strip()
            self.collection.add({"message": message})
            return message
        except Exception:
            fallback = [doc.to_dict()["message"] for doc in self.collection.stream()]
            return random.choice(fallback) if fallback else "Keep going. Great things take time."

    @commands.command(name="motivateme")
    async def motivate_prefix(self, ctx: commands.Context):
        if await self.bot.is_owner(ctx.author):
            await ctx.send("💪 You don't need motivation — **motivation needs you**.")
            return

        message = await self.generate_motivation()
        embed = discord.Embed(
            description=f"💡 {ctx.author.mention} **{message}**",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @app_commands.command(name="motivateme", description="Get a motivational message")
    async def motivate_slash(self, interaction: discord.Interaction):
        if await self.bot.is_owner(interaction.user):
            await interaction.response.send_message("💪 You don't need motivation — **motivation needs you**.", ephemeral=True)
            return

        message = await self.generate_motivation()
        embed = discord.Embed(
            description=f"💡 {interaction.user.mention} **{message}**",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

    # Remove this line to avoid CommandAlreadyRegistered
    # async def cog_load(self):
    #     self.bot.tree.add_command(self.motivate_slash)


async def setup(bot):
    await bot.add_cog(Motivate(bot))
