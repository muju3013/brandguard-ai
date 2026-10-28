import logging
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import re

from app.config import settings
from app.rate_limiter import rate_limiter_check
from app.routes import auth_routes, guidelines_routes, drafts_routes, audit_routes, r3_routes

# Configure structured production logging
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("brandguard.main")

app = FastAPI(
    title=settings.app_title,
    version=settings.version,
    description="Explainable Brand Governance API with Firebase Auth, RBAC, Versioned Guidelines, and Deterministic Checking."
)

# Global production exception handler (masks internal traces in production)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception processing {request.method} {request.url.path}: {exc}", exc_info=True)
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please contact the administrator."}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# CORS configuration supporting Authorization headers and REST methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Phase 1 Starter Endpoints (Preserved for backwards compatibility)
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    draft: str = Field(min_length=1, max_length=10000)
    channel: str = 'social'

@app.get('/health')
def health():
    """Phase 1 backwards-compatible and production diagnostic health endpoint."""
    from app.firebase_setup import get_firebase_app
    from app.db import db, FirestoreStore
    is_firestore = isinstance(db, FirestoreStore)
    return {
        'status': 'ok',
        'service': 'BrandGuard AI Backend',
        'environment': settings.environment,
        'mode': 'production' if settings.is_production else 'deterministic-demo',
        'phase': 3,
        'version': settings.version,
        'database': 'firestore' if is_firestore else 'in_memory',
        'gemini_configured': bool(settings.gemini_api_key and not settings.gemini_api_key.startswith("your_")),
        'gemini_model': settings.gemini_model,
        'firebase_admin_initialized': bool(get_firebase_app())
    }

@app.post('/review', dependencies=[Depends(rate_limiter_check)])
def review(request: ReviewRequest):
    """
    Phase 1 backwards-compatible starter pre-check endpoint.
    Maintains existing deterministic demo pattern behavior.
    """
    findings = []
    rules = [
        ('DEMO-001', r'\b(guaranteed|100% guaranteed)\b', 'Absolute guarantees require approved evidence.', 'Avoid absolute guarantees unless substantiated.'),
        ('DEMO-002', r'\b(cures?|miracle cure)\b', 'Medical effectiveness claims require approved evidence.', 'Remove unsupported medical claims and request human review.'),
        ('DEMO-003', r'\b(best in the world|number one|#1)\b', 'Superlative claims require approved evidence.', 'Use a factual, supported product description.'),
    ]
    for rule_id, pattern, reason, suggestion in rules:
        for match in re.finditer(pattern, request.draft, re.IGNORECASE):
            findings.append({
                'rule_id': rule_id,
                'matched_text': match.group(0),
                'start': match.start(),
                'end': match.end(),
                'severity': 'high',
                'reason': reason,
                'suggestion': suggestion,
                'evidence_status': 'demo_rule_only'
            })
    return {
        'mode': 'deterministic-demo',
        'outcome': 'needs_revision' if findings else 'insufficient_evidence',
        'findings': findings,
        'note': 'Starter demo only. For authenticated organization-specific evidence and workflows, use Phase 2 /api endpoints.'
    }

# ---------------------------------------------------------------------------
# Phase 2 Protected Governance API Routers
# ---------------------------------------------------------------------------

app.include_router(auth_routes.router)
app.include_router(guidelines_routes.router)
app.include_router(drafts_routes.router)
app.include_router(audit_routes.router)

app.include_router(r3_routes.router)
