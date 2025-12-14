import firebase_admin
import json
import os
from firebase_admin import credentials
from firebase_admin import firestore

# Configuration

TRACKED_USERS_COLLECTION = "tracked_users"
GUILD_CONFIG_COLLECTION = "guild_config"

def database_startup():
    if not firebase_admin._apps:
        try:
            firebase_json_env = os.getenv("FIREBASE_CREDENTIALS_JSON")
            if firebase_json_env:
                try:
                    cred_info = json.loads(firebase_json_env)
                    cred = credentials.Certificate(cred_info)
                    firebase_admin.initialize_app(cred)
                    print("✅ Firebase initialized successfully!")
                    return firestore.client()
                except json.JSONDecodeError:
                    print("❌ ERROR: 'FIREBASE_CREDENTIALS_JSON' is not valid JSON.")
                    return None
            elif os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
                print("✅ Firebase initialized successfully!")
                return firestore.client()
            else:
                print("❌ ERROR: No Firebase credentials found.")
                print("   - Checked Env Var: FIREBASE_CREDENTIALS_JSON")
                print("   - Checked Local File: serviceAccountKey.json")
                return None
        except Exception as e:
            print(f"❌ ERROR initializing Firebase: {e}")
            return None
    return firestore.client()
