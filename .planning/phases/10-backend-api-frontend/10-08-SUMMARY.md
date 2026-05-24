---
phase: 10
plan: "08"
subsystem: factory-ui
tags: [angular, sse, ng2-charts, kpi-dashboard, rbac, operator, manager]
dependency_graph:
  requires: ["10-06", "10-07"]
  provides: ["operator-area-wired", "manager-control-room-wired", "ng2-charts-lazy"]
  affects: ["app.routes.ts", "operator.component", "manager.component"]
tech_stack:
  added:
    - ng2-charts@8 (BaseChartDirective + selective Chart.js registration)
  patterns:
    - "@defer on viewport for lazy ChartsRow (SSR-safe)"
    - "isPlatformBrowser guard in ngOnInit for SSE connect"
    - "loadChildren feature routes replacing loadComponent placeholders"
    - "jest.config.ts transformIgnorePatterns for ESM ng2-charts/chart.js"
key_files:
  created:
    - apps/factory-ui/src/app/features/operator/operator.component.spec.ts
    - apps/factory-ui/src/app/features/operator/operator.routes.ts
    - apps/factory-ui/src/app/features/manager/charts-row.component.ts
    - apps/factory-ui/src/app/features/manager/manager.component.spec.ts
    - apps/factory-ui/src/app/features/manager/manager.routes.ts
  modified:
    - apps/factory-ui/src/app/features/operator/operator.component.ts
    - apps/factory-ui/src/app/features/manager/manager.component.ts
    - apps/factory-ui/src/app/app.routes.ts
    - apps/factory-ui/src/app/shared/approval-queue/approval-queue-feed.component.ts
    - apps/factory-ui/jest.config.ts
decisions:
  - "@defer on viewport chosen for ChartsRow lazy loading (SSR-safe, no separate lazy route needed)"
  - "Selective Chart.js registration: LineController+BarController+elements only (tree-shake T-10-08-02)"
  - "jest.config.ts transformIgnorePatterns extended to include ng2-charts, chart.js, lodash-es (ESM compat)"
  - "app.routes.ts /operator and /manager use loadChildren pointing to feature routes files"
metrics:
  duration: "~25 min"
  completed: "2026-05-24T19:25:00Z"
  tasks: 2
  files: 10
---

# Phase 10 Plan 08: Operator Area + Manager Control Room Summary

**One-liner:** Operator area (ApprovalQueueFeed focal + AlertFeed + 3-tile KPI row) and Manager control room (6-tile KPI grid + widgets + lazy ng2-charts OEE trend / Downtime Pareto) fully wired to SSE signals with RBAC guards, SSR-safe, 104 Jest specs green.

---

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Operator area (approval-queue focal + alert feed + KPI summary) | d4143b8 | operator.component.ts, operator.routes.ts, operator.component.spec.ts |
| 2 | Manager control room (6 KPI grid + widgets + charts) + route wiring | d78677c | manager.component.ts, charts-row.component.ts, manager.routes.ts, app.routes.ts |

---

## What Was Built

### Task 1: Operator Area

**OperatorComponent** (`sft-operator`) implements the operator's primary workspace:

- 2-column desktop layout (≥1024px): `ApprovalQueueFeed` as primary focal point (left), `AlertFeed` secondary (right)
- Compact KPI summary row: 3 tiles (OEE, Scrap Rate, Downtime) via `KpiTile`
- SSE live integration: `sseService.approvals()` and `sseService.alerts()` signals bound directly
- Disconnection banner after 5s of `sseService.disconnectedTooLong()` (10-UI-SPEC SSE contract)
- `data-testid="operator-area"` on root for Playwright E2E
- SSR guard: `connect()` called only in `ngOnInit` inside `isPlatformBrowser()` check

**operator.routes.ts**: lazy feature routes with `rbacGuard` (roles: `operator`).

### Task 2: Manager Control Room

**ManagerComponent** (`sft-manager`) implements the Sala Controllo:

- `DashboardHeader`: title "Sala Controllo" + ShiftSelector dropdown + DateRangePicker + SSE LiveIndicator (animated dot, `data-testid="sse-indicator"`)
- **`KPIGrid`** (`data-testid="kpi-grid"`): CSS Grid 3col/2col/1col responsive, 6 KpiTiles: OEE, MTTR, MTBF, Scrap Rate, Throughput, Downtime bound to `sseService.kpiSnapshot()` signal
- Widget row: `ApprovalQueueFeed` + `AlertFeed` in 2-column grid
- `@defer (on viewport)`: ChartsRow lazy-loaded only when scrolled into view (T-10-08-02 DoS mitigation)

**ChartsRowComponent** (`sft-charts-row`):

