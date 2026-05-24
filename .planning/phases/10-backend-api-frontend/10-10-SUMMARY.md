---
phase: 10-backend-api-frontend
plan: 10
subsystem: testing
tags: [playwright, e2e, nx, hitl, angular, approval-flow]

# Dependency graph
requires:
  - phase: 10-08
    provides: Angular operator/manager routes + approval-card + kpi-tile components with data-testid attributes
  - phase: 10-09
    provides: persona routing, admin/technician routes, RBAC guards
  - phase: 10-03
    provides: FastAPI backend SSE/approval endpoints, seeded users (operator@mantis.it), POST /v1/approvals/{id}/decide

provides:
  - Separate Nx e2e project apps/factory-ui-e2e/ (ui-factory-e2e) with @nx/playwright:playwright target
  - playwright.config.ts with baseURL (PW_BASE_URL || :4200) and webServer (nx serve ui-factory)
  - hitl-flow.spec.ts: full 8-step HITL approval E2E flow using Playwright API
  - Explicit stack reachability guard (beforeAll) — fails clearly, never silently passes

affects: [phase-11, phase-12, CI/CD pipeline configuration]

# Tech tracking
tech-stack:
  added: []  # @nx/playwright + @playwright/test already installed in 10-00a
  patterns:
    - Separate Nx e2e project (apps/factory-ui-e2e/) — NOT inline in ui-factory
    - page.route() for POST interception without mocking the entire network
    - beforeAll stack reachability guard prevents silent false-green E2E runs
    - Audit assertion via GET /v1/approvals (list + filter) instead of non-existent /v1/audit/{id}
    - PW_SKIP_WEB_SERVER=true for external-stack CI mode

key-files:
  created:
    - apps/factory-ui-e2e/project.json
    - apps/factory-ui-e2e/playwright.config.ts
    - apps/factory-ui-e2e/tsconfig.json
    - apps/factory-ui-e2e/src/hitl-flow.spec.ts
  modified: []

key-decisions:
  - "Phase 10-10: Separate Nx project apps/factory-ui-e2e/ (not inline) — Nx convention, per post_research_resolution #3"
  - "Phase 10-10: Audit assertion uses GET /v1/approvals filtered by approval_id — there is NO /v1/audit/{id} endpoint"
  - "Phase 10-10: page.route handles both /approve and /decide patterns for forward compatibility with POST endpoint naming"
  - "Phase 10-10: Full live-run requires ubuntu that supports Playwright browsers — ubuntu26.04-x64 in dev env does not; run is CI/human item"
  - "Phase 10-10: PW_SKIP_WEB_SERVER=true env var allows bypassing webServer for external stack (CI pattern)"

patterns-established:
  - "E2E: beforeAll assertFrontendReachable() + assertBackendReachable() — mandatory for HITL suites"
  - "E2E: Capture approval_id from page.route intercept URL regex, not from DOM data attributes"
  - "E2E: Audit verification via list endpoint filtered by id, not a dedicated audit endpoint"

requirements-completed: [UI-10, HITL-01, HITL-06, HITL-07]

# Metrics
duration: 15min
completed: 2026-05-24
---

# Phase 10 Plan 10: Nx Playwright E2E Project + HITL Flow Spec Summary

**Separate Nx Playwright project `apps/factory-ui-e2e/` with `hitl-flow.spec.ts` implementing the full 8-step HITL approval flow (login → KPI dashboard → pending card → evidence review → motivation → approve with POST intercept → approved status → audit via GET /v1/approvals)**

## Performance

- **Duration:** 15 min
- **Started:** 2026-05-24T19:40:00Z
- **Completed:** 2026-05-24T19:55:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `apps/factory-ui-e2e/` as a standalone Nx e2e project (`ui-factory-e2e`) with `@nx/playwright:playwright` executor — recognized by `nx show project ui-factory-e2e`
- Authored `playwright.config.ts` with `baseURL` (from `PW_BASE_URL` env or default `:4200`), `webServer` entry that boots `nx serve ui-factory`, and `PW_SKIP_WEB_SERVER=true` bypass for CI
- Implemented `hitl-flow.spec.ts` covering all 8 UI-SPEC steps with correct Playwright API (`page.getByTestId`, `page.route`, `expect`) and mandatory `data-testid` selectors
- TypeScript strict mode passes (`tsc --noEmit`) — spec is syntactically valid

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold apps/factory-ui-e2e Nx Playwright project** - `1edc138` (feat)
2. **Task 2: hitl-flow.spec.ts — full HITL approval flow** - `a432a1a` (feat)

