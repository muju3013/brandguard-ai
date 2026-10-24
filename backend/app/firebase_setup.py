import os
import logging
from app.config import settings

logger = logging.getLogger("brandguard.firebase")

_firebase_app = None

def get_firebase_app():
    """
    Initializes and returns the singleton Firebase Admin SDK app instance.
    Uses resolved service account key file or project ID.
    """
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app

        # 1. First priority: Inline service account JSON from environment variable (ideal for Render / Cloud)
        raw_json = settings.firebase_service_account_json.strip()
        if raw_json:
            import json, base64
            # Handle potential base64 encoded JSON
            if not raw_json.startswith("{") and len(raw_json) > 50:
                try:
                    raw_json = base64.b64decode(raw_json).decode("utf-8")
                except Exception:
                    pass
            try:
                cert_dict = json.loads(raw_json)
                cred = credentials.Certificate(cert_dict)
                _firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized from FIREBASE_SERVICE_ACCOUNT_JSON environment variable.")
                return _firebase_app
            except Exception as e:
                logger.error(f"Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

        # 2. Second priority: Service account key JSON file from disk
        key_path = settings.resolved_service_account_path
        if key_path and os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin initialized with service account key: {os.path.basename(key_path)}")
        elif settings.firebase_project_id:
            _firebase_app = firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
            logger.info(f"Firebase Admin initialized with project ID: {settings.firebase_project_id}")
    except Exception as e:
        logger.warning(f"Firebase Admin SDK initialization: {e}")
        _firebase_app = None

    return _firebase_app
