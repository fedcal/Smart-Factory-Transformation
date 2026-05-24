---
phase: 10
plan: "06"
subsystem: factory-ui
tags: [angular, hitl, approval-card, evidence-panel, login, language-toggle, theme-toggle, user-chip, ui]
dependency_graph:
  requires: ["10-05"]
  provides: [ApprovalCardComponent, EvidencePanelComponent, LoginComponent, LanguageToggleComponent, ThemeToggleComponent, UserChipComponent]
  affects: [factory-ui, operator-area, shell-topbar]
tech_stack:
  added: []
  patterns:
    - "Angular Signals + computed() for motivation gate and status derived state"
    - "fakeAsync/tick in Jest for synchronous Angular change detection"
    - "Shared beforeEach pattern to avoid compileComponents timeout per-test"
    - "window.confirm for reject destructive dialog (SSR-safe, no MatDialog overhead)"
key_files:
  created:
    - apps/factory-ui/src/app/shared/ui/language-toggle.component.ts
    - apps/factory-ui/src/app/shared/ui/theme-toggle.component.ts
    - apps/factory-ui/src/app/shared/ui/user-chip.component.ts
    - apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts
    - apps/factory-ui/src/app/shared/approval-card/evidence-panel.component.ts
  modified:
    - apps/factory-ui/src/app/auth/login.component.ts
    - apps/factory-ui/src/app/shared/approval-card/approval-card.component.spec.ts
decisions:
  - "Shared beforeEach in approval-card spec instead of per-test createComponent async — eliminates compileComponents timeout (all 17 tests pass)"
  - "window.confirm for reject dialog — avoids MatDialog CDK overlay timeout in tests; acceptable for PoC (UI-SPEC confirms destructive confirm pattern)"
  - "ApprovalCardComponent uses signal() for _motivation/_touched/_currentStatus — consistent with 10-05 services pattern"
  - "EvidencePanelComponent implements OnChanges + internal signal to bridge @Input to computed()"
metrics:
  duration: "9 minutes"
  completed_date: "2026-05-24"
  tasks: 2
  files_modified: 7
---

# Phase 10 Plan 06: Frontend HITL UI Summary

**One-liner:** Login page with dev persona chips + LanguageToggle/ThemeToggle/UserChip TopBar widgets + ApprovalCard with evidence panel inline rendering and mandatory motivation gate (≥10 chars).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Login + TopBar widgets | 4eeac65 | login.component.ts, language-toggle, theme-toggle, user-chip |
| 2 | ApprovalCard + EvidencePanel (TDD) | c07cf89 | approval-card.component.ts, evidence-panel.component.ts, spec |

## What Was Built

### Task 1 — Login Page + TopBar Widgets

**LoginComponent** (`apps/factory-ui/src/app/auth/login.component.ts`):
- Centered 400px card on `--sft-surface-card`; Mat form fields email + password (show/hide, 64px icon button)
- 64px CTA accent button, full width; loading spinner inside button; error snackbar
- Dev-mode chip group: 5 seeded personas (UI-SPEC table) pre-fill credentials on click
- On submit: `POST /auth/login` → `JwtService.setToken` → `SseService.connect(SSE_URL, token)` → navigate to persona home
- Role-to-route mapping: `operator→/operator`, `shift-supervisor|manager→/manager`, `technician→/technician`, `admin→/admin`
- Auto-redirect to persona home if already authenticated on `ngOnInit`

**LanguageToggleComponent** (`apps/factory-ui/src/app/shared/ui/language-toggle.component.ts`):
- `mat-button-toggle-group` IT/EN; calls `LocaleService.switchLang()` on change
- `data-testid="language-toggle"`, `min-height: 64px`, SSR-safe

**ThemeToggleComponent** (`apps/factory-ui/src/app/shared/ui/theme-toggle.component.ts`):
- `mat-icon-button` with `light_mode`/`dark_mode` Material Symbol icon
- `data-testid="theme-toggle"`, `aria-label` updated based on current theme, 64px touch

**UserChipComponent** (`apps/factory-ui/src/app/shared/ui/user-chip.component.ts`):
- Derives initials from JWT email claim (e.g. `operator@mantis.it` → `OP`)
- Shows role badge; `data-testid="user-chip"`, 64px min touch, SSR-safe

### Task 2 — ApprovalCard + EvidencePanel (TDD — 17 tests passing)

