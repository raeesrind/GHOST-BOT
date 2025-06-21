# bot/commands/utility/firebase_test.py
import discord
from discord.ext import commands
from firebase_admin import firestore

class FirebaseTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = firestore.client()

    @commands.command(name="testdb")
    async def test_db(self, ctx):
        print("🔥 testdb command triggered")  # DEBUG: Make sure this prints in terminal
        try:
            doc_ref = self.db.collection("test").document(str(ctx.author.id))
            doc_ref.set({"name": ctx.author.name})
            await ctx.send(f"✅ Stored your name in Firestore, {ctx.author.mention}!")
        except Exception as e:
            await ctx.send(f"❌ Firestore error: {e}")
            print("❌ Exception in testdb:", e)

async def setup(bot):
    await bot.add_cog(FirebaseTest(bot))
