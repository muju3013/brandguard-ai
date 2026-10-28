import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.models import (
    Draft, DraftCreateRequest, DraftUpdateRequest, ReviewDecisionRequest,
    CheckResult, AuthenticatedUser, AuditLog
)
from app.auth import get_current_user, require_role
from app.checker import evaluate_draft_against_guidelines
from app.db import db, now_iso
from app.rate_limiter import rate_limiter_general, rate_limiter_check
from app.routes.r3_routes import resolve_approval_evidence

from app.firebase_setup import get_firebase_app
try:
    from firebase_admin import auth as firebase_auth
except ImportError:
    firebase_auth = None

router = APIRouter(prefix="/api/drafts", tags=["drafts"])

def _resolve_and_repair_creator(draft: Draft) -> Draft:
    """
    Ensures creator identity is authoritative and never a raw JWT string or token substring.
    Repairs legacy records where creator_id can be authoritatively resolved.
    """
    raw_email = draft.creator_email or ""
    # Corrupt condition: starts with eyJ, contains substring fragment, or missing
    if not raw_email or raw_email.startswith("eyJ") or (raw_email.endswith("@example.com") and not draft.creator_id.startswith("user_")):
        resolved_email = None
        mem = db.get_membership(draft.creator_id)
        if mem and mem.email and not mem.email.startswith("eyJ") and not mem.email.endswith("@example.com"):
            resolved_email = mem.email
        else:
            fb_app = get_firebase_app()
            if fb_app and firebase_auth:
                try:
                    u = firebase_auth.get_user(draft.creator_id, app=fb_app)
                    if u.email and not u.email.startswith("eyJ"):
                        resolved_email = u.email
                except Exception:
                    pass

        draft.creator_email = resolved_email or "Creator email unavailable"
        if resolved_email:
            try:
                db.save_draft(draft)
            except Exception:
                pass
    return draft

