from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.models import AuditLog, AuthenticatedUser
from app.auth import get_current_user, require_role
from app.db import db

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])

@router.get("", response_model=List[AuditLog])
def list_audit_logs(
    entity_id: Optional[str] = Query(None, description="Optional entity ID filter"),
    user: AuthenticatedUser = Depends(require_role(["admin", "reviewer", "creator"]))
):
    """
    Returns the persistent audit trail of all governance events for the user's organisation.
    Enforces server-authoritative RBAC for Admin, Reviewer, and Creator.
    Enforces strict tenant isolation: never exposes cross-tenant records.
    """
    logs = db.list_audit_logs(org_id=user.org_id, entity_id=entity_id)
    sanitized_logs = []
    for log in logs:
        if log.actor_email and log.actor_email.startswith("eyJ"):
            log.actor_email = "User email unavailable"
        sanitized_logs.append(log)
    return sanitized_logs
