---
phase: 04-core-agentic-runtime-hitl
verified: 2026-05-18T17:56:14Z
status: human_needed
score: 5/5 success criteria verified
overrides_applied: 0
human_verification:
  - test: "Live PG migration run on production-grade PG instance (deferred from automated CI to operator)"
    expected: "All four Phase 4 migrations (002–005) apply cleanly + idempotent re-run no-op; agent_role created NOLOGIN; REVOKE UPDATE/DELETE on audit.actions enforced"
    why_human: "Phase 04-02 explicitly marked as `autonomous: false` (BLOCKING migration push); operator already approved a 9-step live PG verification run during plan 04-02 execution. Documented for milestone audit traceability."
  - test: "Live NATS AUDIT_STREAM bootstrap against a real JetStream node"
    expected: "scripts/nats-bootstrap-streams.py exit 0 first run; second run idempotent (BadRequestError → update_stream); AUDIT_STREAM declared with 90-day retention"
    why_human: "Stream creation is verified in testcontainers tests, but production NATS deployment is a Phase 11 concern; smoke-run on a real broker provides additional confidence before agents start publishing audit rows."
  - test: "Langfuse v3 callback emits spans against a live Langfuse server"
    expected: "supervisor/cluster/agent spans visible in Langfuse UI; metadata field langfuse_session_id propagates via config['metadata']"
    why_human: "Phase 4 deliberately defers Langfuse server self-hosting to Phase 11 (per CONTEXT.md scope boundary). Smoke test requires either Langfuse Cloud credentials or a stood-up self-hosted instance — neither is available in CI."
  - test: "vLLM Hermes tool-calling smoke against real GPU-served Qwen2.5-14B-Instruct-AWQ"
    expected: "vLLM serve command from docs/architecture/llm-serving.md runs; agent issues function-call request and receives a structured tool response"
    why_human: "Requires a real GPU (RTX 4090 / L40 / similar). Documentation is verified; behaviour cannot be validated in CI."
  - test: "Full HITL UI walkthrough by an operator persona"
    expected: "Operator clicks approve in (future) UI, decision flows REST → PG row update → NATS resolved publish → AgentState resume from checkpoint → audit row written with motivation"
    why_human: "Phase 10 UI not yet built; flow currently verified via REST + asyncpg in tests/e2e/test_hitl_cycle.py. Once the Angular UI lands (Phase 10), the full human-in-the-loop ergonomics need a real persona walkthrough."
---

# Phase 4: Core Agentic Runtime & HITL — Verification Report

**Phase Goal:** The LangGraph supervisor graph with five cluster subgraph skeletons (Operations, Maintenance, Knowledge-Curation, Knowledge-Training, Supply per D-53), PostgreSQL checkpointer, provider-agnostic LLM adapter, full HITL interrupt-to-resume loop, 4-tier escalation model, and immutable audit trail are operational end-to-end.

