import discord
from discord.ext import commands
import re
import pytesseract
from PIL import Image
import aiohttp
from io import BytesIO
from bot.database.database import database


class XPClaim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="xpclaim")
    async def xp_claim(self, ctx: commands.Context):
        await ctx.typing()

        # ✅ Must be a reply
        if not ctx.message.reference:
            return await ctx.send("❌ Please reply to your Scrump level card image using `?xpclaim`.")

        # ✅ Get the replied message
        replied_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)

        # ✅ Must have an image attached
        if not replied_msg.attachments:
            return await ctx.send("❌ That message doesn’t contain any image.")

        image_url = replied_msg.attachments[0].url

        # ✅ Download image
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await ctx.send("⚠️ Failed to download the image.")
                    image_bytes = await resp.read()
        except Exception as e:
            return await ctx.send(f"❌ Error downloading image: `{e}`")

        # ✅ OCR from image
        try:
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            print(f"OCR TEXT:\n{text}")
        except Exception as e:
            return await ctx.send(f"❌ OCR failed: `{e}`")

        # ✅ Check username match
        username = ctx.author.name.lower()
        if username not in text.lower():
            return await ctx.send("🚫 This card doesn’t belong to you. Claim rejected.")

        # ✅ Extract level
        match = re.search(r"level\s*[:\-]?\s*(\d+)", text.lower())
        if not match:
            return await ctx.send("⚠️ Couldn’t detect your level in the image.")

        level = int(match.group(1))
        xp = self.level_to_xp(level)

        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        # ✅ Check if already claimed
        async with database.db.execute(
            "SELECT claimed FROM claimed_xp WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            claimed = await cursor.fetchone()

        if claimed:
            return await ctx.send("❌ You’ve already claimed XP from Scrump.")

        # ✅ Store XP
        await database.update_xp(guild_id, user_id, xp, ts=0)
        await database.db.execute(
            "INSERT INTO claimed_xp (guild_id, user_id, claimed) VALUES (?, ?, 1)",
            (guild_id, user_id),
        )
        await database.db.commit()

        await ctx.send(f"✅ Scrump level **{level}** claimed → `{xp}` XP granted!")

    def level_to_xp(self, level: int) -> int:
        return level * 1000  # 🔧 Adjust this formula as needed


async def setup(bot):
    await bot.add_cog(XPClaim(bot))
