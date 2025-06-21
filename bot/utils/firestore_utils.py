# bot/utils/log_moderation_action.py

from firebase_admin import firestore
from discord.utils import utcnow
from bot.utils.casecounter import get_next_case_number

db = firestore.client()

async def log_moderation_action(guild_id, user, moderator, reason, action, duration="n/a"):
    case = await get_next_case_number(guild_id)
    log_data = {
        "case": case,
        "user_id": user.id,
        "user_tag": str(user),
        "moderator_id": moderator.id,
        "moderator_tag": str(moderator),
        "reason": reason,
        "action": action,
        "duration": duration,
        "timestamp": int(utcnow().timestamp())
    }
    db.collection("moderation").document(guild_id).collection("logs").document().set(log_data)
    return case
