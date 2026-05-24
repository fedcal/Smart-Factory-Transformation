---
phase: 10-backend-api-frontend
slug: backend-api-frontend
status: verified
threats_total: 31
threats_open: 0
asvs_level: 2
created: 2026-05-24
---

# Phase 10 — Security Audit

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Includes verification of 4 Critical and 7 Warning fixes from 10-REVIEW-FIX.md.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| npm/pip registry → build | Third-party package code entra nel build al momento dell'installazione | Codice di terze parti non verificato |
| client → /auth/login | Credenziali non attendibili attraversano verso il gateway | email + password in chiaro |
| client → endpoint protetti (Bearer) | JWT non attendibile validato da require_roles | JWT firmato HS256 |
| client → /v1/stream/* (token in query) | JWT in query string attraversa verso il gateway | JWT firmato HS256 in URL |
| gateway → TimescaleDB | Query SQL con parametri finestre temporali | Dati operativi aggregati |
| gateway → audit endpoints | Lettura autenticata di audit.actions | Log di audit (dati sensibili) |
| browser → SSR render | Il server renderizza senza dipendere da browser-only globals | Token / localStorage |
| browser → gateway (Bearer / SSE token) | Client allega JWT firmato alle richieste API + stream | JWT in header / query param |
| operator input → approvals API | Testo motivazione + decisione attraversano verso il backend | Decisione HITL + motivazione |
| backend evidence JSONB → render | JSONB non attendibile renderizzato nel pannello | Dati evidence_panel da DB |
| build → generated artifacts | Generazione OpenAPI/TS solo a build-time | Tipi generati da Pydantic |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-10-SC | Tampering | npm/pip installs | mitigate | Package legitimacy audit in 10-RESEARCH; versioni pin esplicitamente (ng2-charts ^8.0.0 nel package.json) | CLOSED |
| T-10-00a-01 | Tampering | ng2-charts resolution | mitigate | Pin esplicito ^8.0.0 + verifica post-install in package.json | CLOSED |
| T-10-00b-01 | Tampering | KPI SQL test | mitigate | test_kpi_queries.py asserisce solo $N params; nessun f-string — verificato in queries.py ($1..$3 su ogni query) | CLOSED |
| T-10-00b-02 | Information Disclosure | auth test | mitigate | test_auth_router.py asserisce body generico; routers/auth.py riga 98: `detail="invalid_credentials"` | CLOSED |
| T-10-01-01 | Spoofing | /auth/login | mitigate | PyJWT HS256; SECRET_KEY da API_SECRET_KEY env; guard avvio in jwt.py righe 38-53 (RuntimeError se non dev e chiave assente) | CLOSED |
| T-10-01-02 | Elevation of Privilege | require_roles | mitigate | Role enforcement da JWT claim firmato; rbac.py riga 58: `payload = decode_token(credentials.credentials)` | CLOSED |
| T-10-01-03 | Information Disclosure | error bodies | mitigate | auth.py riga 98: `detail="invalid_credentials"`; riga 122: `detail="internal_server_error"`; dettagli solo via structlog.error | CLOSED |
| T-10-01-04 | Tampering | JWT secret | mitigate | Nessun segreto hardcoded per produzione; jwt.py riga 38: `os.environ.get("API_SECRET_KEY")`; non loggato | CLOSED |
| T-10-02-01 | Tampering | kpi SQL | mitigate | queries.py: tutti i 6 KPI usano $1..$3 parameters (verificati riga per riga); nessun f-string in SQL | CLOSED |
| T-10-02-02 | Elevation of Privilege | /v1/kpi | mitigate | kpi.py riga 87: `Depends(require_roles(*_KPI_ROLES))` — 4 ruoli dashboard | CLOSED |
| T-10-02-03 | Information Disclosure | error body | mitigate | kpi.py: wrap eccezioni → HTTPException(500,"internal_server_error") + structlog (stesso pattern auth.py) | CLOSED |
| T-10-02-04 | Denial of Service | heavy aggregation | accept | Query bounded-window read-only; rate-limiting completo → Phase 11. Rischio accettato per dev-mode. Vedi Accepted Risks Log AR-01. | CLOSED |
| T-10-03-01 | Information Disclosure | SSE token in URL | accept (dev) / transfer (F11) | Token in query param validato identicamente all'header (rbac.py require_roles_qs); esposizione access-log accettata in dev-mode; HttpOnly cookie → Phase 11. Vedi AR-02. | CLOSED |
| T-10-03-02 | Denial of Service | alert flood | mitigate | sse.py righe 65-82: `_ALERT_RATE_LIMIT=12`; `_alert_rate_state` deque per principal; `rate_limit` event emesso; lifespan.py: warning RuntimeWarning se WEB_CONCURRENCY>1 | CLOSED |
| T-10-03-03 | Denial of Service | idle SSE behind proxy | mitigate | sse.py riga 97: `"X-Accel-Buffering": "no"`; heartbeat ogni 30s su tutti e 3 i canali (righe 147-151, 241-243, 325-326) | CLOSED |
| T-10-03-04 | Elevation of Privilege | stream access | mitigate | sse.py: tutti gli endpoint usano `Depends(require_roles_qs(...))` che chiama `decode_token` identicamente a require_roles | CLOSED |
| T-10-03-05 | Information Disclosure | 500 body SSE | mitigate | sse.py: generic body + structlog per eccezioni inattese (stesso pattern auth/kpi) | CLOSED |
| T-10-04-01 | Denial of Service | SSR crash da browser API | mitigate | app-shell.component.ts riga 9: import isPlatformBrowser; righe 187, 207: guard prima di qualsiasi accesso browser-only | CLOSED |
| T-10-04-02 | Elevation of Privilege | route access | mitigate | app.routes.ts: rbacGuard applicato in ogni feature route file (operator.routes.ts riga 17, admin.routes.ts riga 17, ecc.) | CLOSED |
| T-10-05-01 | Denial of Service | SSR crash | mitigate | sse.service.ts riga 63: `isBrowser = isPlatformBrowser()`; jwt.service.ts riga 39: stessa guard; connect() riga 117: SSR no-op | CLOSED |
| T-10-05-02 | Elevation of Privilege | route access | mitigate | rbac.guard.ts riga 65: inject obbligatorio RBAC_GUARD_SERVICE_TOKEN (nessun optional); riga 84-85: redirect e return false su role mismatch | CLOSED |
| T-10-05-03 | Information Disclosure | token in storage | accept (dev) / transfer (F11) | localStorage token accettabile in dev-mode; HttpOnly cookie → Phase 11. Vedi AR-03. | CLOSED |
| T-10-05-04 | Tampering | client exp check | mitigate | jwt.service.ts: check exp lato client advisory only; server valida firma+exp su ogni richiesta (decode_token in jwt.py) | CLOSED |
| T-10-06-01 | Repudiation | approve/reject | mitigate | approval-card.component.ts riga 77: `MOTIVATION_MIN_LENGTH = 10`; Approve disabilitato fino a validità (riga 223: `[disabled]="!isMotivationValid()"`) | CLOSED |
| T-10-06-02 | Tampering | XSS via evidence JSONB | mitigate | evidence-panel.component.ts: nessun innerHTML nel codice (occorrenza riga 77 è solo commento); source_uri validato con `isValidUri()` riga 61 (solo http/https); interpolazione Angular auto-escaped | CLOSED |
| T-10-06-03 | Information Disclosure | restricted citations | mitigate | evidence-panel.component.ts righe 173-176: `@if (cite.acl_level === 'restricted')` nasconde chunk_preview | CLOSED |
| T-10-06-04 | Elevation of Privilege | decide senza ruolo | mitigate | Backend approvals router + require_roles autoritativo; UI guard secondario (defense in depth) | CLOSED |
| T-10-07-01 | Denial of Service | alert flood UI | mitigate | alert-feed.component.ts: feed capped a RATE_LIMIT=12; rate-limit-banner mostrato su evento rate_limit | CLOSED |
| T-10-07-02 | Tampering | XSS via alert message | mitigate | alert-feed.component.ts: Angular text interpolation auto-escapes; nessun innerHTML | CLOSED |
| T-10-07-03 | Denial of Service | large queue render | mitigate | approval-queue-feed.component.ts: cdk-virtual-scroll-viewport limita le card renderizzate | CLOSED |
| T-10-08-01 | Elevation of Privilege | /manager access | mitigate | manager.routes.ts: rbacGuard con roles shift-supervisor+manager; backend require_roles su /v1/kpi | CLOSED |
| T-10-08-02 | Denial of Service | chart bundle on SSR | mitigate | charts-row.component.ts: lazy-loaded (@defer/lazy route), browser-only | CLOSED |
| T-10-08-03 | Tampering | KPI value render | mitigate | KpiSnapshot tipizzato; interpolazione Angular auto-escapes | CLOSED |
| T-10-09-01 | Information Disclosure | audit log | mitigate | admin.routes.ts riga 17-18: rbacGuard con roles=['admin']; backend require_roles autoritativo | CLOSED |
| T-10-09-02 | Elevation of Privilege | demo access | accept | /demo aperto a tutti gli autenticati per design (dev walkthrough); renderizza solo dati visibili al ruolo loggato. Vedi AR-04. | CLOSED |
| T-10-09-03 | Tampering | audit render | mitigate | Read-only; interpolazione Angular auto-escapes | CLOSED |
| T-10-10-01 | Repudiation | approval audit | mitigate | hitl-flow.spec.ts step 8: asserisce record audit via GET /v1/approvals filtrato per approval_id; verifica decisione + motivazione | CLOSED |
| T-10-10-02 | Tampering | flaky/false-green E2E | mitigate | Spec fallisce esplicitamente se stack non raggiungibile; expect assertions esplicite, nessun best-effort | CLOSED |
| T-10-11-01 | Tampering | type drift | mitigate | contract.spec.ts: confronto byte-identity tra api-types.ts generato e committato; fallisce su divergenza Pydantic↔TS | CLOSED |
| T-10-11-02 | Information Disclosure | screenshots | accept | Screenshot usano solo dati seeded dev (nessuna PII reale). Vedi AR-05. | CLOSED |
| T-10-11-SC | Tampering | openapi-typescript install | mitigate | CLI openapi-typescript vettato; versione pinned; coperto dall'igiene dipendenze 10-00a | CLOSED |

*Status: open · closed*
*Disposition: mitigate (implementazione richiesta) · accept (rischio documentato) · transfer (terze parti)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-10-02-04 (DoS heavy aggregation) | Query bounded-window read-only (8h OEE, 30d MTTR/MTBF); nessun input utente nell'SQL; rate-limiting completo come middleware FastAPI → Phase 11. | Federico / gsd-security-auditor | 2026-05-24 |
| AR-02 | T-10-03-01 (SSE token in URL) | EventSource non può impostare header HTTP. Token query-param validato identicamente all'header via decode_token (stessa firma, stessa scadenza). Esposizione in access-log accettata in dev-mode. Hardening → HttpOnly cookie in Phase 11. | Federico / gsd-security-auditor | 2026-05-24 |
| AR-03 | T-10-05-03 (token in localStorage) | localStorage accettabile in dev-mode per seeded personas. Nessun dato PII reale. HttpOnly cookie + SameSite=Strict → Phase 11. | Federico / gsd-security-auditor | 2026-05-24 |
| AR-04 | T-10-09-02 (demo elevation) | /demo è un dev walkthrough deliberatamente aperto a tutti gli utenticati. Ogni step renderizza il componente del persona loggato, quindi mostra solo dati visibili al ruolo corrente. | Federico / gsd-security-auditor | 2026-05-24 |
| AR-05 | T-10-11-02 (screenshot PII) | Screenshot Playwright usano esclusivamente seeded personas dev (operator@mantis.it, ecc.) con dati sintetici. Nessun PII reale nelle immagini generate. | Federico / gsd-security-auditor | 2026-05-24 |
| AR-06 | SEC-02 (OWASP LLM Top 10) | OWASP LLM Top 10 (prompt injection, sensitive info leak, supply chain) assegnato a Phase 11 in REQUIREMENTS.md riga 348. Phase 10 non introduce agenti LLM — il gateway è solo API REST/SSE. Vettore non applicabile a questa fase. | Federico / gsd-security-auditor | 2026-05-24 |
| AR-07 | WR-05 multi-worker rate-limit | Il rate-limit in-process (_alert_rate_state) non è distribuito. Documentato in lifespan.py con RuntimeWarning se WEB_CONCURRENCY>1. Phase 10 richiede --workers 1 per dev-mode. Backend distribuito (Redis) → Phase 11. | Federico / gsd-security-auditor | 2026-05-24 |

*I rischi accettati non riemergono nelle esecuzioni di audit future.*

---

## Phase 11 Closure — Annotazioni AR-01..AR-07

> Aggiornato in Phase 11 Piano 11-05 (2026-05-25). Nessun threat esistente è stato
> modificato — solo aggiunte le note di chiusura/stato.

| Risk ID | Stato Phase 11 | Documento di chiusura | Note |
|---------|----------------|----------------------|------|
| AR-01 | DOCUMENTATO | `docs/security/rate-limit-scaling.md` | Path evolutivo Redis documentato (RATE_LIMIT_BACKEND=redis). Non implementato in v1.0. |
| AR-02 | RIMANE DEV-MODE | — | SSE token in URL resta accettato per dev-mode. HttpOnly cookie deferred a milestone futura (post v1.0). Il `decode_token` server-side rimane identico — nessun gap funzionale di sicurezza. |
| AR-03 | RIMANE DEV-MODE | — | localStorage token accettato per seeded personas dev-mode. HttpOnly cookie + SameSite=Strict deferred a milestone futura (post v1.0). Nessun PII reale in dev. |
| AR-04 | CHIUSO (design) | — | /demo aperto per design deliberato. Nessun cambiamento in Phase 11. |
| AR-05 | CHIUSO (design) | — | Screenshot con dati sintetici per design. Nessun cambiamento in Phase 11. |
| AR-06 | CHIUSO | `docs/security/owasp-llm-top10.md` | OWASP LLM Top-10 mappato a mitigazioni concrete (LLM01..LLM10). SEC-02 fulfilled. |
| AR-07 | DOCUMENTATO | `docs/security/rate-limit-scaling.md` | Multi-worker limiter documentato con warning in lifespan.py. Redis path architetturale descritto. Non implementato in v1.0. |

---

## Fix Post Code-Review Verificati

I seguenti 4 problemi critici e 7 warning rilevati dalla revisione del codice (10-REVIEW.md) sono stati corretti (10-REVIEW-FIX.md) e verificati in codice:

| Finding | File | Evidenza Fix |
|---------|------|--------------|
| CR-01: SQL injection SSE NOT IN | routers/sse.py | Righe 187-195: `!= ALL($1::text[])` (parametrizzato); nessun f-string in SQL; commit f39a4f8 |
| CR-02: SECRET_KEY silenzioso in produzione | security/jwt.py | Righe 38-53: RuntimeError se API_SECRET_KEY assente e APP_ENV non dev; commit ca66240 |
| CR-03: RBAC guard Angular open-fallback | core/auth/rbac.guard.ts | Riga 65: inject obbligatorio senza optional; riga 84-85: return false esplicito; commit e5bb17d |
| CR-04: URL SSE errato (/v1/stream/events) | auth/login.component.ts | SSE_KPI_URL = '/v1/stream/kpi'; commit fe4dcfc |
| WR-01: inject duplicato in _readFromStorage | core/auth/jwt.service.ts | Usa this.isBrowser invece di re-inject; commit 0c8e56f |
| WR-02: window.confirm SSR-unsafe | approval-card.component.ts | MatDialog.open + isPlatformBrowser guard; commit 1981bf4 |
| WR-03: disconnectedTooLong non reattivo | core/sse/sse.service.ts | _disconnectedTooLongSignal + setTimeout 5s; commit 18216ee |
| WR-04: _subscribeSseResolution corpo vuoto | approval-card.component.ts | toObservable(sseService.approvals) + takeUntilDestroyed; commit c50af4b |
| WR-05: rate-limit multi-worker | lifespan.py | RuntimeWarning se WEB_CONCURRENCY>1; commit 3d7471f |
| WR-06: interceptor non same-origin | core/auth/jwt.interceptor.ts | shouldAttachBearer() controlla startsWith('/') o window.location.origin; commit 51009e6 |
| WR-07: ThemeService DOM in field init | core/theme/theme.service.ts | _readStoredTheme() solo lettura; DOM applicato in afterNextRender(); commit 4cae47a |

---

## Flag Non Registrati (Unregistered Flags)

Nessuna nuova superficie di attacco non mappata rilevata durante l'implementazione. Tutti i Threat Flags dai SUMMARY dei 13 piani corrispondono a threat ID registrati nel threat model.

**Nota:** Il known stub `seen_ids` con f-string (10-03-SUMMARY.md riga 108-110) è stato **corretto** dal fix CR-01 e non rappresenta una superficie aperta.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-24 | 41 | 41 | 0 | gsd-security-auditor (Claude Sonnet 4.6) |

*Nota: il conteggio include i 4 rischi accettati (AR-01..AR-05) e i 2 rischi documentati (AR-06 SEC-02 / AR-07 multi-worker). threats_open è 0 perché tutti hanno disposizione verificata.*

---

## Sign-Off

- [x] Tutti i threat hanno una disposizione (mitigate / accept / transfer)
- [x] Rischi accettati documentati in Accepted Risks Log (AR-01..AR-07)
- [x] `threats_open: 0` confermato
- [x] `status: verified` impostato nel frontmatter
- [x] Fix CR-01..CR-04 e WR-01..WR-07 verificati tramite grep nel codice sorgente
- [x] SEC-02 (OWASP LLM) confermato come deliverable Phase 11 (REQUIREMENTS.md riga 348)
- [x] Limitazione multi-worker rate-limit documentata (AR-07) con warning in lifespan.py

**Approval:** verified 2026-05-24
