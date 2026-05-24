---
phase: 10-backend-api-frontend
reviewed: 2026-05-24T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - apps/api-gateway/src/svc_api_gateway/security/jwt.py
  - apps/api-gateway/src/svc_api_gateway/security/rbac.py
  - apps/api-gateway/src/svc_api_gateway/routers/auth.py
  - apps/api-gateway/src/svc_api_gateway/routers/kpi.py
  - apps/api-gateway/src/svc_api_gateway/routers/sse.py
  - apps/api-gateway/src/svc_api_gateway/kpi/queries.py
  - apps/api-gateway/src/svc_api_gateway/dependencies.py
  - apps/factory-ui/src/app/core/auth/jwt.service.ts
  - apps/factory-ui/src/app/core/auth/jwt.interceptor.ts
  - apps/factory-ui/src/app/core/auth/rbac.guard.ts
  - apps/factory-ui/src/app/core/sse/sse.service.ts
  - apps/factory-ui/src/app/core/theme/theme.service.ts
  - apps/factory-ui/src/app/core/i18n/locale.service.ts
  - apps/factory-ui/src/app/auth/login.component.ts
  - apps/factory-ui/src/app/shell/app-shell.component.ts
  - apps/factory-ui/src/app/shared/ui/user-chip.component.ts
  - apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts
  - apps/factory-ui/src/app/shared/approval-card/evidence-panel.component.ts
findings:
  critical: 4
  warning: 7
  info: 3
  total: 14
status: issues_found
---

# Phase 10: Backend API & Frontend — Code Review Report

**Reviewed:** 2026-05-24
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

La fase 10 introduce un gateway FastAPI (JWT/RBAC/SSE) e un'applicazione Angular 19 SSR
per la fabbrica. Il codice è strutturalmente ordinato e rispetta la maggior parte delle
guardrail delle fasi precedenti. Emergono tuttavia **4 problemi critici** con impatto
diretto su sicurezza (SQL injection nel polling SSE, segreto silenzioso in produzione,
RBAC bypassabile sul guard Angular, token JWT esposto in URL senza TTL breve lato client)
e **7 warning** che riguardano robustezza e correttezza comportamentale.

---

## Critical Issues

### CR-01: SQL injection nella costruzione dinamica del NOT IN nei generatori SSE

**File:** `apps/api-gateway/src/svc_api_gateway/routers/sse.py:192-198` (approvals) e `sse.py:285-292` (alerts)

**Issue:** I set `seen_ids` (UUID come stringhe) vengono interpolati direttamente
nell'SQL tramite f-string/join. Sebbene gli ID provengano da righe DB (quindi non
direttamente da input utente), il pattern viola la regola assoluta "nessuna
interpolazione SQL" (CR-05) e apre un vettore se un `action_id` contenesse caratteri
speciali o se la logica di derivazione cambiasse. La forma `"'%s'" % aid` con
concatenazione stringa è classificata SQL injection anche se l'origine è interna,
perché non c'è sanitizzazione esplicita e asyncpg non parametrizza dinamicamente una
lista variabile con questo pattern.

```python
# SBAGLIATO (sse.py righe 192-198 e 285-292):
"   AND action_id::text NOT IN ("
+ (", ".join(f"'{aid}'" for aid in seen_ids) if seen_ids else "SELECT NULL WHERE false")
+ ") LIMIT 10"
```

**Fix:** Usare il parametro array di asyncpg oppure riformulare con `= ANY($1::uuid[])`:

```python
# In approvals_stream — sostituire il blocco NOT IN con:
seen_list = list(seen_ids) if seen_ids else []
pending_rows = await conn.fetch(
    "SELECT action_id::text AS approval_id, agent_id AS agent,"
    "       'operator' AS tier, 120 AS sla_seconds"
    " FROM audit.actions"
    " WHERE decision = 'hitl_operator'"
    "   AND action_id::text != ALL($1::text[])"
    " LIMIT 10",
    seen_list,
)
# Stessa trasformazione in alerts_stream.
```

---

### CR-02: Il SECRET_KEY di produzione può rimanere silenziosamente quello di default

**File:** `apps/api-gateway/src/svc_api_gateway/security/jwt.py:34`

**Issue:** `SECRET_KEY = os.environ.get("API_SECRET_KEY", _DEV_ONLY_DEFAULT)` non
emette né un warning né un errore se `API_SECRET_KEY` non è impostata. In un ambiente
di staging o produzione in cui la variabile fosse dimenticata, il servizio si
avvierebbe normalmente firmando token con il segreto debole noto pubblicamente
`"_dev_only_change_before_production_"`. Un attaccante che conosce il segreto
(visibile nel sorgente) può forgiare qualsiasi JWT, ottenendo accesso a tutti i ruoli
incluso `admin`.

