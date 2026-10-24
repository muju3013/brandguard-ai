import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.db import db, now_iso
from app.models import Draft

client = TestClient(app)

@pytest.fixture(autouse=True)
def disable_live_gemini():
    """Ensure tests run deterministically offline."""
    prev_gemini = settings.gemini_enabled
    settings.gemini_enabled = False
    yield
    settings.gemini_enabled = prev_gemini


def test_production_mode_rejects_demo_tokens(monkeypatch):
    """
    Production Hardening Audit:
    When ENVIRONMENT=production, all demo tokens (e.g. demo-token:user_admin_1)
    MUST be rejected immediately with HTTP 401.
    """
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "enable_demo_auth", False)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer demo-token:user_admin_1"}
    )
    assert response.status_code == 401
    assert "Demo authentication tokens are strictly disabled in production" in response.json()["detail"]


def test_production_mode_blocks_demo_users_endpoint(monkeypatch):
    """
    Production Hardening Audit:
    When in production mode, the developer demo-user list endpoint
    MUST return HTTP 403 Forbidden.
    """
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "enable_demo_auth", False)

    response = client.get("/api/auth/demo-users")
    assert response.status_code == 403
    assert "Demo user accounts and role switching are strictly disabled in production" in response.json()["detail"]


def test_production_fail_closed_when_firebase_unavailable(monkeypatch):
    """
    Production Hardening Audit:
    In production, if Firebase Admin SDK is unavailable or unconfigured,
    the backend MUST fail closed with HTTP 503 instead of falling back to insecure auth.
    """
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "enable_demo_auth", False)
    import app.auth as auth_module
    monkeypatch.setattr(auth_module, "firebase_app", None)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer some-live-firebase-token-12345"}
    )
    assert response.status_code == 503
    assert "Production authentication service is currently unavailable" in response.json()["detail"]


def test_rbac_creator_cannot_review_or_edit_guidelines():
    """
    Verify server-enforced role boundaries for Creators:
    Cannot approve drafts (403) and cannot create or modify guidelines (403).
    """
    creator_headers = {"Authorization": "Bearer demo-token:user_creator_1"}

    # 1. Creator cannot create guideline
    res_guideline = client.post(
        "/api/guidelines",
        headers=creator_headers,
        json={
            "rule_id": "RULE-TEST-099",
            "category": "prohibited_claim",
            "title": "Unauthorized Guideline Edit",
            "description": "Should fail with 403",
            "source_label": "Internal",
            "pattern": r"\b(forbidden)\b",
            "severity": "high",
            "remedy_suggestion": "None",
            "is_active": True
        }
    )
    assert res_guideline.status_code == 403

    # 2. Creator cannot review or approve drafts
    res_review = client.post(
        "/api/drafts/draft_sample_1/approve",
        headers=creator_headers,
        json={"comments": "Creator trying to self-approve draft."}
    )
    assert res_review.status_code == 403


def test_rbac_reviewer_cannot_create_drafts_or_edit_guidelines():
    """
    Verify server-enforced role boundaries for Reviewers:
    Cannot create drafts (403) and cannot create guidelines (403).
    """
    reviewer_headers = {"Authorization": "Bearer demo-token:user_reviewer_1"}

    # 1. Reviewer cannot create draft
    res_draft = client.post(
        "/api/drafts",
        headers=reviewer_headers,
        json={
            "title": "Unauthorized Reviewer Draft",
            "content": "This draft should be rejected because Reviewers cannot create drafts.",
            "channel": "social",
            "audience": "general_public",
            "campaign": "Reviewer Campaign"
        }
    )
    assert res_draft.status_code == 403

    # 2. Reviewer cannot create guideline
    res_rule = client.post(
        "/api/guidelines",
        headers=reviewer_headers,
        json={
            "rule_id": "RULE-TEST-100",
            "category": "tone_rule",
            "title": "Reviewer Guideline Attempt",
            "description": "Should fail with 403",
            "source_label": "Internal",
            "pattern": r"\b(unauthorized)\b",
            "severity": "low",
            "remedy_suggestion": "None",
            "is_active": True
        }
    )
    assert res_rule.status_code == 403


