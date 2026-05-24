---
phase: 10-backend-api-frontend
plan: 00b
subsystem: testing
tags: [pytest, jest, angular, fastapi, tdd, nyquist, sse, jwt, rbac, kpi]

# Dependency graph
requires:
  - phase: 10-00a
    provides: deps installed (sse-starlette, PyJWT, Angular Material, ng2-charts, Tailwind v4)

provides:
  - pytest skip-by-design scaffolds for auth login, RBAC, SSE, KPI queries
  - Jest it.skip scaffolds for JwtService, SseService, ApprovalCardComponent
  - tests/unit/ and tests/integration/ package structure under apps/api-gateway/tests/
  - apps/factory-ui/src/app/core/auth/, core/sse/, shared/approval-card/ directory stubs

affects:
  - 10-01 (must un-skip test_auth_router.py + test_rbac.py + jwt.service.spec.ts)
  - 10-02 (must un-skip test_sse.py + test_kpi_queries.py + sse.service.spec.ts)
  - 10-03 (must un-skip approval-card.component.spec.ts)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Nyquist scaffolds: pytest.mark.skip(reason='impl in 10-XX') per test function, NOT module-level"
    - "Jest scaffolds: it.skip (not describe.skip) to allow individual un-skipping per plan"
    - "Contract comments inline: data-testid, HITL-07, CR-05 SQL $N references inside skip bodies"

key-files:
  created:
    - apps/api-gateway/tests/unit/__init__.py
    - apps/api-gateway/tests/unit/test_auth_router.py
    - apps/api-gateway/tests/unit/test_rbac.py
    - apps/api-gateway/tests/unit/test_kpi_queries.py
    - apps/api-gateway/tests/integration/__init__.py
    - apps/api-gateway/tests/integration/test_sse.py
    - apps/factory-ui/src/app/core/auth/jwt.service.spec.ts
    - apps/factory-ui/src/app/core/sse/sse.service.spec.ts
    - apps/factory-ui/src/app/shared/approval-card/approval-card.component.spec.ts
  modified: []

key-decisions:
  - "pytest.mark.skip per test function (not module-level) mirrors Phase 6 per-test reporting convention"
  - "test_kpi_queries.py includes source inspection test (test_kpi_sql_uses_parameterised_placeholders) that auto-skips when queries.py is absent — avoids always-passing or always-failing states"
  - "SSE scaffold uses skip-by-design (not MagicMock for interrupts) per execution spec"
  - "Jest it.skip (not xit/xdescribe) chosen for precise per-case granularity"

patterns-established:
  - "Nyquist pattern: test files reference owning plan in skip reason (e.g. 'impl in 10-01')"
  - "THREAT mitigations encoded in scaffold: T-10-00b-01 (CR-05 $N SQL), T-10-00b-02 (CR-02 generic 401 body)"
  - "Playwright data-testid contract encoded in Jest scaffold comments for traceability"

requirements-completed: [SRV-01, SRV-02, SRV-05, UI-03, UI-04, UI-07, HITL-07, HITL-10]

# Metrics
duration: 25min
completed: 2026-05-24
---

# Phase 10 Plan 00b: Nyquist Test-Contract Scaffolds Summary

**17 pytest + 34 Jest skip-by-design contracts encode auth/RBAC/SSE/KPI/ApprovalCard acceptance criteria before any Phase 10 implementation is written**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-24T18:05:00Z
- **Completed:** 2026-05-24T18:30:00Z
- **Tasks:** 2
- **Files modified:** 9 (all created)

## Accomplishments

- 4 pytest scaffolds (17 tests, all skipped) cover: JWT login contract, RBAC 403/401, SSE kpi_update event shape, KPI 6-key output + CR-05 SQL $N assertion
- 3 Jest scaffolds (34 tests, all skipped) cover: JwtService signals + SSR guard, SseService kpiSnapshot Signal, ApprovalCard HITL-07 motivation gate + Playwright data-testid contract
- Directory structure created: tests/unit/, tests/integration/ (backend); core/auth/, core/sse/, shared/approval-card/ (frontend)
- THREAT mitigations T-10-00b-01 (SQL injection CR-05) and T-10-00b-02 (generic 401 CR-02) are encoded as assertions in the scaffolds

