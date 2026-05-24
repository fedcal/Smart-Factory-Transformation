---
phase: 10-backend-api-frontend
plan: "03"
subsystem: api-gateway
tags: [sse, streaming, jwt, rbac, rate-limit, otel, migration, hitl]
dependency_graph:
  requires: ["10-01", "10-02"]
  provides: ["sse-endpoints", "query-param-jwt", "hitl-10-rate-limit", "otel-spans", "auth-users-seed"]
  affects: ["10-04", "10-05", "10-06"]
tech_stack:
  added:
    - "sse-starlette>=2.3,<3 (already pinned in pyproject) — EventSourceResponse"
    - "opentelemetry-instrumentation-fastapi (already pinned) — FastAPIInstrumentor"
  patterns:
    - "Sliding-window in-process rate-limit via deque of timestamps per principal"
    - "Finite async generator pattern for SSE tests (avoids blocking httpx.AsyncClient)"
    - "best-effort OTEL guard (try/except around FastAPIInstrumentor.instrument_app)"
key_files:
  created:
    - apps/api-gateway/src/svc_api_gateway/routers/sse.py
    - infra/migrations/timescale/013_create_auth_users.sql
    - infra/migrations/timescale/tests/test_migration_013.py
  modified:
    - apps/api-gateway/src/svc_api_gateway/security/rbac.py
    - apps/api-gateway/src/svc_api_gateway/main.py
    - apps/api-gateway/tests/integration/test_sse.py
decisions:
  - "Finite async generator for SSE HTTP tests: patch kpi_stream with a 1-event generator instead of mocking asyncio.sleep + request.is_disconnected to avoid sse-starlette AppStatus event-loop re-use error across test functions"
  - "X-Accel-Buffering + Content-Type checks combined in one test to avoid sse-starlette AppStatus RuntimeError on second stream in the same test session"
  - "auth schema (not public) for auth_users to isolate identity concerns from operational schemas"
  - "OTEL instrumentor added best-effort in build_app() with try/except — missing exporter does not crash startup (SRV-04 spans-only this phase)"
metrics:
  duration: "14 minutes"
  completed: "2026-05-24"
  tasks: 3
  files_modified: 6
---

# Phase 10 Plan 03: SSE Streaming + OTEL Middleware + Migration 013 Summary

SSE streaming endpoints (kpi/approvals/alerts) with query-param JWT auth, HITL-10 12/hr/persona sliding-window rate-limit, best-effort OTEL endpoint spans, and idempotent auth_users seed migration.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Query-param JWT validator + SSE stream endpoints | 629d565 | rbac.py, sse.py, main.py, test_sse.py |
| 2 | HITL-10 alert rate limit (12/hr/persona) | 629d565 | sse.py (included in Task 1 commit) |
| 3 | OTEL middleware + migration 013 (auth_users seed) | 292feba | main.py (OTEL), 013_create_auth_users.sql, test_migration_013.py |

## What Was Built

### routers/sse.py
Three `EventSourceResponse` endpoints:
- `GET /v1/stream/kpi` — yields `kpi_update` (every 5s via `compute_kpi_snapshot`) + `sse_heartbeat` (every 30s)
- `GET /v1/stream/approvals` — yields `approval_pending` + `approval_resolved` + `sse_heartbeat` (polls DB at 5s intervals; Phase 11: replace with NATS JetStream consumer)
- `GET /v1/stream/alerts` — yields `alert_new` + `rate_limit` + `sse_heartbeat` (HITL-10 enforced)

All endpoints:
- Auth via `require_roles_qs(*roles)` — reads `?token=<JWT>` query parameter
- Set `X-Accel-Buffering: no` + `Cache-Control: no-cache` headers (T-10-03-03)
- Generic 500 error body (T-10-03-05)

### security/rbac.py — require_roles_qs()
New dependency factory that reads JWT from the `token` query parameter. Validates identically to `require_roles` via the same `decode_token` call. Raises 401 on missing/invalid token, 403 on role mismatch ("rbac_forbidden" — frontend contract preserved).