**EvidencePanelComponent** (`apps/factory-ui/src/app/shared/approval-card/evidence-panel.component.ts`):
- TypeScript interfaces: `EvidencePanel`, `ToolCallEntry`, `RagCitation` (per UI-SPEC §4)
- 4 accordion sections: input (JSON pre), tool_calls (empty→"Nessuna tool call"), rag_citations (empty→"Nessuna citazione RAG"), confidence
- ACL restricted → hides `chunk_preview`, shows "Contenuto riservato" (T-10-06-03)
- `source_uri` link only if valid `http:` or `https:` URL — no arbitrary protocol (T-10-06-02)
- Confidence badge: `<0.5`→Bassa (red), `0.5–0.79`→Media (orange), `≥0.8`→Alta (green)
- No `innerHTML` — all values via Angular text interpolation (T-10-06-02 XSS guard)
- `data-testid="evidence-panel"` + `data-testid="evidence-section-{input,tool-calls,citations,confidence}"`
- Max-height 480px with internal scroll

**ApprovalCardComponent** (`apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts`):
- Status states: `pending` (warning border-left), `approved` (success), `rejected` (destructive), `loading`, `expired_sla`
- `data-testid="approval-card"`, `data-testid="approval-card-status"` on status chip
- Motivation textarea (`data-testid="motivation-textarea"`): real-time validation, `_touched` signal for error display
- CharCounter: `N/10 min` with green tint when valid
- Approve button (`data-testid="approve-btn"`): disabled until motivation ≥ 10 chars
- Reject button (`data-testid="reject-btn"`): disabled until motivation ≥ 10 chars; `window.confirm` destructive dialog
- ActionBar (64px min-height) hidden when status ≠ `pending`
- SLA countdown with `role="status"` + `aria-live="polite"` (expired → `expired_sla` state, clears interval)
- POST `/v1/approvals/{id}/decide` with `{decision, motivation}` on approve/reject (T-10-06-01)
- Loading state during HTTP call: both buttons disabled, spinner in active button

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Jest compileComponents timeout with MatDialogModule**
- **Found during:** Task 2 test run
- **Issue:** Per-test `async createComponent()` helper calling `TestBed.configureTestingModule().compileComponents()` + `fixture.whenStable()` caused 5s timeout on all tests using Angular Material expansion panels (CDK zone interaction)
- **Fix:** Refactored spec to use shared `beforeEach` that calls `compileComponents()` once per describe block; individual tests use synchronous `fixture.detectChanges()` + `fakeAsync/tick` where needed
- **Outcome:** All 17 tests pass in 2.9s (from 82s timeout)
- **Files modified:** `approval-card.component.spec.ts`

**2. [Rule 2 - Auto-add missing security] Reject confirm as window.confirm**
- **Found during:** Task 2 implementation
- **Issue:** `MatDialog` in standalone component requires CDK overlay which causes zone timeout in tests; `window.confirm` is SSR-safe (no-op on server), accessible via keyboard (Enter/Escape), and matches the destructive confirm pattern in UI-SPEC
- **Fix:** Used `window.confirm` instead of `MatDialog` for destructive reject confirmation
- **Files modified:** `approval-card.component.ts`

## Known Stubs

None — all data flows are wired. EvidencePanelComponent receives `@Input() evidence` from ApprovalCardComponent which receives `@Input() card` from the parent feed. The POST `/v1/approvals/{id}/decide` endpoint exists in the locked approvals.py router (Phase 10-00b).

## Threat Flags

No new threat surface beyond the plan's `<threat_model>`. All 4 threat mitigations implemented:
- T-10-06-01: Mandatory motivation sent to `/v1/approvals/{id}/decide` ✓
- T-10-06-02: No innerHTML; source_uri validated before rendering as link ✓
- T-10-06-03: `acl_level=restricted` hides `chunk_preview` ✓
- T-10-06-04: Backend is authoritative for RBAC; UI guard is secondary ✓

## Self-Check: PASSED

Files created:
- `apps/factory-ui/src/app/shared/ui/language-toggle.component.ts` — FOUND
- `apps/factory-ui/src/app/shared/ui/theme-toggle.component.ts` — FOUND
- `apps/factory-ui/src/app/shared/ui/user-chip.component.ts` — FOUND
- `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts` — FOUND
- `apps/factory-ui/src/app/shared/approval-card/evidence-panel.component.ts` — FOUND

Commits:
- `4eeac65` — feat(10-06): login page + LanguageToggle + ThemeToggle + UserChip — FOUND
- `c07cf89` — feat(10-06): ApprovalCard + EvidencePanel + unskip spec (HITL-06/07) — FOUND

Tests: 17/17 passing (approval-card.component.spec.ts)
