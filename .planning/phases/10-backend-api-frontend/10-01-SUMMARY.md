---
phase: 10-backend-api-frontend
plan: "01"
subsystem: api-gateway/security
tags: [jwt, rbac, auth, fastapi, pyjwt, security]
dependency_graph:
  requires: ["10-00a", "10-00b"]
  provides: ["JWT-issuance", "RBAC-require_roles", "auth-router"]
  affects: ["10-02-kpi", "10-03-sse", "Angular-route-guards"]
tech_stack:
  added: ["PyJWT>=2.9 (already in pyproject.toml)", "fastapi.security.HTTPBearer"]
  patterns: ["HTTPBearer bearer scheme", "dependency factory (require_roles)", "seeded persona registry"]
key_files:
  created:
    - apps/api-gateway/src/svc_api_gateway/security/__init__.py
    - apps/api-gateway/src/svc_api_gateway/security/jwt.py
    - apps/api-gateway/src/svc_api_gateway/security/rbac.py
    - apps/api-gateway/src/svc_api_gateway/routers/auth.py
    - apps/api-gateway/tests/unit/conftest.py
  modified:
    - apps/api-gateway/src/svc_api_gateway/main.py
    - apps/api-gateway/tests/unit/test_auth_router.py
    - apps/api-gateway/tests/unit/test_rbac.py
decisions:
  - "RBAC test route changed from /v1/approvals (unguarded) to /auth/me (guarded by require_roles) to avoid modifying existing endpoints before their JWT migration phase"
  - "Dev password 'mantis2026' confirmed from test_auth_router.py contract (overrides plan text which said 'operator123')"
  - "test_rbac_forbidden_when_no_token asserts status in (401, 403) since FastAPI HTTPBearer auto_error=True returns 403 when no credentials provided"
metrics:
  duration: "~35 min"
  completed_date: "2026-05-24"
  tasks_completed: 2
  files_created: 5
  files_modified: 3
requirements: [SRV-01, HITL-02]
---

# Phase 10 Plan 01: JWT Auth + RBAC Summary

**One-liner:** HS256 JWT issuance via PyJWT with 5 seeded personas (mantis2026 dev credentials) + `require_roles` RBAC dependency factory wired into /auth/login and /auth/me, unlocking all downstream RBAC-guarded endpoints.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | security/jwt.py + security/rbac.py | a5cc3af | security/__init__.py, jwt.py, rbac.py, tests/unit/conftest.py |
| 2 | routers/auth.py + wire into build_app | f4f2f03 | routers/auth.py, main.py, test_auth_router.py, test_rbac.py |

## Verification Results

- `test_auth_router.py`: 5/5 passed (un-skipped from 10-00b scaffold)
- `test_rbac.py`: 4/4 passed (un-skipped from 10-00b scaffold)
- Full unit suite: 9 passed, 4 skipped (KPI scaffold for 10-02), 0 failures attributable to this plan

## What Was Built

### security/jwt.py
- `create_token(email, role)` — issues HS256 JWT, exp = 8h, tz-aware `datetime.now(timezone.utc)` (CR-04)
- `decode_token(token)` — validates signature + expiry; raises HTTPException 401 "token_expired" or "token_invalid"
- `SEEDED_USERS` dict — 5 personas: operator / shift-supervisor / technician / manager / admin, all with dev password "mantis2026"
- `SECRET_KEY` from `API_SECRET_KEY` env with documented dev-only default (T-10-01-04)

### security/rbac.py
- `require_roles(*allowed_roles)` — dependency factory returning `_check_roles`; raises 403 "rbac_forbidden" on role mismatch
- `bearer_scheme = HTTPBearer(auto_error=True)` — shared instance across all guarded endpoints

### routers/auth.py
- `POST /auth/login` — validates dev credentials, returns `{access_token, token_type: "bearer", role}`; generic 401 "invalid_credentials" on failure (T-10-01-03)
- `GET /auth/me` — echoes `{sub, email, role}` via `Depends(require_roles(*_ALL_ROLES))`
- `LoginRequest` — `model_config = ConfigDict(extra="forbid", frozen=True)` (CR-03)
- Unexpected errors: structlog.error server-side, generic 500 "internal_server_error" in body

### main.py
- `from svc_api_gateway.routers import auth as auth_router` added inside `build_app()` local imports
- `app.include_router(auth_router.router)` registered after health router

## Deviations from Plan

### Auto-fixed / Plan-adjusted Issues

**1. [Rule 1 - Bug] RBAC test route changed from /v1/approvals to /auth/me**
- **Found during:** Task 2 analysis of test_rbac.py + approvals.py
- **Issue:** The Nyquist scaffold test pointed `OPERATOR_PROTECTED_ROUTE = "/v1/approvals"` but that endpoint has no `require_roles` dependency (Phase 6 dev-mode ACL, not JWT-guarded yet). Using it would have required either modifying existing approvals endpoints (breaking backward compatibility) or producing a false-passing test.
- **Fix:** Updated test_rbac.py to use `/auth/me` (a new Plan 10-01 endpoint explicitly guarded by `require_roles`) as the test route. The scaffold comment itself noted "or any route guarded by operator role" — this is within contract.
- **Files modified:** apps/api-gateway/tests/unit/test_rbac.py
- **Commit:** f4f2f03

**2. [Rule 1 - Correction] Dev password corrected to "mantis2026"**
- **Found during:** Task 1, comparing 10-CONTEXT.md to test_auth_router.py constants
- **Issue:** Plan text for action said "dev passwords like 'operator123'" but test_auth_router.py hardcodes `OPERATOR_PASSWORD = "mantis2026"`. The test file is the authoritative contract.
- **Fix:** SEEDED_USERS populated with `"mantis2026"` for all personas.
- **Files modified:** apps/api-gateway/src/svc_api_gateway/security/jwt.py
- **Commit:** a5cc3af

**3. [Rule 2 - Missing fixture] Added tests/unit/conftest.py with make_test_token**
- **Found during:** Task 2, test_rbac.py used PLACEHOLDER tokens — needed a real token factory
- **Fix:** Created `make_test_token` fixture in tests/unit/conftest.py so RBAC tests can create valid signed tokens without calling the HTTP endpoint.
- **Files modified:** tests/unit/conftest.py (new)
- **Commit:** a5cc3af

### Pre-existing Failures (out of scope)
- `test_supply_cluster_e2e.py::test_inventory_manager_check_and_signoff_audit_rows` — FAILED (pre-existing, introduced in commit 5e52f3a phase 09-07)
- `test_supply_cluster_e2e.py::test_supply_cluster_four_agent_full_sweep` — FAILED (pre-existing, same origin)
- These failures are unrelated to Plan 10-01 changes and are logged to `deferred-items.md`.

## Known Stubs

None — all endpoints return real data: JWT is genuine PyJWT output, /auth/me echoes real decoded claims.

## Threat Flags

No new security surface beyond what is documented in the Plan 10-01 threat model:
- T-10-01-01: /auth/login (mitigated — HS256 signed JWT, env-driven secret)
- T-10-01-02: require_roles (mitigated — role from signed JWT claim only)
- T-10-01-03: error bodies (mitigated — generic "invalid_credentials" / "internal_server_error")
- T-10-01-04: JWT secret (mitigated — no hardcoded production secret, env-driven)

## Self-Check: PASSED
