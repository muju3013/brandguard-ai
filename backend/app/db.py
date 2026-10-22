import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from app.models import (
    Organization, Membership, GuidelineRule, GuidelineVersionRecord,
    Draft, AuditLog, Finding
)
from app.config import settings

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class InMemoryStore:
    def __init__(self):
        self.organizations: Dict[str, Organization] = {}
        self.memberships: Dict[str, Membership] = {}  # key: f"{org_id}:{user_id}" or user_id
        self.user_to_membership: Dict[str, Membership] = {} # user_id -> active membership
        self.guidelines: Dict[str, GuidelineRule] = {} # guideline.id -> GuidelineRule
        self.drafts: Dict[str, Draft] = {} # draft.id -> Draft
        self.audit_logs: List[AuditLog] = []
        self._seed_initial_data()

    def _seed_initial_data(self):
        # Seed Org 1: Acme Brands
        acme = Organization(
            id="org_acme",
            name="Acme Global Brands",
            created_at=now_iso(),
            created_by="system"
        )
        self.organizations[acme.id] = acme

        # Seed Acme Members
        m1 = Membership(
            user_id="user_admin_1",
            email="sarah.admin@acme.com",
            org_id=acme.id,
            org_name=acme.name,
            role="admin"
        )
        m2 = Membership(
            user_id="user_reviewer_1",
            email="alex.reviewer@acme.com",
            org_id=acme.id,
            org_name=acme.name,
            role="reviewer"
        )
        m3 = Membership(
            user_id="user_creator_1",
            email="jordan.creator@acme.com",
            org_id=acme.id,
            org_name=acme.name,
            role="creator"
        )
        for m in (m1, m2, m3):
            self.memberships[f"{m.org_id}:{m.user_id}"] = m
            self.user_to_membership[m.user_id] = m
            self.user_to_membership[m.email] = m

        # Seed Org 2: Beta Health (For tenant isolation verification)
        beta = Organization(
            id="org_beta",
            name="Beta Health & Wellness",
            created_at=now_iso(),
            created_by="system"
        )
        self.organizations[beta.id] = beta
        mb1 = Membership(
            user_id="user_beta_admin",
            email="carol.admin@betahealth.com",
            org_id=beta.id,
            org_name=beta.name,
            role="admin"
        )
        mb2 = Membership(
            user_id="user_beta_creator",
            email="dave.creator@betahealth.com",
            org_id=beta.id,
            org_name=beta.name,
            role="creator"
        )
        for m in (mb1, mb2):
            self.memberships[f"{m.org_id}:{m.user_id}"] = m
            self.user_to_membership[m.user_id] = m
            self.user_to_membership[m.email] = m

        # Seed Acme Guidelines
        rules = [
            GuidelineRule(
                id=str(uuid.uuid4()),
                rule_id="RULE-PRH-001",
                org_id=acme.id,
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
                created_by="sarah.admin@acme.com",
                updated_at=now_iso(),
                updated_by="sarah.admin@acme.com"
            ),
            GuidelineRule(
                id=str(uuid.uuid4()),
                rule_id="RULE-PRH-002",
                org_id=acme.id,
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
                created_by="sarah.admin@acme.com",
                updated_at=now_iso(),
                updated_by="sarah.admin@acme.com"
            ),
            GuidelineRule(
                id=str(uuid.uuid4()),
                rule_id="RULE-CLM-001",
                org_id=acme.id,
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
                created_by="sarah.admin@acme.com",
                updated_at=now_iso(),
                updated_by="sarah.admin@acme.com"
            ),
            GuidelineRule(
                id=str(uuid.uuid4()),
                rule_id="RULE-TONE-001",
                org_id=acme.id,
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
                created_by="sarah.admin@acme.com",
                updated_at=now_iso(),
                updated_by="sarah.admin@acme.com"
            )
        ]
        for r in rules:
            self.guidelines[r.id] = r

        # Seed sample draft for Acme
        sample_draft = Draft(
            id="draft_sample_1",
            org_id=acme.id,
            title="Q3 Radiance Serum Social Campaign",
            content="Introducing our Radiance Serum! Clinically tested to hydrate skin and guaranteed results for your glow.",
            channel="social",
            audience="general_public",
            campaign="Q3 Product Launch",
            status="draft",
            creator_id=m3.user_id,
            creator_email=m3.email,
            findings=[],
            review_notes=None,
            reviewed_by=None,
            reviewed_by_email=None,
            reviewed_at=None,
            created_at=now_iso(),
            updated_at=now_iso()
        )
        self.drafts[sample_draft.id] = sample_draft

        # Seed audit log for initial setup
        self.audit_logs.append(AuditLog(
            id=str(uuid.uuid4()),
            org_id=acme.id,
            entity_type="draft",
            entity_id=sample_draft.id,
            action="created",
            actor_id=m3.user_id,
            actor_email=m3.email,
            actor_role=m3.role,
            details={"title": sample_draft.title},
            timestamp=now_iso()
        ))

    # Organization & Membership methods
    def get_organization(self, org_id: str) -> Optional[Organization]:
        return self.organizations.get(org_id)

    def create_organization(self, name: str, creator_id: str) -> Organization:
        org = Organization(
            id=f"org_{uuid.uuid4().hex[:8]}",
            name=name,
            created_at=now_iso(),
            created_by=creator_id
        )
        self.organizations[org.id] = org
        return org

    def get_membership(self, user_id_or_email: str) -> Optional[Membership]:
        return self.user_to_membership.get(user_id_or_email)

    def set_membership(self, user_id: str, email: str, org_id: str, role: str) -> Membership:
        org = self.get_organization(org_id)
        org_name = org.name if org else "Default Org"
        membership = Membership(
            user_id=user_id,
            email=email,
            org_id=org_id,
            org_name=org_name,
            role=role # type: ignore
        )
        self.memberships[f"{org_id}:{user_id}"] = membership
        self.user_to_membership[user_id] = membership
        self.user_to_membership[email] = membership
        return membership

    def list_org_memberships(self, org_id: str) -> List[Membership]:
        return [m for m in self.memberships.values() if m.org_id == org_id]

    # Guidelines methods
    def list_guidelines(self, org_id: str, active_only: bool = False) -> List[GuidelineRule]:
        rules = [r for r in self.guidelines.values() if r.org_id == org_id]
        if active_only:
            rules = [r for r in rules if r.is_active]
        return sorted(rules, key=lambda x: x.rule_id)

    def get_guideline(self, guideline_id: str) -> Optional[GuidelineRule]:
        return self.guidelines.get(guideline_id)

    def get_guideline_by_rule_id(self, org_id: str, rule_id: str) -> Optional[GuidelineRule]:
        for r in self.guidelines.values():
            if r.org_id == org_id and r.rule_id.lower() == rule_id.lower():
                return r
        return None

    def create_guideline(self, rule: GuidelineRule) -> GuidelineRule:
        self.guidelines[rule.id] = rule
        return rule

    def update_guideline(self, rule: GuidelineRule) -> GuidelineRule:
        self.guidelines[rule.id] = rule
        return rule

    # Drafts methods
    def list_drafts(self, org_id: str, creator_id: Optional[str] = None) -> List[Draft]:
        drafts = [d for d in self.drafts.values() if d.org_id == org_id]
        if creator_id:
            drafts = [d for d in drafts if d.creator_id == creator_id]
        return sorted(drafts, key=lambda x: x.created_at, reverse=True)

    def get_draft(self, draft_id: str) -> Optional[Draft]:
        return self.drafts.get(draft_id)

    def save_draft(self, draft: Draft) -> Draft:
        self.drafts[draft.id] = draft
        return draft

    def record_audit(self, log: AuditLog):
        self.audit_logs.append(log)

    def list_audit_logs(self, org_id: str, entity_id: Optional[str] = None) -> List[AuditLog]:
        logs = [log for log in self.audit_logs if log.org_id == org_id]
        if entity_id:
            logs = [log for log in logs if log.entity_id == entity_id]
        return sorted(logs, key=lambda x: x.timestamp, reverse=True)