### HITL-10 Rate Limit (_check_alert_rate)
Module-level `_alert_rate_state: dict[str, deque[float]]` tracks per-principal alert timestamps. `_check_alert_rate(principal_sub, now)` evicts timestamps outside the 1-hour window and returns `False` when the count reaches 12. On the 13th alert, the `alerts_stream` generator emits a single `rate_limit` event (`{"limit": 12, "window": "1h"}`).

### main.py — OTEL + SSE router registration
- `include_router(sse_router.router)` added after `kpi_router`
- `FastAPIInstrumentor.instrument_app(app)` wrapped in try/except — best-effort (spans only this phase; full OTEL stack → Phase 11)

### Migration 013 — auth.auth_users
Creates `auth` schema + `auth_users` table (email PK, role, display_name, created_at) and seeds 5 persona rows with `INSERT ... ON CONFLICT DO NOTHING`. Fully idempotent (CREATE IF NOT EXISTS + ON CONFLICT). No password hashes stored.

## Test Results

```
apps/api-gateway/tests/integration/test_sse.py  — 6 passed
apps/api-gateway/tests/                         — 108 passed, 2 skipped (pre-existing)
```

Migration 013 tests require testcontainers (Docker) — marked `@pytest.mark.testcontainers @pytest.mark.integration`. Run separately in CI with `docker` marker.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] sse-starlette AppStatus event-loop collision in HTTP tests**
- **Found during:** Task 1 — test_sse_endpoint_sets_x_accel_buffering
- **Issue:** `AppStatus.should_exit_event` (asyncio.Event) bound to first event loop; second `c.stream()` call in a different test function reused the same object → `RuntimeError: bound to a different event loop`
- **Fix:** Combined Content-Type + X-Accel-Buffering assertions into a single test function (`test_sse_endpoint_content_type_and_headers`). No functional behavior changed.
- **Files modified:** `apps/api-gateway/tests/integration/test_sse.py`
- **Commit:** 629d565

**2. [Rule 2 - Missing] Finite generator pattern for SSE HTTP tests**
- **Found during:** Task 1 — tests blocking indefinitely because generator + mocked sleep ran without yielding control to the event loop
- **Fix:** Patch `kpi_stream` with a finite async generator (yields 1 event then stops) in HTTP-level tests. Generator-level tests use disconnect mocks directly.
- **Files modified:** `apps/api-gateway/tests/integration/test_sse.py`
- **Commit:** 629d565

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| Approvals/Alerts DB polling (5s) | `routers/sse.py` | ~120, ~170 | Phase 11 NATS JetStream consumer replaces polling; polling is correct fallback for dev-mode |
| `seen_ids` f-string in SQL (approvals/alerts) | `routers/sse.py` | ~130, ~180 | ID list injection uses string formatting on UUIDs from DB; safe for dev but plan 10-09 integrations should use a proper pagination cursor |

The stubs do not prevent the plan goal (SSE streams functional, test_sse.py passing). Phase 11 will replace the polling pattern.

## Threat Flags

All STRIDE threats mitigated as planned:

| Threat | Status |
|--------|--------|
| T-10-03-01 Info Disclosure (token in URL) | Accepted dev-mode; documented in rbac.py |
| T-10-03-02 DoS (alert flood) | Mitigated — 12/hr sliding window |
| T-10-03-03 DoS (idle SSE) | Mitigated — 30s heartbeat + X-Accel-Buffering: no |
| T-10-03-04 EoP (stream access) | Mitigated — require_roles_qs enforces role |
| T-10-03-05 Info Disclosure (500 body) | Mitigated — generic body + structlog |

No new threat surface beyond what the plan's threat_model covers.

## Self-Check: PASSED

Files created:
- [x] `/run/media/federicocalo/D/prj/Smart Factory Transformation/apps/api-gateway/src/svc_api_gateway/routers/sse.py`
- [x] `/run/media/federicocalo/D/prj/Smart Factory Transformation/infra/migrations/timescale/013_create_auth_users.sql`
- [x] `/run/media/federicocalo/D/prj/Smart Factory Transformation/infra/migrations/timescale/tests/test_migration_013.py`

Commits:
- [x] 629d565 — feat(10-03): SSE streaming endpoints + query-param JWT + OTEL middleware
- [x] 292feba — feat(10-03): migration 013 auth_users reference table + idempotent seed

Tests: 108 passed, 2 skipped (pre-existing), 0 failed.