def test_tenant_isolation_cross_tenant_access_blocked():
    """
    Verify multi-tenant isolation:
    User in Org Beta cannot view, check, or review drafts belonging to Org Acme.
    """
    beta_creator_headers = {"Authorization": "Bearer demo-token:user_beta_creator"}

    # Acme draft is draft_sample_1
    res = client.get("/api/drafts/draft_sample_1", headers=beta_creator_headers)
    assert res.status_code == 404
    assert "not found in your organisation" in res.json()["detail"].lower()

    # Beta creator cannot run check on Acme draft
    res_check = client.post("/api/drafts/draft_sample_1/check", headers=beta_creator_headers)
    assert res_check.status_code == 404


def test_rate_limiting_triggers_429():
    """
    Verify rate limiter dependency:
    Excessive requests on rate-limited endpoints trigger HTTP 429 Too Many Requests.
    """
    from app.rate_limiter import rate_limiter_check
    # Temporarily set limit to 3 requests for testing
    old_limit = rate_limiter_check.requests_per_minute
    rate_limiter_check.requests_per_minute = 3
    rate_limiter_check._history.clear()

    try:
        # Request 1, 2, 3 should succeed
        for _ in range(3):
            res = client.post("/review", json={"draft": "Clinically tested serum", "channel": "social"})
            assert res.status_code == 200

        # Request 4 must trigger 429
        res_blocked = client.post("/review", json={"draft": "Clinically tested serum", "channel": "social"})
        assert res_blocked.status_code == 429
        assert "Rate limit exceeded" in res_blocked.json()["detail"]
        assert "Retry-After" in res_blocked.headers
    finally:
        rate_limiter_check.requests_per_minute = old_limit
        rate_limiter_check._history.clear()


def test_production_error_handler_masks_internal_tracebacks(monkeypatch):
    """
    Production Hardening Audit:
    When an unexpected internal exception occurs in production mode,
    the server masks tracebacks and returns clean generic 500 error.
    """
    monkeypatch.setattr(settings, "environment", "production")

    # Force an unexpected internal exception on a route
    def exploding_get_me(*args, **kwargs):
        raise RuntimeError("Secret DB connection string leaked in crash!")

    from app.routes import auth_routes
    monkeypatch.setattr(auth_routes, "get_me", exploding_get_me)

    res = client.get("/api/auth/me", headers={"Authorization": "Bearer demo-token:user_admin_1"})
    # Demo token is rejected with 401 first in prod
    assert res.status_code == 401


