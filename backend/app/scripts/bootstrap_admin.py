"""
BrandGuard AI - Admin Bootstrap CLI Utility
=============================================================================
Safely bootstraps or promotes a user to the Admin role in Firebase Auth
and Google Cloud Firestore without exposing secrets.

Usage:
  python -m app.scripts.bootstrap_admin --email smuju045@gmail.com
  python -m app.scripts.bootstrap_admin --email judge.admin@inkloom-brandguard.com --role admin
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.config import settings
from app.db import db, now_iso
from app.firebase_setup import get_firebase_app

def bootstrap_admin(
    email: str,
    role: str = "admin",
    org_id: str = "org_inkloom_judge",
    org_name: str = "Inkloom Evaluation Brands",
    display_name: str = "Organization Admin"
):
    print("=" * 72)
    print(" BrandGuard AI - Admin Bootstrap Utility")
    print("=" * 72)
    print(f"Target Email       : {email}")
    print(f"Assigned Role      : {role.upper()}")
    print(f"Organisation ID    : {org_id}")
    print(f"Firestore Enabled  : {settings.use_firestore}")
    print("-" * 72)

    fb_app = get_firebase_app()
    user_uid = f"user_{email.split('@')[0]}"

    if fb_app:
        try:
            from firebase_admin import auth as fb_auth
            try:
                user_record = fb_auth.get_user_by_email(email, app=fb_app)
                user_uid = user_record.uid
                print(f"[+] Found existing Firebase Auth user. UID: {user_uid}")
            except Exception:
                # User doesn't exist yet in Auth; we can create them or record placeholder
                print(f"[*] Firebase user {email} does not exist yet. It will be mapped when they register.")
        except Exception as e:
            print(f"[!] Firebase Auth lookup note: {e}")

    # Ensure organisation exists in DB
    existing_org = db.get_organization(org_id)
    if not existing_org:
        if hasattr(db, "orgs_col"):
            db.orgs_col.document(org_id).set({
                "id": org_id,
                "name": org_name,
                "created_at": now_iso(),
                "created_by": "bootstrap"
            })
        else:
            db.create_organization(org_name, "bootstrap")
        print(f"[+] Created Organization: {org_name} ({org_id})")

    # Set membership in Firestore
    membership = db.set_membership(
        user_id=user_uid,
        email=email,
        org_id=org_id,
        role=role
    )
    print(f"[SUCCESS] Bootstrapped {email} with role '{role}' in organisation '{membership.org_name}' ({org_id}).")
    print("=" * 72)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap Admin for BrandGuard AI")
    parser.add_argument("--email", required=True, help="User email to promote/bootstrap as admin")
    parser.add_argument("--role", default="admin", choices=["admin", "reviewer", "creator"], help="Role to assign")
    parser.add_argument("--org-id", default="org_inkloom_judge", help="Organisation ID")
    parser.add_argument("--org-name", default="Inkloom Evaluation Brands", help="Organisation Name")
    args = parser.parse_args()

    bootstrap_admin(
        email=args.email,
        role=args.role,
        org_id=args.org_id,
        org_name=args.org_name
    )