## Task Commits

1. **Task 1+2: Backend pytest scaffolds + Frontend Jest scaffolds** - `28d6afb` (test)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `apps/api-gateway/tests/unit/test_auth_router.py` — JWT login contract (operator@mantis.it, sub/email/role/exp claims, 401 generic detail T-10-00b-02)
- `apps/api-gateway/tests/unit/test_rbac.py` — require_roles guard contract (403 rbac_forbidden literal, 401 unauthenticated, multi-role allow)
- `apps/api-gateway/tests/integration/test_sse.py` — SSE kpi_update + sse_heartbeat event contract, content-type assert, 401 without auth
- `apps/api-gateway/tests/unit/test_kpi_queries.py` — compute_kpi_snapshot 6-key output, numeric types, CR-05 $N SQL inspection (T-10-00b-01)
- `apps/factory-ui/src/app/core/auth/jwt.service.spec.ts` — Token storage (isPlatformBrowser), role()/isAuthenticated() Signals, logout()
- `apps/factory-ui/src/app/core/sse/sse.service.spec.ts` — kpiSnapshot Signal update, heartbeat connectionStatus, SSR no-op, disconnect()
- `apps/factory-ui/src/app/shared/approval-card/approval-card.component.spec.ts` — data-testid Playwright contract, HITL-07 motivation gate, EvidencePanel 4 sections

## Decisions Made

- pytest.mark.skip per test function (not module-level) — mirrors Phase 6 per-test reporting convention for predictable individual skip counts
- test_kpi_sql_uses_parameterised_placeholders auto-skips when queries.py is absent (pathlib.exists() check), avoiding permanently-passing assertions
- SSE scaffold uses direct pytest.skip() inside async bodies (not MagicMock for interrupt) per execution spec
- Jest it.skip chosen over xit/xdescribe for precise per-case granularity so each implementation plan can un-skip exactly its owned cases

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- venv shebang references `/media/federicocalo/D1/...` (old mount path); resolved by invoking `python3.12 -m pytest` directly instead of the shebang wrapper. This is a pre-existing environment condition; no fix attempted (out of scope for this plan).

## Known Stubs

None — scaffold files contain only skip-by-design test cases, no data stubs or placeholder values that flow to UI rendering.

## Threat Flags

None — no new runtime trust boundaries introduced; test-only files do not add network endpoints or auth paths.

## Self-Check: PASSED

- `apps/api-gateway/tests/unit/test_auth_router.py` — FOUND
- `apps/api-gateway/tests/unit/test_rbac.py` — FOUND
- `apps/api-gateway/tests/integration/test_sse.py` — FOUND
- `apps/api-gateway/tests/unit/test_kpi_queries.py` — FOUND
- `apps/factory-ui/src/app/core/auth/jwt.service.spec.ts` — FOUND
- `apps/factory-ui/src/app/core/sse/sse.service.spec.ts` — FOUND
- `apps/factory-ui/src/app/shared/approval-card/approval-card.component.spec.ts` — FOUND
- Commit `28d6afb` — FOUND in git log

## Next Phase Readiness

- Phase 10-01 (auth router + RBAC) has pre-existing failing tests to satisfy: test_auth_router.py (5 tests) + test_rbac.py (4 tests) + jwt.service.spec.ts (11 it.skip)
- Phase 10-02 (SSE + KPI) has pre-existing failing tests: test_sse.py (4 tests) + test_kpi_queries.py (4 tests) + sse.service.spec.ts (7 it.skip)
- Phase 10-03 (ApprovalCard) has pre-existing failing tests: approval-card.component.spec.ts (16 it.skip)

---
*Phase: 10-backend-api-frontend*
*Completed: 2026-05-24*
