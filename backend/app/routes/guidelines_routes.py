import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.models import (
    GuidelineRule, GuidelineCreateRequest, GuidelineUpdateRequest,
    GuidelineVersionRecord, AuthenticatedUser, AuditLog
)
from app.auth import get_current_user, require_role
from app.db import db, now_iso

router = APIRouter(prefix="/api/guidelines", tags=["guidelines"])

@router.get("", response_model=List[GuidelineRule])
def get_guidelines(
    active_only: bool = Query(False, description="Filter for active rules only"),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    List brand guidelines strictly isolated to the caller's organisation.
    Available to admin, creator, and reviewer.
    """
    return db.list_guidelines(org_id=user.org_id, active_only=active_only)

@router.get("/{rule_id_or_id}", response_model=GuidelineRule)
def get_guideline(
    rule_id_or_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Fetch single guideline rule ensuring tenant isolation."""
    rule = db.get_guideline(rule_id_or_id) or db.get_guideline_by_rule_id(user.org_id, rule_id_or_id)
    if not rule or rule.org_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guideline '{rule_id_or_id}' not found in your organisation."
        )
    return rule

@router.post("", response_model=GuidelineRule, status_code=status.HTTP_201_CREATED)
def create_guideline(
    req: GuidelineCreateRequest,
    user: AuthenticatedUser = Depends(require_role(["admin"]))
):
    """Admin-only: Create a new brand guideline rule for the organisation."""
    # Check for duplicate rule_id in organisation
    existing = db.get_guideline_by_rule_id(user.org_id, req.rule_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule ID '{req.rule_id}' already exists in your organisation."
        )

    new_rule = GuidelineRule(
        id=f"rule_{uuid.uuid4().hex[:10]}",
        rule_id=req.rule_id.strip().upper(),
        org_id=user.org_id,
        category=req.category,
        title=req.title.strip(),
        description=req.description.strip(),
        source_label=req.source_label.strip(),
        pattern=req.pattern.strip(),
        severity=req.severity,
        remedy_suggestion=req.remedy_suggestion.strip(),
        is_active=req.is_active,
        version=1,
        version_history=[],
        created_at=now_iso(),
        created_by=user.email,
        updated_at=now_iso(),
        updated_by=user.email
    )

    created = db.create_guideline(new_rule)

    # Persistent audit log
    db.record_audit(AuditLog(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        entity_type="guideline",
        entity_id=created.rule_id,
        action="guideline_created",
        actor_id=user.user_id,
        actor_email=user.email,
        actor_role=user.role,
        details={
            "rule_id": created.rule_id,
            "version": 1,
            "source_label": created.source_label,
            "category": created.category
        },
        timestamp=now_iso()
    ))

    return created

@router.put("/{rule_id_or_id}", response_model=GuidelineRule)
def update_guideline(
    rule_id_or_id: str,
    req: GuidelineUpdateRequest,
    user: AuthenticatedUser = Depends(require_role(["admin"]))
):
    """
    Admin-only: Update a brand guideline.
    Automatically increments version number and preserves past version in version_history.
    """
    rule = db.get_guideline(rule_id_or_id) or db.get_guideline_by_rule_id(user.org_id, rule_id_or_id)
    if not rule or rule.org_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guideline not found in your organisation."
        )

    # Snapshot current version before updating
    snapshot = GuidelineVersionRecord(
        version=rule.version,
        title=rule.title,
        category=rule.category,
        description=rule.description,
        source_label=rule.source_label,
        pattern=rule.pattern,
        severity=rule.severity,
        remedy_suggestion=rule.remedy_suggestion,
        is_active=rule.is_active,
        updated_at=rule.updated_at,
        updated_by=rule.updated_by
    )

    history = list(rule.version_history)
    history.append(snapshot)

    # Apply updates
    if req.title is not None:
        rule.title = req.title.strip()
    if req.category is not None:
        rule.category = req.category
    if req.description is not None:
        rule.description = req.description.strip()
    if req.source_label is not None:
        rule.source_label = req.source_label.strip()
    if req.pattern is not None:
        rule.pattern = req.pattern.strip()
    if req.severity is not None:
        rule.severity = req.severity
    if req.remedy_suggestion is not None:
        rule.remedy_suggestion = req.remedy_suggestion.strip()
    if req.is_active is not None:
        rule.is_active = req.is_active

    rule.version += 1
    rule.version_history = history
    rule.updated_at = now_iso()
    rule.updated_by = user.email

    updated = db.update_guideline(rule)

    db.record_audit(AuditLog(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        entity_type="guideline",
        entity_id=updated.rule_id,
        action="guideline_updated",
        actor_id=user.user_id,
        actor_email=user.email,
        actor_role=user.role,
        details={
            "rule_id": updated.rule_id,
            "new_version": updated.version,
            "source_label": updated.source_label
        },
        timestamp=now_iso()
    ))

    return updated

@router.delete("/{rule_id_or_id}")
def deactivate_guideline(
    rule_id_or_id: str,
    user: AuthenticatedUser = Depends(require_role(["admin"]))
):
    """Admin-only: Deactivate a brand guideline rule."""
    rule = db.get_guideline(rule_id_or_id) or db.get_guideline_by_rule_id(user.org_id, rule_id_or_id)
    if not rule or rule.org_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guideline not found in your organisation."
        )

    rule.is_active = False
    rule.updated_at = now_iso()
    rule.updated_by = user.email
    db.update_guideline(rule)

    db.record_audit(AuditLog(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        entity_type="guideline",
        entity_id=rule.rule_id,
        action="guideline_deactivated",
        actor_id=user.user_id,
        actor_email=user.email,
        actor_role=user.role,
        details={"rule_id": rule.rule_id, "is_active": False},
        timestamp=now_iso()
    ))

    return {"status": "deactivated", "rule_id": rule.rule_id}
