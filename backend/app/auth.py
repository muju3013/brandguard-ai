import os
import logging
from typing import Optional, List, Callable
from fastapi import Header, HTTPException, status, Depends
from app.config import settings
from app.models import AuthenticatedUser, RoleType
from app.db import db

logger = logging.getLogger("brandguard.auth")

from app.firebase_setup import get_firebase_app
try:
    from firebase_admin import auth as firebase_auth
except ImportError:
    firebase_auth = None

firebase_app = get_firebase_app()

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
        
        # Allow email-based demo tokens in non-production
        if "@" in identifier:
            return {"uid": f"user_{identifier.split('@')[0]}", "email": identifier}
        
        # Check known demo users
        demo_map = {
            "user_admin_1": {"uid": "user_admin_1", "email": "sarah.admin@acme.com"},
            "user_reviewer_1": {"uid": "user_reviewer_1", "email": "alex.reviewer@acme.com"},
            "user_creator_1": {"uid": "user_creator_1", "email": "jordan.creator@acme.com"},
            "user_beta_creator": {"uid": "user_beta_creator", "email": "dave.creator@betahealth.com"},
            "user_beta_admin": {"uid": "user_beta_admin", "email": "carol.admin@betahealth.com"}
        }
        if identifier in demo_map:
            return demo_map[identifier]

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unknown demo identity '{identifier}'. Demo fallback accounts are strictly bounded.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Resolve active Firebase Admin app instance
    import app.auth as self_mod
    active_fb_app = getattr(self_mod, "firebase_app", None)

    # Fail closed in production if Firebase Admin is unconfigured
    if settings.is_production and not active_fb_app:
        logger.error("Production request blocked: Firebase Admin SDK is not initialized with live credentials.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Production authentication service is currently unavailable. Contact administrator.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not active_fb_app:
        active_fb_app = get_firebase_app()

    # Live Firebase ID Token Verification
    if active_fb_app and firebase_auth:
        try:
            decoded = firebase_auth.verify_id_token(token, app=active_fb_app)
            uid = decoded.get("uid")
            email = decoded.get("email")
            # If email claim is not present in token payload, query Firebase Admin user record
            if not email:
                try:
                    user_record = firebase_auth.get_user(uid, app=active_fb_app)
                    email = user_record.email
                except Exception as user_err:
                    logger.warning(f"Could not fetch Firebase user record for UID {uid}: {user_err}")
                    email = None

            return {
                "uid": uid,
                "email": email or "Creator email unavailable"
            }
        except Exception as e:
            logger.error(f"Firebase ID token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired Firebase ID token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # Fail closed: never substring a JWT into a fake email address
    logger.error("Request blocked: Firebase Admin SDK credentials are not configured on server.")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Server authentication service is currently unconfigured. Live Firebase Admin credentials are required.",
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
    membership = db.get_membership(uid) or (db.get_membership(email) if email and "@" in email else None)

    if membership:
        # Auto-repair corrupt legacy membership email if live verified token claims provide legitimate email
        if email and not email.startswith("eyJ") and not email.endswith("@example.com") and membership.email != email:
            logger.info(f"Repairing legacy membership email for {uid} from '{membership.email}' to verified '{email}'")
            membership = db.set_membership(
                user_id=membership.user_id,
                email=email,
                org_id=membership.org_id,
                role=membership.role
            )
    else:
        # First-time user onboarding:
        # Check if the user matches the configured bootstrap admin email
        is_bootstrap_admin = bool(
            settings.bootstrap_admin_email and
            email and email.lower() == settings.bootstrap_admin_email.strip().lower()
        )
        role = "admin" if is_bootstrap_admin else "creator"

        target_org = db.get_organization("org_inkloom_judge") or db.get_organization("org_acme")
        org_id = target_org.id if target_org else "org_inkloom_judge"
        membership = db.set_membership(
            user_id=uid,
            email=email if (email and "@" in email) else f"user_{uid[:8]}@workspace.local",
            org_id=org_id,
            role=role
        )
        logger.info(f"Onboarded new user {membership.email} (UID: {uid}) to org {org_id} with role '{role}'.")

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
