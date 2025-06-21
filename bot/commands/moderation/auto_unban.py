# bot/commands/moderation/auto_unban.py

import discord
from discord.ext import commands, tasks
from firebase_admin import firestore
from datetime import datetime
import traceback

class AutoUnban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = firestore.client()
        self.auto_unban.start()

    def cog_unload(self):
        self.auto_unban.cancel()

    @tasks.loop(seconds=30)
    async def auto_unban(self):
        try:
            now = datetime.utcnow().isoformat()
            query = self.db.collection("bans").where("unban_time", "<=", now)
            docs = list(query.stream())  # ✅ Fix: Not async

            for doc in docs:
                data = doc.to_dict()
                guild_id = int(data["guild_id"])
                user_id = int(data["user_id"])

                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue

                try:
                    await guild.unban(discord.Object(id=user_id), reason="Auto unban after timed ban expired")

                    # Log auto-unban (optional Firestore modlog)
                    logs_ref = self.db.collection("logs").document(str(guild_id)).collection("moderation")
                    logs_ref.document().set({
                        "case_id": f"AUTO-{datetime.utcnow().timestamp()}",
                        "type": "Unban",
                        "user_id": str(user_id),
                        "moderator_id": "0",
                        "moderator_tag": "AutoMod",
                        "reason": "Temporary ban duration expired",
                        "timestamp": datetime.utcnow().isoformat(),
                        "duration": None,
                        "auto": True
                    })

                    # Delete the ban document
                    doc.reference.delete()

                    print(f"✅ Auto-unbanned user {user_id} in guild {guild_id}")

                except discord.NotFound:
                    # User already unbanned
                    doc.reference.delete()
                except Exception as e:
                    print(f"⚠️ Error auto-unbanning {user_id} in guild {guild_id}:", e)

        except Exception as e:
            print("❌ AutoUnban Task Error:")
            traceback.print_exc()

    @auto_unban.before_loop
    async def before_auto_unban(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AutoUnban(bot))
