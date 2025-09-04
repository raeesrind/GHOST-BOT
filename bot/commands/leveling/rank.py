import discord
from discord.ext import commands
from discord import app_commands
from bot.database.database import database
from PIL import Image, ImageDraw, ImageFont
from colorthief import ColorThief
import requests
from io import BytesIO
import os
import traceback

class Rank(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_leveling_enabled(self, guild_id):
        async with database.db.execute("SELECT leveling_enabled FROM xp_settings WHERE guild_id = ?", (str(guild_id),)) as cursor:
            row = await cursor.fetchone()
            return bool(row[0]) if row else True

    @commands.command(name="rank", help="Check your or another user's level and XP.")
    async def rank_prefix(self, ctx, user: discord.Member = None):
        # Silent block if rank command is disabled
        guild_id = str(ctx.guild.id)
        if ctx.command.name.lower() in self.bot.disabled_commands.get(guild_id, []):
            return
        
        if not await self.is_leveling_enabled(ctx.guild.id):
            return await ctx.send("❌ Leveling is currently disabled on this server.")
        target = user or ctx.author
        await self.show_rank(ctx.guild, target, ctx, ephemeral=False)

    @app_commands.command(name="rank", description="Check your or another user's level and XP.")
    @app_commands.describe(user="User to check (leave blank to view your own rank)")
    async def rank_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        if not await self.is_leveling_enabled(interaction.guild.id):
            return await interaction.response.send_message("❌ Leveling is currently disabled on this server.", ephemeral=True)
        target = user or interaction.user
        is_private = (target.id == interaction.user.id)
        await self.show_rank(interaction.guild, target, interaction, ephemeral=is_private)

    async def show_rank(self, guild, member, context, ephemeral=False):
        try:
            guild_id, user_id = str(guild.id), str(member.id)

            async with database.db.execute("SELECT xp FROM user_xp WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cursor:
                row = await cursor.fetchone()
                current_xp = row[0] if row else 0

            level = self.calculate_level(current_xp)
            next_level_xp = self.get_xp_for_level(level + 1)
            prev_level_xp = self.get_xp_for_level(level)
            xp_into_level = current_xp - prev_level_xp
            xp_needed = next_level_xp - prev_level_xp
            rank = await self.get_user_rank(guild_id, user_id)

            # Avatar
            avatar_url = member.display_avatar.replace(size=256).url
            avatar_bytes = requests.get(avatar_url).content
            avatar_img = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((160, 160))
            mask = Image.new("L", (160, 160), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 160, 160), fill=255)
            avatar_img.putalpha(mask)

            # Background
            bg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "rankghost.png"))
            base = Image.open(bg_path).convert("RGBA").resize((800, 250))
            
            # ✅ Boost background alpha ×2.0
            try:
                r, g, b, a = base.split()
                boosted_a = a.point(lambda p: min(255, int(p * 2.0)))
                base = Image.merge("RGBA", (r, g, b, boosted_a))
            except Exception as e:
                print(f"[Opacity Boost Error] {e}")

            # Tint background with avatar dominant color
            try:
                dominant = ColorThief(BytesIO(avatar_bytes)).get_color(quality=1)
                overlay = Image.new("RGBA", base.size, dominant + (60,))
                base = Image.alpha_composite(base, overlay)
            except Exception:
                pass

            draw = ImageDraw.Draw(base)

            font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts", "ARIAL.TTF"))
            font_bold = ImageFont.truetype(font_path, 32)
            font_medium = ImageFont.truetype(font_path, 24)
            font_small = ImageFont.truetype(font_path, 18)

            base.paste(avatar_img, (30, 45), avatar_img)
            draw.text((210, 40), member.name, font=font_bold, fill="white")
            draw.text((210, 85), f"LEVEL {level}", font=font_medium, fill="white")
            draw.text((360, 85), f"RANK #{rank}", font=font_medium, fill="white")

            bar_x, bar_y, bar_w, bar_h = 210, 130, 500, 26
            progress = int((xp_into_level / xp_needed) * bar_w) if xp_needed > 0 else 0
            draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], 13, fill=(80, 80, 80))
            draw.rounded_rectangle([bar_x, bar_y, bar_x + progress, bar_y + bar_h], 13, fill=(255, 255, 255))

            xp_text = f"{xp_into_level:,} / {xp_needed:,} XP"
            text_w = font_small.getbbox(xp_text)[2]
            draw.text((bar_x + bar_w - text_w - 10, bar_y + 3), xp_text, font=font_small, fill="black")

            logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "ghost.png"))
            if os.path.exists(logo_path):
                logo = Image.open(logo_path).convert("RGBA").resize((60, 60))
                base.paste(logo, (base.width - 70, base.height - 70), logo)

            buffer = BytesIO()
            base.save(buffer, format="PNG")
            buffer.seek(0)
            file = discord.File(fp=buffer, filename="rank.png")

            if isinstance(context, discord.Interaction):
                await context.response.send_message(file=file, ephemeral=ephemeral)
            else:
                await context.send(file=file)

        except Exception as e:
            traceback.print_exc()
            error_msg = f"❌ An error occurred while generating the rank card:\n{type(e).__name__}: {e}"
            if isinstance(context, discord.Interaction):
                await context.response.send_message(error_msg, ephemeral=True)
            else:
                await context.send(error_msg)

    async def get_user_rank(self, guild_id, user_id):
        async with database.db.execute("SELECT user_id FROM user_xp WHERE guild_id = ? ORDER BY xp DESC", (guild_id,)) as cursor:
            rows = await cursor.fetchall()
        for idx, row in enumerate(rows):
            if str(row[0]) == user_id:
                return idx + 1
        return "?"

    def get_xp_for_level(self, level):
        return int(5 / 6 * level * (2 * level ** 2 + 27 * level + 91))

    def calculate_level(self, xp):
        level = 0
        while self.get_xp_for_level(level + 1) <= xp:
            level += 1
        return level

    @rank_prefix.error
    async def on_prefix_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Please wait {error.retry_after:.1f} seconds before using ?rank again.")
        else:
            await ctx.send(f"❌ Rank error: {type(error).__name__}: {error}")

    @rank_slash.error
    async def on_slash_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(
            f"❌ Rank error: {type(error).__name__}: {error}", ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Rank(bot))