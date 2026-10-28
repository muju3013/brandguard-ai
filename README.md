# BrandGuard AI — Explainable Brand Governance Platform
## Production Readiness & Hackathon Round 2 Audit Documentation

BrandGuard AI is an enterprise brand governance and regulatory compliance platform engineered for the **Inkloom AI Round 2 Hackathon**. It empowers regulated brands to enforce claim substantiation, avoid deceptive advertising, maintain tone guidelines, and leverage Google Gemini AI with strict source grounding.

- **Phase 1:** Deterministic demo pattern checking baseline (`/health`, `/review`).
- **Phase 2:** Multi-tenant workspaces, Firebase Auth, server-authoritative RBAC (Admin, Reviewer, Creator), versioned guidelines, and reviewer approval workflows.
- **Phase 3:** Source-grounded **Gemini AI review** via the official Google GenAI Python SDK (`google-genai`), running independently alongside deterministic rule checking, with strict server-side citation validation, prompt injection defense, and resilient deterministic-only fallback.
- **Production Hardening (Audit Complete):** Fail-closed authentication, server-enforced tenant isolation, rate limiting, masked production errors, zero client secrets, Docker/Vercel deployment configs, and safe judge provisioning.

---

## 1. Production Architecture & Security Hardening

```
  ┌───────────────────────────────────────────────────────────┐
  │                    React 18 SPA (Vercel)                  │
  │   - Firebase Client SDK (Email/Password Auth)             │
  │   - Zero Client-side Secrets (No Gemini Keys)             │
  │   - Demo Mode Automatically Disabled in Production        │
  └─────────────────────────────┬─────────────────────────────┘
                                │ Bearer ID Token (HTTPS)
                                ▼
  ┌───────────────────────────────────────────────────────────┐
  │                   FastAPI Backend Host                    │
  │               (Render / Cloud Run / Docker)               │
  │                                                           │
  │  [Security Perimeter]                                     │
  │   ├─ Rate Limiting (In-Memory Sliding Window / Token)     │
  │   ├─ CORS Middleware (Restricted to Authorized Domains)   │
  │   ├─ Global Exception Handler (Masks Tracebacks in Prod)  │
  │   └─ Structured Production Logging                        │
  │                                                           │
  │  [Authentication & RBAC (auth.py)]                        │
  │   ├─ Firebase Admin SDK ID Token Verification             │
  │   ├─ Fail-Closed: Blocks requests if Firebase unavailable │
  │   ├─ Role & Tenant Lookup: 100% Server-Authoritative      │
  │   └─ Demo Tokens Strictly Blocked in Production Mode      │
  │                                                           │
  │  [Dual Independent Governance Engines]                   │
  │   ├─ Deterministic Rule Engine (Regex & Source Citations) │
  │   └─ Grounded Gemini Engine (google-genai / Prompt Delim) │
  │                                                           │
  │  [Persistence & Audit Layer (db.py)]                      │
  │   ├─ Google Cloud Firestore (USE_FIRESTORE=true)          │
  │   ├─ Fail-Closed: Refuses insecure fallback in prod       │
  │   └─ Immutable Audit Log Trail for every lifecycle event  │
  └───────────────────────────────────────────────────────────┘
```

### Key Security Safeguards
1. **Fail-Closed Firebase Authentication:**
   - In production (`ENVIRONMENT=production`), the backend verifies authentic Firebase ID tokens via the Firebase Admin SDK.
   - If the Firebase Admin SDK is unconfigured or unreachable, all authenticated requests fail closed with HTTP 503 instead of falling back to insecure mock authentication.
   - Demo tokens (`demo-token:*`) and `/api/auth/demo-users` are strictly blocked with HTTP 401 and 403 in production.
2. **Zero Client Trust & Role Impersonation Defense:**
   - The frontend never dictates the user's role or organization ID. Roles are resolved authoritatively from the database upon token verification.
3. **Multi-Tenant Isolation:**
   - All guidelines, drafts, and audit logs are strictly scoped by `org_id`. Cross-tenant reads and mutations return HTTP 404/403.
