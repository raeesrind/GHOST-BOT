import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute("SELECT leveling_enabled FROM xp_settings WHERE guild_id = ?", (str(guild_id),)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

    @commands.command(name="leaderboard", help="Show the leveling leaderboard.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def leaderboard_prefix(self, ctx):
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send("❌ Leveling is currently disabled on this server.")
        await self.send_leaderboard(ctx)

    @app_commands.command(name="leaderboard", description="Show the leveling leaderboard.")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message(
                "❌ Leveling is currently disabled on this server.", ephemeral=True
            )
        await self.send_leaderboard(interaction)

    async def send_leaderboard(self, context):
        guild_id = str(context.guild.id)
        async with database.db.execute(
            "SELECT user_id, xp FROM user_xp WHERE guild_id = ? ORDER BY xp DESC", (guild_id,)
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            embed = discord.Embed(
                title="🏆 Leaderboard",
                description="No XP data available yet.",
                color=discord.Color.purple()
            )
            return await self.send(context, embed)

        pages = [rows[i:i + 10] for i in range(0, len(rows), 10)]
        total_pages = len(pages)

        def format_xp(xp: int):
            if xp >= 1_000_000:
                return f"{xp / 1_000_000:.1f}m"
            elif xp >= 1_000:
                return f"{xp / 1_000:.1f}k"
            else:
                return str(xp)

        async def create_embed(page_num):
            page = pages[page_num]
            embed = discord.Embed(
                title=f"Leaderboard for {context.guild.name} 🌍",
                color=discord.Color.purple()
            )

            rank_emoji = ["🥇", "🥈", "🥉"]

            for index, row in enumerate(page):
                user_id, xp = row
                level = self.calculate_level(xp)
                try:
                    user = context.guild.get_member(int(user_id)) or await self.bot.fetch_user(int(user_id))
                    name = user.name
                except:
                    name = f"User {user_id}"

                formatted_xp = format_xp(xp)
                global_rank = page_num * 10 + index + 1
                rank = rank_emoji[global_rank - 1] if global_rank <= 3 else str(global_rank)
                embed.add_field(
                    name=f"{rank} {name}",
                    value=f"Level {level} ({formatted_xp} XP)",
                    inline=False
                )

            embed.set_footer(text=f"Page: {page_num + 1} / {total_pages}")
            return embed

        class LeaderboardView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.page = 0

            @discord.ui.button(label="◀️", style=discord.ButtonStyle.blurple)
            async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.page = (self.page - 1) % total_pages
                await interaction.response.edit_message(embed=await create_embed(self.page), view=self)

            @discord.ui.button(label="⏹️", style=discord.ButtonStyle.gray)
            async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
                for item in self.children:
                    item.disabled = True
                await interaction.response.edit_message(view=self)

            @discord.ui.button(label="▶️", style=discord.ButtonStyle.blurple)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.page = (self.page + 1) % total_pages
                await interaction.response.edit_message(embed=await create_embed(self.page), view=self)

        await self.send(context, await create_embed(0), view=LeaderboardView())

    def calculate_level(self, xp):
        level = 0
        while self.get_xp_for_level(level + 1) <= xp:
            level += 1
        return level

    def get_xp_for_level(self, level):
        return int(5/6 * level * (2 * level**2 + 27 * level + 91))

    async def send(self, ctx_or_inter, embed, view=None):
        if isinstance(ctx_or_inter, commands.Context):
            await ctx_or_inter.send(embed=embed, view=view)
        else:
            await ctx_or_inter.response.send_message(embed=embed, view=view, ephemeral=False)

    @leaderboard_prefix.error
    async def on_prefix_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait {error.retry_after:.1f} seconds before reusing this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

    @leaderboard_slash.error
    async def on_slash_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(f"❌ An error occurred: {error}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
