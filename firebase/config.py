import firebase_admin
from firebase_admin import credentials, firestore
import os

def init_firebase():
    # Build full absolute path to the credential file
    base_path = os.path.dirname(os.path.abspath(__file__))
    cred_path = os.path.join(base_path, 'serviceAccount.json')
    print(f"🔍 Firebase credential path: {cred_path}")

    cred = credentials.Certificate(cred_path)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()
