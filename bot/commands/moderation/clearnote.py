import discord
from discord.ext import commands
from firebase_admin import firestore

db = firestore.client()

class ClearNote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="clearnote")
    @commands.has_permissions(manage_messages=True)
    async def clearnote(self, ctx, member: discord.Member = None):
        """Clear all notes for a specific member in this server."""
        if member is None:
            return await ctx.send(embed=discord.Embed(
                title="❌ Missing Member",
                description="Please mention a user to clear their notes.\n\nUsage: `?clearnote @user`",
                color=discord.Color.red()
            ))

        query = db.collection("notes") \
            .where("guild_id", "==", str(ctx.guild.id)) \
            .where("user_id", "==", str(member.id))

        docs = list(query.stream())

        if not docs:
            return await ctx.send(embed=discord.Embed(
                title="📭 No Notes Found",
                description=f"{member.mention} has no notes to clear.",
                color=discord.Color.gold()
            ))

        for doc in docs:
            doc.reference.delete()

        embed = discord.Embed(
            title="🧹 All Notes Cleared",
            description=f"Successfully cleared {len(docs)} note(s) for {member.mention}.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Cleared by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ClearNote(bot))