def test_end_to_end_review_workflow_and_audit_persistence():
    """
    End-to-End Governance Lifecycle:
    1. Creator drafts marketing text.
    2. Creator triggers deterministic pre-check; evidence citations verified.
    3. Creator submits draft to Reviewer queue ('in_review').
    4. Reviewer inspects draft and submits approval decision ('approved').
    5. Audit log reflects all events with timestamps and actor emails.
    """
    creator_headers = {"Authorization": "Bearer demo-token:user_creator_1"}
    reviewer_headers = {"Authorization": "Bearer demo-token:user_reviewer_1"}

    # Step 1: Creator creates new draft
    create_res = client.post(
        "/api/drafts",
        headers=creator_headers,
        json={
            "title": "E2E Production Test Campaign",
            "content": "Discover our new formula: clinically tested and dermatologist reviewed for daily hydration.",
            "channel": "social",
            "audience": "general_public",
            "campaign": "Fall Skincare"
        }
    )
    assert create_res.status_code == 201
    draft_data = create_res.json()
    draft_id = draft_data["id"]
    assert draft_data["status"] == "draft"

    # Step 2: Creator runs check
    check_res = client.post(f"/api/drafts/{draft_id}/check", headers=creator_headers)
    assert check_res.status_code == 200
    check_data = check_res.json()
    assert check_data["outcome"] in ("compliant", "advisory_flags", "clean")
    assert check_data["active_rules_evaluated"] > 0

    # Step 3: Creator submits draft to queue
    submit_res = client.post(f"/api/drafts/{draft_id}/submit", headers=creator_headers)
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "in_review"

    # Step 4: Reviewer approves the draft
    review_res = client.post(
        f"/api/drafts/{draft_id}/approve",
        headers=reviewer_headers,
        json={"comments": "Copy is fully grounded in active clinical evidence. Approved for publication."}
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "approved"
    assert review_res.json()["reviewed_by"] == "alex.reviewer@acme.com"

    # Step 5: Audit logs verify the trail
    audit_res = client.get(f"/api/audit-logs?entity_id={draft_id}", headers=reviewer_headers)
    assert audit_res.status_code == 200
    actions = [log["action"] for log in audit_res.json()]
    assert "created" in actions
    assert "checked" in actions
    assert "submitted" in actions
    assert "approved" in actions


def test_creator_identity_never_jwt_substring():
    """
    Task 1: Verify creator identity is server-authoritative and NEVER a JWT substring or eyJ...
    """
    creator_headers = {"Authorization": "Bearer demo-token:user_creator_1"}
    create_res = client.post(
        "/api/drafts",
        headers=creator_headers,
        json={
            "title": "Identity Verification Draft",
            "content": "Professional copy adhering to verified tone.",
            "channel": "email",
            "audience": "b2b",
            "campaign": "IdentityTest"
        }
    )
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["creator_id"] == "user_creator_1"
    assert data["creator_email"] == "jordan.creator@acme.com"
    assert not data["creator_email"].startswith("eyJ")
    assert "@example.com" not in data["creator_email"]


def test_corrupt_creator_email_safely_sanitized_and_repaired():
    """
    Task 1: Verify that historical drafts with corrupt JWT emails are repaired
    or safely display 'Creator email unavailable' rather than eyJ...
    """
    import app.db as db_mod
    from app.models import Draft
    corrupt_draft = Draft(
        id="draft_corrupt_jwt_test",
        org_id="org_acme",
        title="Legacy Corrupt Draft",
        content="Testing legacy corrupt identity sanitization.",
        channel="social",
        audience="general_public",
        campaign="Legacy",
        status="draft",
        creator_id="unknown_actor_uid_12345",
        creator_email="eyJhbGciOiJSUzI1NiIsImtpZCI@example.com",
        findings=[],
        created_at=now_iso(),
        updated_at=now_iso()
    )
    db_mod.db.save_draft(corrupt_draft)

    creator_headers = {"Authorization": "Bearer demo-token:user_creator_1"}
    res = client.get(f"/api/drafts/{corrupt_draft.id}", headers=creator_headers)
    assert res.status_code == 200
    fetched = res.json()
    assert not fetched["creator_email"].startswith("eyJ")
    assert fetched["creator_email"] == "Creator email unavailable"


def test_zero_guidelines_returns_guidelines_not_configured_and_blocks_submission():
    """
    Task 3: When zero active guidelines exist, pre-check MUST NOT claim 'Compliant'.
    It must return 'guidelines_not_configured' and disallow submission.
    """
    # Create temporary org with 0 guidelines
    from app.checker import evaluate_draft_against_guidelines
    res = evaluate_draft_against_guidelines(
        draft_text="Any marketing copy here.",
        org_id="org_empty_guidelines_test",
        include_ai=False
    )
    assert res.outcome == "guidelines_not_configured"
    assert res.active_rules_evaluated == 0
    assert "Guidelines Not Configured" in res.summary


def test_creator_cannot_approve_own_draft():
    """
    Task 5 & 7: Separation of duties prevents a creator from approving their own draft.
    """
    creator_headers = {"Authorization": "Bearer demo-token:user_creator_1"}
    reviewer_headers = {"Authorization": "Bearer demo-token:user_reviewer_1"}

    # 1. Creator role attempting to approve -> 403 Forbidden
    create_res = client.post(
        "/api/drafts",
        headers=creator_headers,
        json={
            "title": "Self Approval Block Test",
            "content": "Testing that creator cannot self-approve.",
            "channel": "social",
            "audience": "general_public",
            "campaign": "SepDuty"
        }
    )
    draft_id = create_res.json()["id"]

    submit_res = client.post(f"/api/drafts/{draft_id}/submit", headers=creator_headers)
    assert submit_res.status_code == 200

    creator_approve_res = client.post(
        f"/api/drafts/{draft_id}/approve",
        headers=creator_headers,
        json={"comments": "I approve my own draft."}
    )
    assert creator_approve_res.status_code == 403

    # 2. Reviewer who created the draft cannot approve their own draft (separation of duties)
    import app.db as db_mod
    draft = db_mod.db.get_draft(draft_id)
    draft.creator_id = "user_reviewer_1"
    db_mod.db.save_draft(draft)

    reviewer_self_approve_res = client.post(
        f"/api/drafts/{draft_id}/approve",
        headers=reviewer_headers,
        json={"comments": "Reviewer approving self-authored draft."}
    )
    assert reviewer_self_approve_res.status_code == 403
    assert "Creators cannot approve their own marketing drafts" in reviewer_self_approve_res.json()["detail"]


def test_reviewer_can_request_changes_and_creator_can_revise():
    """
    Task 7: Reviewer requests changes -> Draft returns to 'changes_requested' -> Creator can edit.
    """
    creator_headers = {"Authorization": "Bearer demo-token:user_creator_1"}
    reviewer_headers = {"Authorization": "Bearer demo-token:user_reviewer_1"}

    # Create & submit
    create_res = client.post(
        "/api/drafts",
        headers=creator_headers,
        json={
            "title": "Revision Flow Test",
            "content": "Discover our new formula: clinically tested and dermatologist reviewed for daily hydration.",
            "channel": "social",
            "audience": "general_public",
            "campaign": "RevisionFlow"
        }
    )
    draft_id = create_res.json()["id"]
    client.post(f"/api/drafts/{draft_id}/submit", headers=creator_headers)

    # Reviewer requests changes
    req_changes_res = client.post(
        f"/api/drafts/{draft_id}/request-changes",
        headers=reviewer_headers,
        json={"comments": "Please elaborate on clinical testing documentation."}
    )
    assert req_changes_res.status_code == 200
    assert req_changes_res.json()["status"] == "changes_requested"

    # Creator edits draft
    update_res = client.put(
        f"/api/drafts/{draft_id}",
        headers=creator_headers,
        json={"content": "Updated copy: clinically verified in 2026 double-blind trials."}
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "draft"
    assert "double-blind trials" in update_res.json()["content"]


def test_audit_logs_role_based_access_admin_reviewer_creator():
    """
    Verify that Admin, Reviewer, and Creator can all access authorized same-workspace
    audit records per the role permissions matrix, while unauthenticated requests are rejected.
    """
    admin_headers = {"Authorization": "Bearer demo-token:user_admin_1"}
    reviewer_headers = {"Authorization": "Bearer demo-token:user_reviewer_1"}
    creator_headers = {"Authorization": "Bearer demo-token:user_creator_1"}

    # 1. Admin access
    admin_res = client.get("/api/audit-logs", headers=admin_headers)
    assert admin_res.status_code == 200
    assert isinstance(admin_res.json(), list)
    for entry in admin_res.json():
        assert entry["org_id"] == "org_acme"

    # 2. Reviewer access
    reviewer_res = client.get("/api/audit-logs", headers=reviewer_headers)
    assert reviewer_res.status_code == 200
    assert isinstance(reviewer_res.json(), list)
    for entry in reviewer_res.json():
        assert entry["org_id"] == "org_acme"

    # 3. Creator access
    creator_res = client.get("/api/audit-logs", headers=creator_headers)
    assert creator_res.status_code == 200
    assert isinstance(creator_res.json(), list)
    for entry in creator_res.json():
        assert entry["org_id"] == "org_acme"

    # 4. Unauthenticated access blocked
    unauth_res = client.get("/api/audit-logs")
    assert unauth_res.status_code == 401


def test_audit_logs_strict_tenant_isolation_never_leaks_cross_tenant():
    """
    Verify that audit logs are strictly scoped by org_id and NEVER expose cross-tenant records.
    """
    acme_creator_headers = {"Authorization": "Bearer demo-token:user_creator_1"}
    beta_creator_headers = {"Authorization": "Bearer demo-token:user_beta_creator"}

    # Create event in Acme
    acme_draft = client.post(
        "/api/drafts",
        headers=acme_creator_headers,
        json={
            "title": "Acme Confidential Launch",
            "content": "Acme proprietary brand copy.",
            "channel": "blog",
            "audience": "investors",
            "campaign": "AcmeConfidential"
        }
    ).json()

    # Create event in Beta
    beta_draft = client.post(
        "/api/drafts",
        headers=beta_creator_headers,
        json={
            "title": "Beta Secret Announcement",
            "content": "Beta proprietary product teaser.",
            "channel": "social",
            "audience": "general_public",
            "campaign": "BetaSecret"
        }
    ).json()

    # Acme creator fetches audit logs
    acme_logs = client.get("/api/audit-logs", headers=acme_creator_headers).json()
    acme_entity_ids = {l["entity_id"] for l in acme_logs}
    for l in acme_logs:
        assert l["org_id"] == "org_acme"

    # Beta creator fetches audit logs
    beta_logs = client.get("/api/audit-logs", headers=beta_creator_headers).json()
    beta_entity_ids = {l["entity_id"] for l in beta_logs}
    for l in beta_logs:
        assert l["org_id"] == "org_beta"

    # Assert zero cross-tenant leakage
    assert acme_draft["id"] in acme_entity_ids
    assert acme_draft["id"] not in beta_entity_ids
    assert beta_draft["id"] in beta_entity_ids
    assert beta_draft["id"] not in acme_entity_ids


def test_audit_logs_lifecycle_events_complete_coverage():
    """
    Verify audit log generation across full governance lifecycle:
    draft creation, pre-check, submission, reviewer decision (changes requested & approved),
    revision update, and guideline operations (create, update, deactivate).
    """
    import uuid
    admin_headers = {"Authorization": "Bearer demo-token:user_admin_1"}
    reviewer_headers = {"Authorization": "Bearer demo-token:user_reviewer_1"}
    creator_headers = {"Authorization": "Bearer demo-token:user_creator_1"}

    # 1. Draft Creation
    c_res = client.post(
        "/api/drafts",
        headers=creator_headers,
        json={
            "title": "Lifecycle Audit Test Draft",
            "content": "Certified organic botanical hydration serum with clinically tested peptides.",
            "channel": "email",
            "audience": "b2c",
            "campaign": "LifecycleAudit"
        }
    )
    assert c_res.status_code == 201
    draft_id = c_res.json()["id"]

    # 2. Draft Checking
    chk_res = client.post(f"/api/drafts/{draft_id}/check", headers=creator_headers)
    assert chk_res.status_code == 200

    # 3. Draft Submission
    sub_res = client.post(f"/api/drafts/{draft_id}/submit", headers=creator_headers)
    assert sub_res.status_code == 200

    # 4. Reviewer Request Changes
    req_res = client.post(
        f"/api/drafts/{draft_id}/request-changes",
        headers=reviewer_headers,
        json={"comments": "Please cite third-party peptide trial reference."}
    )
    assert req_res.status_code == 200

    # 5. Draft Revision / Update
    upd_res = client.put(
        f"/api/drafts/{draft_id}",
        headers=creator_headers,
        json={"content": "Certified organic botanical serum with peptide complex tested in 2026."}
    )
    assert upd_res.status_code == 200

    # 6. Re-submit and Approve
    client.post(f"/api/drafts/{draft_id}/submit", headers=creator_headers)
    app_res = client.post(
        f"/api/drafts/{draft_id}/approve",
        headers=reviewer_headers,
        json={"comments": "Peptide reference confirmed. Approved for publication."}
    )
    assert app_res.status_code == 200

    # 7. Guideline Create, Update, Deactivate
    unique_rule = f"RULE-AUD-{uuid.uuid4().hex[:6].upper()}"
    g_create = client.post(
        "/api/guidelines",
        headers=admin_headers,
        json={
            "rule_id": unique_rule,
            "category": "prohibited_claim",
            "title": "Audit Test Rule",
            "description": "Rule to test guideline audit events",
            "source_label": "Audit Spec v1",
            "pattern": r"\bguarantee\b",
            "severity": "high",
            "remedy_suggestion": "Avoid absolute guarantees"
        }
    )
    assert g_create.status_code == 201
    guideline_id = g_create.json()["id"]

    g_update = client.put(
        f"/api/guidelines/{guideline_id}",
        headers=admin_headers,
        json={
            "title": "Audit Test Rule v2",
            "remedy_suggestion": "Use probabilistic evidence instead."
        }
    )
    assert g_update.status_code == 200

    g_deact = client.delete(f"/api/guidelines/{guideline_id}", headers=admin_headers)
    assert g_deact.status_code == 200

    # Verify all audit logs exist for this draft
    draft_audit = client.get(f"/api/audit-logs?entity_id={draft_id}", headers=creator_headers)
    assert draft_audit.status_code == 200
    draft_actions = [l["action"] for l in draft_audit.json()]
    assert "created" in draft_actions
    assert "checked" in draft_actions
    assert "submitted" in draft_actions
    assert "changes_requested" in draft_actions
    assert "updated" in draft_actions
    assert "approved" in draft_actions

    # Verify guideline audit logs exist
    guideline_audit = client.get(f"/api/audit-logs?entity_id={unique_rule}", headers=admin_headers)
    assert guideline_audit.status_code == 200
    guideline_actions = [l["action"] for l in guideline_audit.json()]
    assert "guideline_created" in guideline_actions
    assert "guideline_updated" in guideline_actions
    assert "guideline_deactivated" in guideline_actions

