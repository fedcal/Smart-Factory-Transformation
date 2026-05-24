# Phase 10: Backend API & Frontend — Research

**Researched:** 2026-05-24
**Domain:** FastAPI JWT/RBAC/SSE gateway + Angular 19 SSR HITL UI
**Confidence:** HIGH (scaffold verificato, pacchetti confermati su registry ufficiali)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Auth/RBAC:** JWT dev-mode (HS256) + utenti persona seedati (operator, shift-supervisor, technician, CIO, admin). FastAPI emette JWT su `/auth/login`; Angular applica RBAC guard per area; endpoint FastAPI enforces dipendenza RBAC per ruolo. Deferred F11: IdP reale, refresh token, JWKS rotation, hardening OWASP.
2. **Streaming:** SSE primario per KPI + alert/approval push. HITL actions (approve/reject) = POST REST su approvals router esistente. Rate-limit 12 alert/ora/persona enforced server-side sul canale SSE alert (HITL-10).
3. **State management Angular:** Signals + injectable services. NO NgRx. computed() per KPI derivati.
4. **Dashboard data:** Aggregazioni FastAPI reali su TimescaleDB (audit.actions, maintenance.downtime_events, scm.*, sensor_events). Nessun mock.
5. **Execution:** worktrees DISABILITATI — sequential su main tree. Tutti i guardrail Phase 8/9 applicati.

### Claude's Discretion

- Scelta JWT library Python: PyJWT (vedi Section Standard Stack — LOCKED per leggerezza e presenza in env)
- Strategia Angular i18n runtime toggle: `@angular/localize` con `loadLocaleData()` lazy (confermato da UI-SPEC)
- Configurazione Tailwind v4 con Angular: `@tailwindcss/postcss` plugin via PostCSS (no config file separato)
- Wave decomposition dettagliata (vedi Section Architecture Patterns)

### Deferred Ideas (OUT OF SCOPE)

- Real IdP/Keycloak, refresh tokens, JWKS rotation, full OWASP LLM/web hardening → Phase 11
- Full OTEL/Langfuse/LGTM observability stack + Grafana dashboards + evals → Phase 11
- WebSocket bidirectional channel
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRV-01 | API Gateway FastAPI con OpenAPI 3.1, autenticazione JWT, RBAC per ruolo | Section Standard Stack (PyJWT, FastAPI dependency pattern), Code Examples |
| SRV-02 | Endpoint REST + SSE per approval queue, evidence, KPI, audit | Section Standard Stack (sse-starlette), Architecture Patterns (SSE router) |
| SRV-03 | WebSocket bridge Angular UI ↔ NATS — per architettura SSE è il canale primario; WS bridge rinviato | Deferred (SSE covers all push cases per CONTEXT.md) |
| SRV-04 | Health/readiness probe + OTEL spans su ogni endpoint | Existing health.py riusabile; OTEL decorator pattern in Code Examples |
| SRV-05 | Contract test Pydantic ↔ TypeScript per type-safety end-to-end | Section Don't Hand-Roll + Code Examples (openapi-typescript) |
| UI-01 | App Angular 18+ SSR, routing app per persona | Scaffold esistente Angular 19.2 SSR; routing plan in Architecture Patterns |
| UI-02 | Design system Tailwind + Angular Material, touch target 64px | UI-SPEC confermata; installazione in Standard Stack |
| UI-03 | Approval queue UI con evidence panel inline | Componente ApprovalCard + EvidencePanel — contratto in UI-SPEC Section 3-4 |
| UI-04 | Dashboard control room con KPI live | KPI SQL in Architecture Patterns; SSE integration in Code Examples |
| UI-05 | Tema dark/light + WCAG AA | Palette e contrasti in UI-SPEC; theming Angular Material in Standard Stack |
| UI-06 | Stream eventi via SSE dal backend | SSE service Angular in Code Examples |
| UI-07 | i18n IT+EN lazy load | @angular/localize con loadLocaleData(), SSR-safe in Code Examples |
| UI-08 | Persona walkthrough demo | Route /demo, mat-stepper, 4 step — contratto UI-SPEC Section 7 |
| UI-09 | Mock UI docs + screenshot CI | Playwright screenshot task in wave 9 |
| UI-10 | Playwright E2E flusso HITL | Test contract in UI-SPEC Section Playwright E2E |
| HITL-01..10 | Governance HITL (interrupt, escalation, evidence, SLA, audit, governor, rate-limit) | Riusa approvals.py + threads.py esistenti; nuovi endpoint SSE per push |
</phase_requirements>

---

## Summary

La Phase 10 aggiunge due strati nuovi al monorepo esistente: un'estensione del gateway FastAPI (auth JWT, SSE, KPI aggregations) e una SPA Angular 19 SSR completa (HITL UI + dashboard). Entrambi i lati hanno scaffold già operativi: `apps/api-gateway` ha tutti i router agente delle fasi 6-9 wired, `apps/factory-ui` ha lo scaffold Angular 19.2 SSR puro (main.server.ts, server.ts, app.config.ts con provideClientHydration+withEventReplay).

**Nessuna dipendenza va installata da zero senza verifica.** Lo scaffold Angular 19.2 non ha ancora Angular Material, Tailwind, ng2-charts né @angular/localize. Il gateway FastAPI ha già fastapi, asyncpg, pydantic, structlog ma manca di PyJWT, sse-starlette e opentelemetry-instrumentation-fastapi.

La scelta critica verificata: **ng2-charts@8.x** (non v10, che richiede Angular 21+) è compatibile con Angular 19. **@angular/material@~19.2.x** e **@angular/cdk@~19.2.x** sono la versione corretta per questo workspace. Tailwind v4 si integra con Angular via `@tailwindcss/postcss` (PostCSS plugin), non via Vite.

**Raccomandazione primaria:** implementare in 9 onde sequenziali — fondamenta backend → auth → SSE/KPI → fondamenta frontend/shell/i18n → approval UI + evidence panel → dashboard → persona walkthrough → Playwright E2E → docs/screenshots.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JWT emissione e verifica | API / Backend (FastAPI) | — | Token firmato HS256 lato server; Angular verifica solo scadenza lato client per redirect |
| RBAC enforcement | API / Backend (FastAPI dependency) | Frontend Server (Angular route guard) | Guard Angular blocca navigazione; dipendenza FastAPI blocca accesso dati (doppio strato) |
| SSE push (KPI, alert, approval) | API / Backend (FastAPI StreamingResponse) | Browser / Client (EventSource + Signals) | Canale unidirezionale server→client; nessuna logica sul SSR server Angular |
| HITL approve/reject | API / Backend (approvals router esistente) | Browser / Client (POST via HttpClient) | Azione su dato persistente; deve passare per backend |
| KPI aggregation SQL | Database / Storage (TimescaleDB) + API | — | Query su hypertable + CAGG oee_hourly; calcolato server-side |
| i18n locale loading | Browser / Client (loadLocaleData) | Frontend Server (SSR sempre in 'it') | SSR non dipende da localStorage; browser lazily carica 'en-US' |
| Tema dark/light | Browser / Client (CSS custom properties) | Frontend Server (classe default 'dark') | prefers-color-scheme + toggle manuale; SSR applica classe default |
| Evidence panel rendering | Browser / Client (Angular component) | — | JSONB già aggregato dal backend; solo rendering client-side |
| Playwright E2E | Browser / Client (test runner headless) | API / Backend (intercept POST) | page.route() intercetta la chiamata REST; headless Chrome |
| OTEL spans | API / Backend (FastAPI middleware) | — | Solo endpoint spans in Phase 10; full OTEL stack in Phase 11 |

