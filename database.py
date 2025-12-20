import firebase_admin
import json
import base64
import os
from firebase_admin import credentials
from firebase_admin import firestore
from logger_config import logger

# Configuration

TRACKED_USERS_COLLECTION = "tracked_users"
GUILD_CONFIG_COLLECTION = "guild_config"

def database_startup():
    if not firebase_admin._apps:
        try:
            b64_creds = os.getenv("FIREBASE_CREDENTIALS_BASE64")
            if b64_creds:
                b64_creds = b64_creds.strip()
                missing_padding = len(b64_creds) % 4
                if missing_padding:
                    b64_creds += '=' * (4-missing_padding)
                json_str = base64.b64decode(b64_creds).decode("utf-8")
                cred_info = json.loads(json_str)
                cred = credentials.Certificate(cred_info)
                firebase_admin.initialize_app(cred)
                logger.info("✅ Firebase initialized successfully!")
                return firestore.client()
            else:
                logger.error("❌ ERROR: No Firebase credentials found.")
                return None
        except Exception as e:
            logger.error(f"❌ ERROR: initializing Firebase: {e}")
            return None
    return firestore.client()
