from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List
from app.models import AuthenticatedUser, Membership, RoleType
from app.auth import get_current_user, require_role
from app.config import settings
from app.db import db, now_iso

router = APIRouter(prefix="/api/auth", tags=["auth"])

class SwitchDemoRequest(BaseModel):
    user_id: str

class MemberInviteRequest(BaseModel):
    user_id: str = Field(min_length=2, max_length=50)
    email: str = Field(min_length=5, max_length=100)
    role: RoleType

@router.get("/me", response_model=AuthenticatedUser)
def get_me(user: AuthenticatedUser = Depends(get_current_user)):
    """Returns the authenticated user, their authoritative organisation, and assigned role."""
    return user

@router.get("/demo-users")
def list_demo_users():
    """Provides available demo accounts for local development and rapid evaluation."""
    if settings.is_production or not settings.enable_demo_auth:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo user accounts and role switching are strictly disabled in production."
        )
    return [
        {
            "user_id": "user_admin_1",
            "email": "sarah.admin@acme.com",
            "display_name": "Sarah Chen",
            "role": "admin",
            "org_id": "org_acme",
            "org_name": "Acme Global Brands",
            "token": "demo-token:user_admin_1"
        },
        {
            "user_id": "user_reviewer_1",
            "email": "alex.reviewer@acme.com",
            "display_name": "Alex Rivera",
            "role": "reviewer",
            "org_id": "org_acme",
            "org_name": "Acme Global Brands",
            "token": "demo-token:user_reviewer_1"
        },
        {
            "user_id": "user_creator_1",
            "email": "jordan.creator@acme.com",
            "display_name": "Jordan Taylor",
            "role": "creator",
            "org_id": "org_acme",
            "org_name": "Acme Global Brands",
            "token": "demo-token:user_creator_1"
        },
        {
            "user_id": "user_beta_creator",
            "email": "dave.creator@betahealth.com",
            "display_name": "Dave Miller (Tenant Isolation Test)",
            "role": "creator",
            "org_id": "org_beta",
            "org_name": "Beta Health & Wellness",
            "token": "demo-token:user_beta_creator"
        }
    ]

@router.get("/members", response_model=List[Membership])
def list_team_members(user: AuthenticatedUser = Depends(get_current_user)):
    """Lists team members belonging strictly to the caller's organisation."""
    return db.list_org_memberships(user.org_id)

@router.post("/members", response_model=Membership)
def add_or_update_member(
    request: MemberInviteRequest,
    user: AuthenticatedUser = Depends(require_role(["admin"]))
):
    """Admin-only endpoint to assign or modify organisation membership roles."""
    membership = db.set_membership(
        user_id=request.user_id,
        email=request.email,
        org_id=user.org_id,
        role=request.role
    )
    return membership