@router.get("", response_model=List[Draft])
def list_drafts(
    my_drafts_only: bool = Query(False, description="Filter only drafts created by caller"),
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    List marketing drafts for the authenticated user's organisation.
    Tenant isolation is strictly enforced.
    """
    creator_id = user.user_id if my_drafts_only else None
    drafts = db.list_drafts(org_id=user.org_id, creator_id=creator_id)
    return [_resolve_and_repair_creator(d) for d in drafts]

@router.get("/{draft_id}", response_model=Draft)
def get_draft(
    draft_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """Fetch a single draft with its governance findings and review status."""
    draft = db.get_draft(draft_id)
    if not draft or draft.org_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found in your organisation."
        )
    return _resolve_and_repair_creator(draft)

@router.post("", response_model=Draft, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limiter_general)])
def create_draft(
    req: DraftCreateRequest,
    user: AuthenticatedUser = Depends(require_role(["creator", "admin"]))
):
    """
    Creator endpoint: Save a new draft with audience, channel, and campaign context.
    Executes independent deterministic pre-check and source-grounded Gemini AI review on save.
    """
    check_result = evaluate_draft_against_guidelines(
        draft_text=req.content,
        org_id=user.org_id,
        channel=req.channel,
        audience=req.audience,
        campaign=req.campaign,
        include_ai=True
    )

    draft = Draft(
        id=f"draft_{uuid.uuid4().hex[:10]}",
        org_id=user.org_id,
        title=req.title.strip(),
        content=req.content,
        channel=req.channel.strip().lower(),
        audience=req.audience.strip().lower(),
        campaign=req.campaign.strip(),
        status="draft",
        creator_id=user.user_id,
        creator_email=user.email if (user.email and not user.email.startswith("eyJ")) else "Creator email unavailable",
        findings=check_result.findings,
        deterministic_findings=check_result.deterministic_findings,
        ai_findings=check_result.ai_findings,
        ai_status=check_result.ai_status,
        outcome=check_result.outcome,
        review_notes=None,
        reviewed_by=None,
        reviewed_by_email=None,
        reviewed_at=None,
        created_at=now_iso(),
        updated_at=now_iso()
    )

    saved = db.save_draft(draft)

    # Audit trail
    db.record_audit(AuditLog(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        entity_type="draft",
        entity_id=saved.id,
        action="created",
        actor_id=user.user_id,
        actor_email=user.email,
        actor_role=user.role,
        details={
            "title": saved.title,
            "campaign": saved.campaign,
            "channel": saved.channel,
            "audience": saved.audience,
            "deterministic_flags": len(saved.deterministic_findings),
            "ai_flags": len(saved.ai_findings),
            "ai_status": saved.ai_status,
            "outcome": saved.outcome
        },
        timestamp=now_iso()
    ))

    return saved

@router.put("/{draft_id}", response_model=Draft)
def update_draft(
    draft_id: str,
    req: DraftUpdateRequest,
    user: AuthenticatedUser = Depends(require_role(["creator", "admin"]))
):
    """
    Creator revision: Edit a draft that is in 'draft' or 'changes_requested' status.
    Drafts currently 'in_review' or already 'approved' cannot be modified directly.
    """
    draft = db.get_draft(draft_id)
    if not draft or draft.org_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found in your organisation."
        )

    # Creators can only edit their own draft unless admin
    if user.role != "admin" and draft.creator_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to edit another creator's draft."
        )

    if draft.status not in ("draft", "changes_requested"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit draft in '{draft.status}' status. Resubmit or request new revision cycle."
        )

    # Apply changes
    if req.title is not None:
        draft.title = req.title.strip()
    if req.content is not None:
        draft.content = req.content
    if req.channel is not None:
        draft.channel = req.channel.strip().lower()
    if req.audience is not None:
        draft.audience = req.audience.strip().lower()
    if req.campaign is not None:
        draft.campaign = req.campaign.strip()

    # Re-evaluate findings with context
    check_result = evaluate_draft_against_guidelines(
        draft_text=draft.content,
        org_id=user.org_id,
        channel=draft.channel,
        audience=draft.audience,
        campaign=draft.campaign,
        include_ai=True
    )
    draft.findings = check_result.findings
    draft.deterministic_findings = check_result.deterministic_findings
    draft.ai_findings = check_result.ai_findings
    draft.ai_status = check_result.ai_status
    draft.outcome = check_result.outcome
    draft.status = "draft"  # Return to draft state after revision
    draft.updated_at = now_iso()

    saved = db.save_draft(draft)

    db.record_audit(AuditLog(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        entity_type="draft",
        entity_id=saved.id,
        action="updated",
        actor_id=user.user_id,
        actor_email=user.email,
        actor_role=user.role,
        details={
            "title": saved.title,
            "revision_cycle": "post_changes_requested" if draft.review_notes else "draft_edit",
            "deterministic_flags": len(saved.deterministic_findings),
            "ai_flags": len(saved.ai_findings),
            "outcome": saved.outcome
        },
        timestamp=now_iso()
    ))

    return saved

@router.post("/{draft_id}/check", response_model=CheckResult, dependencies=[Depends(rate_limiter_check)])
def run_precheck(
    draft_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    On-demand guideline checking using active org guidelines and source-grounded Gemini AI.
    Refreshes draft findings with evidence-linked citations.
    """
    draft = db.get_draft(draft_id)
    if not draft or draft.org_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found in your organisation."
        )

    check_result = evaluate_draft_against_guidelines(
        draft_text=draft.content,
        org_id=user.org_id,
        channel=draft.channel,
        audience=draft.audience,
        campaign=draft.campaign,
        include_ai=True
    )
    draft.findings = check_result.findings
    draft.deterministic_findings = check_result.deterministic_findings
    draft.ai_findings = check_result.ai_findings
    draft.ai_status = check_result.ai_status
    draft.outcome = check_result.outcome
    draft.updated_at = now_iso()
    db.save_draft(draft)

    db.record_audit(AuditLog(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        entity_type="draft",
        entity_id=draft.id,
        action="checked",
        actor_id=user.user_id,
        actor_email=user.email,
        actor_role=user.role,
        details={
            "outcome": check_result.outcome,
            "deterministic_findings": len(check_result.deterministic_findings),
            "ai_findings": len(check_result.ai_findings),
            "ai_status": check_result.ai_status,
            "rules_evaluated": check_result.active_rules_evaluated
        },
        timestamp=now_iso()
    ))

    return check_result

