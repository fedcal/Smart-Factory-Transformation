---
phase: 10-backend-api-frontend
plan: 00a
subsystem: deps-baseline
tags: [dependencies, tailwind, angular-material, otel, sse-starlette, pyjwt, ng2-charts]
dependency_graph:
  requires: []
  provides:
    - backend-phase10-deps
    - frontend-phase10-deps
    - tailwind-material-baseline
  affects:
    - apps/api-gateway
    - apps/factory-ui
tech_stack:
  added:
    - PyJWT>=2.9,<3
    - sse-starlette>=2.3,<3
    - opentelemetry-api>=1.40,<2
    - opentelemetry-sdk>=1.40,<2
    - opentelemetry-instrumentation-fastapi>=0.55b0
    - "@angular/material ~19.2.0"
    - "@angular/cdk ~19.2.0"
    - "@angular/localize ~19.2.0"
    - "@angular/animations ~19.2.0"
    - "@jsverse/transloco ^8.3.0"
    - "ng2-charts ^8.0.0"
    - "chart.js ^4.5.1"
    - "tailwindcss ^4.3.0"
    - "@tailwindcss/postcss ^4.3.0"
    - "@nx/playwright 20.8.4"
    - "@playwright/test ^1.60.0"
  patterns:
    - Tailwind v4 CSS-first via @import (no config file)
    - Angular Material 3 MDC with provideAnimations()
    - SCSS @use before @import order (Dart Sass requirement)
    - @layer utilities for touch target overrides
key_files:
  created:
    - apps/factory-ui/postcss.config.json
  modified:
    - apps/api-gateway/pyproject.toml
    - uv.lock
    - package.json
    - package-lock.json
    - apps/factory-ui/src/styles.scss
    - apps/factory-ui/src/app/app.config.ts
    - apps/factory-ui/project.json
decisions:
  - "sse-starlette pinned to 2.x (not 3.x): 3.3+ requires starlette>=0.49.1 which conflicts with fastapi<0.117"
  - "SCSS @use before @import: Dart Sass requires @use first; Tailwind @import comes after Angular Material @use"
  - "provideAnimations() used instead of provideAnimationsAsync(): SSR-safe for current scaffold"
  - "prerender:false in development config: pre-existing NG0401 in empty scaffold (no routes defined yet); production prerender:true preserved"
metrics:
  duration: "~20min"
  completed: "2026-05-24"
  tasks_completed: 3
  files_changed: 8
---

# Phase 10 Plan 00a: Dependency Installation + Material/Tailwind Baseline Summary

**One-liner:** Backend PyJWT/SSE/OTEL + frontend Angular Material 19 + ng2-charts@8 + Tailwind v4 PostCSS baseline with 64px touch override, build verified.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add backend Phase 10 dependencies | 619072f | apps/api-gateway/pyproject.toml, uv.lock |
| 2 | Add frontend Phase 10 dependencies (Angular-19-compatible, pinned) | 148be79 | package.json, package-lock.json |
| 3 | Wire Tailwind v4 PostCSS + Angular Material baseline, verify 64px touch | cfe9de6 | postcss.config.json, styles.scss, app.config.ts, project.json |

## Verification Results

- Backend smoke test: `import jwt, sse_starlette, opentelemetry.instrumentation.fastapi; print('deps-ok')` — PASSED
- Frontend deps assertion: `frontend-deps-ok` — PASSED (ng2-charts is ^8.0.0, all required packages present)
- Build verification: `tailwind-material-ok` — PASSED (nx build ui-factory --configuration=development succeeded)
- postcss.config.json contains `@tailwindcss/postcss` — VERIFIED
- styles.scss contains `min-height: 64px` — VERIFIED

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] sse-starlette version conflict with fastapi<0.117**
- **Found during:** Task 1 — uv lock
- **Issue:** Plan specified `sse-starlette>=3.4,<4`. However, sse-starlette 3.3+ requires `starlette>=0.49.1`, which conflicts with `fastapi>=0.115,<0.117` (which requires `starlette<0.48`). The plan research noted "3.4.4 latest" but did not account for the starlette transitive constraint.
- **Fix:** Changed to `sse-starlette>=2.3,<3` (the 2.x series has no hard starlette dependency — starlette is optional/extras-only). Resolved to 2.4.1.
- **Files modified:** apps/api-gateway/pyproject.toml, uv.lock
- **Commit:** 619072f

**2. [Rule 1 - Bug] SCSS @use/@import order — Dart Sass requirement**
- **Found during:** Task 3 — first build attempt
- **Issue:** Plan Pattern 6 placed `@import "tailwindcss"` before `@use "@angular/material"`. Dart Sass requires all `@use` rules to appear before any other rules (including `@import`). Build failed with: `@use rules must be written before any other rules`.
- **Fix:** Reordered to `@use "@angular/material" as mat` first, then `@import "tailwindcss"`. The preflight conflict risk (Tailwind before Material) still exists but the Tailwind `@layer` cascade system mitigates it — the `@layer utilities` touch target override remains effective regardless of `@use` order since it targets MDC classes.
- **Files modified:** apps/factory-ui/src/styles.scss
- **Commit:** cfe9de6

**3. [Rule 2 - Missing critical functionality] provideAnimations() required by Angular Material**
- **Found during:** Task 3 — build time
- **Issue:** `@angular/material` requires animations to be provided. The scaffold `app.config.ts` had no animation provider. Without it, Material components warn/fail silently.
- **Fix:** Added `provideAnimations()` from `@angular/platform-browser/animations` + installed `@angular/animations ~19.2.0` (the peer dependency).
- **Files modified:** apps/factory-ui/src/app/app.config.ts, package.json, package-lock.json
- **Commit:** cfe9de6

**4. [Rule 3 - Blocking] Pre-existing NG0401 in SSR scaffold blocked build verification**
- **Found during:** Task 3 — all initial build attempts
- **Issue:** `NG0401: Missing Platform` during route extraction — a pre-existing bug in the Angular SSR scaffold. The scaffold has `"prerender": true` globally but an empty `appRoutes: Route[] = []`. The error existed BEFORE any of our changes (verified by reverting to stash).
- **Fix:** Added `"prerender": false` to the development configuration in `project.json`. Production `prerender: true` is preserved for when routes are defined in Wave 4+.
- **Files modified:** apps/factory-ui/project.json
- **Commit:** cfe9de6

## Known Stubs

None — this plan only installs dependencies and wires the toolchain baseline. No UI components or data wiring yet.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced in this plan. All changes are to package manifests and CSS/build configuration.

## Self-Check: PASSED

- [x] apps/api-gateway/pyproject.toml — contains sse-starlette, PyJWT, opentelemetry entries
- [x] uv.lock — updated (102 lines added)
- [x] package.json — contains ng2-charts, @angular/material, tailwindcss, @jsverse/transloco, etc.
- [x] package-lock.json — updated
- [x] apps/factory-ui/postcss.config.json — created, contains @tailwindcss/postcss
- [x] apps/factory-ui/src/styles.scss — contains tailwindcss import and min-height: 64px
- [x] apps/factory-ui/src/app/app.config.ts — contains provideAnimations()
- [x] apps/factory-ui/project.json — development config has prerender:false
- [x] Commit 619072f exists (Task 1)
- [x] Commit 148be79 exists (Task 2)
- [x] Commit cfe9de6 exists (Task 3)
- [x] .claude/ directory never staged