class FirestoreStore:
    """
    Production-grade Google Cloud Firestore adapter.
    Enforces cloud persistence, tenant isolation, and audit trail integrity.
    """
    def __init__(self, client):
        self.client = client
        self.orgs_col = self.client.collection("organizations")
        self.members_col = self.client.collection("memberships")
        self.guidelines_col = self.client.collection("guidelines")
        self.drafts_col = self.client.collection("drafts")
        self.audit_col = self.client.collection("audit_logs")

    # Organization & Membership methods
    def get_organization(self, org_id: str) -> Optional[Organization]:
        doc = self.orgs_col.document(org_id).get()
        return Organization(**doc.to_dict()) if doc.exists else None

    def create_organization(self, name: str, creator_id: str) -> Organization:
        org_id = f"org_{uuid.uuid4().hex[:8]}"
        org = Organization(
            id=org_id,
            name=name,
            created_at=now_iso(),
            created_by=creator_id
        )
        self.orgs_col.document(org_id).set(org.model_dump())
        return org

    def get_membership(self, user_id_or_email: str) -> Optional[Membership]:
        # Search by user_id
        docs = list(self.members_col.where("user_id", "==", user_id_or_email).limit(1).stream())
        if docs:
            return Membership(**docs[0].to_dict())
        # Search by email
        docs = list(self.members_col.where("email", "==", user_id_or_email).limit(1).stream())
        if docs:
            return Membership(**docs[0].to_dict())
        return None

    def set_membership(self, user_id: str, email: str, org_id: str, role: str) -> Membership:
        org = self.get_organization(org_id)
        org_name = org.name if org else "Default Org"
        membership = Membership(
            user_id=user_id,
            email=email,
            org_id=org_id,
            org_name=org_name,
            role=role  # type: ignore
        )
        doc_id = f"{org_id}_{user_id}"
        self.members_col.document(doc_id).set(membership.model_dump())
        return membership

    def list_org_memberships(self, org_id: str) -> List[Membership]:
        docs = self.members_col.where("org_id", "==", org_id).stream()
        return [Membership(**d.to_dict()) for d in docs]

    # Guidelines methods
    def list_guidelines(self, org_id: str, active_only: bool = False) -> List[GuidelineRule]:
        q = self.guidelines_col.where("org_id", "==", org_id)
        if active_only:
            q = q.where("is_active", "==", True)
        rules = [GuidelineRule(**d.to_dict()) for d in q.stream()]
        return sorted(rules, key=lambda x: x.rule_id)

    def get_guideline(self, guideline_id: str) -> Optional[GuidelineRule]:
        doc = self.guidelines_col.document(guideline_id).get()
        return GuidelineRule(**doc.to_dict()) if doc.exists else None

    def get_guideline_by_rule_id(self, org_id: str, rule_id: str) -> Optional[GuidelineRule]:
        docs = list(self.guidelines_col.where("org_id", "==", org_id).where("rule_id", "==", rule_id).limit(1).stream())
        if docs:
            return GuidelineRule(**docs[0].to_dict())
        return None

    def create_guideline(self, rule: GuidelineRule) -> GuidelineRule:
        self.guidelines_col.document(rule.id).set(rule.model_dump())
        return rule

    def update_guideline(self, rule: GuidelineRule) -> GuidelineRule:
        self.guidelines_col.document(rule.id).set(rule.model_dump())
        return rule

    # Drafts methods
    def list_drafts(self, org_id: str, creator_id: Optional[str] = None) -> List[Draft]:
        q = self.drafts_col.where("org_id", "==", org_id)
        if creator_id:
            q = q.where("creator_id", "==", creator_id)
        drafts = [Draft(**d.to_dict()) for d in q.stream()]
        return sorted(drafts, key=lambda x: x.created_at, reverse=True)

    def get_draft(self, draft_id: str) -> Optional[Draft]:
        doc = self.drafts_col.document(draft_id).get()
        return Draft(**doc.to_dict()) if doc.exists else None

    def save_draft(self, draft: Draft) -> Draft:
        self.drafts_col.document(draft.id).set(draft.model_dump())
        return draft

    # Audit Logs methods
    def record_audit(self, log: AuditLog):
        self.audit_col.document(log.id).set(log.model_dump())

    def list_audit_logs(self, org_id: str, entity_id: Optional[str] = None) -> List[AuditLog]:
        q = self.audit_col.where("org_id", "==", org_id)
        if entity_id:
            q = q.where("entity_id", "==", entity_id)
        logs = [AuditLog(**d.to_dict()) for d in q.stream()]
        return sorted(logs, key=lambda x: x.timestamp, reverse=True)


def initialize_db():
    import logging
    logger = logging.getLogger("brandguard.db")
    if settings.use_firestore:
        try:
            from firebase_admin import firestore
            fs_client = firestore.client()
            logger.info("Connected to live Google Cloud Firestore.")
            return FirestoreStore(fs_client)
        except Exception as e:
            if settings.is_production:
                logger.critical(f"FATAL: Production Firestore initialization failed: {e}. Insecure fallback disabled.")
                raise RuntimeError(f"Production Firestore initialization failed: {e}. Insecure database fallback is strictly disabled in production.")
            logger.warning(f"Firestore unavailable ({e}). Using InMemoryStore for development.")
            return InMemoryStore()
    else:
        if settings.is_production:
            logger.warning("Production server running with InMemoryStore (USE_FIRESTORE is false). Set USE_FIRESTORE=true and configure Firebase for cloud persistence.")
        return InMemoryStore()

# Singleton DB instance
db = initialize_db()

