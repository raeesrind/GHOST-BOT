import asyncio
from firebase_admin import firestore

db = firestore.client()
lock = asyncio.Lock()  # Prevent race conditions between simultaneous calls

async def get_next_case_number(guild_id: str) -> int:
    async with lock:
        counter_ref = db.collection("metadata").document(f"case_counter_{guild_id}")
        snapshot = counter_ref.get()

        if snapshot.exists:
            current = snapshot.to_dict().get("count", 0)
        else:
            current = 0

        next_case = current + 1
        counter_ref.set({"count": next_case})
        return next_case