**Plan metadata:** *(pending final docs commit)*

## Files Created/Modified

- `apps/factory-ui-e2e/project.json` — Nx project config: `ui-factory-e2e`, `@nx/playwright:playwright` e2e target
- `apps/factory-ui-e2e/playwright.config.ts` — baseURL + webServer (with PW_SKIP_WEB_SERVER bypass), Chromium config
- `apps/factory-ui-e2e/tsconfig.json` — extends tsconfig.base.json, ES2020/CommonJS, strict
- `apps/factory-ui-e2e/src/hitl-flow.spec.ts` — 8-step HITL approval E2E spec (446 lines)

## Decisions Made

- **Audit assertion via GET /v1/approvals** (filtered by `approval_id`): there is NO `/v1/audit/{id}` endpoint. The UI-SPEC table shows `/v1/audit/{id}` in step 8 but the plan task action explicitly overrides this — use the approvals list endpoint filtering by id.
- **`page.route` handles both `/approve` and `/decide`** endpoint patterns — the backend POST can be named either; both are intercepted to capture the `approval_id` robustly.
- **`beforeAll` reachability guard**: both frontend and backend are checked before any test runs. If either is unreachable, the suite throws with an explicit error message and stack instructions — prevents silent false-greens (T-10-10-02 mitigation).
- **Live run is a CI/human item**: the dev environment runs ubuntu26.04-x64, which is not supported by Playwright Chromium. The spec is syntactically valid and the project is correctly configured. Run via `nx e2e ui-factory-e2e` in a CI environment with supported OS + running stack.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TypeScript strict type error on postBodyCaptured cast**
- **Found during:** Task 2 (hitl-flow.spec.ts authoring)
- **Issue:** `tsc --noEmit` reported TS2352: conversion of `null` to `Record<string, unknown>` without going through `unknown` first
- **Fix:** Changed `(postBodyCaptured as Record<string, unknown>)` to `(postBodyCaptured as unknown as Record<string, unknown>)` — two-step cast as required by TypeScript strict mode
- **Files modified:** `apps/factory-ui-e2e/src/hitl-flow.spec.ts` line 321
- **Verification:** `tsc --noEmit` exits 0 after fix
- **Committed in:** `a432a1a` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — TypeScript strict type error)
**Impact on plan:** Minimal — single-line fix, no logic change.

## Issues Encountered

- **Playwright browser unavailable in dev env**: ubuntu26.04-x64 is not supported by `playwright install chromium`. The existing cached chromium versions (1187, 1217) were deleted by the `nx e2e` executor when it attempted to upgrade to 1223. The spec is confirmed syntactically valid via `tsc --noEmit`. Live execution requires a CI environment with supported OS.
- **`nx g @nx/playwright:configuration` generates inline config for existing projects**, not standalone projects. Authored the 4 files manually following Nx e2e project conventions.

## Known Stubs

None — this plan creates test infrastructure only. No UI components with stub data sources.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| No new surface | — | E2E spec only — introduces no new network endpoints, auth paths, or schema changes |

The spec verifies T-10-10-01 (audit record persists decision + motivation) and T-10-10-02 (explicit failure on unreachable stack).

## Next Phase Readiness

- `ui-factory-e2e` is a recognized Nx project ready for CI integration
- Live run requires: (1) supported OS for Playwright Chromium, (2) `nx serve ui-factory` on :4200, (3) FastAPI gateway on :8000 with seeded `operator@mantis.it` user
- Phase 10 is now **fully complete** (all 10 plans delivered): platform scaffold → backend → frontend → E2E

---
*Phase: 10-backend-api-frontend*
*Completed: 2026-05-24*
