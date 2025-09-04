import discord 
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import random
import io
import aiohttp
import os
import aiosqlite

DATABASE = "media.db"

class ShipCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ship", help="Ship two people together 💖")
    async def ship(self, ctx: commands.Context):
        # ✅ Restrict to ship channel
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT ship_channel_id FROM purrbot_settings WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    allowed_channel_id = row[0]
                    if ctx.channel.id != allowed_channel_id:
                        return #await ctx.send("❌ You can only use this command in the configured ship channel.")
                else:
                    return await ctx.send("❌ No ship channel set. Use `?setship #channel` first.")

        user1 = ctx.author
        user2 = None

        # Get user from reply
        ref = ctx.message.reference
        if ref:
            try:
                msg = await ctx.channel.fetch_message(ref.message_id)
                user2 = msg.author
            except:
                pass

        if not user2 and ctx.message.mentions:
            user2 = ctx.message.mentions[0]

        if not user2:
            await ctx.send("❌ Mention someone or reply to their message to ship!")
            return

        # Compatibility %
        percentage = random.randint(1, 100)

        if percentage <= 10:
            message = "You both don’t even look like friends… "
        elif percentage <= 30:
            message = "Maybe acquaintances at best. "
        elif percentage <= 50:
            message = "There’s something there… kinda. "
        elif percentage <= 70:
            message = "A solid match! You vibe well. "
        elif percentage <= 90:
            message = "Ooh, you two are definitely close! "
        else:
            message = "Soulmates confirmed. "

        # Fetch avatars
        async with aiohttp.ClientSession() as session:
            async with session.get(user1.display_avatar.url) as r1:
                avatar1 = Image.open(io.BytesIO(await r1.read())).convert("RGBA").resize((256, 256))
            async with session.get(user2.display_avatar.url) as r2:
                avatar2 = Image.open(io.BytesIO(await r2.read())).convert("RGBA").resize((256, 256))

        # Create canvas
        canvas = Image.new("RGBA", (768, 256), (0, 0, 0, 0))
        canvas.paste(avatar1, (0, 0))
        canvas.paste(avatar2, (512, 0))

        # Load heart image and resize to fit center
        heart_path = os.path.join(os.path.dirname(__file__), "assets", "heart.png")
        heart_img = Image.open(heart_path).convert("RGBA").resize((256, 256))

        # Paste heart in center
        canvas.paste(heart_img, (256, 0), heart_img)

        # Draw percentage text over heart
        draw = ImageDraw.Draw(canvas)
        try:
            font_path = os.path.join(os.path.dirname(__file__), "assets", "ARIBLK.TTF")
            font = ImageFont.truetype(font_path, 60)
        except:
            font = ImageFont.load_default()

        text = f"{percentage}%"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = 256 + (256 - text_width) // 2
        text_y = 64 + (256 - text_height) // 2 - 80 

        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

        # Save
        buffer = io.BytesIO()
        canvas.save(buffer, format="PNG")
        buffer.seek(0)

        await ctx.send(f"**{message}**", file=discord.File(buffer, filename="ship.png"))

async def setup(bot):
    await bot.add_cog(ShipCommand(bot))
