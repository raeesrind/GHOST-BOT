import discord
from discord.ext import commands
from datetime import datetime, timezone
import uuid
from firebase_admin import firestore
from discord.ui import View, Select, Modal, TextInput

db = firestore.client()

class Notes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(AdminDeleteViewMulti([]))  # Persistent view

    @commands.command(name="note", help="📝 Add a note about a user. Anyone can use this.\n❌ Skips if command is disabled for the server.")
    async def note(self, ctx, member: discord.Member = None, *, note_text: str = None):
        if ctx.command.name.lower() in self.bot.disabled_commands.get(str(ctx.guild.id), []):
            return

        if member is None or note_text is None:
            embed = discord.Embed(
                title="📝 How to Use `?note`",
                description="Add a note about a member.\n\n**Usage:**\n`?note @user note text`",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        note_id = str(uuid.uuid4())
        note_data = {
            "note_id": note_id,
            "guild_id": str(ctx.guild.id),
            "user_id": str(member.id),
            "mod_id": str(ctx.author.id),
            "mod_tag": str(ctx.author),
            "note": note_text,
            "timestamp": datetime.utcnow().isoformat()
        }

        db.collection("notes").document(note_id).set(note_data)

        embed = discord.Embed(
            title=":GhostSuccess: Note Added",
            description=f"Successfully added a note for {member.mention}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"By {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="notes", help="📬 View a member’s notes. Anyone can use this.\n❌ Skips if command is disabled for the server.")
    async def notes(self, ctx, member: discord.Member = None):
        if ctx.command.name.lower() in self.bot.disabled_commands.get(str(ctx.guild.id), []):
            return

        member = member or ctx.author

        query = db.collection("notes") \
            .where("guild_id", "==", str(ctx.guild.id)) \
            .where("user_id", "==", str(member.id))

        docs = list(query.stream())
        if not docs:
            embed = discord.Embed(
                title="📬 No Notes Found",
                description=f"{member.mention} has no notes in this server.",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)

        sorted_docs = sorted(docs, key=lambda d: d.to_dict().get("timestamp", ""), reverse=True)[:10]

        embed = discord.Embed(
            title=f"📝 Notes for {member.display_name}",
            color=discord.Color.blurple()
        )

        for i, doc in enumerate(sorted_docs, start=1):
            note = doc.to_dict()
            mod_tag = note.get("mod_tag", "Unknown")

            if mod_tag == "Unknown":
                try:
                    user_obj = self.bot.get_user(int(note["mod_id"])) or await self.bot.fetch_user(int(note["mod_id"]))
                    mod_tag = str(user_obj)
                except:
                    mod_tag = "Unknown"

            note_text = note.get("note", "No note text provided")
            timestamp = datetime.fromisoformat(note["timestamp"]).replace(tzinfo=timezone.utc)
            relative_time = discord.utils.format_dt(timestamp, style="R")

            embed.add_field(
                name=f"**{i}.** By `{mod_tag}` — {relative_time}",
                value=note_text,
                inline=False
            )

        embed.set_footer(text=f"User ID: {member.id}", icon_url=ctx.author.display_avatar.url)

        if ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_messages:
            view = AdminDeleteViewMulti(sorted_docs)
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="editnote", help="✏️ Edit a note. Mods/Admins only.\n❌ Skips if command is disabled for the server.")
    @commands.has_permissions(manage_messages=True)
    async def editnote(self, ctx, member: discord.Member = None):
        if ctx.command.name.lower() in self.bot.disabled_commands.get(str(ctx.guild.id), []):
            return

        if not member:
            return await ctx.send(embed=discord.Embed(
                title=":GhostError: Missing Member",
                description="Please mention a user to edit their notes.\n\nUsage: `?editnote @user`",
                color=discord.Color.red()
            ))

        query = db.collection("notes") \
            .where("guild_id", "==", str(ctx.guild.id)) \
            .where("user_id", "==", str(member.id))
        docs = list(query.stream())

        if not docs:
            return await ctx.send(embed=discord.Embed(
                title="📬 No Notes Found",
                description=f"{member.mention} has no notes in this server.",
                color=discord.Color.gold()
            ))

        notes = [doc.to_dict() for doc in docs]
        embed = discord.Embed(
            title=f"📝 Editing Notes for {member.display_name}",
            description="Select a note to edit from the dropdown below:",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed, view=EditNoteDropdownView(notes))

class EditNoteModal(discord.ui.Modal, title="Edit Note"):
    def __init__(self, note_id, original_note):
        super().__init__()
        self.note_id = note_id
        self.original_note = original_note
        self.note_input = TextInput(
            label="New note",
            default=original_note["note"][:200],
            max_length=400,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.note_input)

    async def on_submit(self, interaction: discord.Interaction):
        db.collection("notes").document(self.note_id).update({
            "note": self.note_input.value,
            "mod_id": str(interaction.user.id),
            "mod_tag": str(interaction.user),
            "timestamp": datetime.utcnow().isoformat()
        })

        embed = discord.Embed(
            title=":GhostSuccess: Note Updated",
            description=f"New note saved for <@{self.original_note['user_id']}>",
            color=discord.Color.green()
        )
        embed.add_field(name="Old Note", value=self.original_note["note"], inline=False)
        embed.add_field(name="New Note", value=self.note_input.value, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class NoteDropdownEdit(discord.ui.Select):
    def __init__(self, notes):
        options = [
            discord.SelectOption(
                label=f"{i + 1}. {note['note'][:80]}",
                description=f"By {note.get('mod_tag', 'Unknown')}",
                value=note["note_id"]
            )
            for i, note in enumerate(notes)
        ]
        super().__init__(placeholder="Select a note to edit...", options=options)
        self.notes = notes

    async def callback(self, interaction: discord.Interaction):
        note_id = self.values[0]
        selected_note = next(n for n in self.notes if n["note_id"] == note_id)
        modal = EditNoteModal(note_id, selected_note)
        await interaction.response.send_modal(modal)

class EditNoteDropdownView(View):
    def __init__(self, notes):
        super().__init__(timeout=60)
        self.add_item(NoteDropdownEdit(notes))

class AdminDeleteViewMulti(View):
    def __init__(self, docs):
        super().__init__(timeout=None)
        self.docs = docs

    @discord.ui.button(label="🗑️ Delete Note", style=discord.ButtonStyle.danger, custom_id="delete_note_btn")
    async def delete_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (
            interaction.user.guild_permissions.administrator or
            interaction.user.guild_permissions.manage_messages
        ):
            embed = discord.Embed(
                title=":GhostError: Permission Denied",
                description="You don't have permission to delete this note.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        options = []
        for i, doc in enumerate(self.docs, start=1):
            note = doc.to_dict()
            options.append(discord.SelectOption(
                label=f"{i}. {note['note'][:80]}",
                description=f"By {note.get('mod_tag', 'Unknown')}",
                value=note["note_id"]
            ))

        view = NoteDropdownDeleteView(options)
        await interaction.followup.send(
            embed=discord.Embed(
                title="📌 Select Note to Delete",
                description="Choose a note from the dropdown below:",
                color=discord.Color.orange()
            ),
            view=view,
            ephemeral=True
        )

class NoteDropdownDeleteView(View):
    def __init__(self, options):
        super().__init__(timeout=60)
        self.add_item(NoteDropdownDelete(options))

class NoteDropdownDelete(discord.ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Select a note to delete...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        note_id = self.values[0]
        db.collection("notes").document(note_id).delete()
        embed = discord.Embed(
            title=":GhostSuccess: Note Deleted",
            description="The selected note has been removed successfully.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Notes(bot))
