---
phase: 10-backend-api-frontend
plan: "04"
subsystem: factory-ui
tags: [angular, material, tokens, theming, shell, routing, wcag-aa, ssr]
dependency_graph:
  requires: ["10-00a"]
  provides: ["AppShell", "design-tokens", "dark-light-theme", "persona-routes", "rbac-guard-scaffold"]
  affects: ["10-05", "10-06", "10-07", "10-08"]
tech_stack:
  added:
    - "Angular Material 19.2 mat.define-theme() with azure palette"
    - "Inter variable font (Google Fonts, font-display: swap)"
    - "CSS custom properties SFT design system"
  patterns:
    - "CSS custom property override pattern for Material M3 tokens"
    - "Standalone lazy-loaded components (loadComponent)"
    - "RBAC canActivate guard with InjectionToken for decoupled service"
    - "isPlatformBrowser SSR guard pattern"
key_files:
  created:
    - apps/factory-ui/src/styles/_tokens.scss
    - apps/factory-ui/src/styles/_typography.scss
    - apps/factory-ui/src/styles/_theme.dark.scss
    - apps/factory-ui/src/styles/_theme.light.scss
    - apps/factory-ui/src/app/shell/app-shell.component.ts
    - apps/factory-ui/src/app/shell/top-bar.component.ts
    - apps/factory-ui/src/app/shell/nav-rail.component.ts
    - apps/factory-ui/src/app/shell/bottom-nav.component.ts
    - apps/factory-ui/src/app/core/auth/rbac.guard.ts
    - apps/factory-ui/src/app/auth/login.component.ts
    - apps/factory-ui/src/app/features/operator/operator.component.ts
    - apps/factory-ui/src/app/features/technician/technician.component.ts
    - apps/factory-ui/src/app/features/manager/manager.component.ts
    - apps/factory-ui/src/app/features/admin/admin.component.ts
    - apps/factory-ui/src/app/features/demo/demo.component.ts
  modified:
    - apps/factory-ui/src/styles.scss
    - apps/factory-ui/src/app/app.routes.ts
    - apps/factory-ui/src/index.html
decisions:
  - "mat.define-theme() with azure palette; SFT hex values applied via CSS custom property override (--mat-sys-* tokens)"
  - "rbac.guard.ts uses RBAC_GUARD_SERVICE_TOKEN InjectionToken so 10-05 (JwtService) can fill the implementation without changing route definitions"
  - "Feature area components are minimal placeholders compiling now; 10-07 replaces with real UI"
  - "TopBar uses ng-content slots so 10-05/10-06 real components (LanguageToggle/ThemeToggle/UserChip) slot in without AppShell changes"
  - "BottomNav capped at 4 items (UI-SPEC constraint); slice(0,4) in template"
  - "isPlatformBrowser guards all router.events subscriptions and DOM manipulation (theme toggle)"
metrics:
  duration: "45min"
  completed_date: "2026-05-24"
  tasks_completed: 3
  files_created: 15
  files_modified: 3
---

# Phase 10 Plan 04: Frontend Foundation — Design Tokens, Themes, AppShell, Persona Routes — Summary

**One-liner:** SFT design token CSS custom properties (dark/light WCAG AA palettes) + Angular Material 19 mat.define-theme() + Inter typography + responsive AppShell (TopBar/NavigationRail/BottomNav) + lazy persona routes with RBAC guard scaffold.

---

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Design tokens + dark/light Material themes + Inter typography | `780ac1b` |
| 2 | AppShell + TopBar + NavigationRail + BottomNav | `29669a3` |
| 3 | Persona route map + RBAC guard scaffold + login page | `bfb54ec` |

---

## What Was Built

### Task 1 — Design Tokens, Typography, Themes

