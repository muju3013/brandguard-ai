from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.models import AuditLog, AuthenticatedUser
from app.auth import get_current_user
from app.db import db

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])

@router.get("", response_model=List[AuditLog])
def list_audit_logs(
    entity_id: Optional[str] = Query(None, description="Optional entity ID filter"),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Returns the persistent audit trail of all governance events for the user's organisation.
    """
    return db.list_audit_logs(org_id=user.org_id, entity_id=entity_id)
