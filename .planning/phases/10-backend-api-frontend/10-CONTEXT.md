# Phase 10: Backend API & Frontend - Context

**Gathered:** 2026-05-24
**Status:** Ready for UI-SPEC + planning
**Mode:** Interactive discuss (4 architectural gray areas resolved with user)

<domain>
## Phase Boundary

Production-ready FastAPI gateway (JWT/RBAC, SSE streaming, OpenAPI, health/readiness, OTEL spans) + Angular 18+ SSR application: HITL approval UI with inline evidence panel, control room dashboard with live KPIs, bilingual i18n (IT default / EN), touch-friendly factory-floor design (≥64px targets), dark/light WCAG AA, and Playwright E2E for the HITL approval flow.

Requirements: API/backend + HITL-01..10 (approval queue, evidence panel, escalation, audit, governor, rate-limit), UI-01..10.

**Out of scope (deferred):** full auth hardening — real IdP/Keycloak, refresh tokens, JWKS rotation, complete OWASP — → Phase 11. OTEL/Langfuse full observability stack (OBS-01..07) → Phase 11 (this phase adds OTEL spans on endpoints only).
</domain>

<decisions>
## Implementation Decisions

### Auth / RBAC (gray area 1) — LOCKED
JWT dev-mode + seeded persona users + RBAC guards.
- FastAPI issues working JWTs (HS256 dev secret) on a /auth/login endpoint backed by seeded persona users: operator, shift-supervisor, technician, CIO (+ admin). Role claims in the token.
- Angular route guards per persona area (operator/, technician/, manager/, admin/ per UI-01); FastAPI dependency enforces RBAC per endpoint, replacing the dev-mode `user_roles` body field used in Phases 6-9 where appropriate (keep backward-compatible until routes migrate).
- HITL escalation tiers (HITL-02): Operator → Supervisor → Manager → Safety Interlock map to roles.
- **Deferred to F11:** real IdP/Keycloak, refresh tokens, JWKS rotation, full OWASP hardening.
- **Why:** satisfies the "operator persona can log in" success criterion without standing up external identity infra, and aligns with the SEC/RBAC hardening already deferred to Phase 11.

### Streaming (gray area 2) — LOCKED
SSE primary for live KPIs + alert/approval push.
- Server-Sent Events (text/event-stream) for control-room KPI updates and pushing new pending-approval/alert events to the operator UI. Native auto-reconnect; works cleanly behind proxies.
- HITL actions (approve/reject with mandatory motivation HITL-07) remain POST REST against the existing approvals router.
- Rate-limit alarm (HITL-10: max 12 alerts/hour/persona) enforced server-side on the SSE alert channel.
- **Why:** KPI + alert push is one-way server→client; SSE is simpler/robust than WebSocket and covers every success criterion. WebSocket only if a future bidirectional need appears.

### Angular state management (gray area 3) — LOCKED
Signals + injectable services. No NgRx.
- Angular 18 signals for component/view state; injectable services hold shared state (auth, SSE streams as signals, i18n). computed() for derived KPIs.
- **Why:** lighter, idiomatic modern Angular, far less boilerplate at this scale.

### Dashboard data (gray area 4) — LOCKED
Real FastAPI aggregations over TimescaleDB.
- KPI endpoints (OEE, MTTR, MTBF, scrap rate, throughput, downtime — UI-04) compute from existing data: audit.actions, maintenance.downtime_events, scm.*, sensor_events, fed by the synthetic seeds from prior phases.
- **Why:** end-to-end coherent, demonstrable data; no mock divergence. The persona walkthrough (UI-08) shows real wired data.

### Carried forward / cross-cutting (NOT re-discussed)
- Monorepo scaffolds exist: `apps/factory-ui` (Angular SSR — main.server.ts/server.ts/app.config.server.ts present) and `apps/api-gateway` (FastAPI; already has approvals.py, health.py, threads.py + agent routers from Phases 6-9).
- Reuse existing `approvals.py` + `threads.py` HITL endpoints; evidence panel (HITL-06, UI-03) renders input + tool calls + RAG citations + confidence from the audit evidence_panel JSONB already produced by agents.
- Design: Tailwind + Angular Material, touch targets ≥64px (UI-02), dark/light WCAG AA (UI-05). i18n IT default, EN toggle without reload, lazy-loaded locale (UI-07).
- API contract: OpenAPI export; Pydantic↔TypeScript type contract test (success criterion).
- Health/readiness probes + OTEL spans on endpoints (full OTEL/Langfuse stack → Phase 11).
- Playwright E2E: full HITL approval flow (alert → approval card → evidence review → approve → audit record) in CI (UI-10).
- Bilingual mock-UI docs with auto-generated screenshots in CI (UI-09) — screenshot generation may be a human/CI-hardware item.
- Execution: worktrees DISABLED — sequential executors on main tree. Apply all Phase 8/9 review guardrails (exact imports, generic error bodies, input validation at boundaries, no secrets).
</decisions>

<code_context>
## Existing Code Insights

- `apps/factory-ui/` — Angular 18 SSR scaffold ready (main.ts, main.server.ts, server.ts, app.config.ts, app.config.server.ts, app.routes.ts). Build via @nx/angular plugin. Jest configured.
- `apps/api-gateway/src/svc_api_gateway/` — routers/: approvals.py, health.py, threads.py, + ops/maintenance/knowledge/supply agent routers, quality.py. lifespan.py builds cluster subgraphs + DI. main.py includes routers.
- Auth currently dev-mode (`user_roles` field on request models). Phase 10 introduces JWT issuance + RBAC dependency.
- KPI source tables: audit.actions, maintenance.downtime_events (OEE/MTTR/MTBF/downtime), scm.* (throughput/inventory), sensor_events (scrap/quality via quality.py).
- HITL evidence: agents already write evidence_panel JSONB into audit.actions (TRN-05 / build_evidence_panel pattern).
</code_context>

<specifics>
## Specific Ideas
- Personas: operator, shift-supervisor, technician, CIO (+ admin) — seeded users, each lands on their area.
- Default language Italian; English toggle without page reload.
- Touch targets ≥64px (factory floor / gloved operation).
- Persona walkthrough demo navigable in-app (UI-08).
</specifics>

<canonical_refs>
## Canonical References (downstream agents MUST read)
- `.planning/REQUIREMENTS.md` — HITL-01..10, UI-01..10, API/gateway, partial OBS (spans only).
- `.planning/ROADMAP.md` — Phase 10 goal + 5 success criteria.
- `apps/api-gateway/src/svc_api_gateway/routers/approvals.py` + threads.py — existing HITL endpoints to build on.
- `apps/factory-ui/src/app/` — Angular SSR scaffold.
- `.planning/phases/08-agents-knowledge-training/08-REVIEW.md` + `09-REVIEW.md` — review-lesson guardrails (exact imports, generic 500 body, tz validators, input validation, no secret leak).
- Phase 11 owns: full auth hardening, OTEL/Langfuse stack, OWASP — do NOT duplicate here.
</canonical_refs>

<deferred>
## Deferred Ideas
- Real IdP/Keycloak, refresh tokens, JWKS rotation, full OWASP LLM/web hardening → Phase 11.
- Full OTEL/Langfuse/LGTM observability stack + Grafana dashboards + evals → Phase 11.
- WebSocket bidirectional channel — only if a real client→server realtime need emerges (not now).
</deferred>
