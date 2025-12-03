import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Configuration

TRACKED_USERS_COLLECTION = "tracked_users"
GUILD_CONFIG_COLLECTION = "guild_config"

def database_startup():
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully!")
        except FileNotFoundError:
            print("❌ ERROR: 'serviceAccountKey.json' not found.")
            return None
        except Exception as e:
            print(f"❌ ERROR initializing Firebase: {e}")
            return None
    return firestore.client()
