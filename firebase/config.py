# firebase/config.py
import firebase_admin
from firebase_admin import credentials, firestore

def init_firebase():
    cred = credentials.Certificate("firebase/serviceAccount.json")  # Make sure path is correct
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()