**`_tokens.scss`:** CSS custom properties at `:root` (dark default, SSR-safe):
- Surfaces: `--sft-surface` (#121418), `--sft-surface-2` (#1C1F26), `--sft-surface-card` (#252932)
- Accent: `--sft-accent` (#3B82F6, ≈5.3:1 WCAG AA)
- Text: `--sft-text-primary` (#F0F2F5, ≈14.8:1 AAA), `--sft-text-secondary` (#9BA3B2, ≈5.1:1 AA)
- Semantic: destructive, success, warning (all WCAG AA verified)
- Light palette under `[data-theme="light"]` / `.theme-light` — accent #2563EB (≈5.9:1 AA)
- Spacing scale: 4/8/16/24/32/48/64px (8-pt system)
- Type tokens: 28/20/16/14px
- Component dimensions: topbar 64px, nav-rail 72px/56px, touch target 64px

**`_typography.scss`:** Inter variable font via Google Fonts, 4 type roles (display/heading/body/label), 2 weights only (400/600), global min-size 14px enforcement.

**`_theme.dark.scss` / `_theme.light.scss`:** `mat.define-theme()` with azure palette; SFT CSS custom properties override `--mat-sys-*` tokens for complete Material component coverage.

**`styles.scss`:** `@use` partials in correct order (before `@import tailwindcss`); 64px touch target override layer preserved from 10-00a.

**`index.html`:** `lang="it"` (SSR Italian default per UI-SPEC), title updated.

### Task 2 — AppShell

**Responsive layout:**
- ≥1024px: NavigationRail 72px + 2-column content
- 768–1023px: NavigationRail 56px (icon-only condensed)
- <768px: BottomNav 64px + full-width content

**TopBar (64px):** logo, area title (signal, updates on route change), SSE indicator (animated dot, pulse animation), language toggle slot, theme toggle slot (stub), user chip slot. All slots use `ng-content select` so 10-05/10-06 real components slot in without AppShell changes. `data-testid` attributes on SSE indicator, language toggle, theme toggle.

**NavigationRail:** 5 persona nav items with 64px min-height, active left accent indicator, uppercase labels (AREA OPERATORE etc.), tooltip in compact mode, `routerLinkActive` styling.

**BottomNav:** max 4 items, 64px height, icon + small label.

**SSR-safe:** All browser API calls (router.events subscription, DOM theme toggle) wrapped in `isPlatformBrowser()`.

### Task 3 — Persona Routes

**`app.routes.ts`:**
- `/auth/login` — public, lazy LoginComponent
- `/` → AppShell layout route with 5 lazy persona children
- `/operator` (canActivate: rbacGuard, roles: ['operator'])
- `/technician` (canActivate: rbacGuard, roles: ['technician'])
- `/manager` (canActivate: rbacGuard, roles: ['shift-supervisor', 'manager'])
- `/admin` (canActivate: rbacGuard, roles: ['admin'])
- `/demo` (canActivate: rbacGuard, roles: [] = all authenticated)
- `**` → redirect to `/auth/login`

**`rbac.guard.ts`:** `CanActivateFn` scaffold; `RBAC_GUARD_SERVICE_TOKEN` InjectionToken stable import path; reads `route.data.roles`; redirects to `/auth/login` on auth failure; falls through to `true` when service not yet provided (10-04 mode). Plan 10-05 fills the JwtService implementation.

**`login.component.ts`:** 400px centered card, mat-form-fields, 64px CTA, dev-mode persona quick-select chips (5 seeded users from UI-SPEC).

---

## Deviations from Plan

### Auto-fixed Issues

None.

### Design Decisions Recorded

1. `mat.define-theme()` with `azure` palette provides the M3 color system; SFT hex values are applied via `--mat-sys-*` CSS custom property overrides rather than custom palette generation — this avoids the complexity of creating a full M3-compatible palette map from SFT hex values and achieves the same visual result.

2. `RBAC_GUARD_SERVICE_TOKEN` InjectionToken created as a stable contract boundary between 10-04 (route definitions) and 10-05 (JwtService implementation) — no circular dependency risk.

3. Feature area components are minimal placeholder stubs (one heading + description) that compile cleanly. Plan 10-07 replaces them with real feature UI. This avoids blocking the routing from compiling.

4. TopBar uses Angular `ng-content select="[slot=...]"` projection for LanguageToggle, ThemeToggle, UserChip — the shell does not need modification when 10-05/10-06 provide real components.

---

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `isDevMode = true` hardcoded | `login.component.ts` | Environment check wired in 10-05 |
| `sseConnected = signal(false)` | `app-shell.component.ts` | SseService wired in 10-05 |
| `rbacGuard` returns `true` (scaffold) | `rbac.guard.ts` | JwtService implementation in 10-05 |
| Feature area components are placeholder UI | `features/*/component.ts` | Real UI in 10-07 |
| TopBar lang/theme/user slots show stubs | `top-bar.component.ts` | Real components in 10-05/10-06 |

These stubs are intentional for 10-04 scope. They do not prevent the plan goal (AppShell renders, routes compile, tokens apply). Future plans fill each stub.

---

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| No new surface | All files | No new network endpoints, auth paths, or schema changes introduced. RBAC guard scaffold is pure client-side routing — no server-side enforcement added in this plan (T-10-04-02 mitigation deferred to 10-05 as planned). |

T-10-04-01 (SSR crash from browser API): mitigated — all browser API calls are wrapped in `isPlatformBrowser()` checks. No `localStorage`, `EventSource`, or `window` accessed in constructors.

---

## Self-Check: PASSED

Files verified:
- `apps/factory-ui/src/styles/_tokens.scss` — exists, contains `--sft-surface`
- `apps/factory-ui/src/styles/_typography.scss` — exists
- `apps/factory-ui/src/styles/_theme.dark.scss` — exists
- `apps/factory-ui/src/styles/_theme.light.scss` — exists
- `apps/factory-ui/src/app/shell/app-shell.component.ts` — exists, contains `router-outlet`
- `apps/factory-ui/src/app/app.routes.ts` — exists, contains `operator`, `demo`
- `apps/factory-ui/src/app/core/auth/rbac.guard.ts` — exists

Commits verified: `780ac1b`, `29669a3`, `bfb54ec` — all on `master` branch.

Build: `nx build ui-factory --configuration=development` — SUCCESS (SCSS deprecation warnings only, no errors).
