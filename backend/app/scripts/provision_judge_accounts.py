"""
BrandGuard AI - Safe Judge & Demo Account Provisioning Script
=============================================================================
This script safely provisions judge evaluation accounts for the Inkloom AI
Round 2 Hackathon without exposing production secrets or API keys.

It provisions:
1. Workspace Organisation (e.g. Acme Global Brands)
2. Admin Judge Account (can edit rules, manage team, view audit trails)
3. Reviewer Judge Account (can approve drafts, request changes with notes)
4. Creator Judge Account (can draft marketing assets, run deterministic + Gemini AI checks, submit for review)
5. Standard Compliance Guidelines (Prohibited Claims, Approved Facts, Tone Guidelines)

Usage:
  python -m app.scripts.provision_judge_accounts
  python -m app.scripts.provision_judge_accounts --org-id org_inkloom_demo --password "JudgeAccess2026!"
"""

import sys
import os
import argparse
import uuid
from datetime import datetime, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.config import settings
from app.db import db, now_iso
from app.models import Organization, Membership, GuidelineRule

def provision_judge_accounts(
    org_id: str = "org_inkloom_judge",
    org_name: str = "Inkloom Evaluation Brands",
    password: str = "BrandGuard2026!Judge",
    admin_email: str = "judge.admin@inkloom-brandguard.com",
    reviewer_email: str = "judge.reviewer@inkloom-brandguard.com",
    creator_email: str = "judge.creator@inkloom-brandguard.com"
):
    print("=" * 72)
    print(" BrandGuard AI - Safe Judge Account Provisioning")
    print("=" * 72)
    print(f"Target Environment : {settings.environment.upper()}")
    print(f"Firestore Enabled  : {settings.use_firestore}")
    print(f"Organisation ID    : {org_id}")
    print(f"Organisation Name  : {org_name}")
    print("-" * 72)

    # 1. Check or initialize Firebase Auth user records if Firebase Admin is available
    from app.firebase_setup import get_firebase_app
    fb_app = get_firebase_app()
    firebase_auth_available = fb_app is not None
    if firebase_auth_available:
        from firebase_admin import auth as fb_auth
        print("[+] Firebase Admin SDK is connected with live credentials.")
    else:
        print("[!] Running in offline/demo mode (Firebase Admin SDK not connected).")

    roles = [
        ("judge_admin_uid", admin_email, "admin", "Judge Sarah (Admin)"),
        ("judge_reviewer_uid", reviewer_email, "reviewer", "Judge Alex (Reviewer)"),
        ("judge_creator_uid", creator_email, "creator", "Judge Jordan (Creator)")
    ]

    for uid, email, role, display_name in roles:
        actual_uid = uid
        if firebase_auth_available:
            try:
                # Try getting existing user
                user_record = fb_auth.get_user_by_email(email, app=fb_app)
                actual_uid = user_record.uid
                print(f"  [OK] Existing Firebase Auth user found: {email} (UID: {actual_uid})")
            except Exception:
                try:
                    # Create new Firebase Auth user
                    user_record = fb_auth.create_user(
                        email=email,
                        password=password,
                        display_name=display_name,
                        app=fb_app
                    )
                    actual_uid = user_record.uid
                    print(f"  [+] Created Firebase Auth user: {email} (UID: {actual_uid})")
                except Exception as e:
                    print(f"  [!] Note: Could not create Firebase Auth user for {email}: {e}")

        # 2. Ensure Organisation exists in DB
        existing_org = db.get_organization(org_id)
        if not existing_org:
            if hasattr(db, "orgs_col"):
                db.orgs_col.document(org_id).set({
                    "id": org_id,
                    "name": org_name,
                    "created_at": now_iso(),
                    "created_by": "system"
                })
            else:
                db.create_organization(org_name, "system")
            print(f"  [+] Created Organization record: {org_name} ({org_id})")

        # Store membership in DB
        db.set_membership(
            user_id=actual_uid,
            email=email,
            org_id=org_id,
            role=role
        )
        print(f"  [OK] Provisioned DB Membership: {email} -> Role: {role.upper()}")

    # 3. Seed baseline guidelines for the judge organization
    guideline_templates = [
        GuidelineRule(
            id=str(uuid.uuid4()),
            rule_id="RULE-PRH-001",
            org_id=org_id,
            category="prohibited_claim",
            title="Prohibit Unsubstantiated Cure or Medical Claims",
            description="Any claim suggesting a product cures, treats, or eliminates medical conditions requires verified regulatory documentation.",
            source_label="FDA & FTC Health Substantiation Policy §3.2",
            pattern=r"\b(cure[sd]?|miracle cure|eliminates? acne|permanently fixes?)\b",
            severity="high",
            remedy_suggestion="Remove curative medical claims and state validated cosmetic or supportive benefits only.",
            is_active=True,
            version=1,
            version_history=[],
            created_at=now_iso(),
            created_by=admin_email,
            updated_at=now_iso(),
            updated_by=admin_email
        ),
        GuidelineRule(
            id=str(uuid.uuid4()),
            rule_id="RULE-PRH-002",
            org_id=org_id,
            category="prohibited_claim",
            title="Prohibit Absolute Guarantees and Overnight Promises",
            description="Absolute guarantees of 100% results or instantaneous overnight efficacy are deceptive under fair advertising standards.",
            source_label="Consumer Protection Standards §8.1",
            pattern=r"\b(100% guaranteed|guaranteed results|overnight miracle|instant transformation)\b",
            severity="high",
            remedy_suggestion="Avoid absolute promises; provide realistic customer experience timelines.",
            is_active=True,
            version=1,
            version_history=[],
            created_at=now_iso(),
            created_by=admin_email,
            updated_at=now_iso(),
            updated_by=admin_email
        ),
        GuidelineRule(
            id=str(uuid.uuid4()),
            rule_id="RULE-CLM-001",
            org_id=org_id,
            category="approved_claim",
            title="Approved Clinical Study Claim",
            description="References to clinical testing must adhere to dermatology trial results dossier.",
            source_label="Brand Claim Substantiation Dossier 2026 - Section C",
            pattern=r"\b(clinically tested|dermatologist reviewed|hypoallergenic)\b",
            severity="low",
            remedy_suggestion="Use verified approved phrasing: 'Clinically tested and dermatologist reviewed for sensitive skin.'",
            is_active=True,
            version=1,
            version_history=[],
            created_at=now_iso(),
            created_by=admin_email,
            updated_at=now_iso(),
            updated_by=admin_email
        ),
        GuidelineRule(
            id=str(uuid.uuid4()),
            rule_id="RULE-TONE-001",
            org_id=org_id,
            category="tone_rule",
            title="Prohibit Hyperbolic Hype & Clickbait Slang",
            description="Brand voice communicates clinical integrity and trusted elegance. Avoid sensational slang and cheapening phrases.",
            source_label="Brand Voice & Tone Guidelines 2026 §1.4",
            pattern=r"\b(blow your mind|insane discount|dirt cheap|insanely good|unbelievable shock)\b",
            severity="medium",
            remedy_suggestion="Replace exaggerated hype with grounded, professional, and confident statements.",
            is_active=True,
            version=1,
            version_history=[],
            created_at=now_iso(),
            created_by=admin_email,
            updated_at=now_iso(),
            updated_by=admin_email
        )
    ]

    for rule in guideline_templates:
        existing = db.get_guideline_by_rule_id(org_id, rule.rule_id)
        if not existing:
            db.create_guideline(rule)
            print(f"  [+] Seeded Rule: {rule.rule_id} ({rule.title})")
        else:
            print(f"  [OK] Rule {rule.rule_id} already exists.")

    print("\n" + "=" * 72)
    print(" PROVISIONING COMPLETE - JUDGE CREDENTIALS SUMMARY")
    print("=" * 72)
    print(f"Organisation : {org_name} (ID: {org_id})")
    print(f"Password     : {password}")
    print()
    print("  1. ADMIN ACCOUNT")
    print(f"     Email : {admin_email}")
    print("     Role  : Admin (manage rules, review audit logs, team members)")
    print()
    print("  2. REVIEWER ACCOUNT")
    print(f"     Email : {reviewer_email}")
    print("     Role  : Reviewer (approve/request changes on drafts)")
    print()
    print("  3. CREATOR ACCOUNT")
    print(f"     Email : {creator_email}")
    print("     Role  : Creator (draft copy, run pre-check & Gemini, submit)")
    print("=" * 72)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision BrandGuard AI Judge Accounts")
    parser.add_argument("--org-id", default="org_inkloom_judge", help="Organisation ID")
    parser.add_argument("--org-name", default="Inkloom Evaluation Brands", help="Organisation Name")
    parser.add_argument("--password", default="BrandGuard2026!Judge", help="Temporary password for judge accounts")
    parser.add_argument("--admin-email", default="judge.admin@inkloom-brandguard.com", help="Admin email")
    parser.add_argument("--reviewer-email", default="judge.reviewer@inkloom-brandguard.com", help="Reviewer email")
    parser.add_argument("--creator-email", default="judge.creator@inkloom-brandguard.com", help="Creator email")
    args = parser.parse_args()

    provision_judge_accounts(
        org_id=args.org_id,
        org_name=args.org_name,
        password=args.password,
        admin_email=args.admin_email,
        reviewer_email=args.reviewer_email,
        creator_email=args.creator_email
    )
