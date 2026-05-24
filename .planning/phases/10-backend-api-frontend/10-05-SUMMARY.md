---
phase: "10"
plan: "05"
subsystem: "factory-ui / core services"
tags: [jwt, sse, theme, i18n, transloco, angular-signals, ssr-safe, rbac]
dependency_graph:
  requires: ["10-04", "10-00b"]
  provides: ["jwt-service", "sse-service", "theme-service", "locale-service", "rbac-guard-token"]
  affects: ["10-06", "10-07", "10-08", "10-09"]
tech_stack:
  added: ["@jsverse/transloco 8.3.0 (HTTP loader, provideTransloco)"]
  patterns:
    - "Angular Signals (signal/computed) for reactive auth + SSE state"
    - "isPlatformBrowser() SSR guard on all browser-global access"
    - "Functional HTTP interceptor (HttpInterceptorFn)"
    - "CanActivateFn RBAC guard with InjectionToken boundary (10-04 pattern)"
    - "Exponential backoff (1s→2s→4s→max 30s) for SSE reconnect"
key_files:
  created:
    - apps/factory-ui/src/app/core/auth/jwt.service.ts
    - apps/factory-ui/src/app/core/auth/jwt.interceptor.ts
    - apps/factory-ui/src/app/core/sse/sse.service.ts
    - apps/factory-ui/src/app/core/theme/theme.service.ts
    - apps/factory-ui/src/app/core/i18n/locale.service.ts
    - apps/factory-ui/src/app/core/i18n/transloco-http-loader.ts
    - apps/factory-ui/src/assets/i18n/it.json
    - apps/factory-ui/src/assets/i18n/en.json
  modified:
    - apps/factory-ui/src/app/app.config.ts
    - apps/factory-ui/src/app/core/auth/jwt.service.spec.ts
    - apps/factory-ui/src/app/core/sse/sse.service.spec.ts
    - apps/factory-ui/project.json
decisions:
  - "JWT_STORAGE_KEY='sft_token' — matches Playwright E2E contract (10-UI-SPEC Step 1)"
  - "SseService.handleEvent() and handleError() exposed for direct unit testing (no live EventSource needed)"
  - "LocaleService.switchLang() calls transloco.load().subscribe() then setActiveLang() for lazy-load correctness"
  - "RBAC_GUARD_SERVICE_TOKEN wired via useExisting: JwtService (InjectionToken boundary from 10-04)"
  - "APP_INITIALIZER restores theme/locale on browser hydration; SSR skipped via isPlatformBrowser"
  - "project.json assets extended with src/assets glob to expose i18n JSON to dev server"
metrics:
  duration: "35min"
  completed: "2026-05-24"
  tasks: 3
  files: 12
---

# Phase 10 Plan 05: Frontend Core Services Summary

**One-liner:** Signal-based JwtService/SseService/ThemeService/LocaleService — SSR-safe with transloco runtime IT/EN switch and JWT Bearer interceptor.

---

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | JwtService + JwtInterceptor + RbacGuard (wiring) | fe6d456 | jwt.service.ts, jwt.interceptor.ts, jwt.service.spec.ts |
| 2 | SseService (Signal-based, SSR-guarded) | 3e5a1ba | sse.service.ts, sse.service.spec.ts |
| 3 | ThemeService + LocaleService + app.config providers + i18n catalogs | b8c21ad | theme.service.ts, locale.service.ts, transloco-http-loader.ts, app.config.ts, it.json, en.json, project.json |

---

## Verification

- **jwt.service.spec.ts:** 12 tests pass — browser platform (setToken/getToken/role/isAuthenticated/logout) + server platform (localStorage not touched)
- **sse.service.spec.ts:** 7 tests pass — server no-op, kpi_update signal, sse_heartbeat, error→reconnecting, disconnect
- **i18n JSON:** `node -e "JSON.parse(...)" ` — both it.json and en.json valid JSON, all Copywriting Contract keys present
- **Build:** `nx run ui-factory:build --configuration=development` — compiles clean (pre-existing SCSS deprecation warnings from 10-00a)

---

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as specified.

### Notes

**JwtService `getCurrentRole()` method:** The 10-04 boundary contract `RBAC_GUARD_SERVICE_TOKEN` requires `{ getCurrentRole(): UserRole | null; isAuthenticated(): boolean }`. JwtService exposes `role()` as a computed signal; added `getCurrentRole()` as an alias method to satisfy the interface without changing the existing signal API.

**SseService unit test strategy:** `handleEvent()` and `handleError()` are exposed as public methods (called internally by EventSource listeners). This avoids needing a fake EventSource in tests while maintaining full behavioral coverage. The spec comment said "spy/stub — NOT MagicMock for interrupts" — consistent with the direct method approach used in 10-00b.

**project.json assets:** Added `src/assets` glob alongside the existing `public` glob so that `assets/i18n/{lang}.json` is served both in dev and production builds. The transloco HTTP loader requests `/assets/i18n/{lang}.json` which requires the files to be in the output `assets/` directory.

---

## Security Review (T-10-05-* Threat Register)

| Threat | Status |
|--------|--------|
| T-10-05-01: SSR crash via browser globals | Mitigated — `isPlatformBrowser()` guards on `localStorage`, `EventSource`, `document.documentElement` in all 4 services |
| T-10-05-02: Route elevation via RBAC bypass | Mitigated — `rbacGuard` enforces role from `JwtService.role()` signal; backend `require_roles` is authoritative |
| T-10-05-03: Token in localStorage | Accepted (dev) / Transfer (Phase 11) — documented in threat model |
| T-10-05-04: Client exp check advisory | Mitigated — only advisory; all requests validated server-side with signature check |

---

## Threat Flags

None — no new network endpoints or auth paths introduced beyond what is declared in the threat model.

---

## Known Stubs

None — all services are fully wired. `ThemeService` and `LocaleService` do not have data stubs; they operate on DOM/localStorage directly. The i18n catalogs contain all Copywriting Contract keys. No placeholder values flow to UI rendering.

---

## Self-Check: PASSED

- [x] `apps/factory-ui/src/app/core/auth/jwt.service.ts` — exists
- [x] `apps/factory-ui/src/app/core/auth/jwt.interceptor.ts` — exists
- [x] `apps/factory-ui/src/app/core/sse/sse.service.ts` — exists
- [x] `apps/factory-ui/src/app/core/theme/theme.service.ts` — exists
- [x] `apps/factory-ui/src/app/core/i18n/locale.service.ts` — exists
- [x] `apps/factory-ui/src/assets/i18n/it.json` — exists, valid JSON
- [x] `apps/factory-ui/src/assets/i18n/en.json` — exists, valid JSON
- [x] Commits fe6d456, 3e5a1ba, b8c21ad — present in git log
- [x] 19 tests pass (12 jwt + 7 sse)
- [x] Build compiles clean