- OEE Trend: `ng2-charts@8 BaseChartDirective` with `type='line'`, 7-day data
- Downtime Pareto: `type='bar'` horizontal, top-5 causes
- Selective Chart.js registration: `LineController`, `BarController`, `LineElement`, `BarElement`, `PointElement`, `CategoryScale`, `LinearScale`, `Tooltip`, `Legend` only — tree-shakes unused controllers
- SSR guard: `isBrowser` flag set in `ngOnInit` via `isPlatformBrowser()`, canvas rendered only in browser
- `data-testid="charts-row"` on root

**manager.routes.ts**: lazy feature routes with `rbacGuard` (roles: `shift-supervisor`, `manager`).

**app.routes.ts**: `/operator` and `/manager` changed from `loadComponent` to `loadChildren` pointing to the real feature route files (replaces 10-04 placeholders). RBAC guards defined inside each feature routes file.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `aria-pressed` interpolation binding in ApprovalQueueFeedComponent**
- **Found during:** Task 1 test execution
- **Issue:** `aria-pressed="{{ activeFilter() === 'all' }}"` caused `NG0303: Can't bind to 'aria-pressed'` — Angular strict property check does not allow string interpolation on non-DOM properties
- **Fix:** Changed to `[attr.aria-pressed]="activeFilter() === 'all'"` (attribute binding pattern)
- **Files modified:** `apps/factory-ui/src/app/shared/approval-queue/approval-queue-feed.component.ts`
- **Commit:** d4143b8

**2. [Rule 3 - Blocking] Fixed Jest ESM transform for ng2-charts/chart.js/lodash-es**
- **Found during:** Task 2 test execution
- **Issue:** Jest could not parse `ng2-charts/fesm2022/ng2-charts.mjs` — `SyntaxError: Unexpected token 'export'`; the existing `transformIgnorePatterns` only matched `*.mjs` files directly but did not include the package directory paths
- **Fix:** Updated `jest.config.ts` `transformIgnorePatterns` to `['node_modules/(?!(.*\\.mjs$|ng2-charts|chart\\.js|lodash-es))']`
- **Files modified:** `apps/factory-ui/jest.config.ts`
- **Commit:** d78677c

---

## Threat Mitigations Applied

| Threat ID | Status | Implementation |
|-----------|--------|---------------|
| T-10-08-01 | Mitigated | `rbacGuard` in operator.routes.ts (role: operator) and manager.routes.ts (roles: shift-supervisor, manager) |
| T-10-08-02 | Mitigated | ChartsRow `@defer (on viewport)` + `isBrowser` guard + selective Chart.js registration |
| T-10-08-03 | Mitigated | Values from typed `KpiSnapshot` signal; text interpolation only (no [innerHTML]) |

---

## Verification Results

- `nx test ui-factory --passWithNoTests`: **104 tests, 8 suites — ALL PASS**
- `nx build ui-factory --configuration=development`: **BUILD SUCCESSFUL**
- `grep -q 'data-testid="kpi-grid"' manager.component.ts`: PASS
- `grep -q 'ng2-charts|BaseChartDirective' charts-row.component.ts`: PASS
- `grep -q 'approval-queue|ApprovalQueue' operator.component.ts`: PASS

---

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| OEE Trend data defaults to zeros | `charts-row.component.ts` — `trendData` input default | Real 7-day trend data comes from `GET /v1/kpi?period=week` (plan 10-02 backend). ChartsRow accepts `trendData` input — parent (ManagerComponent) will wire once the HTTP client call is added (deferred to 10-09 or a follow-up plan) |
| Downtime Pareto data defaults to zeros | `charts-row.component.ts` — `paretoData` input default | Same as above — real pareto data from backend |

Both stubs are intentional scaffolding: `ChartsRowComponent` accepts typed `OeeTrendPoint[]` and `DowntimePareto[]` inputs ready for wiring. The goal of plan 10-08 was to establish the ng2-charts integration and chart rendering pipeline; the data wire-up is follow-on work.

---

## Self-Check

### Created files exist:
- [x] `apps/factory-ui/src/app/features/operator/operator.component.ts` — FOUND
- [x] `apps/factory-ui/src/app/features/operator/operator.routes.ts` — FOUND
- [x] `apps/factory-ui/src/app/features/operator/operator.component.spec.ts` — FOUND
- [x] `apps/factory-ui/src/app/features/manager/manager.component.ts` — FOUND
- [x] `apps/factory-ui/src/app/features/manager/charts-row.component.ts` — FOUND
- [x] `apps/factory-ui/src/app/features/manager/manager.routes.ts` — FOUND
- [x] `apps/factory-ui/src/app/features/manager/manager.component.spec.ts` — FOUND

### Commits exist:
- [x] d4143b8 — feat(10-08): operator area wired to SSE
- [x] d78677c — feat(10-08): manager control room

## Self-Check: PASSED
