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
