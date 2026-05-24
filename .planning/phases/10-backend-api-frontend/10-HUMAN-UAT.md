---
status: partial
phase: 10-backend-api-frontend
source: [10-VERIFICATION.md, 10-UI-REVIEW.md]
started: 2026-05-24T23:00:00Z
updated: 2026-05-24T23:00:00Z
---

## Current Test

[awaiting human testing — requires live stack: Docker + browser]

## Tests

### 1. Playwright E2E HITL flow (live)
expected: `nx e2e ui-factory-e2e` against a live Angular + FastAPI + TimescaleDB stack passes the 8-step HITL approval flow (login → dashboard ≥6 KPI → pending card → evidence → motivation → approve → approved → audit record). Requires an OS with Playwright Chromium support.
result: [pending]

### 2. i18n IT/EN toggle in-browser (no reload)
expected: in the running app, toggling EN switches all visible text without a page reload (transloco), IT is default. (UI-07 / SC-2)
result: [pending]

### 3. WCAG AA contrast (formal)
expected: run an automated contrast checker (axe/Lighthouse) on dark + light themes — all text meets AA.
result: [pending]

### 4. SSE integration vs real TimescaleDB
expected: with the backend + TimescaleDB up, /v1/stream/kpi emits live kpi_update events; /v1/stream/approvals + /v1/stream/alerts push events; rate-limit caps alerts at 12/h/persona.
result: [pending]

### 5. Migration 013 auth_users on TimescaleDB
expected: `make migrate-timescale` applies 013 idempotently; auth schema + 5 seeded persona users present.
result: [pending]

### 6. SSR first-load + hydration
expected: app renders via SSR on first load (view-source has content) then hydrates to SPA; no console hydration errors. (SC-2)
result: [pending]

### 7. Persona walkthrough demo (live)
expected: /demo 4-step stepper navigates operator/supervisor/technician/CIO views with no broken routes / missing data. (SC-5)
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
