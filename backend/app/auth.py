import os
import logging
from typing import Optional, List, Callable
from fastapi import Header, HTTPException, status, Depends
from app.config import settings
from app.models import AuthenticatedUser, RoleType
from app.db import db

logger = logging.getLogger("brandguard.auth")

# Firebase Admin SDK initialization
firebase_app = None
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials

    if settings.firebase_service_account_path and os.path.exists(settings.firebase_service_account_path):
        cred = credentials.Certificate(settings.firebase_service_account_path)
        firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin initialized with service account key.")
    elif settings.firebase_project_id:
        firebase_app = firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
        logger.info(f"Firebase Admin initialized with project ID: {settings.firebase_project_id}")
except Exception as e:
    logger.warning(f"Firebase Admin SDK not initialized with live credentials ({e}). Mock/Demo authentication active.")

def verify_firebase_or_demo_token(token: str) -> dict:
    """
    Verifies Firebase ID token using Firebase Admin SDK if configured,
    or falls back to deterministic dev/demo tokens if enabled.
    Returns decoded token dictionary with 'uid' and 'email'.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Demo/Mock token support for developer environment and automated tests ONLY
    if token.startswith("demo-token:") or token.startswith("mock-token:"):
        if settings.is_production or not settings.enable_demo_auth:
            logger.warning("Attempted demo token usage while demo auth is disabled / in production.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Demo authentication tokens are strictly disabled in production.",
                headers={"WWW-Authenticate": "Bearer"}
            )

        parts = token.split(":", 1)
        identifier = parts[1] if len(parts) > 1 else "user_creator_1"
        
        # Check if identifier matches a seeded user
        membership = db.get_membership(identifier)
        if membership:
            return {"uid": membership.user_id, "email": membership.email}
        
        # Allow email-based demo tokens
        if "@" in identifier:
            return {"uid": f"user_{identifier.split('@')[0]}", "email": identifier}
        
        return {"uid": identifier, "email": f"{identifier}@example.com"}

    # Fail closed in production if Firebase Admin is unconfigured
    if settings.is_production and not firebase_app:
        logger.error("Production request blocked: Firebase Admin SDK is not initialized with live credentials.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Production authentication service is currently unavailable. Contact administrator.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Live Firebase ID Token Verification
    if firebase_app:
        try:
            decoded = firebase_auth.verify_id_token(token)
            return {
                "uid": decoded.get("uid"),
                "email": decoded.get("email", f"{decoded.get('uid')}@firebase.user")
            }
        except Exception as e:
            logger.error(f"Firebase ID token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired Firebase ID token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # If Firebase Admin is not configured but a non-demo bearer token was sent in dev
    if settings.enable_demo_auth and not settings.is_production:
        # Dev fallback: treat token as user identifier if demo auth is enabled
        return {"uid": token[:32], "email": f"{token[:12]}@example.com"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Firebase authentication is not configured on the server and demo auth is disabled.",
        headers={"WWW-Authenticate": "Bearer"}
    )

def get_current_user(authorization: Optional[str] = Header(None)) -> AuthenticatedUser:
    """
    FastAPI dependency extracting and verifying the Bearer token, then
    resolving the user's organisation membership and server-authoritative role.
    Security: The browser cannot supply or override its role or organisation ID.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header with Bearer token is required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    raw_token = authorization.split("Bearer ", 1)[1].strip()
    decoded = verify_firebase_or_demo_token(raw_token)
    uid = decoded["uid"]
    email = decoded["email"]

    # Authoritative server-side lookup of user's organisation & role
    membership = db.get_membership(uid) or db.get_membership(email)

    if not membership:
        # First-time user onboarding: auto-assign to default Acme workspace as Creator
        acme_org = db.get_organization("org_acme")
        org_id = acme_org.id if acme_org else "org_acme"
        membership = db.set_membership(
            user_id=uid,
            email=email,
            org_id=org_id,
            role="creator"
        )

    return AuthenticatedUser(
        user_id=membership.user_id,
        email=membership.email,
        org_id=membership.org_id,
        org_name=membership.org_name,
        role=membership.role
    )

def require_role(allowed_roles: List[RoleType]) -> Callable:
    """
    Dependency factory to enforce server-side Role-Based Access Control (RBAC).
    """
    def role_dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{user.role}' is not authorized. Required: {allowed_roles}"
            )
        return user
    return role_dependency
