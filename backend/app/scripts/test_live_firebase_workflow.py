"""
BrandGuard AI - Live Firebase End-to-End Workflow Integration Test
=============================================================================
Tests live authentication with Google Firebase Auth, Cloud Firestore persistence,
multi-tenant RBAC, deterministic & Gemini AI checking, reviewer approval,
and tamper-evident audit logging.
"""

import sys
import os
import json
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.config import settings
from app.db import db

# Firebase Web API Key for Auth REST API
FIREBASE_API_KEY = "AIzaSyBhwzQXepSIDz_R27ytt97tKyRTuUSieV8"
FIREBASE_AUTH_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_SIGNUP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"

def sign_in_firebase(email, password):
    """Sign in to Firebase via Google Identity Toolkit REST API."""
    payload = json.dumps({
        "email": email,
        "password": password,
        "returnSecureToken": True
    }).encode("utf-8")
    req = urllib.request.Request(FIREBASE_AUTH_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["idToken"], data["localId"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise RuntimeError(f"Firebase sign-in failed for {email}: {err_body}")

def create_firebase_user(email, password):
    """Create a new Firebase Auth user via REST API."""
    payload = json.dumps({
        "email": email,
        "password": password,
        "returnSecureToken": True
    }).encode("utf-8")
    req = urllib.request.Request(FIREBASE_SIGNUP_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["idToken"], data["localId"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise RuntimeError(f"Firebase user creation failed for {email}: {err_body}")

def run_live_e2e_test():
    print("=" * 76)
    print(" BrandGuard AI: Live Firebase & Firestore Full Lifecycle Verification")
    print("=" * 76)
    print(f"Project ID        : {settings.firebase_project_id}")
    print(f"Environment       : {settings.environment}")
    print(f"Using Firestore   : {settings.use_firestore}")
    print(f"Gemini Configured : {bool(settings.gemini_api_key and not settings.gemini_api_key.startswith('your_'))}")
    print("-" * 76)

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # -------------------------------------------------------------------------
    # STEP 1: Verify Live Firebase Auth for Judge Creator
    # -------------------------------------------------------------------------
    creator_email = "judge.creator@inkloom-brandguard.com"
    creator_pass = "BrandGuard2026!Judge"
    print(f"\n[Step 1] Authenticating Creator ({creator_email}) via Live Firebase Auth REST API...")
    creator_token, creator_uid = sign_in_firebase(creator_email, creator_pass)
    print(f"  [OK] Successfully retrieved live Google-issued ID token (UID: {creator_uid})")

    # Verify backend /api/auth/me resolves against Firestore
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {creator_token}"})
    assert resp.status_code == 200, f"Auth verification failed: {resp.text}"
    user_data = resp.json()
    print(f"  [OK] Backend resolved caller identity: {user_data['email']}, Role: {user_data['role']}, Org ID: {user_data['org_id']}, Org Name: {user_data['org_name']}")
    assert user_data["role"] == "creator", f"Expected role 'creator', got {user_data['role']}"
    assert user_data["org_id"] == "org_inkloom_judge", f"Expected org_inkloom_judge, got {user_data['org_id']}"
    assert user_data["org_name"] == "Inkloom Evaluation Brands"

    # -------------------------------------------------------------------------
    # STEP 2: Authenticate Reviewer & Admin Accounts
    # -------------------------------------------------------------------------
    reviewer_email = "judge.reviewer@inkloom-brandguard.com"
    reviewer_pass = "BrandGuard2026!Judge"
    print(f"\n[Step 2] Authenticating Reviewer ({reviewer_email}) via Live Firebase Auth...")
    reviewer_token, reviewer_uid = sign_in_firebase(reviewer_email, reviewer_pass)
    print(f"  [OK] Reviewer token retrieved (UID: {reviewer_uid})")

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert resp.status_code == 200
    rev_data = resp.json()
    assert rev_data["role"] == "reviewer"
    print(f"  [OK] Reviewer verified with role '{rev_data['role']}' in '{rev_data['org_name']}'")

    admin_email = "judge.admin@inkloom-brandguard.com"
    admin_pass = "BrandGuard2026!Judge"
    print(f"\n[Step 2b] Authenticating Admin ({admin_email}) via Live Firebase Auth...")
    admin_token, admin_uid = sign_in_firebase(admin_email, admin_pass)
    print(f"  [OK] Admin token retrieved (UID: {admin_uid})")

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    admin_data = resp.json()
    assert admin_data["role"] == "admin"
    print(f"  [OK] Admin verified with role '{admin_data['role']}' in '{admin_data['org_name']}'")

    # -------------------------------------------------------------------------
    # STEP 3: Test New User Account Creation & Organisation Membership
    # -------------------------------------------------------------------------
    test_user_email = f"test.creator.{int(time.time())}@inkloom-brandguard.com"
    test_user_pass = "BrandGuard2026!NewUser"
    print(f"\n[Step 3] Testing dynamic user creation in Firebase Auth ({test_user_email})...")
    new_user_token, new_user_uid = create_firebase_user(test_user_email, test_user_pass)
    print(f"  [OK] Created new live Firebase user (UID: {new_user_uid})")

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_user_token}"})
    assert resp.status_code == 200
    new_member_data = resp.json()
    assert new_member_data["role"] == "creator"
    print(f"  [OK] New user onboarded in Firestore with role '{new_member_data['role']}' in '{new_member_data['org_name']}'")

    # Verify admin can list members from Firestore
    resp = client.get("/api/auth/members", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    members = resp.json()
    print(f"  [OK] Admin listed {len(members)} team members from Firestore")
    assert any(m["email"] == test_user_email for m in members)

    # -------------------------------------------------------------------------
    # STEP 4: Verify Dashboard & Guidelines Data from Firestore
    # -------------------------------------------------------------------------
    print("\n[Step 4] Verifying guideline rules loaded from Firestore...")
    resp = client.get("/api/guidelines", headers={"Authorization": f"Bearer {creator_token}"})
    assert resp.status_code == 200
    guidelines = resp.json()
    rule_ids = [r["rule_id"] for r in guidelines]
    print(f"  [OK] Loaded {len(guidelines)} active guidelines: {rule_ids}")
    assert "RULE-PRH-001" in rule_ids
    assert "RULE-PRH-002" in rule_ids
    assert "RULE-CLM-001" in rule_ids
    assert "RULE-TONE-001" in rule_ids

    # -------------------------------------------------------------------------
    # STEP 5: Creator Creates a Marketing Draft in Firestore
    # -------------------------------------------------------------------------
    print("\n[Step 5] Creator creating marketing draft in Firestore...")
    draft_payload = {
        "title": "Summer Radiance Launch Campaign",
        "channel": "instagram",
        "audience": "skincare enthusiasts",
        "campaign": "Summer 2026",
        "content": (
            "Experience the Summer Radiance Serum! It cures skin inflammation and provides 100% guaranteed results overnight. "
            "Our clinically tested formula is dirt cheap and dermatologically backed."
        )
    }
    resp = client.post("/api/drafts", json=draft_payload, headers={"Authorization": f"Bearer {creator_token}"})
    assert resp.status_code == 201, f"Failed to create draft: {resp.text}"
    created_draft = resp.json()
    draft_id = created_draft["id"]
    print(f"  [OK] Draft created with ID: {draft_id}, status: {created_draft['status']}")

    # -------------------------------------------------------------------------
    # STEP 6: Run Real Pre-Check (Deterministic + Gemini Review)
    # -------------------------------------------------------------------------
    print(f"\n[Step 6] Running compliance check (Deterministic + Gemini AI) on draft {draft_id}...")
    resp = client.post(f"/api/drafts/{draft_id}/check", headers={"Authorization": f"Bearer {creator_token}"})
    assert resp.status_code == 200, f"Check failed: {resp.text}"
    check_result = resp.json()
    print(f"  [OK] Check completed. Outcome: {check_result['outcome']}")
    print(f"  [OK] Total Findings: {len(check_result.get('findings', []))}")
    
    # Detail the findings
    for idx, f in enumerate(check_result.get("findings", []), 1):
        rule_info = f.get("rule_id", "Unknown")
        rule_version = f.get("rule_version", "N/A")
        matched = f.get("matched_text", "")
        sev = f.get("severity", "medium")
        print(f"      Finding #{idx}: [{sev.upper()}] Rule: {rule_info} v{rule_version} | Match: '{matched}'")
    
    ai_review = check_result.get("ai_review")
    if ai_review:
        print(f"  [OK] Gemini AI Review returned: Status='{ai_review.get('status')}', Model='{ai_review.get('model_used')}'")
        if ai_review.get("summary"):
            print(f"      AI Summary: {ai_review['summary']}")
        if ai_review.get("findings"):
            print(f"      AI Grounded Findings: {len(ai_review['findings'])}")

    # -------------------------------------------------------------------------
    # STEP 7: Creator Submits Draft for Review
    # -------------------------------------------------------------------------
    print(f"\n[Step 7] Creator submitting draft {draft_id} for reviewer approval...")
    resp = client.post(f"/api/drafts/{draft_id}/submit", headers={"Authorization": f"Bearer {creator_token}"})
    assert resp.status_code == 200, f"Submission failed: {resp.text}"
    submitted_draft = resp.json()
    assert submitted_draft["status"] == "in_review"
    print(f"  [OK] Draft submitted. New status: {submitted_draft['status']}")

    # -------------------------------------------------------------------------
    # STEP 8: Reviewer Approves Draft
    # -------------------------------------------------------------------------
    print(f"\n[Step 8] Reviewer approving draft {draft_id}...")
    approval_payload = {
        "decision": "approved",
        "comments": "Reviewed clinical claim citations. Permitted subject to social copy disclaimer update."
    }
    resp = client.post(
        f"/api/drafts/{draft_id}/approve",
        json=approval_payload,
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert resp.status_code == 200, f"Approval failed: {resp.text}"
    approved_res = resp.json()
    assert approved_res["status"] == "approved"
    print(f"  [OK] Draft approved. Final status: {approved_res['status']}")
    print(f"      Reviewer Notes: {approved_res.get('notes')}")

    # -------------------------------------------------------------------------
    # STEP 9: Verify Tamper-Resistant Audit Trail in Firestore
    # -------------------------------------------------------------------------
    print(f"\n[Step 9] Verifying audit trail in Cloud Firestore...")
    resp = client.get(f"/api/audit-logs?entity_id={draft_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    audit_logs = resp.json()
    print(f"  [OK] Retrieved {len(audit_logs)} audit records for draft {draft_id}:")
    for log in audit_logs:
        print(f"      - Action: {log['action']} | Actor: {log['actor_id']} | Time: {log['timestamp']}")
    
    actions = [l["action"] for l in audit_logs]
    assert "created" in actions
    assert "checked" in actions
    assert "submitted" in actions
    assert "approved" in actions

    # Verify Firestore persistence directly
    db_draft = db.get_draft(draft_id)
    assert db_draft is not None
    assert db_draft.status == "approved"
    print(f"\n[Step 10] Direct Firestore record verified: ID={db_draft.id}, Status={db_draft.status}")

    print("\n" + "=" * 76)
    print(" ALL LIVE FIREBASE & FIRESTORE WORKFLOW STEPS VERIFIED SUCCESSFULLY! ")
    print("=" * 76)

if __name__ == "__main__":
    run_live_e2e_test()
