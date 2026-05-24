---
phase: 10
plan: "07"
subsystem: factory-ui
tags: [frontend, angular, signals, kpi, alert-feed, approval-queue, cdk, virtual-scroll, sse, tdd]
dependency_graph:
  requires: ["10-05", "10-06", "10-00b"]
  provides: ["kpi-tile", "alert-feed", "approval-queue-feed"]
  affects: ["operator dashboard", "manager dashboard", "playwright-e2e"]
tech_stack:
  added:
    - "@angular/cdk/scrolling (ScrollingModule — cdk-virtual-scroll-viewport)"
  patterns:
    - "Angular 17+ input() signal API for reactive computed()"
    - "Pure threshold function computeKpiStatus() (exported, unit-testable)"
    - "CDK VirtualScroll for bounded queue rendering (T-10-07-03)"
    - "text interpolation only — no [innerHTML] (T-10-07-02)"
key_files:
  created:
    - apps/factory-ui/src/app/shared/kpi-tile/kpi-tile.component.ts
    - apps/factory-ui/src/app/shared/kpi-tile/kpi-tile.component.spec.ts
    - apps/factory-ui/src/app/shared/alert-feed/alert-feed.component.ts
    - apps/factory-ui/src/app/shared/alert-feed/alert-feed.component.spec.ts
    - apps/factory-ui/src/app/shared/approval-queue/approval-queue-feed.component.ts
  modified: []
decisions:
  - "input() signal API (Angular 17+) instead of @Input+ngOnChanges for reactive computed() — avoids manual signal bridging"
  - "computeKpiStatus() exported pure function — directly testable, no component instantiation needed"
  - "Throughput uses ratio (value/baseline) against 1.0/0.9 bounds — aligns with UI-SPEC percentage-of-baseline language"
  - "AlertFeed visibleAlerts() caps at 12 (RATE_LIMIT) newest-first — mirrors HITL-10 12/hr backend limit"
  - "ApprovalQueueFeed maps ApprovalPendingEvent → ApprovalCardData locally — queue never stores full card data in SSE"
  - "apostrophe in aria-label template expression escaped by rewriting to avoid single-quote interpolation parse error"
metrics:
  duration: "18min"
  completed_date: "2026-05-24"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
---

# Phase 10 Plan 07: Frontend Feed Components (KpiTile + AlertFeed + ApprovalQueueFeed) Summary

**One-liner:** KpiTile with 6-KPI threshold-colored status bars (input() signals + computed()), AlertFeed with HITL-10 rate-limit banner (aria-live polite), and CDK virtual-scroll ApprovalQueueFeed wrapping ApprovalCard from 10-06.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | KpiTile (threshold status, SSE-live) | `99741ce` | kpi-tile.component.ts, kpi-tile.component.spec.ts |
| 2 | AlertFeed + ApprovalQueueFeed | `52f073b` | alert-feed.component.ts, alert-feed.component.spec.ts, approval-queue-feed.component.ts |

---

## Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| kpi-tile.component.spec.ts | 35 | PASS |
| alert-feed.component.spec.ts | 9 | PASS |
| approval-queue (passWithNoTests) | 0 | PASS |

**Total: 44 tests, 44 passed.**

---

## Verification

- KpiTile + AlertFeed specs pass (44 tests).
- ApprovalQueueFeed contains `cdk-virtual-scroll-viewport` (verified via grep).
- data-testid coverage: `kpi-tile-oee/mttr/mtbf/scrap_rate/throughput/downtime`, `alert-feed`, `rate-limit-banner`, `approval-queue-feed`.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Angular @Input property assignment does not trigger computed() signals**
- **Found during:** Task 1, GREEN phase
- **Issue:** `fixture.componentInstance.key = key` (direct property assignment) does not update Angular `input()` signals in the test harness; computed() returned stale values.
- **Fix:** Switched component to `input()` signal API (Angular 17+) and updated spec to use `fixture.componentRef.setInput()`. input() signals are reactive by default without ngOnChanges.
- **Files modified:** kpi-tile.component.ts (full rewrite from @Input+ngOnChanges to input()), kpi-tile.component.spec.ts (createFixture helper)
- **Commit:** `99741ce`

**2. [Rule 1 - Bug] Italian apostrophe in Angular template aria-label binding**
- **Found during:** Task 2, GREEN phase
- **Issue:** `[attr.aria-label]="'Vai all\'approvazione per: ' + alert.message"` caused Angular JIT parser error — the escaped apostrophe inside the single-quoted expression is invalid.
- **Fix:** Rewrote aria-label to `"'Vai alla approvazione per: ' + alert.message"` (avoiding the apostrophe issue entirely).
- **Files modified:** alert-feed.component.ts
- **Commit:** `52f073b`

---

## Known Stubs

**ApprovalQueueFeed — "Solo miei" filter:**
- File: `apps/factory-ui/src/app/shared/approval-queue/approval-queue-feed.component.ts`
- Line: `filteredCards` computed, filter `'mine'` branch
- Reason: The "Solo miei" filter requires authenticated user context (user ID) which is not available in the minimal ApprovalPendingEvent SSE payload. Filter chip is rendered and interactive but has same behavior as "Tutti". Wiring requires integration with JwtService (10-01) — tracked for future plan.

---

## Threat Flags

No new unplanned threat surface introduced. All T-10-07-* threats addressed:

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-10-07-01 (DoS — alert flood) | visibleAlerts() capped at RATE_LIMIT=12 | Mitigated |
| T-10-07-02 (XSS via alert message) | Text interpolation only, no [innerHTML] | Mitigated |
| T-10-07-03 (DoS — large queue) | CDK cdk-virtual-scroll-viewport bounds rendered cards | Mitigated |

---

## Self-Check: PASSED

- [x] `apps/factory-ui/src/app/shared/kpi-tile/kpi-tile.component.ts` — FOUND
- [x] `apps/factory-ui/src/app/shared/kpi-tile/kpi-tile.component.spec.ts` — FOUND
- [x] `apps/factory-ui/src/app/shared/alert-feed/alert-feed.component.ts` — FOUND
- [x] `apps/factory-ui/src/app/shared/alert-feed/alert-feed.component.spec.ts` — FOUND
- [x] `apps/factory-ui/src/app/shared/approval-queue/approval-queue-feed.component.ts` — FOUND
- [x] Commit `99741ce` — FOUND
- [x] Commit `52f073b` — FOUND
