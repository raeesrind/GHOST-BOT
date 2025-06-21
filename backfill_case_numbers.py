import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("./firebase/serverAccount.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def resync_case_counter():
    max_case = 0
    guilds = db.collection("moderation").stream()

    for guild in guilds:
        logs = db.collection("moderation").document(guild.id).collection("logs").stream()
        for log in logs:
            data = log.to_dict()
            if "case" in data:
                max_case = max(max_case, data["case"])

    db.collection("bot_meta").document("case_counter").set({"count": max_case})
    print(f"✅ Global case counter resynced to {max_case}")

if __name__ == "__main__":
    resync_case_counter()
