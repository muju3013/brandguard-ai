"""Round 3 approval-gate HTTP integration checks, no real credentials or production data."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.routes import r3_routes, drafts_routes

client = TestClient(app)
CREATOR = {"Authorization": "Bearer demo-token:user_creator_1"}
REVIEWER = {"Authorization": "Bearer demo-token:user_reviewer_1"}
ADMIN = {"Authorization": "Bearer demo-token:user_admin_1"}
BETA = {"Authorization": "Bearer demo-token:user_beta_creator"}
DEMO_EXCEPTION = (
    "TEST ONLY — this is a synthetic QA exercise for checking the "
    "evidence exception audit trail; it is not permission to publish this claim."
)


@pytest.fixture(autouse=True)
def setup_round3(monkeypatch):
    monkeypatch.setattr(settings, "gemini_enabled", False)
    # Keep the Round 3 module pointed to the fresh InMemoryStore from conftest.
    monkeypatch.setattr(r3_routes, "db", drafts_routes.db)
    monkeypatch.setattr(r3_routes, "_collection", lambda name: None)
    r3_routes._memory.clear()
    yield
    r3_routes._memory.clear()


def create_in_review_draft(content="TEST ONLY — 100% guaranteed results"):
    r = client.post("/api/drafts", headers=CREATOR, json={
        "title": "R3 QA - Evidence Approval Test",
        "content": content,
        "channel": "social",
        "audience": "general_public",
        "campaign": "QA Test Only"
    })
    assert r.status_code == 201, r.text
    payload = r.json()
    assert any(f["severity"] == "high" for f in payload["findings"])
    draft_id = payload["id"]
    submitted = client.post(f"/api/drafts/{draft_id}/submit", headers=CREATOR)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "in_review"
    return draft_id


def make_dossier(claim_text):
    result = client.post("/api/r3/dossiers", headers=ADMIN, json={
        "claim_text": claim_text,
        "source_title": "QA-only internal test case",
        "source_url": None,
        "source_excerpt": "Synthetic evidence fixture for verifying software logic only. Not a factual advertising claim.",
        "verification_note": "Test fixture — admin input is not independently fact-checked or publication approval."
    })
    assert result.status_code == 201, result.text
    return result.json()


def test_high_risk_approval_rejects_missing_or_short_exception():
    draft_id = create_in_review_draft()
    url = f"/api/drafts/{draft_id}/approve"
    for reason in (None, "not enough"):
        reply = client.post(url, headers=REVIEWER, json={
            "comments": "Reviewer QA test notes",
            "exception_reason": reason
        })
        assert reply.status_code == 422, reply.text
        current = client.get(f"/api/drafts/{draft_id}", headers=REVIEWER)
        assert current.json()["status"] == "in_review"
    audits = client.get(f"/api/audit-logs?entity_id={draft_id}", headers=REVIEWER).json()
    assert not any(a["action"] == "approved" for a in audits)


def test_reviewer_exception_records_immutable_audit_snapshot_and_no_duplicate_approval():
    draft_id = create_in_review_draft()
    url = f"/api/drafts/{draft_id}/approve"
    reply = client.post(url, headers=REVIEWER, json={
        "comments": "QA verification: exception is explicitly documented",
        "exception_reason": DEMO_EXCEPTION
    })
    assert reply.status_code == 200, reply.text
    assert reply.json()["status"] == "approved"
    audit = client.get(f"/api/audit-logs?entity_id={draft_id}", headers=REVIEWER).json()
    approvals = [entry for entry in audit if entry["action"] == "approved"]
    assert len(approvals) == 1
    evidence = approvals[0]["details"]["evidence_record"]
    assert evidence["method"] == "recorded_reviewer_exception"
    assert evidence["reason"] == DEMO_EXCEPTION
    assert approvals[0]["details"]["high_risk"] is True
    duplicate = client.post(url, headers=REVIEWER, json={
        "comments": "Attempt to approve twice", "exception_reason": DEMO_EXCEPTION
    })
    assert duplicate.status_code == 400


def test_unrelated_dossier_cannot_approve_high_risk_draft_even_if_mentioned():
    draft_id = create_in_review_draft(
        "TEST ONLY — clinically tested daily. We also promise 100% guaranteed results."
    )
    dossier = make_dossier("clinically tested daily")
    reply = client.post(f"/api/drafts/{draft_id}/approve", headers=REVIEWER, json={
        "comments": "Test with irrelevant evidence", "evidence_dossier_id": dossier["id"]
    })
    assert reply.status_code == 422
    assert "does not cover" in reply.json()["detail"]
    assert client.get(f"/api/drafts/{draft_id}", headers=REVIEWER).json()["status"] == "in_review"


def test_matching_dossier_is_versioned_and_audited_on_approval():
    draft_id = create_in_review_draft()
    d = make_dossier("100% guaranteed results")
    updated = client.put(f"/api/r3/dossiers/{d['id']}", headers=ADMIN, json={
        "claim_text": "100% guaranteed results",
        "source_title": "QA-only internal dossier v2",
        "source_url": None,
        "source_excerpt": "QA fixture version two; claims are synthetic and must never be published.",
        "verification_note": "Second synthetic verification record for integration testing."
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 2
    assert len(updated.json()["history"]) == 1
    approved = client.post(f"/api/drafts/{draft_id}/approve", headers=REVIEWER, json={
        "comments": "Test reference dossier verified", "evidence_dossier_id": d["id"]
    })
    assert approved.status_code == 200, approved.text
    audit = client.get(f"/api/audit-logs?entity_id={draft_id}", headers=REVIEWER).json()
    record = next(entry["details"]["evidence_record"] for entry in audit if entry["action"]=="approved")
    assert record["method"] == "approved_dossier"
    assert record["version"] == 2
    assert record["dossier_id"] == d["id"]
    assert record["source_excerpt"] == updated.json()["source_excerpt"]


def test_authorisation_and_cross_tenant_evidence_rejected():
    draft_id = create_in_review_draft()
    cant_create = client.post("/api/r3/dossiers", headers=REVIEWER, json={
        "claim_text": "100% guaranteed results",
        "source_title": "Not authorised",
        "source_excerpt": "This should never be stored by a reviewer role.",
        "verification_note": "This user is not authorised for this action."
    })
    assert cant_create.status_code == 403
    d = make_dossier("100% guaranteed results")
    cross_tenant = client.get("/api/r3/dossiers", headers=BETA)
    assert cross_tenant.status_code == 200
    assert all(item["id"] != d["id"] for item in cross_tenant.json())
    creator_approve = client.post(f"/api/drafts/{draft_id}/approve", headers=CREATOR,
        json={"comments":"Attempt self approval","evidence_dossier_id":d["id"]})
    assert creator_approve.status_code == 403
