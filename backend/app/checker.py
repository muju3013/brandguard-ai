import re
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from app.models import Finding, CheckResult, GuidelineRule
from app.db import db
from app.gemini_service import evaluate_with_gemini

def evaluate_draft_against_guidelines(
    draft_text: str,
    org_id: str,
    channel: str = "social",
    audience: str = "general_public",
    campaign: str = "General",
    include_ai: bool = True
) -> CheckResult:
    """
    Evaluates marketing draft text against the active brand guidelines of the tenant organisation.
    Combines:
    1. Independent deterministic regex pattern checking.
    2. Source-grounded Gemini AI review (when enabled and configured).
    Ensures zero fabricated citations, server-side validated findings, and strict tenant isolation.
    """
    active_rules: List[GuidelineRule] = db.list_guidelines(org_id=org_id, active_only=True)
    deterministic_findings: List[Finding] = []

    # 1. Independent Deterministic Rule Evaluation
    for rule in active_rules:
        try:
            pattern = re.compile(rule.pattern, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(rule.pattern), re.IGNORECASE)

        for match in pattern.finditer(draft_text):
            if rule.category in ("prohibited_claim", "tone_rule"):
                deterministic_findings.append(Finding(
                    rule_id=rule.rule_id,
                    rule_version=rule.version,
                    category=rule.category,
                    matched_text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    severity=rule.severity,
                    source_label=rule.source_label,
                    reason=rule.description,
                    suggestion=rule.remedy_suggestion,
                    is_ai_generated=False,
                    confidence_or_status="deterministic_verified"
                ))

    # 2. Source-Grounded Gemini AI Review
    ai_findings: List[Finding] = []
    ai_status = "disabled"
    ai_model = None
    ai_summary = ""

    if include_ai:
        ai_findings, ai_status, ai_outcome, ai_summary, ai_model = evaluate_with_gemini(
            draft_content=draft_text,
            channel=channel,
            audience=audience,
            campaign=campaign,
            active_rules=active_rules
        )

    # 3. Combine Findings (preserving separation)
    combined_findings = list(deterministic_findings)
    # Add unique AI findings not already caught identically by deterministic check
    det_keys = {(f.rule_id, f.start, f.end) for f in deterministic_findings}
    for aif in ai_findings:
        if (aif.rule_id, aif.start, aif.end) not in det_keys:
            combined_findings.append(aif)

    # 4. Resolve Final Preserved Outcome: Compliant | Needs Revision | Insufficient Evidence | Guidelines Not Configured
    has_high = any(f.severity == "high" for f in combined_findings)
    has_insufficient = (
        ai_status == "insufficient_evidence" or
        any(f.confidence_or_status == "insufficient_evidence" for f in combined_findings)
    )

    if len(active_rules) == 0:
        final_outcome = "guidelines_not_configured"
        summary_text = "Guidelines Not Configured: No active guidelines exist for your organisation. Compliance could not be evaluated."
    elif has_high or any(f.severity == "high" for f in deterministic_findings):
        final_outcome = "needs_revision"
        summary_text = f"Flagged {len(combined_findings)} governance issues ({len(deterministic_findings)} deterministic, {len(ai_findings)} AI)."
    elif has_insufficient:
        final_outcome = "insufficient_evidence"
        summary_text = "Factual or promotional claims lack verified approved evidence. Human review required."
    elif len(combined_findings) > 0:
        final_outcome = "needs_revision"
        summary_text = f"Identified {len(combined_findings)} advisory brand tone or style flags."
    else:
        final_outcome = "compliant"
        summary_text = f"Compliant: Verified against {len(active_rules)} active guidelines with 0 violations."

    if ai_summary and ai_status != "disabled":
        summary_text = f"{summary_text} [{ai_summary}]"

    ai_disclosure_text = (
        "Deterministic checks run independently. "
        "Gemini AI review is strictly source-grounded in active authorized guidelines. "
        "AI findings cannot approve or publish marketing assets."
    )

    return CheckResult(
        outcome=final_outcome,
        findings=combined_findings,
        deterministic_findings=deterministic_findings,
        ai_findings=ai_findings,
        ai_status=ai_status,
        ai_model=ai_model,
        ai_disclosure=ai_disclosure_text,
        active_rules_evaluated=len(active_rules),
        checked_at=datetime.now(timezone.utc).isoformat(),
        summary=summary_text
    )