4. **Server-Only Gemini Secrets:**
   - `GEMINI_API_KEY` is loaded exclusively on the backend and is never returned in API payloads, serialized to client configs, or logged in server output.
5. **Prompt Injection & Untrusted Data Defense:**
   - Marketing drafts and guidelines are wrapped inside `<marketing_draft>` and `<authorized_guidelines>` XML-style boundary delimiters. The system prompt instructs Gemini that draft content is untrusted data and forbids executing embedded instructions.
6. **Server-Side AI Citation Verification:**
   - Every AI finding is verified against the database. Stale versions or hallucinated `rule_id` values are rejected immediately. Unsupported claims are forced to **Insufficient Evidence / Human Review**.
7. **Rate Limiting & DoS Protection:**
   - Sensitive endpoints (`/review`, `/api/drafts/{id}/check`, draft creation) are protected by sliding-window rate limiters to prevent DDoS and API quota exhaustion.
8. **Information Leakage Prevention:**
   - Global production error handler catches unhandled exceptions, logs the full trace internally, and returns a clean, sanitized HTTP 500 error to clients.

---

## 2. Role Permissions Matrix

| Capability | Admin | Reviewer | Creator |
| :--- | :---: | :---: | :---: |
| Create / Update Guidelines & Rules | ✅ | ❌ | ❌ |
| View Guideline Library & Version History | ✅ | ✅ | ✅ |
| Create Drafts & Run Pre-checks | ✅ | ❌ | ✅ |
| Edit & Revise Own Drafts | ✅ | ❌ | ✅ |
| Submit Draft for Review | ✅ | ❌ | ✅ |
| Approve / Request Changes on Drafts | ✅ | ✅ | ❌ |
| Approve Own Draft | ❌ *(Separation)* | ❌ | ❌ |
| View Organization Audit Trail | ✅ | ✅ | ✅ |

---

## 3. Production Environment Checklist

Before releasing to production, verify each item:

- [x] **Repository Secrets:** `.env` and `*serviceAccountKey*.json` are included in `.gitignore` and not committed.
- [x] **Fail-Closed Auth:** `ENVIRONMENT=production` set on Python host; verifies demo tokens are rejected with 401.
- [x] **Server-Side Secrets:** `GEMINI_API_KEY` set as host environment variable only; absent from frontend code.
- [x] **Rate Limiting:** In-memory sliding window rate limiter active on `/review` and `/api/drafts/{id}/check`.
- [x] **Error Handling:** Production exception handler masks stack traces on 500 errors.
- [x] **CORS Configuration:** `CORS_ORIGINS` configured to point strictly to the Vercel production frontend domain.
- [x] **Persistence:** `USE_FIRESTORE=true` configured with valid `FIREBASE_SERVICE_ACCOUNT_KEY_PATH`.
- [x] **Frontend Production Build:** `npm run build` succeeds cleanly; `isDemoAuthEnabled` evaluates to `false`.
- [x] **Deployment Configs:** `frontend/vercel.json`, `backend/Procfile`, and `backend/Dockerfile` prepared.

---

## 4. Deployment Instructions

### A. Deploy React Frontend to Vercel

