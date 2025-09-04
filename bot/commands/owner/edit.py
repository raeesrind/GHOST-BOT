import discord
from discord.ext import commands
from discord import app_commands
import os
import math

# ✅ Define owner-only check
def is_app_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(predicate)

# ✅ Main cog
class EditFileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="edit", description="Edit a Python file in bot.commands (paginated)")
    @app_commands.describe(file_path="Relative path like fun/test.py")
    @is_app_owner()
    async def edit_file(self, interaction: discord.Interaction, file_path: str):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "commands"))
        full_path = os.path.normpath(os.path.join(base_dir, file_path.replace("/", os.sep)))

        if not full_path.startswith(base_dir) or not os.path.exists(full_path):
            await interaction.response.send_message("❌ File not found or invalid path.", ephemeral=True)
            return

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        view = PaginatedEditView(self.bot, full_path, file_path, content)
        await interaction.response.send_message(embed=view.create_embed(), view=view, ephemeral=True)

# ✅ View for pagination and actions
class PaginatedEditView(discord.ui.View):
    def __init__(self, bot, full_path, file_path, content: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.full_path = full_path
        self.file_path = file_path
        self.module_path = f"bot.commands.{file_path.replace('/', '.').replace('.py', '')}"
        self.content = content
        self.chunk_size = 1800
        self.total_pages = math.ceil(len(content) / self.chunk_size)
        self.current_page = 0

    def create_embed(self):
        start = self.current_page * self.chunk_size
        end = start + self.chunk_size
        chunk = self.content[start:end]

        # ✅ Add line numbers
        numbered_chunk = "\n".join(
            f"{i+1+start:>4} | {line}"
            for i, line in enumerate(chunk.splitlines())
        )

        embed = discord.Embed(
            title=f"Editing `{self.file_path}` (Page {self.current_page + 1}/{self.total_pages})",
            description=f"```py\n{numbered_chunk}```",
            color=discord.Color.blurple()
        )
        return embed


    @discord.ui.button(label="◀️ Prev", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="📝 Edit Page", style=discord.ButtonStyle.success)
    async def edit_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PageEditModal(self, reload=False))

    @discord.ui.button(label="💾 Save & Reload", style=discord.ButtonStyle.primary)
    async def edit_reload_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PageEditModal(self, reload=True))

# ✅ Modal for editing page content
class PageEditModal(discord.ui.Modal, title="Edit Current Page"):
    def __init__(self, view: PaginatedEditView, reload: bool):
        super().__init__()
        self.view = view
        self.reload = reload
        self.start = view.current_page * view.chunk_size
        self.end = self.start + view.chunk_size
        existing = view.content[self.start:self.end]
        self.input = discord.ui.TextInput(
            label="Edit Code",
            style=discord.TextStyle.paragraph,
            default=existing,
            max_length=4000
        )
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        new_text = self.input.value
        self.view.content = self.view.content[:self.start] + new_text + self.view.content[self.end:]

        # Save to file
        with open(self.view.full_path, "w", encoding="utf-8") as f:
            f.write(self.view.content)

        msg = f"✅ Page {self.view.current_page + 1} saved."

        # Attempt to reload
        if self.reload:
            try:
                await self.view.bot.reload_extension(self.view.module_path)
                msg += " 🔄 Module reloaded."
            except Exception as e:
                msg += f" ❌ Reload failed: `{e}`"

        await interaction.response.edit_message(embed=self.view.create_embed(), view=self.view)
        await interaction.followup.send(msg, ephemeral=True)

# ✅ Required setup function
async def setup(bot):
    await bot.add_cog(EditFileCog(bot))
