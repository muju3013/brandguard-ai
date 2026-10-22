from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

RoleType = Literal["admin", "creator", "reviewer"]
CategoryType = Literal["approved_claim", "prohibited_claim", "tone_rule"]
SeverityType = Literal["high", "medium", "low"]
DraftStatusType = Literal["draft", "in_review", "approved", "changes_requested"]

class UserProfile(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None

class Membership(BaseModel):
    user_id: str
    email: str
    org_id: str
    org_name: str
    role: RoleType

class AuthenticatedUser(BaseModel):
    user_id: str
    email: str
    org_id: str
    org_name: str
    role: RoleType

class Organization(BaseModel):
    id: str
    name: str
    created_at: str
    created_by: str

class GuidelineVersionRecord(BaseModel):
    version: int
    title: str
    category: CategoryType
    description: str
    source_label: str
    pattern: str
    severity: SeverityType
    remedy_suggestion: str
    is_active: bool
    updated_at: str
    updated_by: str

class GuidelineRule(BaseModel):
    id: str
    rule_id: str
    org_id: str
    category: CategoryType
    title: str
    description: str
    source_label: str
    pattern: str
    severity: SeverityType
    remedy_suggestion: str
    is_active: bool = True
    version: int = 1
    version_history: List[GuidelineVersionRecord] = Field(default_factory=list)
    created_at: str
    created_by: str
    updated_at: str
    updated_by: str

class GuidelineCreateRequest(BaseModel):
    rule_id: str = Field(min_length=3, max_length=50)
    category: CategoryType
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=1000)
    source_label: str = Field(min_length=3, max_length=200)
    pattern: str = Field(min_length=1, max_length=500)
    severity: SeverityType = "high"
    remedy_suggestion: str = Field(min_length=3, max_length=1000)
    is_active: bool = True

class GuidelineUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    category: Optional[CategoryType] = None
    description: Optional[str] = Field(None, min_length=3, max_length=1000)
    source_label: Optional[str] = Field(None, min_length=3, max_length=200)
    pattern: Optional[str] = Field(None, min_length=1, max_length=500)
    severity: Optional[SeverityType] = None
    remedy_suggestion: Optional[str] = Field(None, min_length=3, max_length=1000)
    is_active: Optional[bool] = None

class Finding(BaseModel):
    rule_id: str
    rule_version: int
    category: str
    matched_text: str
    start: int
    end: int
    severity: SeverityType
    source_label: str
    reason: str
    suggestion: str
    is_ai_generated: bool = False
    confidence_or_status: Optional[str] = None

class CheckResult(BaseModel):
    outcome: Literal["compliant", "needs_revision", "insufficient_evidence", "clean", "advisory_flags"]
    findings: List[Finding] = Field(default_factory=list)
    deterministic_findings: List[Finding] = Field(default_factory=list)
    ai_findings: List[Finding] = Field(default_factory=list)
    ai_status: Literal["completed", "insufficient_evidence", "fallback_deterministic_only", "disabled", "error"] = "disabled"
    ai_model: Optional[str] = None
    ai_disclosure: str = "Evaluated against active authorized guidelines with evidence grounding. AI findings do not grant publication approval."
    active_rules_evaluated: int = 0
    checked_at: str
    summary: str

class DraftCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    channel: str = Field("social", min_length=1, max_length=50)
    audience: str = Field("general_public", min_length=1, max_length=100)
    campaign: str = Field("General", min_length=1, max_length=100)

class DraftUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1, max_length=20000)
    channel: Optional[str] = Field(None, min_length=1, max_length=50)
    audience: Optional[str] = Field(None, min_length=1, max_length=100)
    campaign: Optional[str] = Field(None, min_length=1, max_length=100)

class ReviewDecisionRequest(BaseModel):
    comments: str = Field(min_length=3, max_length=2000)

class Draft(BaseModel):
    id: str
    org_id: str
    title: str
    content: str
    channel: str
    audience: str
    campaign: str
    status: DraftStatusType = "draft"
    creator_id: str
    creator_email: str
    findings: List[Finding] = Field(default_factory=list)
    deterministic_findings: List[Finding] = Field(default_factory=list)
    ai_findings: List[Finding] = Field(default_factory=list)
    ai_status: str = "pending"
    outcome: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_by_email: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str
    updated_at: str

class AuditLog(BaseModel):
    id: str
    org_id: str
    entity_type: str
    entity_id: str
    action: str
    actor_id: str
    actor_email: str
    actor_role: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str