@router.post("/{draft_id}/submit", response_model=Draft)
def submit_draft(
    draft_id: str,
    user: AuthenticatedUser = Depends(require_role(["creator", "admin"]))
):
    """
    Creator submits draft for reviewer evaluation ('in_review').
    """
    draft = db.get_draft(draft_id)
    if not draft or draft.org_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found in your organisation."
        )

    if user.role != "admin" and draft.creator_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator who owns this draft can submit it for review."
        )

    if draft.status not in ("draft", "changes_requested"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit draft currently in '{draft.status}' status."
        )

    # Re-run check on submission to guarantee fresh findings
    check_result = evaluate_draft_against_guidelines(
        draft_text=draft.content,
        org_id=user.org_id,
        channel=draft.channel,
        audience=draft.audience,
        campaign=draft.campaign,
        include_ai=True
    )
    if check_result.outcome == "guidelines_not_configured":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit draft for review: No active brand guidelines are configured in your workspace. Guidelines must be created and activated first."
        )

    draft.findings = check_result.findings
    draft.deterministic_findings = check_result.deterministic_findings
    draft.ai_findings = check_result.ai_findings
    draft.ai_status = check_result.ai_status
    draft.outcome = check_result.outcome
    draft.status = "in_review"
    draft.updated_at = now_iso()

    saved = db.save_draft(draft)

    db.record_audit(AuditLog(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        entity_type="draft",
        entity_id=saved.id,
        action="submitted",
        actor_id=user.user_id,
        actor_email=user.email,
        actor_role=user.role,
        details={
            "status": "in_review",
            "findings_count": len(saved.findings),
            "outcome": saved.outcome
        },
        timestamp=now_iso()
    ))

    return saved

@router.post("/{draft_id}/approve", response_model=dict)
def approve_draft(
    draft_id: str,
    req: ReviewDecisionRequest,
    user: AuthenticatedUser = Depends(require_role(["reviewer", "admin"]))
):
    """
    Reviewer approval action.
    Security rules:
    - Creator cannot approve their own draft (separation of duties).
    - Draft must be in 'in_review' status.
    - No automatic publication.
    """
    draft = db.get_draft(draft_id)
    if not draft or draft.org_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found in your organisation."
        )

    # Creator cannot approve own draft
    if user.role != "admin" and draft.creator_id == user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Governance separation of duties: Creators cannot approve their own marketing drafts."
        )

    if draft.status != "in_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only drafts with status 'in_review' can be approved. Current status: '{draft.status}'."
        )

    high_risk = any(f.severity == "high" for f in draft.findings)
    evidence_record = None
    if high_risk:
        evidence_record = resolve_approval_evidence(user.org_id, draft.content, req.evidence_dossier_id, req.exception_reason)

    draft.status = "approved"
    draft.review_notes = req.comments.strip()
    draft.reviewed_by = user.user_id
    draft.reviewed_by_email = user.email
    draft.reviewed_at = now_iso()
    draft.updated_at = now_iso()

    saved = db.save_draft(draft)

    db.record_audit(AuditLog(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        entity_type="draft",
        entity_id=saved.id,
        action="approved",
        actor_id=user.user_id,
        actor_email=user.email,
        actor_role=user.role,
        details={
            "decision": "approved",
            "review_notes": req.comments.strip(),
            "publication_status": "manual_only_no_auto_publish",
            "high_risk": high_risk,
            "evidence_record": evidence_record
        },
        timestamp=now_iso()
    ))

    return {
        "status": "approved",
        "draft_id": saved.id,
        "reviewed_by": user.email,
        "reviewed_at": draft.reviewed_at,
        "notes": req.comments.strip(),
        "publication_notice": "Approval complete. In accordance with governance policy, no automatic publication was triggered."
    }

@router.post("/{draft_id}/request-changes", response_model=dict)
def request_changes(
    draft_id: str,
    req: ReviewDecisionRequest,
    user: AuthenticatedUser = Depends(require_role(["reviewer", "admin"]))
):
    """
    Reviewer requests changes with mandatory revision instructions.
    """
    draft = db.get_draft(draft_id)
    if not draft or draft.org_id != user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found in your organisation."
        )

    if draft.status != "in_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only drafts in 'in_review' can receive change requests. Current status: '{draft.status}'."
        )

    draft.status = "changes_requested"
    draft.review_notes = req.comments.strip()
    draft.reviewed_by = user.user_id
    draft.reviewed_by_email = user.email
    draft.reviewed_at = now_iso()
    draft.updated_at = now_iso()

    saved = db.save_draft(draft)

    db.record_audit(AuditLog(
        id=str(uuid.uuid4()),
        org_id=user.org_id,
        entity_type="draft",
        entity_id=saved.id,
        action="changes_requested",
        actor_id=user.user_id,
        actor_email=user.email,
        actor_role=user.role,
        details={
            "decision": "changes_requested",
            "feedback": req.comments.strip()
        },
        timestamp=now_iso()
    ))

    return {
        "status": "changes_requested",
        "draft_id": saved.id,
        "reviewed_by": user.email,
        "reviewed_at": draft.reviewed_at,
        "feedback": req.comments.strip()
    }