---

## Standard Stack

### Core — Backend (FastAPI gateway extensions)

| Library | Version | Purpose | Fonte |
|---------|---------|---------|-------|
| `fastapi` | `>=0.115,<0.117` | Web framework (già in pyproject.toml) | `[VERIFIED: pyproject.toml esistente]` |
| `PyJWT` | `>=2.9,<3` | JWT HS256 encode/decode (più leggero di python-jose, zero deps extra) | `[VERIFIED: PyPI 2.13.0 latest; già installato 2.10.1]` |
| `sse-starlette` | `>=3.4,<4` | SSE via `EventSourceResponse` in FastAPI | `[VERIFIED: PyPI 3.4.4 latest]` |
| `opentelemetry-api` | `>=1.40,<2` | OTEL API per span decoration (Phase 10: spans only) | `[VERIFIED: PyPI 1.42.1 latest]` |
| `opentelemetry-sdk` | `>=1.40,<2` | OTEL SDK + TracerProvider | `[VERIFIED: PyPI 1.42.1 latest]` |
| `opentelemetry-instrumentation-fastapi` | `>=0.55b0` | Middleware auto-instrumentazione FastAPI | `[VERIFIED: PyPI — package name su PyPI è opentelemetry-instrumentation-fastapi]` |
| `asyncpg` | `>=0.30,<0.31` | Pool PG (già presente) | `[VERIFIED: pyproject.toml esistente]` |
| `pydantic` | `>=2.9,<3` | Modelli request/response (già presente) | `[VERIFIED: pyproject.toml esistente]` |
| `structlog` | `>=24.4` | Logging strutturato (già presente) | `[VERIFIED: pyproject.toml esistente]` |

### Core — Frontend (Angular workspace additions)

| Library | Version | Purpose | Fonte |
|---------|---------|---------|-------|
| `@angular/material` | `~19.2.x` | Component library MDC-based (mat-card, mat-button, ecc.) | `[VERIFIED: npm registry 19.2.19 latest]` |
| `@angular/cdk` | `~19.2.x` | Virtual scroll, overlay, focus trap | `[VERIFIED: npm registry 19.2.x — dipendenza di @angular/material]` |
| `tailwindcss` | `^4.3.0` | Utility CSS v4 (no tailwind.config.js separato) | `[VERIFIED: npm registry 4.3.0 latest]` |
| `@tailwindcss/postcss` | `^4.3.0` | Plugin PostCSS per Tailwind v4 con Angular builder | `[VERIFIED: npm registry 4.3.0]` |
| `@angular/localize` | `~19.2.x` | i18n con loadLocaleData() per runtime locale switch | `[VERIFIED: npm registry 19.2.14]` |
| `ng2-charts` | `^8.0.0` | Wrapper Chart.js per Angular 19 (v10 richiede Angular 21+) | `[VERIFIED: npm registry 8.0.0; peer deps @angular/core>=19.0.0]` |
| `chart.js` | `^4.4.0` | Libreria chart sottostante | `[VERIFIED: npm registry 4.5.1 latest]` |
| `@nx/playwright` | `20.8.4` | Plugin Nx per Playwright E2E (uguale alla versione Nx workspace) | `[VERIFIED: npm registry 20.8.4]` |
| `@playwright/test` | `^1.50.0` | Test runner E2E (installato tramite @nx/playwright) | `[VERIFIED: npm registry 1.60.0 latest]` |