1. **Connect Repository:** Import the repository into [Vercel](https://vercel.com).
2. **Root Directory:** Set Root Directory to `frontend`.
3. **Build Settings:**
   - Framework Preset: `Vite`
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. **Environment Variables:**
   Copy variables from `frontend/.env.production.example`:
   ```env
   VITE_API_BASE_URL=https://your-brandguard-backend.onrender.com
   VITE_FIREBASE_API_KEY=AIzaSy...
   VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=your-project-id
   VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   VITE_FIREBASE_MESSAGING_SENDER_ID=123456789012
   VITE_FIREBASE_APP_ID=1:123456789012:web:abcdef
   VITE_ENABLE_DEMO_AUTH=false
   ```
5. **Deploy:** Click **Deploy**. Vercel will apply the SPA rewrites defined in `frontend/vercel.json`.

---

### B. Deploy FastAPI Backend to Python Host (Render / Cloud Run)

#### Option 1: Render / PaaS (using `Procfile`)
1. Create a **New Web Service** on [Render](https://render.com) pointing to the repository.
2. Root Directory: `backend`
3. Environment: `Python 3`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Set Environment Variables (refer to `backend/.env.production.example`):
   ```env
   ENVIRONMENT=production
   USE_FIRESTORE=true
   ENABLE_DEMO_AUTH=false
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL=gemini-3.8-flash
   CORS_ORIGINS=https://your-brandguard-frontend.vercel.app
   FIREBASE_SERVICE_ACCOUNT_KEY_PATH=/etc/secrets/serviceAccountKey.json
   ```
7. Add Secret File: Upload your Firebase `serviceAccountKey.json` under Render **Secret Files**.

#### Option 2: Containerized Deploy (using `Dockerfile`)
```bash
docker build -t brandguard-api:latest -f backend/Dockerfile backend/
docker run -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e GEMINI_API_KEY=your_api_key \
  brandguard-api:latest
```

---

## 5. Safe Judge-Demo Account Provisioning

To safely provision judge evaluation accounts in Firebase and Firestore without manual console entry:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.scripts.provision_judge_accounts \
  --org-id org_inkloom_judge \
  --org-name "Inkloom Evaluation Brands" \
  --password "<YOUR_SECURE_PASSWORD>"
```

### Generated Judge Credentials:
- **Organisation:** `Inkloom Evaluation Brands` (`org_inkloom_judge`)
- **Password:** `<Configured securely during provisioning or via environment>`
- **1. Admin Judge:** `judge.admin@inkloom-brandguard.com` (Rule library management, member roles, audit logs)
- **2. Reviewer Judge:** `judge.reviewer@inkloom-brandguard.com` (Approve drafts, request revisions with notes)
- **3. Creator Judge:** `judge.creator@inkloom-brandguard.com` (Draft marketing text, run Gemini pre-check, submit to queue)

---

## 6. Verification & Automated Test Results

Run the complete test suite:

```powershell
cd backend
.\.venv\Scripts\pytest.exe -v
```

### Exact Backend Test Results (39 Tests Passing):
```
tests/test_brandguard.py::test_phase1_health PASSED                      [  2%]
tests/test_brandguard.py::test_phase1_review_endpoint PASSED             [  5%]
tests/test_brandguard.py::test_unauthenticated_requests_rejected PASSED  [  7%]
tests/test_brandguard.py::test_server_authoritative_user_profile PASSED  [ 10%]
tests/test_brandguard.py::test_creator_cannot_approve_or_request_changes PASSED [ 12%]
tests/test_brandguard.py::test_creator_cannot_manage_guidelines PASSED   [ 15%]
tests/test_brandguard.py::test_reviewer_cannot_create_drafts PASSED      [ 17%]
tests/test_brandguard.py::test_tenant_isolation_drafts PASSED            [ 20%]
tests/test_brandguard.py::test_tenant_isolation_guidelines PASSED        [ 23%]
tests/test_brandguard.py::test_tenant_isolation_audit_logs PASSED        [ 25%]
tests/test_brandguard.py::test_rule_versioning_and_history PASSED        [ 28%]
tests/test_brandguard.py::test_deterministic_findings_using_active_rules_only PASSED [ 30%]
tests/test_brandguard.py::test_full_governance_review_workflow PASSED    [ 33%]
tests/test_gemini_review.py::test_gemini_malformed_ai_output PASSED      [ 35%]
tests/test_gemini_review.py::test_gemini_fabricated_rule_id_rejected PASSED [ 38%]
tests/test_gemini_review.py::test_gemini_stale_rule_version_rejected PASSED [ 41%]
tests/test_gemini_review.py::test_gemini_prompt_injection_defense PASSED [ 43%]
tests/test_gemini_review.py::test_gemini_unavailable_fallback PASSED     [ 46%]
tests/test_gemini_review.py::test_gemini_cross_tenant_evidence_isolation PASSED [ 48%]
tests/test_gemini_review.py::test_gemini_insufficient_evidence_unsupported_claim PASSED [ 51%]
tests/test_gemini_review.py::test_gemini_grounded_successful_review PASSED [ 53%]
tests/test_gemini_review.py::test_real_gemini_controlled_live_call PASSED [ 56%]
tests/test_production_security.py::test_production_mode_rejects_demo_tokens PASSED [ 58%]
tests/test_production_security.py::test_production_mode_blocks_demo_users_endpoint PASSED [ 61%]
tests/test_production_security.py::test_production_fail_closed_when_firebase_unavailable PASSED [ 64%]
tests/test_production_security.py::test_rbac_creator_cannot_review_or_edit_guidelines PASSED [ 66%]
tests/test_production_security.py::test_rbac_reviewer_cannot_create_drafts_or_edit_guidelines PASSED [ 69%]
tests/test_production_security.py::test_tenant_isolation_cross_tenant_access_blocked PASSED [ 71%]
tests/test_production_security.py::test_rate_limiting_triggers_429 PASSED [ 74%]
tests/test_production_security.py::test_production_error_handler_masks_internal_tracebacks PASSED [ 76%]
tests/test_production_security.py::test_end_to_end_review_workflow_and_audit_persistence PASSED [ 79%]
tests/test_production_security.py::test_creator_identity_never_jwt_substring PASSED [ 82%]
tests/test_production_security.py::test_corrupt_creator_email_safely_sanitized_and_repaired PASSED [ 84%]
tests/test_production_security.py::test_zero_guidelines_returns_guidelines_not_configured_and_blocks_submission PASSED [ 87%]
tests/test_production_security.py::test_creator_cannot_approve_own_draft PASSED [ 89%]
tests/test_production_security.py::test_reviewer_can_request_changes_and_creator_can_revise PASSED [ 92%]
tests/test_production_security.py::test_audit_logs_role_based_access_admin_reviewer_creator PASSED [ 94%]
tests/test_production_security.py::test_audit_logs_strict_tenant_isolation_never_leaks_cross_tenant PASSED [ 97%]
tests/test_production_security.py::test_audit_logs_lifecycle_events_complete_coverage PASSED [100%]

======================== 39 passed, 1 warning in 8.77s ========================
```

### Exact Frontend Build Results:
```
> brandguard-ai-frontend@0.1.0 build
> vite build

vite v6.4.5 building for production...
transforming...
✓ 44 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.36 kB │ gzip:  0.26 kB
dist/assets/index-OJaiLuaM.css   38.67 kB │ gzip:  7.53 kB
dist/assets/index-J0GN4Z9P.js   385.35 kB │ gzip: 98.80 kB
✓ built in 1.29s
```

---

## 7. Known Limitations & Production Next Steps

1. **Transient Google AI 503 / 429 Demand Limits:** Free-tier limits for experimental Gemini models may throttle during burst usage. BrandGuard's built-in retry and fallback ensures zero downtime by degrading gracefully to deterministic rule checking automatically.
2. **Multi-Instance Rate Limiting:** The current rate limiter uses an in-memory sliding window, ideal for single-instance or container deployments. For horizontally scaled clusters (>5 instances), swap with a Redis-backed rate limiter (e.g. `slowapi` with Redis).
3. **Live Firestore Credentials in Development:** In local development without GCP credentials, BrandGuard operates cleanly with `InMemoryStore`. In production, setting `USE_FIRESTORE=true` strictly enforces Firestore persistence and fails closed if unconfigured.

---

## 8. Live Firebase Integration & Cloud Firestore Verification

### Target Cloud Project:
- **Firebase Project ID:** `brandguard-ai-techwithmujju`
- **Project Number:** `844207936178`
- **Firestore Security Rules:** `allow read, write: if false;` (deployed live via Firebase CLI). All client operations strictly mediated by authoritative FastAPI backend.

### Secure First-Admin Bootstrap:
To bootstrap or promote an admin account in Firebase Auth and Cloud Firestore:
```bash
# In backend virtualenv:
python -m app.scripts.bootstrap_admin --email judge.admin@inkloom-brandguard.com --role admin
```
Additionally, `BOOTSTRAP_ADMIN_EMAIL` in `.env` automatically promotes the specified email upon their first registration.

### Evaluation & Judge Accounts:
| Role | Email | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **Admin** | `judge.admin@inkloom-brandguard.com` | `[Set securely via provisioning script]` | Create/edit rules, manage team, view tamper-evident audit logs |
| **Reviewer** | `judge.reviewer@inkloom-brandguard.com` | `[Set securely via provisioning script]` | Review pending queue, approve/request changes with notes |
| **Creator** | `judge.creator@inkloom-brandguard.com` | `[Set securely via provisioning script]` | Submit drafts, run deterministic + Gemini AI check, submit for review |

### Full Live Lifecycle Verification Test:
Run the end-to-end integration test against live Google Firebase and Cloud Firestore:
```bash
# Authenticates real users via Google Identity Toolkit REST API, creates drafts in Firestore, runs Gemini review, executes reviewer approval, and verifies Firestore audit records:
python -m app.scripts.test_live_firebase_workflow
```

---

## 9. Critical Security & Deployment Advisory

> [!CAUTION]
> **Gemini API Key Rotation Required Prior to Public Hosting:**
> The Gemini API key utilized during development was transmitted in chat sessions and is flagged as exposed. Before deploying this project to a publicly accessible host (e.g. Vercel or Render production domain), generate a new API key in Google AI Studio, update `backend/.env` with the new key, and revoke the previous key.



---

## TechCircuit Round 3 — Live QA verification (October 28, 2026)

**Current status:** The three Round 3 feature groups have been merged to `main`. The frontend Vercel production domain `https://brandguard-ai-phi.vercel.app` was verified as `READY` on commit `0f9a5234eb4348443ef645e19d25f82802f7d291` before this documentation update. The signed-in app was also manually tested against its hosted API. Confirm backend Render commit separately before claiming that every backend patch is deployed.

### Exactly three committed improvements

1. **Visual creative and logo governance:** Admin can configure an approved HEX palette and upload a reference JPG/PNG logo (200 KB). Signed-in users can upload JPG/PNG creatives (4 MB, maximum 16 megapixels). Server checks dominant colours; deterministic prohibited-phrase matching works for user-entered creative text. When Gemini is available, the server requests logo comparison and guideline-grounded visual findings with normalized bounding-box coordinates. Logo recognition, image coordinates and colour heuristics are **advisory, not guaranteed**; no reliable image text OCR is claimed.
2. **PDF/DOCX compliance review:** Signed-in users can upload up to 5 MB (25 PDF pages, 250 DOCX text sections); extract selectable PDF text and DOCX paragraphs/tables; run tenant-scoped active deterministic brand guidelines and download a location-linked CSV report from the UI. Scanned/empty PDF pages are explicitly reported as **unreviewed**. A scanned-page OCR pathway and semantic whole-document Gemini review are **not delivered**.
3. **Evidence-backed claims and risk-gated approvals:** Admin-created/versioned dossiers store exact claim wording, source title, optional source URL, source excerpt, verification notes and verifier identity. For a draft with **detected high-severity findings**, the approval API requires a same-tenant admin-created dossier whose claim appears in the draft **and covers all distinct high-severity matches**, or a documented reviewer exception of 25+ characters. Approval audit includes the dossier/version/evidence snapshot or the exception rationale. Caveat: currently the gate relies on existing high-severity findings; an unflagged risky phrase may escape this gate. Evidence is administrator-submitted, not independently validated by an external regulatory authority.

### Reviewer / judge journey

1. Sign in with a separately provisioned, authorised account; never expose active admin passwords.
2. Admin: **Creative & Evidence Studio** → configure colour palette, reference logo, and verified claim dossiers.
3. Creator: **Creative & Evidence Studio** → test an image creative and inspect visual findings and limitations; upload PDF/DOCX and download the location-linked issues CSV.
4. Creator: create a draft under **Drafts & Pre-check**, include a deliberately prohibited claim, submit for review.
5. Reviewer: visit **Reviewer Queue**; for high-risk findings enter a verified `claim_...` dossier ID or a detailed exception and review notes; approve or request changes. Confirm the actor, method and evidence snapshot in **Audit Trail**.

### Local setup

Install Python 3.11+ and Node 22+. Use a real, separately configured Firebase project for hosted workflows. Local memory storage exists for development/testing only.

```sh
cd backend
python -m venv .venv
# Activate your environment, then:
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Set frontend `VITE_API_BASE_URL=http://localhost:8000` and the Firebase client env variables described above. For production configure `ENVIRONMENT=production`, `USE_FIRESTORE=true`, Firebase Admin credentials, and `GEMINI_API_KEY` on the Render backend; do not put Gemini secrets in Vite variables. Configure allowed CORS origins, and rebuild the Vercel frontend.

### Safety / limits / known issues

- Image reviews don't persist the uploaded image itself; brand palette/logo metadata persists in Firestore. Do not upload confidential or sensitive source material into a public judge demo.
- The dossier source excerpt is stored by the admin, not independently fact-checked; verify legitimacy before release.
- File limits must be exercised with malformed, empty, oversized, encrypted and scanned content.
- High-risk evidence gate uses the latest draft findings; verify rule updates and concurrent reviewers before production use.
- Hosted authenticated role flows and Gemini image findings were manually tested on October 28, 2026; independent judge access and backend Render commit/version verification remain separate release checks.
- Existing exposed demo credentials must be rotated and secure judge access must be provisioned separately.


### Live functional QA results — October 28, 2026

Manual end-to-end checks were performed with separately authenticated Creator, Reviewer, and Admin roles in the **Inkloom Evaluation Brands** test workspace. All deliberately noncompliant text and evidence were **synthetic QA fixtures, not legitimate product substantiation**. Do not publish or reuse test claims.

| Test | Observed result | Scope / caveat |
|---|---|---|
| Visual JPG/PNG creative | 2 high-severity findings: deterministic banned text match and Gemini visual advisory for `100% guaranteed results` | Human interpretation needed for model findings |
| Reference logo governance | After admin configuration, review reported `logo_status: absent` and a high-severity `logo_advisory` | Advisory only; human confirmation required |
| Approved palette | Admin palette settings accessible and configurable | Colour mismatch against a controlled test image **not independently demonstrated** |
| PDF compliance review | 4 located findings across pages 1–2; `needs_revision` | Selectable text, not scanned-image OCR |
| DOCX compliance review | 4 findings at paragraphs 5–8 (3 high, 1 medium); `needs_revision` | Deterministic rule extraction |
| Location-linked CSV | Download succeeded; 4 issue data rows inspected | CSV format may prompt an Excel compatibility notice |
| Evidence-free approval attempt | High-risk draft approval rejected: missing matching dossier or recorded exception of at least 25 characters | Draft remained in reviewer flow |
| Reviewer exception approval | Test-only draft approved with documented exception; Audit Trail recorded `method: recorded_reviewer_exception` and reviewer rationale | No automatic publication |
| Admin evidence dossier | Created versioned QA dossier `claim_0a988087bc2c`, version 1 | Source explicitly labelled **not real evidence** |
| Dossier-backed approval | New high-risk synthetic QA draft approved; Audit Trail showed `method: approved_dossier`, matching dossier ID/version, verifier/time/evidence excerpt | Tests workflow correctness, **not** truth of the prohibited claim |
| Publication gate | Both approval variants recorded `publication_status: manual_only_no_auto_publish` | No public-content publication |

**Remaining release checks:** independently confirm latest backend Render commit, test a controlled off-palette creative, verify a matching-logo positive case, and consider scanned PDF OCR/concurrency/independent source verification for future production hardening. CI and user-reported manual tests should not be conflated.

### Evidence of testing

`.github/workflows/round3.yml` runs backend pytest and frontend Vite build on pull requests and pushes. The latest known green Round 3 backend CI before this documentation change recorded **49 passed, 1 skipped**, with a successful frontend production build; check current GitHub Actions for any newer outcome. The manual results below are separately observed behavior, not automated CI results.