**Verified:** 2026-05-18T17:56:14Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth                                                                                                                                                                                                                                                                                                  | Status     | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | A full HITL cycle completes end-to-end: agent proposes action → LangGraph `interrupt()` → state persists to PG → NATS publishes approval request → human decision resumes the graph → audit record written to immutable append-only PG table and NATS AUDIT_STREAM                                     | VERIFIED   | `packages/sft-agents/src/sft_agents/hitl/interrupt.py:88` (`human_approval_node`) wires the full cycle; `packages/sft-agents/src/sft_agents/audit/writer.py:1-107` enforces PG-first sync + NATS async dual-write; `infra/migrations/timescale/003_create_audit_actions.sql:6,114-125` REVOKEs UPDATE/DELETE on audit.actions from agent_role; `tests/e2e/test_hitl_cycle.py:253` exercises the full loop including `docker compose restart api-gateway`. Operator-approved live PG verification documented on 04-02 SUMMARY.                            |
| 2   | The SDK `recursion_limit` is enforced on every `graph.invoke()` call; a graph exceeding the limit escalates to HITL rather than crashing                                                                                                                                                                | VERIFIED   | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:99-165` — `safe_invoke` raises `ValueError` if `recursion_limit` is missing in `config`, catches `GraphRecursionError`, and emits a `ProposedAction(action_type=GRAPH_RECURSION_REVIEW)` routed to Manager tier instead of re-raising; covered by `packages/sft-agents/tests/test_recursion_limit.py` and `test_supervisor.py` (passing).                                                                                                                                                  |
| 3   | The LLM adapter switches between Ollama (Qwen2.5-7B Q4_K_M) and vLLM (Qwen2.5-14B AWQ) by changing one environment variable with no code changes in agents                                                                                                                                              | VERIFIED   | Live behavioral spot-check: `LLM_BACKEND=ollama … get_llm()` → `ChatOllama` (model `qwen2.5:7b-instruct-q4_K_M`); `LLM_BACKEND=vllm … get_llm()` → `ChatOpenAI` (model `Qwen/Qwen2.5-14B-Instruct-AWQ`, `stream_usage=True`); `LLM_BACKEND=foo` raises `RuntimeError` mentioning `ollama\|vllm`. Factory in `packages/sft-agents/src/sft_agents/llm/factory.py:38-121`. Hermes tool-call parser documented in `docs/docs/architecture/llm-serving.md`.                                                                                                |
| 4   | A paused HITL approval thread survives a full service restart and resumes correctly from the PostgreSQL checkpoint                                                                                                                                                                                     | VERIFIED   | `tests/e2e/test_hitl_cycle.py::test_hitl_cycle_survives_restart` (line 253, 800-line file) launches docker compose stack, pauses graph on `interrupt()`, calls `docker compose restart api-gateway`, polls `/v1/health`, then completes the decide cycle from the same PG checkpoint. Orchestrator confirms E2E HITL cycle test passes against testcontainer compose stack including service-restart survival. AsyncPostgresSaver wired in `packages/sft-agents/src/sft_agents/runtime/checkpointer.py:1-167`. |
| 5   | The approval rate governor fires an alert to the Manager role when more than 80% of consecutive actions are auto-approved                                                                                                                                                                              | VERIFIED   | `packages/sft-agents/src/sft_agents/runtime/governor.py:5-115` — sliding 1-hour window; emits when `auto_count/total > 0.80 AND total >= 20`; writes `audit.actions` row `decision='governor_alert'` + publishes NATS `hitl.governor.alert` + creates Manager-tier ApprovalRequest. 5-min cooldown. Covered by `test_governor.py` (passing).                                                                                                                                                                                                          |

**Score:** 5/5 ROADMAP success criteria verified

### Required Artifacts

| Artifact                                                                            | Expected                                                                                              | Status     | Details                                                                                                                                                                                                  |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `packages/sft-agents/src/sft_agents/sdk/{agent,tool,memory,policy}.py`               | ABCs for Agent / Tool / Memory / Policy (CORE-01)                                                     | VERIFIED   | 4 files present; imports resolve from `sft_agents`; tests `test_sdk_interfaces.py` pass                                                                                                                  |
| `packages/sft-agents/src/sft_agents/models/{evidence,audit,approval,budget,proposed_action,memory_record,enums}.py` | EvidencePanel, AuditRecord, ApprovalRequest/Decision, BudgetSnapshot/Limits, Tier/Decision/ActionType enums    | VERIFIED   | 8 model modules, frozen Pydantic v2 + `extra=forbid`; HITL-07 motivation invariant enforced via `model_validator` in audit.py (verified by `test_audit_record.py`)                                       |
| `infra/migrations/timescale/00{2,3,4,5}*.sql`                                       | 4 idempotent migrations (hitl.approvals, audit.actions hypertable+outbox+REVOKE, budget.executions, langgraph schema) | VERIFIED   | All 4 files present; `003_create_audit_actions.sql` (154 LOC) creates hypertable + REVOKE + agent_role + outbox + HITL motivation CHECK; integration tests `test_migrations_idempotent.py` + `test_audit_immutability.py` pass |
| `scripts/langgraph-init.py`                                                          | Idempotent AsyncPostgresSaver.setup() runner                                                          | VERIFIED   | 134 LOC; idempotent; operator confirmed clean run                                                                                                                                                       |
| `packages/sft-agents/src/sft_agents/runtime/{state,checkpointer,supervisor,clusters,budget,escalation,governor}.py` | AgentState TypedDict, AsyncPostgresSaver wiring, supervisor StateGraph + safe_invoke, 5 cluster subgraphs, BudgetTracker, EscalationSupervisor, Governor | VERIFIED   | 7 modules totaling 1259 LOC; 5 clusters confirmed via `ALL_CLUSTERS = ('ops', 'maintenance', 'knowledge-curation', 'knowledge-training', 'supply')`; 16 placeholder children in `clusters/*`                                                                                  |
| `packages/sft-agents/src/sft_agents/llm/{factory,budgeting,langfuse_callback,usage}.py` | LLM_BACKEND={ollama,vllm} factory + BudgetingChatModel + Langfuse v3 callback                          | VERIFIED   | Behavioral switching confirmed live (see truth #3); BudgetingChatModel captures usage_metadata + duration_ms                                                                                              |
| `packages/sft-agents/src/sft_agents/tools/registry.py`                              | ToolRegistry + export_tool_schemas (Pydantic v2 model_json_schema by_alias)                            | VERIFIED   | 125 LOC; OpenAI function-calling schemas exported; covered by `test_tool_registry.py`                                                                                                                    |
| `packages/sft-agents/src/sft_agents/audit/{subjects,nats_publisher,writer,pg_writer,outbox}.py` | Audit dual-write infra (subject derivation, NATS publisher, PG writer, outbox retry, dual-write orchestrator) | VERIFIED   | 5 modules / 916 LOC; subject derivation rejects subject-hijack attempts; `AuditWriter` enforces PG-sync-first, NATS-async, outbox-on-failure                                                              |
| `packages/sft-agents/src/sft_agents/hitl/{interrupt,approval_queue,redactor}.py`    | human_approval_node + ApprovalQueueWriter + GDPRRedactor                                                | VERIFIED   | 3 modules / 623 LOC; ON CONFLICT DO NOTHING idempotent insert; sha256-deterministic approval id; PII regex strips phone/email/codice fiscale                                                              |
| `packages/sft-agents/src/sft_agents/policies/{safety_interlock.py,*.yaml}`           | SafetyInterlockMiddleware + policy YAMLs (safety-interlock, escalation-sla, budgets, routing)          | VERIFIED   | 4 YAML files + middleware module; fnmatch-style NATS subject matching for forbidden subjects; tests `test_safety_interlock.py` pass                                                                       |
| `packages/sft-agents/src/sft_agents/memory/{episodic,long_term_stub}.py`            | EpisodicReplay (audit-log projection) + StubLongTermMemory (D-59 contract anchor)                      | VERIFIED   | 232 LOC; StubLongTermMemory.query() returns []; episodic uses `query_timescale` Phase 3 tool                                                                                                              |
| `packages/sft-agents/src/sft_agents/replay/from_checkpoint.py`                       | replay_thread + ReplayResult (CORE-10)                                                                  | VERIFIED   | 359 LOC; tool calls deterministic from audit log; REPLAY:-prefixed audit rows for tamper-distinction                                                                                                      |
| `scripts/nats-bootstrap-streams.py`                                                  | AUDIT_STREAM bootstrap with subjects audit.actions.>, hitl.approvals.>, hitl.governor.> @ 90d retention | VERIFIED   | 219 LOC; AUDIT_STREAM declared with 90-day retention; integration test `test_audit_stream_bootstrap.py` confirms idempotency                                                                              |
| `apps/api-gateway/src/svc_api_gateway/{main,lifespan,routers/{health,approvals,threads}.py,idempotency.py}` | FastAPI app with lifespan, /v1/health, /v1/approvals*, /v1/threads/{id}/resume, Idempotency-Key support | VERIFIED   | 8 modules; lifespan opens pool, NATS, AsyncPostgresSaver, builds supervisor graph, starts EscalationSupervisor + Governor + OutboxRetry; build succeeds; 14/14 api-gateway tests pass                     |
| `tests/e2e/test_hitl_cycle.py`                                                       | E2E HITL cycle test with docker compose restart survival                                                | VERIFIED   | 800 LOC; orchestrator confirmed pass; covers restart-survival + idempotency-replay + thread-resume                                                                                                        |
| `docs/docs/architecture/{agentic-runtime,hitl-cycle,llm-serving}.md`                | Phase 4 architecture docs incl. Mermaid sequence diagram for HITL cycle                                 | VERIFIED   | 3 files / 717 LOC; mkdocs `--strict` build clean (1.76s)                                                                                                                                                  |
| `.planning/ROADMAP.md` Phase 4 mention of "5 cluster"                                | D-53 override committed to ROADMAP                                                                     | VERIFIED   | Line 83: "five cluster subgraph skeletons (Operations, Maintenance, Knowledge-Curation, Knowledge-Training, Supply per D-53)"; line 97 plan title mentions "5 cluster subgraphs"                          |

### Key Link Verification

| From                                                                                                              | To                                              | Via                                                              | Status | Details                                                                                                                                                  |
| ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sft_agents.llm.factory.build_chat_model`                                                                          | `langchain_ollama.ChatOllama` / `langchain_openai.ChatOpenAI` | Conditional import on LLM_BACKEND env                            | WIRED  | Behavioral spot-check confirmed both branches; RuntimeError on unknown backend                                                                            |
| `apps/api-gateway/.../routers/approvals.py`                                                                       | `sft_agents.hitl.approval_queue.ApprovalQueueWriter` + supervisor graph resume | Lifespan dependency injection; `Command(resume=)` via supervisor | WIRED  | `POST /v1/approvals/{id}/decide` updates PG row + publishes resolved + builds Command(resume=); covered by e2e + api-gateway tests                       |
| `sft_agents.audit.writer.AuditWriter.write`                                                                         | PG `audit.actions` + NATS `audit.actions.>`     | Sync PG INSERT (re-raise on fail) → async NATS publish (outbox on fail) | WIRED  | D-56 invariant; outbox table populated on NATS failure; `OutboxRetry` background task drains                                                              |
| `sft_agents.runtime.escalation.EscalationSupervisor`                                                                | `hitl.approvals` SLA deadline scan + tier escalation | Background asyncio task; SET LOCAL ROLE; FK escalated_to_id      | WIRED  | 2m/15m/60m timers per `escalation-sla.yaml`; safety_interlock excluded                                                                                    |
| `sft_agents.runtime.governor.Governor`                                                                              | `audit.actions` 1h window scan + Manager alert  | Background asyncio task; 80% threshold + min_sample=20 + 5m cooldown | WIRED  | Verified by `test_governor.py`                                                                                                                            |
| `sft_agents.policies.safety_interlock.SafetyInterlockMiddleware`                                                    | Pre-ToolNode check                              | YAML whitelist `forbidden_subjects` + `forbidden_action_types`   | WIRED  | fnmatch prefix match; raises SafetyInterlockRejection + emits interlock_reject audit                                                                      |
| `packages/sft-agents/src/sft_agents/replay/from_checkpoint.py`                                                    | `EpisodicReplay` + `get_postgres_checkpointer`  | Direct import + composition                                      | WIRED  | replay_thread reads audit + checkpoint; optional write-back with REPLAY: prefix                                                                            |
| `docs/mkdocs.yml`                                                                                                  | agentic-runtime.md + hitl-cycle.md              | Nav entries (en + it)                                            | WIRED  | mkdocs --strict build OK                                                                                                                                  |

### Data-Flow Trace (Level 4)

Phase 4 ships infrastructure components (no UI rendering dynamic data). Applicable traces:

| Artifact                                          | Data Variable        | Source                                                  | Produces Real Data | Status   |
| ------------------------------------------------- | -------------------- | ------------------------------------------------------- | ------------------ | -------- |
| `GET /v1/approvals` (router)                       | rows from query     | asyncpg fetch on `hitl.approvals` (parameterized SQL)   | Yes — read from PG | FLOWING  |
| `human_approval_node` resume path                  | ApprovalDecision     | `Command(resume=)` via FastAPI decide endpoint           | Yes — operator input | FLOWING  |
| `Governor.run` window stats                        | auto_count / total   | SQL SELECT on `audit.actions` filtered by 1h window      | Yes — real audit rows | FLOWING  |
| `EpisodicReplay.replay_thread`                     | list[AuditRecord]    | SQL SELECT on `audit.actions WHERE thread_id=$1`         | Yes — real audit rows | FLOWING  |
| `StubLongTermMemory.query`                         | always []            | Hardcoded — D-59 contract anchor for Phase 5 swap        | No (intentional)   | STATIC (intentional stub — Phase 5 swap) |
| Cluster child nodes                                | empty dict           | Placeholders for Phase 6–9 agent business logic          | No (intentional)   | STATIC (intentional placeholder per D-53/scope) |

The two intentional STATIC items (`StubLongTermMemory`, cluster placeholder children) are explicitly in scope per Phase 4 CONTEXT.md `<scope_boundaries>` — Phase 4 does NOT build agent business logic. These satisfy D-59 contract-anchor + Phase 6-9 plug-points respectively.

### Behavioral Spot-Checks

| Behavior                                                          | Command                                                                                                | Result                                              | Status |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------- | ------ |
| sft-agents test suite passes                                       | `uv run --package sft-agents pytest packages/sft-agents/tests -q`                                       | `301 passed, 2 skipped in 7.91s`                    | PASS   |
| api-gateway test suite passes                                      | `uv run --package svc-api-gateway pytest apps/api-gateway/tests -q`                                     | `14 passed in 0.54s`                                | PASS   |
| sft-agents wheel builds cleanly                                    | `uv build --package sft-agents`                                                                          | `Successfully built dist/sft_agents-0.1.0-py3-none-any.whl` | PASS   |
| svc-api-gateway wheel builds cleanly                              | `uv build --package svc-api-gateway`                                                                     | `Successfully built dist/svc_api_gateway-0.1.0-py3-none-any.whl` | PASS   |
| Public API surface imports                                         | 27 imports across SDK/models/runtime/llm/tools/audit/hitl/policies/memory/replay                         | `ALL IMPORTS OK`                                    | PASS   |
| LLM_BACKEND=ollama selects ChatOllama                              | `LLM_BACKEND=ollama python -c "from sft_agents.llm import get_llm; print(type(get_llm()).__name__)"`     | `ChatOllama`                                        | PASS   |
| LLM_BACKEND=vllm selects ChatOpenAI                                | `LLM_BACKEND=vllm … python -c "from sft_agents.llm import get_llm; print(type(get_llm()).__name__)"`     | `ChatOpenAI`                                        | PASS   |
| LLM_BACKEND=foo raises RuntimeError mentioning ollama/vllm        | `LLM_BACKEND=foo python -c "from sft_agents.llm import get_llm; get_llm()"`                              | `RuntimeError: LLM_BACKEND must be one of ollama\|vllm, got 'foo'` | PASS   |
| 5 clusters wired                                                   | `python -c "from sft_agents.runtime.state import ALL_CLUSTERS; print(len(ALL_CLUSTERS))"`                | `5` → `('ops', 'maintenance', 'knowledge-curation', 'knowledge-training', 'supply')` | PASS   |
| mkdocs --strict build clean                                        | `cd docs && mkdocs build --strict`                                                                       | `Documentation built in 1.76 seconds` (no warnings)  | PASS   |

### Probe Execution

No `scripts/*/tests/probe-*.sh` style probes are declared by Phase 4 plans. The phase's "probe" equivalents are the integration / e2e pytest suites (run above) and the operator-approved live PG migration verification documented on plan 04-02.

### Requirements Coverage (20 IDs)

All 20 Phase 4 requirements declared in ROADMAP.md + REQUIREMENTS.md are claimed by at least one plan frontmatter and have supporting implementation evidence in the codebase:

| Requirement | Description (REQUIREMENTS.md)                                                              | Source Plan(s)        | Status     | Evidence                                                                                       |
| ----------- | ------------------------------------------------------------------------------------------ | --------------------- | ---------- | ---------------------------------------------------------------------------------------------- |
| CORE-01     | SDK Python `sft-agents` con interfaccia uniforme `Agent`, `Tool`, `Memory`, `Policy`         | 04-01                  | SATISFIED  | 4 ABC modules in `sft_agents/sdk/`; tests pass                                                  |
| CORE-02     | Orchestratore LangGraph con pattern supervisor + cluster subgraphs (4 cluster)              | 04-01, 04-05           | SATISFIED  | `build_supervisor_graph` + 5 clusters (D-53 override approved in ROADMAP)                       |
| CORE-03     | `recursion_limit` esplicito su ogni `graph.invoke()` (default ≤25, configurabile)            | 04-05                  | SATISFIED  | `safe_invoke` enforces recursion_limit + escalates GraphRecursionError to HITL Manager tier     |
| CORE-04     | Checkpointer PostgreSQL per persistenza stato LangGraph                                      | 04-02, 04-05, 04-07    | SATISFIED  | `AsyncPostgresSaver` + 005_create_langgraph_checkpoints.sql + `scripts/langgraph-init.py`        |
| CORE-05     | Adapter LLM provider-agnostic con backend Ollama (dev) e vLLM (prod) selezionabile           | 04-03                  | SATISFIED  | Behavioral spot-check confirmed                                                                  |
| CORE-06     | Default LLM Qwen2.5 14B AWQ (vLLM) con fallback 7B Q4_K_M (Ollama) per dev                   | 04-03                  | SATISFIED  | factory.py default model strings `qwen2.5:7b-instruct-q4_K_M` + `Qwen/Qwen2.5-14B-Instruct-AWQ` |
| CORE-07     | Tool registry con tipizzazione Pydantic e schema JSON esportabili per function calling       | 04-03, 04-05           | SATISFIED  | `ToolRegistry` + `export_tool_schemas` (Pydantic v2 model_json_schema(by_alias=True))           |
| CORE-08     | Memory layer: short-term (LangGraph state), long-term (Qdrant + PG), episodic (NATS replay)  | 04-02, 04-04, 04-06    | SATISFIED  | Short-term via AgentState/checkpointer; episodic via EpisodicReplay+query_timescale; long-term stub (D-59) |
| CORE-09     | Budget/quota tracker per token, costo simulato, durata esecuzione per ogni agente            | 04-02, 04-06           | SATISFIED  | `BudgetTracker` middleware + budget.executions UPSERT + soft/hard threshold approvals           |
| CORE-10     | Replay deterministico di esecuzioni passate da checkpoint + audit log                        | 04-08                  | SATISFIED  | `replay_thread` + `ReplayResult`; tool calls deterministic from audit log                       |
| HITL-01     | `interrupt()` LangGraph nativo con resume tramite checkpointer                               | 04-06, 04-07           | SATISFIED  | `human_approval_node` full cycle + `Command(resume=)` via api-gateway                           |
| HITL-02     | 4 livelli di escalation: Operator → Supervisor → Manager → Safety Interlock                  | 04-06                  | SATISFIED  | Tier enum + escalation-sla.yaml + safety_interlock terminal tier                                |
| HITL-03     | Safety Interlock rifiuta a priori azioni che scrivono setpoint PLC (whitelist tool)         | 04-06                  | SATISFIED  | `SafetyInterlockMiddleware` + safety-interlock.yaml forbidden subjects/action_types             |
| HITL-04     | Approval queue persistente con SLA per livello                                                | 04-06, 04-07           | SATISFIED  | hitl.approvals table + sla_deadline + REST endpoints                                            |
| HITL-05     | Audit trail immutabile su NATS `AUDIT_STREAM` (90d retention) + tabella PG append-only       | 04-02, 04-04, 04-06    | SATISFIED  | audit.actions hypertable + REVOKE + AUDIT_STREAM 90d                                            |
| HITL-06     | Ogni decisione AI include evidence panel (input, tool calls, citazioni RAG, confidence)      | 04-01, 04-06           | SATISFIED  | `EvidencePanel` Pydantic schema + attached at every interrupt; covered by test_evidence_panel.py |
| HITL-07     | Override umano sempre tracciato con motivazione obbligatoria                                  | 04-01, 04-06           | SATISFIED  | `AuditRecord` model_validator + SQL CHECK constraint enforces motivation NOT NULL on hitl_* decisions |
| HITL-08     | Rollback di azione agente tramite event sourcing replay                                       | 04-06, 04-08           | SATISFIED  | `replay_thread(action_id=...)` action_id truncation + REPLAY:-prefixed audit rows               |
| HITL-09     | Approval rate governor: se >80% azioni auto-approvate, alert al Manager                       | 04-06                  | SATISFIED  | `Governor` sliding window — see Truth #5                                                          |
| HITL-10     | Rate-limit alarm su UI operatore (max 12 alert/ora per persona)                               | 04-06                  | SATISFIED  | `test_rate_limit_audit_query.py` + per-persona aggregation (UI-side enforcement deferred Phase 10/11 per A-018) |

**Orphaned requirements:** None — all 20 IDs in REQUIREMENTS.md mapped to Phase 4 are claimed by at least one plan.

### Anti-Patterns Found

| File                                                                | Line | Pattern        | Severity | Impact                                                                                          |
| ------------------------------------------------------------------- | ---- | -------------- | -------- | ----------------------------------------------------------------------------------------------- |
| `packages/sft-agents/src/sft_agents/memory/long_term_stub.py`         | 45, 57, 73 | "placeholder" / "not available in Phase 4" | Info   | Intentional Phase 5 contract anchor per D-59; Phase 4 scope_boundary explicitly excludes Qdrant long-term memory. Returns `[]` from query() as documented behaviour. |
| `packages/sft-agents/src/sft_agents/clusters/*/__init__.py`           | n/a  | "placeholder children" | Info   | Per D-53 + Phase 4 scope_boundary: cluster child nodes are placeholders for Phase 6-9 agent business logic. Logs and returns `{}` as designed. |
| `packages/sft-agents/src/sft_agents/runtime/clusters.py`             | 55-66 | `_make_placeholder` factory function | Info   | Same as above — explicit, named, tested factory for the 16 placeholder agents.                  |
| Conftest path collision when running `pytest packages/sft-agents/tests apps/api-gateway/tests` together | n/a  | Test runner config | Info   | Not a phase artifact issue. Both suites pass when invoked separately under their `uv --package` context, mirroring how Nx run-many invokes them. |

**Zero TBD / FIXME / XXX markers** in Phase 4 source (`packages/sft-agents/src/**`, `apps/api-gateway/src/**`, `infra/migrations/timescale/00{2,3,4,5}*.sql`, `scripts/{langgraph-init,nats-bootstrap-streams}.py`, `docs/docs/architecture/`).

### Human Verification Required

#### 1. Live PG migration sign-off on production-grade PG instance

**Test:** Run `python scripts/timescale-migrate.py` and `python scripts/langgraph-init.py` against the production-grade PG instance (not testcontainers); re-run both and confirm zero schema changes.

**Expected:** First run applies 002–005 + langgraph schema. Second run is a no-op. `\dt audit.*`, `\dt hitl.*`, `\dt budget.*`, `\dt langgraph.*` all show expected tables. `\dp audit.actions` shows `agent_role` has no UPDATE/DELETE.

**Why human:** Phase 04-02 was explicitly `autonomous: false` (BLOCKING migration push). Operator already approved a 9-step live PG verification run during plan 04-02 execution. Documenting here for milestone-audit traceability — no re-run required unless schema drift suspected.

#### 2. Live NATS AUDIT_STREAM bootstrap against a real JetStream node

**Test:** Run `python scripts/nats-bootstrap-streams.py` against a real JetStream broker (not testcontainers). Re-run.

**Expected:** First run exits 0 and declares AUDIT_STREAM with 90-day retention; second run is idempotent (BadRequestError → update_stream).

**Why human:** Production NATS deployment is a Phase 11 concern; smoke-run on a real broker provides additional confidence before agents start publishing audit rows.

#### 3. Langfuse v3 callback emits spans against a live Langfuse server

**Test:** Set `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`; invoke the supervisor graph via api-gateway; confirm spans in Langfuse UI.

**Expected:** supervisor / cluster / agent span hierarchy visible; metadata `langfuse_session_id` populated from `config['metadata']`.

**Why human:** Phase 4 deliberately defers Langfuse server self-hosting to Phase 11 (per CONTEXT.md scope boundary). Smoke test requires either Langfuse Cloud credentials or a self-hosted instance — neither is available in CI.

#### 4. vLLM Hermes tool-calling smoke against real GPU-served Qwen2.5-14B-Instruct-AWQ

**Test:** Follow `docs/docs/architecture/llm-serving.md` to start vLLM with `--tool-call-parser hermes`; invoke a function-calling agent through the supervisor.

**Expected:** Structured tool response returned; usage_metadata populated; Langfuse span shows tool_call.

**Why human:** Requires a real GPU (RTX 4090 / L40 / similar). Documentation is verified; behaviour cannot be validated in CI.

#### 5. Full HITL UI walkthrough by an operator persona

**Test:** When Phase 10 UI ships, run through approve / reject / escalate cycle from an operator persona.

**Expected:** Decision flows REST → PG row update → NATS resolved publish → AgentState resume from checkpoint → audit row written with motivation.

**Why human:** Phase 10 UI not yet built. Currently verified via REST + asyncpg in `tests/e2e/test_hitl_cycle.py`. Re-verify after Phase 10 lands.

### Gaps Summary

No blocking gaps. Phase 4 delivers a fully wired LangGraph supervisor with 5 cluster subgraphs (D-53), 16 placeholder children (Phase 6-9 plug-points), AsyncPostgresSaver checkpointer (CORE-04), provider-agnostic LLM adapter with one-env-var switch (CORE-05/06), full HITL interrupt→resume→audit dual-write cycle (HITL-01, HITL-05, HITL-06, HITL-07), 4-tier escalation with auto-timers (HITL-02, HITL-04), safety interlock whitelist (HITL-03), approval-rate governor (HITL-09), budget/quota middleware (CORE-09), GDPR-aware checkpoint redaction, episodic replay (CORE-08) + long-term memory stub (D-59 Phase 5 anchor), deterministic replay tool (CORE-10, HITL-08), and the api-gateway REST surface that brokers it all.

All 5 ROADMAP success criteria are observably true in the codebase. All 20 declared requirements (CORE-01..10, HITL-01..10) map to implemented artifacts with passing tests. The package builds cleanly (`uv build --package sft-agents`, `uv build --package svc-api-gateway`). 315 tests pass (301 sft-agents + 14 api-gateway). `mkdocs build --strict` is clean.

The five `human_needed` items are operational smoke-checks that are deliberately deferred (per Phase 4 scope_boundaries) and require infrastructure that is not in CI: live PG / live NATS / live Langfuse / live vLLM GPU / Phase 10 UI. Operator has already approved the live PG run during plan 04-02 execution. The remaining four are advisory — no additional code work is required for Phase 4 to be considered complete; they will be exercised naturally during Phase 11 (observability hardening) and Phase 10 (UI).

---

_Verified: 2026-05-18T17:56:14Z_
_Verifier: Claude (gsd-verifier)_
