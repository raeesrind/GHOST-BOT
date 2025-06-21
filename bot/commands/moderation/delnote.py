import discord
from discord.ext import commands
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

class DeleteNoteDropdown(discord.ui.Select):
    def __init__(self, notes):
        options = [
            discord.SelectOption(
                label=f"{i+1}. {note['note'][:80]}",
                description=f"By {note.get('mod_tag', 'Unknown')}",
                value=note["note_id"]
            )
            for i, note in enumerate(notes)
        ]
        super().__init__(placeholder="Select a note to delete...", options=options)
        self.notes = notes

    async def callback(self, interaction: discord.Interaction):
        note_id = self.values[0]
        note = next((n for n in self.notes if n["note_id"] == note_id), None)

        if not note:
            return await interaction.response.send_message("❌ Note not found.", ephemeral=True)

        db.collection("notes").document(note_id).delete()

        embed = discord.Embed(
            title="✅ Note Deleted",
            description=f"Note by `{note.get('mod_tag', 'Unknown')}` has been deleted.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DeleteNoteView(discord.ui.View):
    def __init__(self, notes):
        super().__init__(timeout=60)
        self.add_item(DeleteNoteDropdown(notes))


class DeleteNoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="delnote")
    @commands.has_permissions(manage_messages=True)
    async def delnote(self, ctx, member: discord.Member = None):
        """Delete a note about a member via dropdown."""
        if not member:
            embed = discord.Embed(
                title="🗑️ How to Use `?delnote`",
                description="**Delete a single note about a member**\n\n**Usage:**\n`?delnote @user`",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        query = db.collection("notes") \
            .where("guild_id", "==", str(ctx.guild.id)) \
            .where("user_id", "==", str(member.id))
        docs = list(query.stream())

        if not docs:
            embed = discord.Embed(
                title="📭 No Notes Found",
                description=f"{member.mention} has no notes in this server.",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)

        notes = [doc.to_dict() for doc in docs]

        embed = discord.Embed(
            title=f"🗑️ Select a Note to Delete",
            description=f"{member.mention} has {len(notes)} notes. Use the dropdown below to delete one.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, view=DeleteNoteView(notes))


async def setup(bot):
    await bot.add_cog(DeleteNoteCog(bot))
