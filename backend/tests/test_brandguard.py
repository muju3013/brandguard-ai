import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import db

from app.config import settings

client = TestClient(app)

# Helper token headers
ADMIN_HEADERS = {"Authorization": "Bearer demo-token:user_admin_1"}
REVIEWER_HEADERS = {"Authorization": "Bearer demo-token:user_reviewer_1"}
CREATOR_HEADERS = {"Authorization": "Bearer demo-token:user_creator_1"}
BETA_CREATOR_HEADERS = {"Authorization": "Bearer demo-token:user_beta_creator"}

@pytest.fixture(autouse=True)
def isolate_phase2_deterministic_tests(monkeypatch):
    """Ensure Phase 2 unit tests evaluate deterministic rules independently of live Gemini network calls."""
    monkeypatch.setattr(settings, "gemini_enabled", False)

# ---------------------------------------------------------------------------
# 1. Phase 1 Backwards Compatibility Tests
# ---------------------------------------------------------------------------

def test_phase1_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["mode"] == "deterministic-demo"

def test_phase1_review_endpoint():
    res = client.post("/review", json={
        "draft": "Our skincare product cures acne in 24 hours. Guaranteed results!",
        "channel": "social"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "deterministic-demo"
    assert data["outcome"] == "needs_revision"
    assert len(data["findings"]) >= 2
    rule_ids = [f["rule_id"] for f in data["findings"]]
    assert "DEMO-001" in rule_ids or "DEMO-002" in rule_ids

# ---------------------------------------------------------------------------
# 2. Authentication & Authorization Enforcement
# ---------------------------------------------------------------------------

def test_unauthenticated_requests_rejected():
    # Calling protected endpoints without authorization header
    res1 = client.get("/api/guidelines")
    assert res1.status_code == 401

    res2 = client.get("/api/drafts")
    assert res2.status_code == 401

    res3 = client.get("/api/audit-logs")
    assert res3.status_code == 401

    # Calling with malformed authorization header
    res4 = client.get("/api/guidelines", headers={"Authorization": "InvalidTokenFormat"})
    assert res4.status_code == 401

def test_server_authoritative_user_profile():
    res = client.get("/api/auth/me", headers=CREATOR_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "creator"
    assert data["org_id"] == "org_acme"
    assert data["email"] == "jordan.creator@acme.com"

# ---------------------------------------------------------------------------
# 3. Role-Based Access Control (RBAC) Permissions Tests
# ---------------------------------------------------------------------------

def test_creator_cannot_approve_or_request_changes():
    # Create draft as creator
    draft_res = client.post("/api/drafts", headers=CREATOR_HEADERS, json={
        "title": "Serum Launch",
        "content": "A high-performance hydrating serum for dry skin.",
        "channel": "social",
        "audience": "general_public",
        "campaign": "Spring2026"
    })
    assert draft_res.status_code == 201
    draft_id = draft_res.json()["id"]

    # Creator submits draft
    client.post(f"/api/drafts/{draft_id}/submit", headers=CREATOR_HEADERS)

    # Creator tries to approve own draft -> 403 Forbidden
    res_approve = client.post(f"/api/drafts/{draft_id}/approve", headers=CREATOR_HEADERS, json={
        "comments": "Self-approval attempt"
    })
    assert res_approve.status_code == 403

    # Creator tries to request changes -> 403 Forbidden
    res_changes = client.post(f"/api/drafts/{draft_id}/request-changes", headers=CREATOR_HEADERS, json={
        "comments": "Unauthorized change request"
    })
    assert res_changes.status_code == 403

def test_creator_cannot_manage_guidelines():
    # Creator tries to create a guideline
    res = client.post("/api/guidelines", headers=CREATOR_HEADERS, json={
        "rule_id": "RULE-UNAUTH-01",
        "category": "prohibited_claim",
        "title": "Unauthorized Guideline",
        "description": "Should fail",
        "source_label": "Internal Legal",
        "pattern": "forbidden",
        "severity": "high",
        "remedy_suggestion": "Remove"
    })
    assert res.status_code == 403

def test_reviewer_cannot_create_drafts():
    # Reviewer trying to create draft -> 403 Forbidden
    res = client.post("/api/drafts", headers=REVIEWER_HEADERS, json={
        "title": "Reviewer Draft",
        "content": "This should not be allowed for reviewer role",
        "channel": "blog",
        "audience": "b2b",
        "campaign": "Reviewer"
    })
    assert res.status_code == 403

# ---------------------------------------------------------------------------
# 4. Tenant Isolation Tests (Multi-Organisation Workspace Security)
# ---------------------------------------------------------------------------

def test_tenant_isolation_drafts():
    # Org Acme creates a draft
    acme_draft_res = client.post("/api/drafts", headers=CREATOR_HEADERS, json={
        "title": "Acme Confidential Strategy",
        "content": "Acme confidential content.",
        "channel": "press_release",
        "audience": "b2b",
        "campaign": "SecretLaunch"
    })
    assert acme_draft_res.status_code == 201
    acme_draft_id = acme_draft_res.json()["id"]

    # Dave (Creator at Org Beta) tries to view Acme draft -> 404 Not Found (or 403)
    res_get = client.get(f"/api/drafts/{acme_draft_id}", headers=BETA_CREATOR_HEADERS)
    assert res_get.status_code == 404

    # Dave tries to update Acme draft -> 404 Not Found
    res_put = client.put(f"/api/drafts/{acme_draft_id}", headers=BETA_CREATOR_HEADERS, json={
        "title": "Hacked Title"
    })
    assert res_put.status_code == 404

    # Dave listing drafts should NOT see Acme draft
    beta_list = client.get("/api/drafts", headers=BETA_CREATOR_HEADERS).json()
    beta_ids = [d["id"] for d in beta_list]
    assert acme_draft_id not in beta_ids

def test_tenant_isolation_guidelines():
    # Acme has seeded guidelines; Beta has none yet
    acme_guidelines = client.get("/api/guidelines", headers=CREATOR_HEADERS).json()
    assert len(acme_guidelines) > 0

    beta_guidelines = client.get("/api/guidelines", headers=BETA_CREATOR_HEADERS).json()
    # None of Acme's guideline IDs should appear in Beta's list
    acme_rule_ids = {g["rule_id"] for g in acme_guidelines}
    beta_rule_ids = {g["rule_id"] for g in beta_guidelines}
    assert acme_rule_ids.isdisjoint(beta_rule_ids)

def test_tenant_isolation_audit_logs():
    # Org Beta audit logs should not contain Org Acme events
    acme_logs = client.get("/api/audit-logs", headers=CREATOR_HEADERS).json()
    beta_logs = client.get("/api/audit-logs", headers=BETA_CREATOR_HEADERS).json()

    acme_log_ids = {l["id"] for l in acme_logs}
    beta_log_ids = {l["id"] for l in beta_logs}
    assert acme_log_ids.isdisjoint(beta_log_ids)

# ---------------------------------------------------------------------------
# 5. Guideline Versioning & Audit History Tests
# ---------------------------------------------------------------------------

def test_rule_versioning_and_history():
    rule_id = "RULE-VER-TEST"
    # Admin creates new guideline
    res_create = client.post("/api/guidelines", headers=ADMIN_HEADERS, json={
        "rule_id": rule_id,
        "category": "tone_rule",
        "title": "Original Tone Rule",
        "description": "Original description",
        "source_label": "Voice Guidelines 2026 v1.0",
        "pattern": r"\bcheap\b",
        "severity": "medium",
        "remedy_suggestion": "Use affordable instead."
    })
    assert res_create.status_code == 201
    created = res_create.json()
    assert created["version"] == 1
    assert len(created["version_history"]) == 0

    # Admin updates the rule
    res_update = client.put(f"/api/guidelines/{rule_id}", headers=ADMIN_HEADERS, json={
        "title": "Updated Tone Rule v2",
        "source_label": "Voice Guidelines 2026 v2.0",
        "pattern": r"\b(cheap|dirt cheap)\b",
        "remedy_suggestion": "Use value-priced or accessible instead."
    })
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated["version"] == 2
    assert len(updated["version_history"]) == 1
    assert updated["version_history"][0]["version"] == 1
    assert updated["version_history"][0]["title"] == "Original Tone Rule"
    assert updated["version_history"][0]["source_label"] == "Voice Guidelines 2026 v1.0"

    # Second update
    res_update_2 = client.put(f"/api/guidelines/{rule_id}", headers=ADMIN_HEADERS, json={
        "severity": "high"
    })
    assert res_update_2.status_code == 200
    updated_2 = res_update_2.json()
    assert updated_2["version"] == 3
    assert len(updated_2["version_history"]) == 2

# ---------------------------------------------------------------------------
# 6. Deterministic Rule Checking & Evidence-Linked Findings Tests
# ---------------------------------------------------------------------------

def test_deterministic_findings_using_active_rules_only():
    # Draft with prohibited claims and tone issues
    content = "Our overnight miracle cures acne and offers guaranteed results with dirt cheap pricing."

    draft_res = client.post("/api/drafts", headers=CREATOR_HEADERS, json={
        "title": "Product Pitch",
        "content": content,
        "channel": "social",
        "audience": "general_public",
        "campaign": "AcneCare"
    })
    assert draft_res.status_code == 201
    draft = draft_res.json()
    findings = draft["findings"]

    # Verify findings are evidence-linked and contain actual source labels (no fabricated citations)
    assert len(findings) >= 2
    for f in findings:
        assert f["rule_id"] in ["RULE-PRH-001", "RULE-PRH-002", "RULE-TONE-001", "RULE-VER-TEST"]
        assert len(f["source_label"]) > 0
        assert f["start"] >= 0
        assert f["end"] > f["start"]
        assert f["matched_text"] in content
        assert f["suggestion"] != ""

    # Test that deactivating a rule excludes it from future checks
    client.delete("/api/guidelines/RULE-PRH-002", headers=ADMIN_HEADERS)
    check_res = client.post(f"/api/drafts/{draft['id']}/check", headers=CREATOR_HEADERS)
    assert check_res.status_code == 200
    refreshed_findings = check_res.json()["findings"]
    refreshed_rule_ids = [f["rule_id"] for f in refreshed_findings]
    assert "RULE-PRH-002" not in refreshed_rule_ids

    # Reactivate rule
    client.put("/api/guidelines/RULE-PRH-002", headers=ADMIN_HEADERS, json={"is_active": True})

# ---------------------------------------------------------------------------
# 7. Creator Revision, Reviewer Approval & Audit Decision Workflow
# ---------------------------------------------------------------------------

def test_full_governance_review_workflow():
    # 1. Creator creates draft with violation
    draft_res = client.post("/api/drafts", headers=CREATOR_HEADERS, json={
        "title": "Summer Hydration Drop",
        "content": "This formula cures dryness with 100% guaranteed results.",
        "channel": "email",
        "audience": "existing_customers",
        "campaign": "Summer2026"
    })
    assert draft_res.status_code == 201
    draft_id = draft_res.json()["id"]
    assert draft_res.json()["status"] == "draft"

    # 2. Creator submits for review
    submit_res = client.post(f"/api/drafts/{draft_id}/submit", headers=CREATOR_HEADERS)
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "in_review"

    # 3. Reviewer reviews and requests changes with feedback
    changes_res = client.post(f"/api/drafts/{draft_id}/request-changes", headers=REVIEWER_HEADERS, json={
        "comments": "Please remove 'cures dryness' and '100% guaranteed'. Use approved claim for clinical testing."
    })
    assert changes_res.status_code == 200
    assert changes_res.json()["status"] == "changes_requested"

    # 4. Creator revises draft according to reviewer feedback
    revised_content = "This formula is clinically tested and dermatologist reviewed to deeply hydrate dry skin."
    revise_res = client.put(f"/api/drafts/{draft_id}", headers=CREATOR_HEADERS, json={
        "content": revised_content
    })
    assert revise_res.status_code == 200
    assert revise_res.json()["status"] == "draft"
    # Violations should now be cleared
    assert len(revise_res.json()["findings"]) == 0

    # 5. Creator resubmits
    resubmit_res = client.post(f"/api/drafts/{draft_id}/submit", headers=CREATOR_HEADERS)
    assert resubmit_res.status_code == 200
    assert resubmit_res.json()["status"] == "in_review"

    # 6. Reviewer approves
    approve_res = client.post(f"/api/drafts/{draft_id}/approve", headers=REVIEWER_HEADERS, json={
        "comments": "Compliant with Brand Claim Substantiation Dossier 2026. Approved for release."
    })
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"
    assert "no automatic publication" in approve_res.json()["publication_notice"].lower()

    # 7. Verify persistent audit log for the draft
    audit_res = client.get(f"/api/audit-logs?entity_id={draft_id}", headers=REVIEWER_HEADERS)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    actions = [l["action"] for l in logs]
    assert "created" in actions
    assert "submitted" in actions
    assert "changes_requested" in actions
    assert "updated" in actions
    assert "approved" in actions