**Nota critica ng2-charts:** ng2-charts@10 (l'ultima versione) richiede `@angular/cdk>=21`. La versione compatibile con Angular 19 workspace è **ng2-charts@8.x** (peer `@angular/core>=19.0.0` confermato via `npm view ng2-charts@8 peerDependencies`). La UI-SPEC menzionava genericamente ng2-charts; questo vincolo di versione deve essere rispettato nel PLAN.

**Nota Tailwind v4 con Angular:** Tailwind v4 non usa più `tailwind.config.js`. La configurazione avviene via CSS (`@import "tailwindcss"` in `styles.scss`). Il builder `@angular-devkit/build-angular` usa PostCSS sotto, quindi il plugin `@tailwindcss/postcss` funziona senza Vite. Il token `@next` suggerito dalla UI-SPEC non è necessario — la v4 stabile è già `4.3.0`.

**Nota PyJWT vs python-jose:** `python-jose` non esiste su npm (irrilevante) ed esiste su PyPI (3.5.0). Tuttavia PyJWT è preferito perché: (a) è già installato nell'ambiente (2.10.1), (b) zero dipendenze extra per HS256, (c) API più semplice per questo use-case. python-jose aggiunge ecdsa e cryptography come optional deps non necessari per HS256 puro. `[ASSUMED: python-jose su PyPI non verificato via Context7/docs ufficiali — scelta PyJWT basata su presenza in ambiente e semplicità]`

**Installazione backend (da aggiungere a pyproject.toml):**
```toml
"PyJWT>=2.9,<3",
"sse-starlette>=3.4,<4",
"opentelemetry-api>=1.40,<2",
"opentelemetry-sdk>=1.40,<2",
"opentelemetry-instrumentation-fastapi>=0.55b0",
```

**Installazione frontend (pnpm, nella root del monorepo):**
```bash
pnpm add @angular/material@~19.2.0 @angular/cdk@~19.2.0
pnpm add @angular/localize@~19.2.0
pnpm add tailwindcss@^4.3.0 @tailwindcss/postcss@^4.3.0
pnpm add ng2-charts@^8.0.0 chart.js@^4.4.0
pnpm add -D @nx/playwright@20.8.4 @playwright/test@^1.50.0
```

---

## Package Legitimacy Audit

> slopcheck disponibile (v0.6.1). Nota: slopcheck usa npm come registry default; i pacchetti Python sono stati verificati via `pip index versions` su PyPI.

### Pacchetti Backend (PyPI)

| Package | Registry | Latest | Downloads (stima) | Source Repo | slopcheck | Disposition |
|---------|----------|--------|-------------------|-------------|-----------|-------------|
| `PyJWT` | PyPI | 2.13.0 | Alto (100M+/mese stima) | github.com/jpadilla/pyjwt | OK (verificato PyPI) | Approved |
| `sse-starlette` | PyPI | 3.4.4 | Medio | github.com/sysid/sse-starlette | OK (verificato PyPI) | Approved |
| `opentelemetry-api` | PyPI | 1.42.1 | Molto alto | github.com/open-telemetry/opentelemetry-python | OK (verificato PyPI) | Approved |
| `opentelemetry-sdk` | PyPI | 1.42.1 | Molto alto | github.com/open-telemetry/opentelemetry-python | OK (verificato PyPI) | Approved |
| `opentelemetry-instrumentation-fastapi` | PyPI | 0.63b0 | Alto | github.com/open-telemetry/opentelemetry-python-contrib | OK (verificato PyPI) | Approved `[ASSUMED: versione esatta non confirmata via Context7]` |

### Pacchetti Frontend (npm)

| Package | Registry | Age | Downloads (slopcheck) | Source Repo | slopcheck | Disposition |
|---------|----------|-----|----------------------|-------------|-----------|-------------|
| `@angular/material` | npm | ~8 anni | Molto alto | github.com/angular/components | [OK] | Approved |
| `@angular/cdk` | npm | ~8 anni | Molto alto | github.com/angular/components | [OK] | Approved |
| `tailwindcss` | npm | ~6 anni | Molto alto | github.com/tailwindlabs/tailwindcss | [OK] | Approved |
| `@tailwindcss/postcss` | npm | ~1 anno | Alto | github.com/tailwindlabs/tailwindcss | [OK] | Approved |
| `@angular/localize` | npm | ~6 anni | Molto alto | github.com/angular/angular | [OK] | Approved |
| `ng2-charts` | npm | ~8 anni | Medio (150k/sett.) | github.com/valor-software/ng2-charts | [OK] | Approved **@8.x — non @10** |
| `chart.js` | npm | ~10 anni | Molto alto | github.com/chartjs/Chart.js | [OK] | Approved |
| `@playwright/test` | npm | ~5 anni | Alto | github.com/microsoft/playwright | [OK] | Approved |
| `@nx/playwright` | npm | ~3 anni | Alto | github.com/nrwl/nx | [OK] | Approved |

**Pacchetti rimossi per SLOP:** nessuno.
**Pacchetti sospetti:** nessuno.
**Avvertenza versione:** ng2-charts DEVE essere @8.x — non @latest (che è @10, incompatibile con Angular 19).

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (Angular 19 SSR hydrated)
│
│  EventSource('/v1/stream/kpi')     ←── SSE push
│  EventSource('/v1/stream/approvals') ←── SSE push
│  POST /v1/approvals/{id}/decide    ──► REST (esistente)
│  POST /auth/login                  ──► REST (nuovo)
│  GET  /v1/kpi                      ──► REST (nuovo)
│
FastAPI Gateway (apps/api-gateway)
├── router: auth.py              [NUOVO] JWT login + RBAC dep
├── router: sse.py               [NUOVO] StreamingResponse endpoints
├── router: kpi.py               [NUOVO] KPI aggregation endpoints
├── router: approvals.py         [ESISTENTE] HITL decide
├── router: threads.py           [ESISTENTE] resume
├── router: health.py            [ESISTENTE] liveness/readiness
└── middleware: OTEL spans       [NUOVO] OpenTelemetryMiddleware
         │
         ├── asyncpg Pool
         │     ├── hitl.approvals          (HITL queue)
         │     ├── audit.actions           (evidence_panel JSONB)
         │     ├── maintenance.downtime_events + oee_hourly CAGG
         │     ├── scm.*                   (supply chain)
         │     └── sensor_events           (scrap/quality proxy)
         └── NATS (audit, alert push)

Angular SSR Server (Express + CommonEngine)
└── SSR rendering in 'it' locale (no EventSource sul server)

Angular SPA (Browser)
├── core/auth/            JwtService, RbacGuard, JwtInterceptor
├── core/sse/             SseService → Signal<KpiSnapshot>
├── core/i18n/            LocaleService → loadLocaleData()
├── core/theme/           ThemeService → CSS class toggle
├── shell/                AppShell, TopBar, NavigationRail, BottomNav
├── features/operator/    ApprovalQueueFeed, AlertFeed
├── features/manager/     KpiDashboard, ChartsRow
├── features/technician/  (manutenzione)
├── features/admin/       (audit log)
├── features/demo/        PersonaWalkthrough (mat-stepper)
├── shared/approval-card/ ApprovalCard + EvidencePanel
└── shared/kpi-tile/      KpiTile
```

### Struttura File Raccomandata

```
apps/api-gateway/src/svc_api_gateway/
├── routers/
│   ├── auth.py          [NUOVO] /auth/login, /auth/me
│   ├── sse.py           [NUOVO] /v1/stream/kpi, /v1/stream/approvals, /v1/stream/alerts
│   ├── kpi.py           [NUOVO] /v1/kpi (aggregations)
│   ├── approvals.py     [ESISTENTE — aggiungere endpoint /approve e /reject separati]
│   ├── health.py        [ESISTENTE]
│   └── threads.py       [ESISTENTE]
├── security/
│   ├── jwt.py           [NUOVO] encode/decode HS256, SEEDED_USERS dict
│   └── rbac.py          [NUOVO] RoleChecker dependency
└── kpi/
    └── queries.py       [NUOVO] SQL aggregation functions

apps/factory-ui/src/
├── app/
│   ├── core/
│   │   ├── auth/           jwt.service.ts, rbac.guard.ts, jwt.interceptor.ts
│   │   ├── sse/            sse.service.ts (Signal-based)
│   │   ├── i18n/           locale.service.ts
│   │   └── theme/          theme.service.ts
│   ├── shell/              app-shell.component.ts, top-bar, nav-rail, bottom-nav
│   ├── features/
│   │   ├── operator/
│   │   ├── technician/
│   │   ├── manager/
│   │   ├── admin/
│   │   └── demo/
│   ├── shared/
│   │   ├── approval-card/
│   │   ├── kpi-tile/
│   │   ├── alert-feed/
│   │   └── ui/             language-toggle, theme-toggle, user-chip
│   └── auth/               login.component.ts
├── styles/
│   ├── _tokens.scss        CSS custom properties SFT design tokens
│   ├── _theme.dark.scss
│   ├── _theme.light.scss
│   └── _typography.scss
└── assets/i18n/
    ├── messages.it.xlf
    └── messages.en.xlf
```

### Pattern 1: JWT dev-mode — FastAPI auth.py

```python
# Source: PyJWT 2.x official docs (jwt.io/introduction)
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = os.environ.get("API_SECRET_KEY", "dev-only-secret-change-in-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8  # turno di lavoro

# Utenti seedati — NESSUN secret in codice, password in chiaro solo per dev-mode
SEEDED_USERS: dict[str, dict] = {
    "operator@mantis.it":    {"password": "operator123",    "role": "operator"},
    "supervisor@mantis.it":  {"password": "supervisor123",  "role": "shift-supervisor"},
    "technician@mantis.it":  {"password": "technician123",  "role": "technician"},
    "cio@mantis.it":         {"password": "cio123",         "role": "manager"},
    "admin@mantis.it":       {"password": "admin123",       "role": "admin"},
}

def create_token(email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "email": email,
        "role": role,
        "exp": now + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": now,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="token_invalid")
```

### Pattern 2: RBAC Dependency FastAPI

```python
# Source: FastAPI docs — Dependencies (fastapi.tiangolo.com/tutorial/dependencies/)
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

bearer_scheme = HTTPBearer()

def require_roles(*allowed_roles: str):
    """Factory che ritorna una FastAPI dependency per RBAC."""
    def _dep(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
        payload = decode_token(creds.credentials)
        if payload.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="rbac_forbidden")
        return payload  # restituisce il payload per uso nel router
    return _dep

# Uso negli endpoint:
@router.get("/v1/kpi")
async def get_kpi(
    principal: dict = Depends(require_roles("operator", "shift-supervisor", "manager", "admin")),
    pool = Depends(get_pool),
):
    ...
```

### Pattern 3: SSE via sse-starlette

```python
# Source: sse-starlette docs (github.com/sysid/sse-starlette)
# Nota: sse-starlette >= 3.x usa EventSourceResponse con async generator
from sse_starlette.sse import EventSourceResponse
import asyncio, json

@router.get("/v1/stream/kpi")
async def stream_kpi(
    request: Request,
    principal: dict = Depends(require_roles("operator", "shift-supervisor", "manager", "admin")),
    pool = Depends(get_pool),
):
    async def kpi_generator():
        while True:
            if await request.is_disconnected():
                break
            # heartbeat ogni 30s (per reset timer riconnessione client)
            snapshot = await _compute_kpi_snapshot(pool)
            yield {"event": "kpi_update", "data": json.dumps(snapshot)}
            await asyncio.sleep(5)  # aggiorna ogni 5s
    return EventSourceResponse(kpi_generator())
```

### Pattern 4: SSE Client Angular — Signal-based

```typescript
// Source: [ASSUMED] — pattern standard Angular 19 Signals + EventSource
// Guardia isPlatformBrowser OBBLIGATORIA per compatibilità SSR
import { isPlatformBrowser } from '@angular/common';
import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class SseService {
  private platformId = inject(PLATFORM_ID);

  readonly kpiSnapshot = signal<KpiSnapshot | null>(null);
  readonly connectionStatus = signal<'connected' | 'disconnected'>('disconnected');

  connect(token: string): void {
    if (!isPlatformBrowser(this.platformId)) return; // CRITICO: no EventSource su SSR server

    const es = new EventSource(`/v1/stream/kpi?token=${token}`);
    es.addEventListener('kpi_update', (e) => {
      this.kpiSnapshot.set(JSON.parse(e.data));
    });
    es.addEventListener('sse_heartbeat', () => {
      this.connectionStatus.set('connected');
    });
    es.onerror = () => {
      this.connectionStatus.set('disconnected');
      // exponential backoff gestito automaticamente da EventSource nativo
    };
    this.connectionStatus.set('connected');
  }
}
```

### Pattern 5: i18n runtime toggle senza ricarica pagina

```typescript
// Source: [ASSUMED] — @angular/localize loadLocaleData pattern
// NOTA: Angular built-in i18n via @angular/localize supporta runtime switch
// solo in modalità specifica (non compile-time). L'approccio corretto per
// "nessun page reload" usa il pattern di caricamento dinamico delle locale data.
import { getLocaleData, registerLocaleData } from '@angular/common';
import localeEn from '@angular/common/locales/en';

@Injectable({ providedIn: 'root' })
export class LocaleService {
  private _locale = signal<string>('it');

  async switchToEnglish(): Promise<void> {
    registerLocaleData(localeEn, 'en-US');
    this._locale.set('en-US');
    // Aggiorna l'attributo lang dell'HTML
    document.documentElement.lang = 'en';
    localStorage.setItem('sft_locale', 'en-US');
    // NOTA: i testi i18n statici richiedono ricompilazione o un approccio
    // runtime alternativo (vedi sezione Pitfalls — i18n runtime switch)
  }
}
```

**ATTENZIONE PITFALL i18n:** Angular `@angular/localize` standard usa traducioni compile-time (xlf) che NON cambiano senza reload. Il "runtime switch senza reload" per testi i18n statici richiede uno dei seguenti approcci:
1. `@jsverse/transloco` o `ngx-translate` (runtime, senza reload) — ma non sono nella UI-SPEC
2. Attributo `i18n` Angular + server-side locale selection (lingua servita via SSR in base a header/cookie) — richiede due build separati o un approccio di lazy chunk per locale
3. Approccio ibrido: UI-SPEC dice `loadLocaleData()` — questo funziona per formati (date, numeri) ma NON per testi i18n compilati. I testi devono essere gestiti via un meccanismo diverso.

**Raccomandazione:** Per rispettare UI-07 (toggle senza reload) con `@angular/localize`, il planner deve scegliere tra: (a) gestire testi i18n tramite `@jsverse/transloco` (runtime, no reload) oppure (b) mantenere `@angular/localize` ma accettare che solo formati (date/numeri) cambino senza reload — i testi richiedono il reload. La UI-SPEC dice `@angular/localize`; l'approccio più fedele senza librerie extra è **serving locale-specific bundles dal SSR server** (Angular supporta i18n multi-locale via `localize` + `build` separati per locale). Questo è il pattern ufficiale Angular. `[ASSUMED: comportamento esatto loadLocaleData per testi i18n — richiedere conferma utente se "nessun reload" è hard requirement per i testi o solo per i formati]`

### Pattern 6: Angular Material 3 + Tailwind v4 — Evitare Conflitti

```scss
/* styles.scss — import order CRITICO */
/* Tailwind v4: singolo import CSS, no @tailwind directives */
@import "tailwindcss";

/* Dopo Tailwind: Angular Material theme */
@use '@angular/material' as mat;

/* Design tokens SFT come CSS custom properties */
:root {
  --sft-surface: #121418;
  /* ... */
}

/* PROBLEMA: Angular Material usa !important in alcuni stili MDC.
   SOLUZIONE: Usare @layer di Tailwind v4 per precedenza esplicita.
   Tailwind v4 usa layers CSS natively. */
@layer utilities {
  .mat-mdc-button {
    min-height: 64px; /* touch target override */
  }
}
```

**Conflitto noto:** Angular Material 3 (MDC) e Tailwind v4 possono avere conflitti su `box-sizing`, `border-color`, e `font-family`. Il preflight di Tailwind v4 resetta gli stili globali. Soluzione: Angular Material applica stili via Sass mixin che non vengono resettati dal preflight se importati dopo. L'ordine `@import "tailwindcss"` prima di `@use '@angular/material'` è corretto. `[ASSUMED: comportamento esatto Tailwind v4 preflight con Angular Material 3 — verificare empiricamente in Wave 0]`

### Pattern 7: KPI SQL Queries su TimescaleDB

```sql
-- OEE (Availability): da maintenance.downtime_events + oee_hourly CAGG
-- Reusa la logica già in mnt_downtime_analyzer.oee.compute_availability
-- OEE.A = (window_min - downtime_min) / window_min
WITH window_params AS (
  SELECT
    NOW() - INTERVAL '8 hours' AS w_start,
    NOW() AS w_end,
    480.0 AS planned_min  -- turno 8h
),
downtime AS (
  SELECT COALESCE(SUM(duration_min), 0) AS total_down
  FROM maintenance.downtime_events, window_params
  WHERE timestamp BETWEEN w_start AND w_end
)
SELECT ROUND(
  GREATEST(0.0, (planned_min - total_down) / planned_min * 100.0)::numeric, 1
) AS oee_availability_pct
FROM window_params, downtime;

-- MTTR: tempo medio di ripristino = AVG(duration_min) per severity IN ('major','critical')
SELECT ROUND(AVG(duration_min)::numeric, 1) AS mttr_min
FROM maintenance.downtime_events
WHERE timestamp > NOW() - INTERVAL '30 days'
  AND severity IN ('major', 'critical');

-- MTBF: tempo medio tra guasti = window_hours / COUNT(eventi critici)
SELECT ROUND(
  (EXTRACT(EPOCH FROM INTERVAL '30 days') / 3600.0 /
   NULLIF(COUNT(*), 0))::numeric, 1
) AS mtbf_hours
FROM maintenance.downtime_events
WHERE timestamp > NOW() - INTERVAL '30 days'
  AND severity IN ('major', 'critical');

-- Throughput: da scm.historical_orders (quantity_kg per turno)
SELECT ROUND(
  COALESCE(SUM(quantity_kg) / 8.0, 0)::numeric, 1
) AS throughput_kg_per_hour
FROM scm.historical_orders
WHERE order_date >= NOW() - INTERVAL '1 day';

-- Downtime %: (total_downtime_min / planned_min) * 100
-- Scrap rate: proxy da audit.actions QUALITY_VERDICT
-- evidence_panel->'tool_calls'->0->'result'->>'score' (vedi repository.py Phase 7)
SELECT ROUND(
  (1.0 - AVG(
    (evidence_panel->'tool_calls'->0->'result'->>'score')::float
  )) * 100.0::numeric, 1
) AS scrap_rate_pct
FROM audit.actions
WHERE ts > NOW() - INTERVAL '8 hours'
  AND action_type = 'QUALITY_VERDICT';
```

**Nota:** L'OEE completo (A × P × Q) richiede sensor_events per il componente Performance. Per Phase 10, OEE viene calcolato come Availability-only con P=1.0 e Q dal proxy audit QUALITY_VERDICT (identico a quanto già fa DowntimeAnalyzer in Phase 7). Il planner deve documentare questa approssimazione. `[ASSUMED: throughput baseline da scm.historical_orders — verificare se il seed Phase 9 ha dati sufficienti]`

### Anti-Pattern da Evitare

- **EventSource su SSR server:** chiamare `new EventSource()` nel costruttore di un servizio Angular senza guard `isPlatformBrowser` causa crash del Node.js SSR server. SEMPRE guardare con `isPlatformBrowser(PLATFORM_ID)`.
- **JWT in localStorage su SSR:** localStorage non è disponibile durante il server-side rendering. Il service Angular deve leggere il token SOLO nel browser. Pattern: `if (isPlatformBrowser(this.platformId)) { localStorage.getItem('jwt') }`.
- **f-string nelle SQL con input utente:** tutti i router existenti usano `$1..$N` — mantenere questo invariante in kpi.py e auth.py.
- **Generic 500 body con str(exc):** applica la regola Phase 8/9 — mai esporre `str(exc)` nel body. Usare messaggi generici come `"internal_server_error"`.
- **Import non esatti in lifespan.py:** quando si aggiunge `jwt_service` o altri componenti alla lifespan, importare con il nome esatto esportato (guardrail CR-01 Phase 8).
- **SSE senza heartbeat:** i proxy (nginx, load balancer) chiudono connessioni idle dopo 60s. Inviare `sse_heartbeat` ogni 30s.
- **SSE dietro proxy senza buffering disabilitato:** se FastAPI è dietro nginx, aggiungere `X-Accel-Buffering: no` nell'header della risposta SSE.
- **ng2-charts@10 con Angular 19:** richiede Angular CDK 21+ — genera ERESOLVE. Usare ng2-charts@8.

---

## Don't Hand-Roll

| Problema | Non Costruire | Usare Invece | Perché |
|----------|---------------|--------------|--------|
| JWT encode/decode | Custom HMAC con hashlib | `PyJWT` | Timing attacks, padding, exp verification |
| SSE response lifecycle | StreamingResponse manuale con try/finally | `sse-starlette EventSourceResponse` | Gestione disconnect, content-type corretto, keepalive |
| OTEL span tracing | Logging manuale con time.time() | `opentelemetry-instrumentation-fastapi` | Propagazione context, auto-instrumentazione |
| Chart rendering Angular | Canvas 2D manuale | `ng2-charts@8 + chart.js` | Responsive, animazioni, tooltip, accessibilità |
| Virtual scroll lista approvazioni | ngFor standard | `@angular/cdk VirtualScrollViewport` | Performance con N > 100 card (HITL-04 queue) |
| Focus trap nei dialog | tabIndex manuale | `@angular/cdk FocusTrap` | WCAG 2.1 AA keyboard navigation |
| TypeScript types da Pydantic | Sync manuale | `openapi-typescript` CLI su OpenAPI export | Garantisce type-safety SRV-05 senza duplicazione |

**Insight chiave:** Non costruire un sistema di autenticazione da zero neanche in dev-mode. PyJWT con una chiave simmetrica è sufficiente e resistente ai bug di implementazione più comuni.

---

## Common Pitfalls

### Pitfall 1: EventSource + SSR crash
**Cosa va storto:** Angular SSR (Node.js) non ha `EventSource` nativo. Se un service Angular chiama `new EventSource()` durante il rendering server-side, il processo crasha con `ReferenceError: EventSource is not defined`.
**Causa radice:** Mancanza della guardia `isPlatformBrowser` nel service SSE.
**Come evitare:** Sempre `if (!isPlatformBrowser(this.platformId)) return;` come prima istruzione di qualsiasi metodo che usa API browser.
**Segnali d'allarme:** Crash del server Express durante il prerendering; errore `EventSource is not defined`.

### Pitfall 2: ng2-charts versione incompatibile
**Cosa va storto:** `pnpm add ng2-charts` installa la versione latest (v10), che richiede `@angular/cdk>=21`. Il workspace ha Angular 19.2. Il build fallisce con ERESOLVE.
**Causa radice:** npm/pnpm non pin la versione — installa latest per default.
**Come evitare:** Specificare esattamente `ng2-charts@^8.0.0` nell'installazione.
**Segnali d'allarme:** `ERESOLVE unable to resolve dependency tree` con `peer @angular/common@"^21.0.0"`.

### Pitfall 3: Tailwind v4 + Angular Material conflitti CSS
**Cosa va storto:** Il preflight CSS di Tailwind v4 resetta `border-color`, `font-family` e `box-sizing`. Angular Material MDC si aspetta alcuni di questi valori. Risultato: button e form field con stili visibilmente degradati.
**Causa radice:** Tailwind v4 applica preflight globalmente; Angular Material non usa `!important` per tutti gli stili base.
**Come evitare:** (1) Importare `@import "tailwindcss"` PRIMA di `@use '@angular/material'` in styles.scss; (2) usare `@layer utilities { ... }` per override specifici; (3) testare la resa visuale in Wave 0 prima dell'implementazione completa.
**Segnali d'allarme:** mat-button senza altezza minima; form-field senza bordo; font Inter non applicato.

### Pitfall 4: i18n Angular — testi statici non cambiano senza reload
**Cosa va storto:** `@angular/localize` con file xlf compila le traduzioni a build-time. `loadLocaleData()` aggiorna solo formati (date, numeri, currency) — NON i testi tradotti. Il toggle "IT/EN" aggiorna i formati ma non i label UI.
**Causa radice:** L'i18n built-in di Angular è compile-time per i testi; runtime solo per formati.
**Come evitare:** Scegliere esplicitamente una delle due strategie: (a) Angular i18n multi-build (un bundle per locale, SSR serve la locale corretta), oppure (b) libreria runtime (transloco). Documentare la scelta nel PLAN.md.
**Segnali d'allarme:** Click su "EN" aggiorna il formato della data ma non "Accedi" → "Sign In".

### Pitfall 5: SSE dietro proxy — connessione si chiude dopo 60s
**Cosa va storto:** nginx con configurazione default bufferizza le risposte e chiude le connessioni idle dopo 60s. Le SSE sembrano funzionare ma si disconnettono periodicamente.
**Causa radice:** `proxy_buffering on` in nginx + timeout predefinito.
**Come evitare:** Aggiungere `response.headers["X-Accel-Buffering"] = "no"` nella risposta SSE FastAPI + heartbeat ogni 30s.
**Segnali d'allarme:** Dashboard si "congela" ogni 60s; indicatore SSE torna "Non connesso".

### Pitfall 6: Generic 500 body con str(exc) — guardrail Phase 8/9
**Cosa va storto:** `raise HTTPException(500, detail=str(exc))` espone stack traces, nomi di file, DSN del database nel body HTTP.
**Causa radice:** Comodità di debug in sviluppo, dimenticata in produzione.
**Come evitare:** In tutti i nuovi router (auth.py, sse.py, kpi.py): usare `detail="internal_server_error"` generico + loggare il dettaglio via structlog.
**Segnali d'allarme:** Response body con `asyncpg.exceptions.UniqueViolationError` o path file Python.

### Pitfall 7: JWT in localStorage + hydration SSR
**Cosa va storto:** Il service Angular legge `localStorage.getItem('jwt')` durante la costruzione del service. Sul server SSR, `localStorage` non esiste → `ReferenceError`.
**Causa radice:** Accesso a localStorage senza guard browser.
**Come evitare:** Leggere localStorage SOLO in `ngOnInit` o con `isPlatformBrowser` guard. Sul SSR server, il service restituisce `null` come stato auth → Angular renderizza la login page (corretto per SSR).

---

## KPI Computation SQL — Riepilogo

Tutte le query KPI sono calcolate nel router `kpi.py` tramite asyncpg. Le fonti dati sono:

| KPI | Fonte primaria | Formula |
|-----|----------------|---------|
| OEE Availability | `maintenance.downtime_events` | `(planned_min - SUM(duration_min)) / planned_min` |
| OEE (completo) | `maintenance.oee_hourly` CAGG (se window hour-aligned) | A × P(=1.0 fallback) × Q |
| MTTR | `maintenance.downtime_events` WHERE severity IN ('major','critical') | `AVG(duration_min)` |
| MTBF | `maintenance.downtime_events` WHERE severity IN ('major','critical') | `window_hours / COUNT(*)` |
| Scrap Rate | `audit.actions` WHERE action_type='QUALITY_VERDICT' | `1 - AVG(evidence_panel->tool_calls->0->result->score)` |
| Throughput | `scm.historical_orders` | `SUM(quantity_kg) / window_hours` |
| Downtime % | `maintenance.downtime_events` | `SUM(duration_min) / planned_min * 100` |

Il proxy Quality da `audit.actions` è la stessa logica già usata in Phase 7 `repository.py:QualityVerdictReader`. Il codice esistente può essere estratto in un modulo condiviso o duplicato in `kpi/queries.py`.

---

## State of the Art

| Vecchio Approccio | Approccio Corrente | Cambiato | Impatto |
|-------------------|-------------------|---------|---------|
| NgRx per state management Angular | Angular Signals + injectable services | Angular 16+ | Meno boilerplate, nativo, nessuna dipendenza aggiuntiva |
| RxJS Subject per SSE | Signal wrappato da EventSource | Angular 17+ (Signals stable) | computed() per KPI derivati senza subscribe manuali |
| Tailwind v3 (tailwind.config.js) | Tailwind v4 (CSS-first, @import) | Tailwind v4.0 (2025) | No config file JS — tutto in CSS; @layer nativo |
| Angular Material 2 (legacy) | Angular Material 3 (MDC-based) | Angular 15+ | Componenti MDC accessibili by default, M3 theming |
| ng2-charts con Chart.js 3 | ng2-charts@8 con Chart.js 4 | 2024 | API aggiornata, tree-shakeable |
| python-jose per JWT in Python | PyJWT | — | python-jose non è mantenuto attivamente dal 2022; PyJWT è l'alternativa raccomandata |

**Deprecato/outdated:**
- `python-jose`: ultima release 3.5.0 a maggio 2023; mantenimento ridotto. PyJWT è preferito.
- `ng2-charts@10+`: richiede Angular 21, non usabile con Angular 19 workspace.
- `EventSource` senza guard SSR: pattern da non usare mai in Angular SSR.
- `ngx-translate`: ancora valido ma non nella UI-SPEC; non introduce senza esplicita richiesta.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework backend | pytest 8 + pytest-asyncio (già configurato) |
| Framework frontend | Jest + jest-preset-angular (già configurato) |
| Framework E2E | Playwright via @nx/playwright (da installare) |
| Config backend | `apps/api-gateway/pyproject.toml` [tool.pytest.ini_options] |
| Config frontend Jest | `apps/factory-ui/jest.config.ts` |
| Config Playwright | `apps/factory-ui/playwright.config.ts` (Wave 0 gap) |
| Quick run backend | `cd apps/api-gateway && uv run pytest tests/unit/ -x` |
| Full suite backend | `cd apps/api-gateway && uv run pytest tests/ -x` |
| Quick run frontend | `nx test ui-factory --testPathPattern=auth` |
| Full suite frontend | `nx test ui-factory` |
| E2E run | `nx e2e ui-factory-e2e` |

### Phase Requirements → Test Map

| Req ID | Comportamento | Test Type | Comando |
|--------|--------------|-----------|---------|
| SRV-01 | POST /auth/login ritorna JWT valido | unit | `pytest tests/unit/test_auth_router.py -x` |
| SRV-01 | RBAC 403 su endpoint non autorizzato | unit | `pytest tests/unit/test_rbac.py -x` |
| SRV-02 | SSE /v1/stream/kpi emette eventi kpi_update | integration | `pytest tests/integration/test_sse.py -x` |
| SRV-04 | /v1/health ritorna 200 + dependencies | unit (esistente) | `pytest tests/unit/test_health.py -x` |
| SRV-05 | TypeScript types corrispondono a Pydantic models | contract | `nx run ui-factory:check-types` |
| UI-01 | Route /operator accessibile solo con role=operator | unit Jest | `nx test ui-factory --testPathPattern=rbac.guard` |
| UI-03 | ApprovalCard renderizza evidence panel | unit Jest | `nx test ui-factory --testPathPattern=approval-card` |
| UI-04 | KpiTile riceve aggiornamento SSE e aggiorna Signal | unit Jest | `nx test ui-factory --testPathPattern=sse.service` |
| UI-07 | LocaleService.switchToEnglish() aggiorna formati | unit Jest | `nx test ui-factory --testPathPattern=locale.service` |
| UI-10 | Flusso HITL completo (login → approve → audit) | E2E Playwright | `nx e2e ui-factory-e2e` |
| HITL-07 | Motivazione obbligatoria (min 10 char) validata | unit Jest | `nx test ui-factory --testPathPattern=motivation` |
| HITL-10 | Rate-limit banner visibile dopo 12 alert/ora | unit Jest | `nx test ui-factory --testPathPattern=alert-feed` |

### Wave 0 Gaps

- [ ] `apps/factory-ui/playwright.config.ts` — config Playwright con baseURL, webServer
- [ ] `apps/factory-ui-e2e/` — progetto Nx Playwright (via `nx g @nx/playwright:configuration`)
- [ ] `apps/api-gateway/tests/unit/test_auth_router.py` — test JWT login + RBAC
- [ ] `apps/api-gateway/tests/unit/test_sse.py` — test SSE generator (mock asyncio)
- [ ] `apps/api-gateway/tests/unit/test_kpi_queries.py` — test query KPI (mock pool)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | api-gateway | ✓ | 3.12.x (pyproject.toml constraint) | — |
| uv | Package manager Python | ✓ | (workspace usa uv) | — |
| pnpm | Package manager Node | ✓ | (workspace usa pnpm) | — |
| Node.js | Angular build | ✓ | v24.11.0 | — |
| PostgreSQL + TimescaleDB | KPI queries | ✓ (Docker Compose) | 2.18.0-pg16 | — |
| NATS | Alert push SSE | ✓ (Docker Compose) | — | SSE senza alert NATS |
| Playwright browsers | E2E tests | ? | — | `npx playwright install` in Wave 0 |

**Missing dependencies con no fallback:**
- Browser Playwright (Chromium) — da installare in Wave 0: `npx playwright install chromium`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | PyJWT HS256, SEEDED_USERS, TOKEN_EXPIRE_HOURS=8 |
| V3 Session Management | Parzialmente | JWT stateless, no server-side session; refresh token → Phase 11 |
| V4 Access Control | yes | RoleChecker FastAPI dependency + Angular RbacGuard |
| V5 Input Validation | yes | Pydantic `extra=forbid`, tz-aware datetime validators (guardrail Phase 8/9) |
| V6 Cryptography | yes | HS256 via PyJWT — mai hand-roll HMAC; SECRET_KEY da env var |

### Threat Pattern per Stack

| Pattern | STRIDE | Mitigazione Standard |
|---------|--------|---------------------|
| JWT secret in codice | Tampering / Info Disclosure | `API_SECRET_KEY` da env var; `.env.example` documentato; nessun valore default in produzione |
| SQL injection in kpi.py | Tampering | Parametri `$1..$N` asyncpg ONLY; no f-string in SQL (guardrail T-V5-sql) |
| RBAC bypass via body field | Elevation of Privilege | Eliminare `user_roles` dal body — usare solo JWT claim `role` (CONTEXT.md decision) |
| SSE token exposure in URL | Info Disclosure | Preferire Authorization header su SSE — se non possibile (EventSource non supporta custom headers), usare short-lived SSE token separato `[ASSUMED: verifica browser compatibility]` |
| Generic 500 body | Info Disclosure | `detail="internal_server_error"` + structlog logging (guardrail Phase 8/9) |
| HITL bypass via approvals | Tampering | Approvals router esistente mantiene triplo layer di difesa (SELECT+UPDATE atomico + idempotency cache) |
| Motivazione vuota | Repudiation | HITL-07 già enforced in approvals.py + validazione Angular (min 10 char textarea) |

**Nota sui guardrail Phase 8/9 applicabili al backend Phase 10:**
1. **CR-01 Import esatti:** ogni class importata in lifespan.py deve usare il nome esatto esportato (es. `JwtService` non `jwt_service`)
2. **CR-02 Corpo 500 generico:** `detail="internal_server_error"` — mai `str(exc)`
3. **CR-03 Pydantic `extra=forbid` + `frozen=True`:** su tutti i modelli request/response nuovi
4. **CR-04 Datetime tz-aware:** validatori che rifiutano datetime naive
5. **CR-05 SQL parametrizzato:** `$1..$N` in tutti i nuovi file SQL (auth.py seeds, kpi.py queries)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `@angular/localize loadLocaleData()` supporta switch runtime per testi i18n senza reload | Standard Stack, Pitfall 4 | Testi UI non cambiano al toggle EN → richiede libreria alternativa o multi-build |
| A2 | `opentelemetry-instrumentation-fastapi` ha versione compatibile con `fastapi>=0.115` | Standard Stack | Conflitto import a startup → OTEL spans non funzionano |
| A3 | SSE token via query param (`?token=...`) è accettabile per Phase 10 (full auth → Phase 11) | Security Domain | Exposure token in access log server → da mitigare in Phase 11 |
| A4 | throughput da `scm.historical_orders` ha dati sufficienti dal seed Phase 9 | KPI SQL | Dashboard throughput mostra 0 → KPI non dimostrabile |
| A5 | Il proxy quality da `audit.actions QUALITY_VERDICT` produce scrap_rate >= 0 con seed esistente | KPI SQL | Scrap rate KPI sempre null → fallback a valore statico |
| A6 | Tailwind v4 preflight non rompe i componenti Angular Material con l'ordine di import consigliato | Pitfall 3 | Stili visual degradati → richiede override SCSS aggiuntivi |
| A7 | `@jsverse/transloco` non è necessario — `@angular/localize` è sufficiente per i requisiti UI-07 | i18n Pattern | Testi non cambiano senza reload → esperienza utente degradata al toggle lingua |

---

## Open Questions (RESOLVED — see 10-CONTEXT.md post_research_resolutions)

1. **i18n runtime switch per testi UI**
   - Cosa sappiamo: `@angular/localize` con `loadLocaleData()` aggiorna formati (date, numeri) ma NON testi compilati. La UI-SPEC dice "nessun page reload".
   - Cosa non è chiaro: l'utente accetta che solo i formati cambino senza reload (testi richiedono reload o multi-build)? O vuole testi runtime tramite transloco?
   - Raccomandazione: Il planner deve inserire un task Wave 0 che chiarisce questa scelta. Default: Angular i18n multi-build con SSR locale detection (pattern ufficiale Angular per i18n SSR).

2. **SSE auth token — header vs query param**
   - Cosa sappiamo: `EventSource` browser non supporta custom HTTP headers natively. L'alternativa è: (a) token in query param (insicuro, esposto in log), (b) cookie HttpOnly (SSR-friendly), (c) short-lived SSE ticket.
   - Cosa non è chiaro: Phase 10 è dev-mode auth — cookie vs query param è tradeoff DX vs sicurezza.
   - Raccomandazione: usare query param per Phase 10 dev-mode, documentare come A3 per hardening Phase 11.

3. **Playwright config in Nx workspace**
   - Cosa sappiamo: `@nx/playwright@20.8.4` è disponibile e allineato al workspace.
   - Cosa non è chiaro: se il progetto E2E deve essere `apps/factory-ui-e2e/` (pattern Nx standard) o configurato direttamente in `factory-ui`.
   - Raccomandazione: creare `apps/factory-ui-e2e/` come progetto separato via `nx g @nx/playwright:configuration --project=ui-factory`.

---

## Sources

### Primary (HIGH confidence)
- `apps/api-gateway/pyproject.toml` — versioni dipendenze backend esistenti
- `apps/factory-ui/project.json` + `package.json` root — configurazione Angular 19.2 SSR, versioni npm
- `infra/migrations/timescale/008_create_downtime_events.sql` — schema maintenance.downtime_events e oee_hourly CAGG
- `infra/migrations/timescale/011_create_scm_schema.sql` — schema scm.*
- `infra/migrations/timescale/003_create_audit_actions.sql` — schema audit.actions + evidence_panel JSONB
- `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py` — formula OEE esistente
- `.planning/phases/10-backend-api-frontend/10-CONTEXT.md` — decisioni locked
- `.planning/phases/10-backend-api-frontend/10-UI-SPEC.md` — contratto design
- `.planning/phases/09-agents-supply-chain-economics/09-REVIEW.md` — guardrail review catalog

### Secondary (MEDIUM confidence)
- `npm view ng2-charts@8 peerDependencies` — compatibilità Angular 19 confermata
- `npm view @angular/material@"~19.2.0" version` — versioni disponibili
- `pip index versions PyJWT` — versione 2.13.0 disponibile su PyPI
- `pip index versions sse-starlette` — versione 3.4.4 disponibile su PyPI
- `pip index versions opentelemetry-sdk` — versione 1.42.1 disponibile su PyPI
- slopcheck v0.6.1 — audit pacchetti npm frontend ([OK] su tutti i 6 pacchetti frontend)

### Tertiary (LOW confidence / ASSUMED)
- Comportamento Angular `@angular/localize loadLocaleData()` per testi runtime (A1)
- Compatibilità esatta `opentelemetry-instrumentation-fastapi` con FastAPI 0.115 (A2)
- Assenza conflitti critici Tailwind v4 preflight + Angular Material 3 MDC (A6)

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — versioni verificate via npm registry e PyPI
- Architecture: HIGH — scaffold esistente ispezionato, pattern confermati da codice Phase 7-9
- KPI SQL: MEDIUM — basato su schemi verificati, formule adattate da oee.py esistente
- i18n: LOW-MEDIUM — comportamento runtime Angular localize non verificato via Context7
- Pitfalls: HIGH — verificati da ispezione diretta del codice + errore npm ERESOLVE osservato live

**Research date:** 2026-05-24
**Valid until:** 2026-06-24 (Angular 19.x LTS, stabile per 30+ giorni)

---

## Decomposizione a Onde Raccomandata

Il planner costruisce i piani seguendo questa sequenza di onde. I file modificati in ogni onda devono essere disgiunti con quelli delle onde parallele all'interno della stessa wave. L'esecuzione è SEQUENZIALE sul main tree.

| Onda | Contenuto | File Principali |
|------|-----------|-----------------|
| Wave 0 | Scaffolding test + installazione dipendenze | `pyproject.toml`, `package.json`, `playwright.config.ts`, stub test files |
| Wave 1 | Backend fondamenta: JWT + RBAC (auth.py, security/) | `routers/auth.py`, `security/jwt.py`, `security/rbac.py`, `dependencies.py` (extend), `lifespan.py` (extend) |
| Wave 2 | Backend KPI aggregations (kpi.py, queries.py) | `routers/kpi.py`, `kpi/queries.py` |
| Wave 3 | Backend SSE (sse.py) + OTEL middleware | `routers/sse.py`, `main.py` (OTEL middleware), migration 013 (auth_users seed) |
| Wave 4 | Frontend fondamenta: Angular Material + Tailwind + shell | `styles.scss`, `_tokens.scss`, `_theme.*.scss`, `app-shell.component`, `top-bar`, `nav-rail`, `bottom-nav`, `app.routes.ts` |
| Wave 5 | Frontend core services: auth + SSE + i18n + theme | `core/auth/`, `core/sse/`, `core/i18n/`, `core/theme/`, `jwt.interceptor.ts`, `rbac.guard.ts` |
| Wave 6 | Frontend HITL UI: login + approval-card + evidence panel | `auth/login.component`, `shared/approval-card/`, `shared/kpi-tile/`, `shared/alert-feed/` |
| Wave 7 | Frontend features: operator + manager dashboard + demo walkthrough | `features/operator/`, `features/manager/`, `features/technician/`, `features/admin/`, `features/demo/` |
| Wave 8 | Playwright E2E: configurazione + HITL full flow test | `apps/factory-ui-e2e/`, `playwright.config.ts`, `hitl-flow.spec.ts` |
| Wave 9 | Contract test Pydantic↔TS + docs/screenshots CI | `packages/sft-contracts/` (openapi-typescript output), CI step screenshot |
