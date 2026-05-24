# Phase 11: Observability, Evaluation & Security Hardening - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning
**Mode:** Interactive discuss (4 gray areas resolved with user)

<domain>
## Phase Boundary

End-to-end observability + evaluation + security hardening:
- OTEL instrumentation across all services with trace-ID propagation UI→gateway→NATS→LangGraph→Langfuse (OBS-02), Langfuse self-hosted traces (OBS-01), LGTM stack documented (OBS-03), pre-built Grafana dashboards for agent + factory + cost KPIs (OBS-04/07).
- RAG/agent evals: DeepEval + RAGAS suites with synthetic ground-truth dataset (30+ scenarios/cluster), CI gate on hallucination/relevance thresholds (OBS-05/06).
- Security: STRIDE threat model doc for IT/OT, RAG ingestion, agent orchestration (SEC-01); OWASP LLM Top-10 defenses incl. ingest prompt-injection sanitization (SEC-02/04); RBAC role set incl. supervisor + auditor (SEC-03); secret management + .env.example (SEC-05); OT Bridge data-diode network-policy verified by test (SEC-06); restricted-document access audit log (SEC-07).

**This phase ABSORBS the deferrals from Phases 9/10:** OWASP LLM hardening (SEC-02), JWT hardening direction, RBAC role expansion (SEC-03), multi-worker rate-limit note. Full auth IdP/Keycloak remains future scope (not in this milestone).
</domain>

<decisions>
## Implementation Decisions

### Evaluation strategy + CI gate (gray area 1) — LOCKED
DeepEval + RAGAS, synthetic ground-truth dataset, CI gate with mock/deterministic LLM.
- RAG eval suite (DeepEval + RAGAS) + agent eval (30+ scenarios per cluster), ground-truth dataset synthetic-generated and documented.
- CI gate BLOCKS on hallucination rate >5% OR answer relevance <0.75 (SC-2) — runs with a mock/deterministic LLM for reproducibility (no GPU in CI). A real-Ollama run is an optional/local job.
- **Why:** reproducible CI without GPU; consistent with the mock-based test posture of prior phases. Real-LLM eval is hardware-gated (human/local).

### Trace propagation + Langfuse (gray area 2) — LOCKED
Full propagation + Langfuse self-hosted (docker-compose dev).
- OTEL SDK on agents + OT Bridge + gateway with trace-ID propagation end-to-end (UI→gateway→NATS→LangGraph→Langfuse), including OTEL context injection/extraction on NATS messages.
- Langfuse v3 self-hosted via `infra/compose/obs.yml` (extend existing) for dev; Helm prod documented. Reuse existing `packages/sft-agents/.../llm/langfuse_callback.py`.
- **Why:** realizes SC-1 (single correlated trace with LLM token counts, latency, HITL metadata).

### Prompt-injection defense in ingest (gray area 3) — LOCKED
Structural sanitization + denylist of known patterns (deterministic, no LLM).
- Ingest pipeline sanitization: strip known injection patterns ("ignore previous instructions", role delimiters, imperative instruction blocks), neutralize markdown/HTML, treat document content as data not instructions. CI security test feeds a crafted prompt-injection PDF and asserts no agent action is influenced (SC-3).
- **Why:** deterministic, testable, CI-gateable, no LLM dependency. (An LLM classifier was considered and rejected for CI reproducibility.)

### OT Bridge data-diode test + Grafana (gray area 4) — LOCKED
App-level guard test (CI-runnable) + real Grafana provisioning JSON.
- SEC-06: automated test asserting a write command from the agent layer toward OPC-UA is blocked by the OT Bridge guard/whitelist (application-level, runnable in CI without OT hardware). Network-policy (Docker) verification documented as a complementary live check.
- Grafana: real provisioning dashboard JSON (agent KPIs + factory KPIs + cost dashboard p50/p95/p99 — OBS-04/07); LGTM stack via compose documented (OBS-03 optional).
- **Why:** executable and demonstrable in CI; complements the existing OT Bridge in `services/ot-bridge/`.

### Carried forward / cross-cutting (NOT re-discussed)
- Reuse existing foundations: `infra/compose/obs.yml`, `services/ot-bridge/`, `packages/sft-agents/.../llm/langfuse_callback.py`, `apps/api-gateway` OTEL middleware (Phase 10 endpoint spans → extend to full propagation).
- SEC-03 RBAC: extend the Phase 10 role set (operator/shift-supervisor/technician/CIO/admin) to include supervisor + auditor per REQUIREMENTS (reconcile naming: shift-supervisor↔supervisor).
- SEC-05/07: env-based secrets + .env.example, no hardcoded secrets (reuse Phase 10 JWT secret guard pattern); restricted-document access audit rows via the existing audit.actions/ActionType pattern.
- Execution: worktrees DISABLED — sequential on main tree. Apply Phase 8/9/10 review guardrails (parameterized SQL, generic error bodies, exact imports, no secret leak, SSR-safety where frontend touched).
- Nyquist: scaffold eval/security tests before implementation where practical.
</decisions>

<code_context>
## Existing Code Insights
- `infra/compose/obs.yml` — observability compose (extend for Langfuse v3 + LGTM).
- `services/ot-bridge/src/svc_ot_bridge/` — OT Bridge (add/verify the write-block guard + SEC-06 test).
- `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py` + `tests/test_langfuse_callback.py` — Langfuse callback already exists; wire it into the trace propagation.
- `apps/api-gateway/src/svc_api_gateway/main.py` — FastAPIInstrumentor OTEL (Phase 10); extend with propagation + Langfuse.
- RAG ingest pipeline: `services/knowledge-ingest/` + `packages/sft-knowledge/` (Phase 5) — add SEC-04 sanitization here.
- Audit/ActionType: `packages/sft-agents/.../models/enums.py` — add a restricted-access audit type if needed (SEC-07).
</code_context>

<canonical_refs>
## Canonical References (downstream agents MUST read)
- `.planning/REQUIREMENTS.md` — OBS-01..07, SEC-01..07.
- `.planning/ROADMAP.md` — Phase 11 goal + 5 success criteria.
- `infra/compose/obs.yml`, `services/ot-bridge/`, `packages/sft-agents/.../llm/langfuse_callback.py`.
- `.planning/phases/10-backend-api-frontend/10-SECURITY.md` — the F11-deferred accepted risks this phase must close (AR-01 DoS rate-limit, AR-02 SSE token, AR-03 localStorage, AR-06 SEC-02 OWASP, AR-07 multi-worker limiter).
- Prior phase SECURITY.md files (08/09/10) — STRIDE registers to consolidate into the SEC-01 threat model doc.
</canonical_refs>

<deferred>
## Deferred Ideas
- Real IdP/Keycloak, JWKS rotation, refresh tokens — future milestone (beyond v1.0).
- Distributed (Redis) rate-limiter — implement here if scoped by planner under AR-07; otherwise documented.
- Live GPU/real-LLM eval runs — human/local hardware items.
</deferred>
