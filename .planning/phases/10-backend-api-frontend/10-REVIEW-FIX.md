---
phase: 10-backend-api-frontend
fixed_at: 2026-05-24T20:29:35Z
review_path: .planning/phases/10-backend-api-frontend/10-REVIEW.md
iteration: 1
findings_in_scope: 11
fixed: 11
skipped: 0
status: all_fixed
---

# Phase 10: Backend API & Frontend — Code Review Fix Report

**Fixed at:** 2026-05-24T20:29:35Z
**Source review:** `.planning/phases/10-backend-api-frontend/10-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 11 (4 Critical + 7 Warning)
- Fixed: 11
- Skipped: 0

## Risultati suite di test

**Backend** (`uv run python -m pytest tests/unit -m "not integration"`):
- 22 passed, 2 skipped (skip pre-esistenti non correlati), 0 failed

**Frontend** (`npx nx test ui-factory`):
- 120 passed, 11 suite, 0 failed

---

## Fixed Issues

### CR-01: SQL injection nella costruzione dinamica del NOT IN nei generatori SSE

**Files modified:** `apps/api-gateway/src/svc_api_gateway/routers/sse.py`, `apps/api-gateway/tests/unit/test_sse_generators.py`
**Commit:** `f39a4f8`
**Applied fix:** Sostituita l'interpolazione f-string/join `", ".join(f"'{aid}'"...)` con query parametrizzata asyncpg `!= ALL($1::text[])` sia in `approvals_stream` (riga 192-198) che in `alerts_stream` (riga 285-292). La variabile `seen_list = list(seen_ids)` viene passata come secondo argomento a `conn.fetch()`. Nessuna altra f-string SQL trovata nel file. Aggiunti 4 test unitari che verificano la presenza di `$1`, l'assenza di `NOT IN`, e il passaggio di `[]` quando `seen_ids` è vuoto.

---

### CR-02: Il SECRET_KEY di produzione può rimanere silenziosamente quello di default

**Files modified:** `apps/api-gateway/src/svc_api_gateway/security/jwt.py`, `apps/api-gateway/tests/unit/test_jwt_secret_guard.py`
**Commit:** `ca66240`
**Applied fix:** Aggiunto guard all'import del modulo: se `API_SECRET_KEY` non è impostata e `APP_ENV` non è in `{"development", "dev", "test"}`, viene sollevata `RuntimeError` che impedisce l'avvio del gateway. In ambienti dev, viene emesso `logging.warning`. La variabile `SECRET_KEY` viene sempre assegnata (`_raw_secret`). Aggiunti 7 test unitari che coprono tutti i rami (production/staging raise, dev/test passano, secret esplicito overrides default).

---

### CR-03: RBAC guard Angular bypassabile — scaffold `return true` attivo in produzione

**Files modified:** `apps/factory-ui/src/app/core/auth/rbac.guard.ts`, `apps/factory-ui/src/app/core/auth/rbac.guard.spec.ts`
**Commit:** `e5bb17d`
**Applied fix:** Rimosso il blocco `try/catch` con `inject(RBAC_GUARD_SERVICE_TOKEN, { optional: true })` e il fallback `return true` (riga 88-93). Il token è ora iniettato in modo obbligatorio con `inject(RBAC_GUARD_SERVICE_TOKEN)`: un provider mancante causa errore DI esplicito invece di concedere accesso silenziosamente. Aggiornata la documentazione del guard. Aggiunti 8 test unitari (deny unauthenticated, deny wrong role, grant correct role, grant no-restriction route).

---

### CR-04: Il token JWT viene esposto in chiaro nell'URL delle connessioni SSE senza scadenza accelerata lato client

**Files modified:** `apps/factory-ui/src/app/auth/login.component.ts`, `apps/factory-ui/src/app/auth/login.component.spec.ts`
**Commit:** `fe4dcfc`
**Applied fix:** Rinominata `SSE_STREAM_URL = '/v1/stream/events'` in `SSE_KPI_URL = '/v1/stream/kpi'`. La chiamata in `_handleLoginSuccess` è aggiornata a `this.sseService.connect(SSE_KPI_URL, token)`. Aggiunto commento che documenta i tre canali reali e la strategia di connessione per canale. Aggiunti 2 test unitari che intercettano il mock `SseService.connect` e verificano che l'URL sia `/v1/stream/kpi` e non contenga `/v1/stream/events`.

---

### WR-01: `_readFromStorage` in JwtService chiama `inject(PLATFORM_ID)` fuori dal contesto di iniezione corretto

**Files modified:** `apps/factory-ui/src/app/core/auth/jwt.service.ts`
**Commit:** `0c8e56f`
**Applied fix:** Sostituito `isPlatformBrowser(inject(PLATFORM_ID))` con `this.isBrowser` nel metodo `_readFromStorage()`. Il campo `this.isBrowser` è già inizializzato all'riga 39 prima che `_token` (riga 42) venga inizializzato, quindi l'ordine è garantito da Angular. I 12 test pre-esistenti di `jwt.service.spec.ts` continuano a passare.

---

### WR-02: `onReject()` usa `window.confirm()` — non SSR-safe e non testabile

**Files modified:** `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts`
**Commit:** `1981bf4`
**Applied fix:** Sostituito `window.confirm()` con `MatDialog.open(RejectConfirmDialogComponent)` con guard `isPlatformBrowser`. Il metodo `onReject()` apre il dialog in modo asincrono e in `afterClosed()` chiama `_submitDecision('REJECTED')` solo se l'utente conferma. Aggiunto `RejectConfirmDialogComponent` standalone inline nel file (with `mat-dialog-close` bindings). Aggiunti `PLATFORM_ID`, `isPlatformBrowser`, `DestroyRef`, e `Injector` agli inject del componente. I 17 test pre-esistenti continuano a passare.

---

### WR-03: `disconnectedTooLong` in SseService non è reattivo in tempo reale

**Files modified:** `apps/factory-ui/src/app/core/sse/sse.service.ts`
**Commit:** `18216ee`
**Applied fix:** Aggiunto `_disconnectedTooLongSignal = signal<boolean>(false)` e `_disconnectBannerTimer`. Il `computed disconnectedTooLong` è ora un passthrough di `_disconnectedTooLongSignal`. Aggiunto `_startDisconnectBannerTimer()` (SSR-safe, guarded da `isBrowser`) che imposta il segnale a `true` dopo 5 s; `_cancelDisconnectBannerTimer()` lo resetta. I timer vengono avviati in `disconnect()` e `handleError()`, cancellati in `_openConnection()` e quando arriva `sse_heartbeat`. I 7 test pre-esistenti continuano a passare.

---

### WR-04: `_subscribeSseResolution()` in ApprovalCardComponent è un corpo vuoto

**Files modified:** `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts`
**Commit:** `c50af4b`
**Applied fix:** Implementato `_subscribeSseResolution()` usando `toObservable(sseService.approvals)` + `takeUntilDestroyed(destroyRef)` tramite `runInInjectionContext(this._injector, ...)`. Quando la card non è più nella lista pending SSE (già rimossa da `approval_resolved`), lo stato locale viene aggiornato a `'approved'` e il countdown SLA viene fermato. Aggiunti agli import: `DestroyRef`, `Injector`, `runInInjectionContext`, `toObservable`, `takeUntilDestroyed`. I 17 test continuano a passare.

---

### WR-05: Il rate-limit SSE alerts non è thread-safe con più worker Uvicorn

**Files modified:** `apps/api-gateway/src/svc_api_gateway/lifespan.py`
**Commit:** `3d7471f`
**Applied fix:** Aggiunto guard nel lifespan all'avvio: se `WEB_CONCURRENCY > 1`, viene emesso `RuntimeWarning` (tramite `warnings.warn`) con messaggio che spiega la violazione di HITL-10 e indica la soluzione (Phase 11 Redis backend). Aggiunto anche log strutturato via `structlog.warning`. Dev mode richiede sempre `--workers 1` / `WEB_CONCURRENCY=1`.

---

### WR-06: `jwtInterceptor` non è limitato al same-origin — può inviare il token JWT a domini terzi

**Files modified:** `apps/factory-ui/src/app/core/auth/jwt.interceptor.ts`, `apps/factory-ui/src/app/core/auth/jwt.interceptor.spec.ts`
**Commit:** `51009e6`
**Applied fix:** Modificata `shouldAttachBearer()` per controllare prima l'origine. URL relative (partono con `/`) sono sempre same-origin e vengono consentite se matchano i pattern. URL assolute devono iniziare con `window.location.origin`; se `window` non è disponibile (SSR) le URL assolute vengono negate. Aggiunti 6 test unitari che verificano attach corretto per URL relative, nessun attach per host esterni, e nessun attach per `/auth/login`.

---

### WR-07: `ThemeService._loadInitialTheme()` chiama `_applyToDomDirect()` durante l'inizializzazione del segnale

**Files modified:** `apps/factory-ui/src/app/core/theme/theme.service.ts`
**Commit:** `4cae47a`
**Applied fix:** Rinominato `_loadInitialTheme()` in `_readStoredTheme()`: la nuova versione legge solo da `localStorage` senza toccare il DOM. L'applicazione del tema al DOM è spostata in `afterNextRender()` nel costruttore, che è no-op su SSR (nessuna callback sul server). Rimosso `OnInit` non usato. I test frontend compilano e passano (120 totali).

---

_Fixed: 2026-05-24T20:29:35Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