**Fix:** All'avvio del modulo, rilevare un ambiente non-dev (es. via `APP_ENV`) e
rifiutare il default:

```python
import logging as _logging
import os as _os

_raw = _os.environ.get("API_SECRET_KEY")
if _raw is None:
    _env = _os.environ.get("APP_ENV", "development").lower()
    if _env not in ("development", "dev", "test"):
        raise RuntimeError(
            "API_SECRET_KEY env var is required in non-development environments."
        )
    _logging.warning(
        "API_SECRET_KEY not set — using insecure dev default. "
        "DO NOT use in production."
    )
    _raw = "_dev_only_change_before_production_"

SECRET_KEY: str = _raw
```

---

### CR-03: RBAC guard Angular bypassabile — scaffold `return true` attivo in produzione

**File:** `apps/factory-ui/src/app/core/auth/rbac.guard.ts:57-93`

**Issue:** La `rbacGuard` contiene un blocco `try/catch` che, se `RBAC_GUARD_SERVICE_TOKEN`
non è iniettato (o l'iniezione lancia eccezione), restituisce `true` consentendo l'accesso
a qualsiasi route protetta senza autenticazione (righe 88-93). Il commento recita
"10-05 wires the real guard", ma il codice di fallback (`return true`) è presente nel
file che verrà incluso nel bundle di produzione. Se `RBAC_GUARD_SERVICE_TOKEN` non viene
fornito in `app.config.ts` (o venisse rimosso per errore), tutte le route protette
diventano pubbliche.

**Fix:** Rimuovere il fallback `return true` e rendere il mancato provider un errore
esplicito:

```typescript
export const rbacGuard: CanActivateFn = (route, _state): boolean => {
  const router = inject(Router);
  const guardService = inject(RBAC_GUARD_SERVICE_TOKEN); // OBBLIGATORIO — errore se mancante

  if (!guardService.isAuthenticated()) {
    router.navigate(['/auth/login']);
    return false;
  }

  const allowedRoles = (route.data[ROUTE_ROLES_KEY] ?? []) as UserRole[];
  if (allowedRoles.length === 0) return true;

  const currentRole = guardService.getCurrentRole();
  if (currentRole && allowedRoles.includes(currentRole)) return true;

  router.navigate(['/auth/login']);
  return false;
};
```

---

### CR-04: Il token JWT viene esposto in chiaro nell'URL delle connessioni SSE senza scadenza accelerata lato client

**File:** `apps/factory-ui/src/app/core/sse/sse.service.ts:204` e `apps/factory-ui/src/app/auth/login.component.ts:72`

**Issue:** L'URL SSE è `/v1/stream/events` (login.component.ts riga 72), ma i tre endpoint
reali sono `/v1/stream/kpi`, `/v1/stream/approvals`, `/v1/stream/alerts` — quindi il
`connect()` in `_handleLoginSuccess` punta a un URL **inesistente**. Conseguenza: nessuna
connessione SSE viene mai aperta dopo il login, rendendo l'intera funzionalità di
streaming (KPI live, approvazioni push) non funzionante nel flusso principale.

In aggiunta, il token JWT (validità 8 ore) viene passato come query param nell'URL
(`?token=<JWT>`) senza alcuna misura di attenuazione lato client (es. TTL ridotto per
le connessioni SSE, token usa-e-getta). Questo è documentato come rischio accettato
per il dev-mode, ma il URL errato è un bug funzionale bloccante indipendente.

**Fix immediato per l'URL:**

```typescript
// login.component.ts — rimuovere la costante errata e aprire i tre canali separati
// oppure usare il canale corretto per il persona home:
const SSE_KPI_URL = '/v1/stream/kpi';
const SSE_APPROVALS_URL = '/v1/stream/approvals';
const SSE_ALERTS_URL = '/v1/stream/alerts';

// In _handleLoginSuccess: aprire il canale appropriato al ruolo, oppure
// spostare la logica di connessione SSE nei componenti specifici per area.
```

---

## Warnings

### WR-01: `_readFromStorage` in JwtService chiama `inject(PLATFORM_ID)` fuori dal contesto di iniezione corretto

**File:** `apps/factory-ui/src/app/core/auth/jwt.service.ts:113`

**Issue:** `_readFromStorage()` è un metodo privato chiamato dall'initializzazione del
campo `_token = signal<string | null>(this._readFromStorage())`. Al momento
dell'esecuzione dell'initializzatore di campo, `inject()` funziona correttamente perché
siamo ancora nel contesto del costruttore Angular. Tuttavia, `inject(PLATFORM_ID)` viene
chiamato una seconda volta (oltre a `this.platformId` già disponibile), creando dipendenza
su un comportamento fragile e duplicando l'iniezione. Se `_readFromStorage` venisse
chiamato fuori dal contesto di costruzione (refactoring futuro), lancerebbe un errore
runtime.

**Fix:** Usare `this.isBrowser` (già calcolato) invece di chiamare di nuovo `inject`:

```typescript
private _readFromStorage(): string | null {
  if (!this.isBrowser) return null;   // usa il campo già inizializzato
  return localStorage.getItem(JWT_STORAGE_KEY);
}
```

---

### WR-02: `onReject()` usa `window.confirm()` — non SSR-safe e non testabile

**File:** `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts:540-545`

**Issue:** `window.confirm(...)` viene chiamato senza guard `isPlatformBrowser`. Se il
componente viene renderizzato lato server (SSR), il riferimento a `window` causa
`ReferenceError`. Inoltre `window.confirm` è sincrono/bloccante, non testabile con
Playwright/Jest, e non rispetta il design system Material (la specifica cita `MatDialog`).

**Fix:** Usare `MatDialog` (già importato) con guard SSR:

```typescript
onReject(): void {
  if (!this.isMotivationValid() || this.isSubmitting()) return;
  if (!isPlatformBrowser(this.platformId)) return;  // SSR guard
  // Aprire un MatDialogRef di conferma, poi in afterClosed():
  //   if (result === true) this._submitDecision('REJECTED');
}
```

---

### WR-03: `disconnectedTooLong` in SseService non è reattivo in tempo reale

**File:** `apps/factory-ui/src/app/core/sse/sse.service.ts:81-85`

**Issue:** `disconnectedTooLong` è un `computed()` che dipende dal segnale
`_disconnectedAt`. Un `computed()` di Angular non rivaluta automaticamente dopo 5 secondi
— viene ricalcolato solo quando un segnale da cui dipende cambia. Se `_disconnectedAt`
non viene aggiornato dopo la disconnessione, il banner di warning non apparirà mai.
Il requisito "mostra banner dopo 5s" richiede un timer o un polling, non solo un computed.

**Fix:** Aggiungere un timer che imposta un segnale booleano dedicato dopo 5 s dalla
disconnessione:

```typescript
private _disconnectedTooLongSignal = signal(false);
readonly disconnectedTooLong = computed(() => this._disconnectedTooLongSignal());

// In handleError / disconnect:
this._disconnectedAt.set(Date.now());
this._disconnectedTooLongTimer = setTimeout(() => {
  this._disconnectedTooLongSignal.set(true);
}, DISCONNECT_BANNER_THRESHOLD_MS);
```

---

### WR-04: `_subscribeSseResolution()` in ApprovalCardComponent è un corpo vuoto — nessuna risoluzione SSE funziona

**File:** `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts:587-592`

**Issue:** Il metodo è completamente vuoto (solo un commento). L'UI non reagisce agli
eventi `approval_resolved` provenienti dall'SSE: un'approvazione effettuata da un altro
utente non aggiornerà lo stato della card. Il commento suggerisce di usare un `effect()`
o `toObservable()`, ma non è stato implementato.

**Fix:** Implementare usando `toObservable` di `@angular/core/rxjs-interop`:

```typescript
import { toObservable } from '@angular/core/rxjs-interop';

private _subscribeSseResolution(): void {
  this._sseSubscription = toObservable(this.sseService.approvals)
    .pipe(takeUntilDestroyed(this._destroyRef))
    .subscribe((list) => {
      if (!this.card) return;
      const resolved = list.find(a => a.approval_id === this.card!.id);
      // Se non è più nella lista pending, aggiornare lo stato locale
      if (!resolved && this._currentStatus() === 'pending') {
        // ...
      }
    });
}
```

---

### WR-05: Il rate-limit SSE alerts non è thread-safe con più worker Uvicorn

**File:** `apps/api-gateway/src/svc_api_gateway/routers/sse.py:69`

**Issue:** `_alert_rate_state` è un dizionario a livello di modulo. Il commento documenta
che "single asyncio event loop" è l'assunzione. Ma se il gateway venisse eseguito con
`--workers N` (multiprocesso Gunicorn/Uvicorn), ogni worker avrebbe il proprio
`_alert_rate_state`, rendendo il rate-limit inefficace (ogni worker conteggia
separatamente). Questo viola HITL-10 in deploy standard di produzione.

**Fix a breve termine:** Documentare esplicitamente nel file di configurazione Uvicorn
che `--workers 1` è obbligatorio per dev-mode. Aggiungere un guard all'avvio:

```python
# In lifespan.py o main.py:
import os
if int(os.environ.get("WEB_CONCURRENCY", "1")) > 1:
    import warnings
    warnings.warn(
        "SSE alert rate-limit is in-process only. "
        "Multi-worker deploy violates HITL-10. Use Redis backend (Phase 11).",
        RuntimeWarning,
        stacklevel=2,
    )
```

---

### WR-06: `jwtInterceptor` non è limitato al same-origin — può inviare il token JWT a domini terzi

**File:** `apps/factory-ui/src/app/core/auth/jwt.interceptor.ts:45-47`

**Issue:** `shouldAttachBearer(url)` controlla solo se l'URL *contiene* `/v1/` o
`/auth/me`. Una chiamata a `https://evil.example.com/v1/kpi` supererebbe il controllo e
riceverebbe il Bearer token JWT. Questo è un potenziale token-leakage verso host di terze
parti (ad es. se un componente usasse un URL assoluto esterno, o in caso di redirect
aperto).

**Fix:** Limitare l'attach del token solo a richieste verso il proprio origin:

```typescript
function shouldAttachBearer(url: string): boolean {
  const isSameOrigin =
    url.startsWith('/') ||
    url.startsWith(window.location.origin);
  if (!isSameOrigin) return false;
  return BEARER_URL_PATTERNS.some((pattern) => url.includes(pattern));
}
```

---

### WR-07: `ThemeService._loadInitialTheme()` chiama `_applyToDomDirect()` durante l'inizializzazione del segnale, prima che il documento sia pronto in SSR

**File:** `apps/factory-ui/src/app/core/theme/theme.service.ts:65-74`

**Issue:** `_loadInitialTheme()` viene chiamato per inizializzare `_theme = signal(...)`.
Se `isBrowser` è true, chiama `_applyToDomDirect(theme)` che accede a
`this.document.documentElement`. Il problema: il campo `this.document` è inizializzato
tramite `inject(DOCUMENT)`, ma `_loadInitialTheme()` viene eseguito come inizializzatore
di campo **prima** che `inject()` venga completato in Angular. In pratica il campo
`this.document` potrebbe essere `undefined` al momento della prima chiamata.

**Fix:** Spostare l'applicazione DOM al DOM a `ngOnInit` o a un `afterNextRender`:

```typescript
private _theme = signal<Theme>(this._readStoredTheme()); // solo lettura, no DOM

ngOnInit(): void {
  this._applyToDomDirect(this._theme()); // applicare dopo che il servizio è costruito
}

private _readStoredTheme(): Theme {
  if (!this.isBrowser) return DEFAULT_THEME;
  const stored = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
  return stored === 'light' || stored === 'dark' ? stored : DEFAULT_THEME;
}
```

---

## Info

### IN-01: `isDevMode()` in LoginComponent è sempre `true` — le chip di accesso rapido appaiono in produzione

**File:** `apps/factory-ui/src/app/auth/login.component.ts:334`

**Issue:** `readonly isDevMode = computed<boolean>(() => true)` restituisce sempre `true`,
rendendo il blocco "Accesso rapido (dev)" sempre visibile, incluso in build di produzione.
Le credenziali plaintext dei persona (mantis2026) sono anche hardcoded nel frontend.

**Fix:** Usare `isDevMode()` di Angular core o una variabile di ambiente al build time:

```typescript
import { isDevMode } from '@angular/core';
readonly isDevMode = computed<boolean>(() => isDevMode());
```

---

### IN-02: `_slaRemainingSeconds` non è un `Signal` privato — l'underscore è fuorviante

**File:** `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts:451`

**Issue:** `private _slaRemainingSeconds = signal(0)` è correttamente privato ma il
pattern di naming non è consistente: `_slaInterval` è un campo normale (non signal) con
lo stesso prefisso. Non è un bug ma aumenta la confusione durante la manutenzione.

**Fix:** Rinominare i campi non-signal senza prefisso `_` oppure documentare la
convenzione di naming esplicitamente nei commenti del file.

---

### IN-03: `motivationText` in ApprovalCardComponent è pubblico e bidirezionale ma duplica `_motivation` signal

**File:** `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts:440,444`

**Issue:** Esistono due sorgenti di verità per la motivazione: `motivationText` (stringa
pubblica per `[(ngModel)]`) e `_motivation` (signal privato aggiornato in
`onMotivationChange`). Se il binding bidirezionale e il signal si desincronizzassero
(es. in un test che imposta direttamente `motivationText`), la validazione fallirebbe.

**Fix:** Eliminare `motivationText` come campo separato e usare il signal come fonte
unica tramite un getter/setter o passando al solo evento `(ngModelChange)` già presente.

---

_Reviewed: 2026-05-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
