---
phase: 4
phase_name: Core Agentic Runtime & HITL
researched_at: "2026-05-18"
researcher: gsd-phase-researcher
confidence: HIGH (LangGraph + checkpointer + dual-write pattern già scolpiti dai Phase 1/3); MEDIUM (replay determinism + vLLM Qwen2.5-14B AWQ tool-calling parity); HIGH (audit immutability + asyncpg pitfalls — Phase 3 precedente già validato)
depends_on_phases: [1, 3]
canonical_inputs:
  - .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-53..D-60 locked)
  - .planning/research/STACK.md
  - .planning/research/ARCHITECTURE.md
  - .planning/phases/03-it-ot-simulation-layer/03-CONTEXT.md (D-44..D-52 precedenti)
  - services/ot-bridge/src/svc_ot_bridge/* (dual-write idiom precedent)
  - infra/migrations/timescale/001_create_sensor_events.sql (idempotent migration pattern)
---

# Phase 4 — Core Agentic Runtime & HITL — Research

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-53 → D-60)

Le seguenti 8 decisioni sono **finali** e non vanno discusse né alternate dal planner. Sono copiate testualmente da `04-CONTEXT.md`.

- **D-53 (5 cluster subgraphs):** supervisor LangGraph → `ops` / `maintenance` / `knowledge-curation` / `knowledge-training` / `supply` (NOT 4 come da ROADMAP). 16 agent placeholder child nodes totali (4/4/2/2/4). Plan deve includere ROADMAP edit task per allineare "four cluster subgraph skeletons" → "five cluster subgraph skeletons".
- **D-54 (hybrid routing supervisor):** Stage 1 rule-based (<10ms) via `sft_agents/policies/routing.yaml` keywords + regex; Stage 2 LLM classifier (~500ms-2s) con structured output `cluster + confidence`, fallback `ops` se `confidence < 0.7`. Ogni decision tracciata Langfuse `supervisor.route` span con `{route, strategy, confidence}`.
- **D-55 (approval queue):** PG primary (`hitl.approvals`) + NATS notify `hitl.approvals.new.<tier>` + REST API `GET /v1/approvals` + `POST /v1/approvals/{id}/decide` in `apps/api-gateway/`. Schema PG già fissato in CONTEXT.md (id UUID, agent_id, thread_id, tier, payload_json, status, sla_deadline, decided_at, decided_by, decision_json, escalated_to_id).
- **D-56 (audit dual-write):** Sync PG `audit.actions` (source-of-truth 7y retention via partitioning hypertable) + async NATS `AUDIT_STREAM` (90d retention). Schema fissato; revoke UPDATE/DELETE on `agent_role`. PG INSERT sync blocking → agent ABORTS se PG fails; NATS fire-and-forget con outbox retry. EvidencePanel embedded JSONB.
- **D-57 (escalation SLA):** Operator 2min → Supervisor 15min → Manager 60min → alert solo (no further escalation); Safety Interlock manual-only NO timeout. Background asyncio scanner `sft_agents.runtime.escalation_supervisor` ogni 30s. Config in `sft_agents/policies/escalation-sla.yaml`.
- **D-58 (Safety Interlock + Governor):** Safety Interlock = middleware LangGraph node PRIMA di ogni ToolNode; whitelist YAML `sft_agents/policies/safety-interlock.yaml` con `forbidden_subjects` (cmd.plc.setpoint.>, cmd.actuator.>, cmd.firmware.deploy, cmd.network.acl.>) + `forbidden_action_types`. NESSUN override UI possibile. Governor = background task ogni 60s, calcola `auto_rate = count(decision='auto') / count(*)` su 1h sliding window; se `>0.80 AND count(*) >= 20` → alert NATS `hitl.governor.alert` + Manager-tier ApprovalRequest.
- **D-59 (memory split):** Short-term = LangGraph PG checkpointer con `thread_id = {cluster}.{agent_id}.{session_uuid}`. Episodic = `sft_agents.memory.EpisodicReplay` via NATS replay + `query_timescale` Tool (Phase 3) su `audit.actions`. Long-term = STUB `StubLongTermMemory` returning `[]` (Phase 5 sostituirà con `QdrantLongTermMemory` + BGE-M3).
- **D-60 (budget tracker):** Middleware LangGraph node PRIMA di ogni LLM call + ToolNode invocation. PG storage `budget.executions (thread_id, agent_id, tokens_total, cost_usd, duration_ms, step_count, started_at, last_step_at)` con PRIMARY KEY composite. UPSERT sync ogni step. Soglie: 80% tokens → operator approval; >100% cost → supervisor approval; >100% duration → operator approval. Limits in `sft_agents/policies/budgets.yaml` per cluster + agent_id override.

### Claude's Discretion (copiato verbatim)

- **sft-agents public API:** `from sft_agents import Agent, Tool, Memory, Policy, Supervisor, ClusterSubgraph, BudgetTracker, EvidencePanel, AuditRecord, ApprovalRequest`. ABC classes con Pydantic frozen + extra=forbid.
- **AgentState (TypedDict):** `messages: list[BaseMessage]`, `thread_id: str`, `cluster: str`, `proposed_actions: list[ProposedAction]`, `budget: BudgetSnapshot`, `evidence: EvidencePanel | None`, `pending_approval_id: UUID | None`.
- **thread_id convention:** `{cluster}.{agent_id}.{session_uuid}` (UUID v4).
- **LLM model versioning:** `EvidencePanel.model` = `qwen2.5-14b-awq@vllm-0.8` o `qwen2.5-7b-q4km@ollama-0.6`.
- **NATS subjects Phase 4:** `hitl.approvals.new.<tier>`, `hitl.approvals.resolved.<tier>`, `hitl.governor.alert`, `audit.actions.<cluster>.<agent_id>`. Stream `AUDIT_STREAM` retention 90d (separato da SENSOR_EVENTS).
- **API gateway:** REST `/v1/` prefix; OpenAPI auto; uvicorn ASGI; deps `fastapi`, `uvicorn`, `langchain-core`, `sft-agents` (workspace), `asyncpg`, `nats-py`.
- **Replay determinism:** best-effort Phase 4 (seed LLM + tool calls deterministici da audit log). Frozen tool outputs → Phase 11.
- **Test strategy:** unit (mock LLM/NATS/PG) + integration (testcontainers PG + NATS + mock LLM via langchain-fake) per HITL E2E loop; load test deferred.
- **Migration ordering:** 002 hitl.approvals → 003 audit.actions → 004 budget.executions → 005 langgraph.checkpoints (via setup tool).
- **EvidencePanel.rag_citations Phase 4:** Empty list; Phase 5 popola. `RagCitation = {source_uri, snippet, score, retrieved_at}` definita Phase 4 per contract stability.
- **Pyproject deps:** `langgraph>=0.4`, `langgraph-checkpoint-postgres>=3.1`, `langchain-core>=0.3`, `langchain-ollama>=0.3`, `langchain-openai>=0.3`, `langfuse>=3`, `fastapi>=0.115`.
- **Audit FK:** se `decision IN ('hitl_*')`, `audit.actions.approval_id UUID REFERENCES hitl.approvals(id)`. Auto → NULL.

### Deferred Ideas (OUT OF SCOPE Phase 4)

- Embedding-based supervisor routing (Stage 3): Phase 7+ con Qdrant
- Per-tool SLA configurabile: Phase 11
- Adaptive governor threshold per cluster: Phase 11
- LLM-based safety classifier: Phase 11 (anti-pattern unless strong evidence)
- Real-time pricing per token: Phase 11
- Cross-cluster checkpoint sharing: Phase 7+
- CQRS event sourcing per AuditRecord: Phase 11
- WebSocket push approval queue: Phase 11
- MCP wrapping di sft-agents: Phase 12+
- OAuth/OIDC su api-gateway: Phase 11
- Cost pricing reale per LLM token: Phase 11
- Cross-cluster supervisor patterns: Phase 7+
- Langfuse v3 self-hosted server deployment (PG+ClickHouse+MinIO): Phase 11; Phase 4 ships solo client config + cloud-or-stub
- Real PLC NATS command channel `cmd.plc.setpoint.*`: Phase 11

</user_constraints>

<phase_requirements>
## Phase Requirements — Mapping Research Coverage

| ID | Requirement | Research Support |
|----|-------------|------------------|
| CORE-01 | SDK Python `sft-agents` con Agent/Tool/Memory/Policy uniformi | §Technical Approach §1 (sft-agents SDK design); §Code Examples §1 |
| CORE-02 | Orchestratore LangGraph supervisor + 5 cluster subgraphs (D-53 override 4→5) | §Technical Approach §2 (Supervisor + Subgraph composition); §Pitfalls — supervisor return type |
| CORE-03 | `recursion_limit` esplicito su ogni `graph.invoke()` (default ≤25, configurabile) | §Technical Approach §2.4; §Pitfalls §1 (GraphRecursionError → HITL escalation) |
| CORE-04 | PG checkpointer per persistenza stato LangGraph (resume cross-session) | §Technical Approach §3 (AsyncPostgresSaver setup + thread_id); §Pitfalls §2 (autocommit + dict_row, statement_cache_size=0) |
| CORE-05 | LLM adapter provider-agnostic Ollama/vLLM via env var | §Technical Approach §4 (`LLM_BACKEND={ollama,vllm}` factory); §Code Examples §2 |
| CORE-06 | Default Qwen2.5-14B AWQ vLLM, fallback Qwen2.5-7B Q4_K_M Ollama | §Technical Approach §4 (verified Hermes tool parser); §Pitfalls §3 (vLLM strict mode non-implementato) |
| CORE-07 | Tool registry tipizzato Pydantic + JSON schema esportabili | §Technical Approach §5 (LangChain BaseTool args_schema → model_json_schema) |
| CORE-08 | Memory layer short-term/long-term/episodic | §Technical Approach §6 (D-59 split); §Code Examples §5 (EpisodicReplay) |
| CORE-09 | Budget/quota tracker per token/cost/duration per agente | §Technical Approach §7 (D-60 middleware + PG UPSERT); §Pitfalls §4 (streaming token leakage) |
| CORE-10 | Replay deterministico da checkpoint + audit log | §Technical Approach §8 (replay best-effort Phase 4); §Pitfalls §5 (LLM determinism caveat) |
| HITL-01 | `interrupt()` LangGraph nativo + resume via checkpointer | §Technical Approach §9 (interrupt/Command round-trip); §Pitfalls §6 (node re-runs from start) |
| HITL-02 | 4 livelli escalation: Operator → Supervisor → Manager → Safety Interlock | §Technical Approach §10 (D-57 background scanner) |
| HITL-03 | Safety Interlock rifiuta a priori PLC setpoint write (whitelist) | §Technical Approach §11 (D-58 middleware before ToolNode); §Code Examples §4 |
| HITL-04 | Approval queue persistente con SLA per livello | §Technical Approach §9 (D-55 PG + NATS notify + REST API) |
| HITL-05 | Audit trail immutabile NATS AUDIT_STREAM 90d + PG append-only | §Technical Approach §12 (D-56 dual-write); §Pitfalls §7 (PG immutability via REVOKE + role isolation) |
| HITL-06 | EvidencePanel su ogni decisione AI (input, tools, RAG, confidence) | §Technical Approach §1.3 (EvidencePanel Pydantic schema D-56) |
| HITL-07 | Override umano tracciato con motivazione obbligatoria | §Technical Approach §9 (decision_json.motivation NOT NULL constraint per `decision IN ('hitl_*')`) |
| HITL-08 | Rollback agente via event sourcing replay | §Technical Approach §8 (replay tool); §Pitfalls §5 (compensating events Phase 11 hard scope) |
| HITL-09 | Governor: >80% auto-approved → Manager alert | §Technical Approach §13 (D-58 sliding window + sample_size threshold) |
| HITL-10 | Rate-limit alarm UI operatore (max 12/h per persona) | §Open Questions §3 — UI rate-limit lives Phase 10/11; Phase 4 espone solo audit + count primitives |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| sft-agents SDK base classes (Agent/Tool/Memory/Policy) | `packages/sft-agents/` (library) | — | Reusable abstraction shared by all agents downstream (Phase 6-9) |
| Supervisor + 5 cluster subgraphs builder | `packages/sft-agents/runtime/` | — | LangGraph compile-time wiring; runtime composition |
| LangGraph PG checkpointer wiring | `packages/sft-agents/runtime/checkpointer.py` | `infra/migrations/timescale/005_*.sql` (setup-driven) | Library-level + idempotent SQL bootstrap |
| LLM adapter `LLM_BACKEND` env switch | `packages/sft-agents/llm/factory.py` | — | One-liner factory; agents never instantiate ChatOllama/ChatOpenAI directly |
| HITL `interrupt()` middleware | `packages/sft-agents/hitl/interrupt.py` | `apps/api-gateway/` (decide endpoint) | Library publishes; API consumes |
| Safety Interlock middleware | `packages/sft-agents/policies/safety_interlock.py` | `sft_agents/policies/safety-interlock.yaml` (config) | Defense-in-depth pre-tool node |
| Budget tracker middleware + PG | `packages/sft-agents/runtime/budget.py` | `infra/migrations/timescale/004_*.sql` | Middleware enforced by graph topology |
| Escalation supervisor (background task) | `packages/sft-agents/runtime/escalation.py` | Started by `apps/api-gateway/` lifespan | Asyncio task spawned at API startup |
| Governor (background task) | `packages/sft-agents/runtime/governor.py` | Started by `apps/api-gateway/` lifespan | Same pattern as escalation |
| Approval queue REST API | `apps/api-gateway/` (FastAPI) | `packages/sft-agents/` (uses sdk classes) | Application layer consuming SDK |
| Audit dual-write | `packages/sft-agents/audit/writer.py` | `infra/migrations/timescale/003_*.sql` | Sync PG + async NATS; replicates ot-bridge precedent |
| Replay tool | `packages/sft-agents/replay/` | extends Phase 3 `ReplayRecord` (sft-tools) | Library; consumes Phase 3 `query_timescale` Tool |
| Migrations | `infra/migrations/timescale/{002..005}.sql` + `scripts/timescale-migrate.py` (Phase 3) | — | Reuse Phase 3 runner; only new SQL files |
| NATS `AUDIT_STREAM` bootstrap | `scripts/nats-bootstrap-streams.py` (extend Phase 3) | — | Idempotent add_stream → update_stream pattern |

## Summary

Phase 4 è quasi interamente **wiring di framework noti** sopra l'infrastruttura Phase 1+3 già operativa. Le 8 decisioni `D-53..D-60` chiudono il 90% del design space; la ricerca tecnica si concentra su (a) **idiomi LangGraph 0.4+ che cambiano spesso fra patch release** (interrupt/Command, AsyncPostgresSaver setup, recursion_limit propagation) e (b) **2-3 pitfalls non-ovvi che bruciano** (auto-commit dict_row su connection pool, vLLM tool_call_parser hermes obbligatorio per Qwen2.5, streaming non emette `usage_metadata`, LLM non è deterministico anche con `temperature=0` su GPU diverse).

L'idioma `dual-write PG-sync + NATS-async` esiste già in `services/ot-bridge/` (`timescale_writer.py` + `nats_publisher.py`) — Phase 4 ne replica il pattern per `audit.actions` con due aggiunte: (1) `REVOKE UPDATE/DELETE ON audit.actions FROM agent_role` per immutabilità DB-side, (2) outbox table per replay NATS publish su failure (vs Phase 3 che logga e droppa).

**Primary recommendation:** allineare la composition `supervisor → 5 cluster subgraphs → 16 placeholder agent nodes` al pattern *hierarchical agent teams* della doc ufficiale LangGraph, usare `AsyncPostgresSaver.from_conn_string()` con context-manager pattern + chiamata esplicita `await saver.setup()` come task one-shot durante migrations (NOT a startup di ogni processo), e installare Langfuse v3 callback come SDK-level dependency con `session_id = thread_id` propagation in `config["metadata"]["langfuse_session_id"]` (Langfuse v3 NON accetta più session_id in constructor; deve essere in invocation config).

## Standard Stack

### Core (versions verified against PyPI/Context7)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | `>=0.4,<0.5` | Agent runtime + StateGraph + supervisor + subgraph composition + `interrupt()`/`Command(resume=)` | Già locked in STACK.md; Phase 4 è il primo phase che lo *usa* (Phase 3 non lo importava) |
| `langgraph-checkpoint-postgres` | `>=3.1,<4.0` | `AsyncPostgresSaver` per persistenza PG durable | Locked STACK.md; richiede `setup()` esplicito |
| `langchain-core` | `>=0.3,<0.4` | `BaseTool`, `BaseMessage`, `BaseChatModel`, `Runnable` | Locked STACK.md; Pydantic v2 native da 0.3+ |
| `langchain-ollama` | `>=0.3,<0.4` | `ChatOllama` adapter dev | Default dev via env `LLM_BACKEND=ollama` |
| `langchain-openai` | `>=0.3,<0.4` | `ChatOpenAI` puntato a endpoint vLLM OpenAI-compatible | Default prod via env `LLM_BACKEND=vllm` |
| `langfuse` | `>=3,<4` | Callback handler per LangGraph (telemetry traces + token usage + cost) | Locked STACK.md; v3 SDK API completamente nuovo vs v2 |
| `fastapi` | `>=0.115,<0.117` | API gateway endpoints `/v1/approvals*` | Locked STACK.md |
| `uvicorn` | `>=0.32` | ASGI server | Standard FastAPI deployment |
| `asyncpg` | `>=0.30,<0.31` | PG async driver — già locked Phase 3 | Pattern già in `services/ot-bridge/timescale_writer.py` |
| `nats-py` | `>=2.7,<2.10` | NATS JetStream client | Pattern già in `services/ot-bridge/nats_publisher.py` |
| `pydantic` | `>=2.9,<3.0` | Pydantic v2 frozen + extra=forbid | Already enforced project-wide |
| `structlog` | `>=24.4` | JSON logging | Already used Phase 3 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langgraph-supervisor` | `>=0.0.10` | **Optional**: helper `create_supervisor()` factory | **Skip** for Phase 4 — D-54 hybrid routing richiede custom routing logic; il helper assume LLM-only routing |
| `langchain-core[fake]` o `langchain-fake` | n/a | Mock LLM `FakeListChatModel` per unit test | Test fixtures; integration test usa real Ollama opzionalmente |
| `httpx` | `>=0.28` | Test client per FastAPI (AsyncClient + ASGITransport) | Già in STACK.md Phase 1; Phase 4 lo usa per HITL E2E test |
| `pytest-asyncio` | `>=0.24` | Async test runner | Già configurato Phase 3 |
| `testcontainers-python[postgres]` | `>=4.8` | PG + NATS ephemeral containers per integration test | Alternativa al `compose_stack` fixture (port-5432 issue Phase 3) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `langgraph-supervisor` factory | `StateGraph` custom + manual `Command(goto=...)` routing | Custom richiesto da D-54 (hybrid rules+LLM); il factory è LLM-only |
| Postgres `AsyncPostgresSaver` | `SqliteSaver` dev fallback | NO — STACK.md explicitly forbids SQLite in prod; Phase 4 uses PG uniformly |
| Custom Pydantic-v2 audit writer | SQLAlchemy ORM | NO — Phase 3 idiom is raw asyncpg ($1..$N placeholders); consistency |
| NATS subjects ad-hoc | NATS subject ACL per role | Defer Phase 11; Phase 4 ships subjects-as-convention, no ACL hardening |
| FastAPI auth (OAuth/OIDC) | bare endpoints | Locked CONTEXT.md: auth deferred Phase 11 per A-018 |

**Installation:** Le deps sono additive a `packages/sft-agents/pyproject.toml` (oggi vuoto). Tutte sono in workspace `uv` Nx già configurato.

```bash
# Inside packages/sft-agents
uv add "langgraph>=0.4,<0.5" "langgraph-checkpoint-postgres>=3.1,<4" \
       "langchain-core>=0.3,<0.4" "langchain-ollama>=0.3,<0.4" \
       "langchain-openai>=0.3,<0.4" "langfuse>=3,<4" \
       "asyncpg>=0.30" "nats-py>=2.7" "pydantic>=2.9" "structlog>=24.4"

# Inside apps/api-gateway
uv add "fastapi>=0.115,<0.117" "uvicorn>=0.32" "httpx>=0.28" \
       "sft-agents" "langchain-core>=0.3" "asyncpg>=0.30" "nats-py>=2.7"
```

**Version verification command (planner must execute before plan ratification):**

```bash
pip index versions langgraph                          # confirm 0.4.x latest
pip index versions langgraph-checkpoint-postgres      # confirm 3.1.x latest
pip index versions langfuse                          # confirm v3 published, NOT v2
pip index versions langchain-ollama langchain-openai
```

## Package Legitimacy Audit

`slopcheck` non risulta installato nell'ambiente; tutti i package sono `[ASSUMED]` come da protocollo. Ma sono tutti package canonici di lunga data, già in uso nel monorepo dalla Phase 3, e i nomi sono cross-referenziati a fonti ufficiali multiple (PyPI + docs.langchain.com + Context7 STACK.md). Il planner deve comunque inserire un task `checkpoint:human-verify` prima del primo `uv add` se vuole rigore massimo.

| Package | Registry | Age | Source Repo | slopcheck | Disposition | Note |
|---------|----------|-----|-------------|-----------|-------------|------|
| `langgraph` | PyPI | 2+ years | github.com/langchain-ai/langgraph | unavailable | `[ASSUMED]` — already in STACK.md, verified via official docs | Confidence HIGH (1M+ downloads/month, official LangChain) |
| `langgraph-checkpoint-postgres` | PyPI | 1+ year | github.com/langchain-ai/langgraph (monorepo) | unavailable | `[ASSUMED]` | Confidence HIGH; v3.1.0 confirmed by [PyPI listing](https://pypi.org/project/langgraph-checkpoint-postgres/) |
| `langchain-core` | PyPI | 2+ years | github.com/langchain-ai/langchain | unavailable | `[ASSUMED]` | Confidence HIGH (official) |
| `langchain-ollama` | PyPI | 1+ year | github.com/langchain-ai/langchain (monorepo) | unavailable | `[ASSUMED]` | Confidence HIGH (official, paired with Ollama daemon) |
| `langchain-openai` | PyPI | 2+ years | github.com/langchain-ai/langchain (monorepo) | unavailable | `[ASSUMED]` | Confidence HIGH (official) |
| `langfuse` | PyPI | 2+ years | github.com/langfuse/langfuse-python | unavailable | `[ASSUMED]` | Confidence HIGH (1M+ deploys self-hosted per STACK.md) |
| `fastapi` | PyPI | 5+ years | github.com/tiangolo/fastapi | unavailable | `[ASSUMED]` | Confidence HIGH (de facto Python async API standard) |
| `uvicorn` | PyPI | 6+ years | github.com/encode/uvicorn | unavailable | `[ASSUMED]` | Confidence HIGH |
| `asyncpg` | PyPI | 8+ years | github.com/MagicStack/asyncpg | unavailable | `[ASSUMED]` | Already in `services/ot-bridge` Phase 3 |
| `nats-py` | PyPI | 5+ years | github.com/nats-io/nats.py | unavailable | `[ASSUMED]` | Already in `services/ot-bridge` Phase 3 |
| `pydantic` | PyPI | 7+ years | github.com/pydantic/pydantic | unavailable | `[ASSUMED]` | Project-wide |
| `structlog` | PyPI | 10+ years | github.com/hynek/structlog | unavailable | `[ASSUMED]` | Project-wide |
| `langgraph-supervisor` | PyPI | < 1 year | github.com/langchain-ai/langgraph-supervisor-py | unavailable | **REMOVED** | Skip — D-54 richiede custom routing logic incompatibile col factory LLM-only |
| `testcontainers` | PyPI | 5+ years | github.com/testcontainers/testcontainers-python | unavailable | `[ASSUMED]` (optional) | Alternative test fixture |

**Packages removed:** `langgraph-supervisor` (incompatible con D-54 hybrid routing).
**Packages flagged suspicious:** none — tutti i package elencati sono già nello stack o sono helper standard LangChain ecosystem.

## Technical Approach

> Le sotto-sezioni che seguono mappano 1:1 le 13 aree tecniche di Phase 4. Ogni sezione ha (a) decisione tecnica, (b) snippet illustrativo, (c) collegamento a CONTEXT.md decision o Open Question.

### §1 — `sft-agents` SDK skeleton

**Layout target** `packages/sft-agents/src/sft_agents/`:

```
sft_agents/
├── __init__.py                # public API exports
├── __version__.py             # già esiste
├── models/                    # Pydantic v2 schemas
│   ├── __init__.py
│   ├── evidence.py            # EvidencePanel, ToolCall, RagCitation, TokenUsage
│   ├── audit.py               # AuditRecord (DB-side projection)
│   ├── approval.py            # ApprovalRequest, ApprovalDecision, Tier (enum)
│   ├── proposed_action.py     # ProposedAction (action_type, payload, target_subject)
│   └── budget.py              # BudgetSnapshot, BudgetLimits
├── base/                      # ABC interfaces
│   ├── __init__.py
│   ├── agent.py               # class Agent(ABC): name, cluster, tools, memory, policy
│   ├── tool.py                # class Tool(BaseTool, ABC) — wraps langchain BaseTool
│   ├── memory.py              # class MemoryStore(ABC): query/store
│   └── policy.py              # class Policy(ABC): pre_tool_check, post_decision_check
├── llm/
│   ├── __init__.py
│   ├── factory.py             # build_chat_model(backend: Literal["ollama","vllm"]) → BaseChatModel
│   └── budgeting.py           # BudgetingChatModel wrapper (D-60)
├── runtime/
│   ├── __init__.py
│   ├── supervisor.py          # build_supervisor_graph() — D-53/D-54
│   ├── clusters.py            # build_cluster_subgraph(cluster_name, child_agents)
│   ├── checkpointer.py        # get_postgres_checkpointer(dsn) async context manager
│   ├── budget.py              # BudgetTracker middleware node
│   ├── escalation.py          # background asyncio.Task — escalation_supervisor
│   └── governor.py            # background asyncio.Task — auto-approval rate governor
├── hitl/
│   ├── __init__.py
│   ├── interrupt.py           # human_approval_node() — emits ApprovalRequest, calls interrupt()
│   └── approval_queue.py      # PG-backed AppovalQueueWriter + NATS notifier
├── audit/
│   ├── __init__.py
│   ├── writer.py              # AuditWriter — dual-write PG sync + NATS async (D-56)
│   └── outbox.py              # PG outbox table for failed NATS publishes (retry loop)
├── policies/
│   ├── __init__.py
│   ├── safety_interlock.py    # SafetyInterlockMiddleware (D-58)
│   ├── routing.py             # HybridRouter (D-54) — yaml + LLM fallback
│   ├── routing.yaml           # 5-cluster keywords/regex
│   ├── escalation-sla.yaml    # D-57 SLA per tier
│   ├── safety-interlock.yaml  # D-58 whitelist
│   └── budgets.yaml           # D-60 limits per cluster + override agent_id
├── memory/
│   ├── __init__.py
│   ├── base.py                # MemoryRecord, MemoryStore ABC
│   ├── episodic.py            # EpisodicReplay (Phase 4 — NATS+TimescaleDB)
│   └── long_term_stub.py      # StubLongTermMemory (Phase 4 returns [])
├── replay/
│   ├── __init__.py
│   └── from_checkpoint.py     # replay_thread(thread_id, action_id) — D-46 + CORE-10
└── tools/
    ├── __init__.py
    └── registry.py            # re-export sft-tools (Phase 3) + per-agent registry helpers
```

**Public API (final):**
```python
from sft_agents import (
    Agent, Tool, Memory, Policy,         # ABC
    Supervisor, ClusterSubgraph,         # runtime builders
    BudgetTracker, EvidencePanel,        # middleware + schema
    AuditRecord, ApprovalRequest,        # schema
    Tier, Decision, ActionType,          # enums
)
```

### §2 — Supervisor + 5 cluster subgraphs (D-53 + D-54)

LangGraph 0.4+ pattern: `StateGraph` + sub-`StateGraph` composti via `add_node(name, subgraph.compile())`. Il supervisor è un *router node*, non un LLM-wrapped agent.

**Custom routing (D-54) — NON usare `langgraph-supervisor` factory** perché:
1. Il factory assume routing LLM-only e usa `model.bind_tools()` per handoff; D-54 richiede Stage 1 rule-based.
2. Il factory aggiunge un implicit `messages: list` reducer che può collidere con la custom `AgentState`.

```python
# packages/sft-agents/src/sft_agents/runtime/supervisor.py (illustrative)
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

ClusterName = Literal["ops","maintenance","knowledge-curation","knowledge-training","supply"]

async def supervisor_route(state: AgentState) -> Command[ClusterName]:
    """Router node: Stage 1 rules → Stage 2 LLM fallback."""
    intent = state["messages"][-1].content
    # Stage 1 (rule-based)
    matches = HybridRouter.match_rules(intent)
    if len(matches) == 1:
        cluster = matches[0]
        log.info("supervisor_route", strategy="rules", cluster=cluster, confidence=1.0)
        return Command(update={"cluster": cluster}, goto=cluster)
    # Stage 2 (LLM)
    result = await HybridRouter.classify_llm(intent, llm=llm)
    cluster = result.cluster if result.confidence >= 0.7 else "ops"
    log.info("supervisor_route", strategy="llm", cluster=cluster, confidence=result.confidence)
    return Command(update={"cluster": cluster}, goto=cluster)

def build_supervisor_graph(child_agents_by_cluster: dict[ClusterName, list[Agent]]) -> CompiledGraph:
    sg = StateGraph(AgentState)
    sg.add_node("supervisor", supervisor_route)
    for cluster_name in ("ops","maintenance","knowledge-curation","knowledge-training","supply"):
        cluster_sub = build_cluster_subgraph(cluster_name, child_agents_by_cluster[cluster_name])
        sg.add_node(cluster_name, cluster_sub)
    sg.add_edge(START, "supervisor")
    for cluster_name in (...):
        sg.add_edge(cluster_name, END)
    return sg.compile(checkpointer=checkpointer)
```

**recursion_limit (CORE-03):** passato a ogni `graph.ainvoke(input, config={"configurable":{"thread_id":...}, "recursion_limit": 25})`. Su `GraphRecursionError`, il caller (`apps/api-gateway/` o background task) cattura l'eccezione, scrive AuditRecord `decision='rolled_back'` con motivation="recursion_limit_exceeded" + emette ApprovalRequest tier=`supervisor`.

```python
from langgraph.errors import GraphRecursionError
try:
    result = await graph.ainvoke(state, config=cfg)
except GraphRecursionError as e:
    await audit_writer.write(AuditRecord(decision="rolled_back", motivation=f"recursion_limit: {e}"))
    await approval_queue.enqueue(ApprovalRequest(tier="supervisor", action_type="GRAPH_RECURSION_REVIEW", payload={...}))
```

### §3 — PostgreSQL checkpointer (`AsyncPostgresSaver`, CORE-04 + success criterion #4)

**Setup pattern (one-shot, NOT per-process startup):**

```python
# scripts/langgraph-init.py — NEW, mirrors scripts/nats-bootstrap-streams.py idiom
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async def bootstrap_checkpointer(dsn: str) -> int:
    async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
        await saver.setup()  # creates checkpoints, checkpoint_blobs, checkpoint_migrations
    return 0
```

**Per-process usage (in api-gateway + runtime tests):**

```python
# packages/sft-agents/src/sft_agents/runtime/checkpointer.py
from contextlib import asynccontextmanager
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

@asynccontextmanager
async def get_postgres_checkpointer(dsn: str):
    async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
        # NO setup() qui — già fatto da scripts/langgraph-init.py durante migrations
        yield saver
```

**Key API notes (verified via [reference.langchain.com](https://reference.langchain.com/python/langgraph.checkpoint.postgres/aio/AsyncPostgresSaver) + community blog [lordpatil](https://blog.lordpatil.com/posts/langgraph-postgres-checkpointer/)):**

- `.setup()` crea 3 tabelle: `checkpoints`, `checkpoint_blobs`, `checkpoint_migrations`. Idempotente.
- Se passi una connessione manualmente (vs `from_conn_string`), DEVI usare `autocommit=True` E `row_factory=dict_row` da `psycopg.rows.dict_row` — questo è un Pitfall §2 sotto.
- Schema PG NON è configurabile in langgraph-checkpoint-postgres Python (issue aperto [forum.langchain.com #3274](https://forum.langchain.com/t/feature-request-configurable-postgresql-schema-for-langgraph-checkpoint-postgres-parity-with-langgraphjs/3274)) — le tabelle vivono nello schema `public` di default. **Implicazione:** il nostro `migrate.py` Phase 3 deve evitare collisione (e.g. usare `sensor_events` non `checkpoints`). Verificato: nessun conflict.

**thread_id (success criterion #4 — paused HITL approval survives restart):**
- Convention `{cluster}.{agent_id}.{session_uuid}` (CONTEXT.md Claude's discretion).
- Resume: `graph.ainvoke(Command(resume=decision_payload), config={"configurable":{"thread_id": same_id}})`.
- **Pitfall:** se cambi shape di `AgentState` tra checkpoint write e read, deserialization fallisce. Phase 4 freeze schema con Pydantic v2 frozen+extra=forbid; future schema migration richiede ad-hoc tooling (Phase 11 governance).

### §4 — Provider-agnostic LLM adapter (CORE-05 + CORE-06)

```python
# packages/sft-agents/src/sft_agents/llm/factory.py
import os
from typing import Literal
from langchain_core.language_models import BaseChatModel

LLMBackend = Literal["ollama","vllm"]

def build_chat_model(
    *, backend: LLMBackend | None = None, temperature: float = 0.0, seed: int = 42, **kw
) -> BaseChatModel:
    backend = backend or os.environ.get("LLM_BACKEND", "ollama").lower()
    if backend == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M"),
            base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            temperature=temperature,
            seed=seed,
            **kw,
        )
    elif backend == "vllm":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.environ.get("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ"),
            base_url=os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1"),
            api_key=os.environ.get("VLLM_API_KEY", "dummy"),
            temperature=temperature,
            seed=seed,
            **kw,
        )
    raise ValueError(f"Unknown LLM_BACKEND: {backend}")
```

**vLLM Qwen2.5-14B AWQ tool calling (verified [docs.vllm.ai/features/tool_calling](https://docs.vllm.ai/en/latest/features/tool_calling/) + [qwen.readthedocs.io function_call](https://qwen.readthedocs.io/en/latest/framework/function_call.html)):**

vLLM serving command (Phase 11 deploy; Phase 4 documenta per integration testing):
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-14B-Instruct-AWQ \
  --quantization awq \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --max-model-len 32768
```

**Critical:** `--tool-call-parser hermes` è MANDATORIO per Qwen2.5 — la tokenizer chat template usa Hermes-style tool tokens. Senza questo flag, `tool_calls` non vengono populated in OpenAI response shape e `langchain-openai` riceve `tool_calls=[]` silenziosamente. Documenta in `docs/docs/architecture/llm-serving.md`.

**vLLM strict mode caveat:** vLLM accetta il campo `strict=True` nei requests ma NON lo implementa (graceful no-op). Quindi Pydantic v2 `args_schema` validation deve essere repliata client-side dopo la response — `langchain-openai` BaseTool fa già questo via `tool.invoke(args)` che attiva Pydantic validation.

### §5 — Tool registry (CORE-07)

```python
# packages/sft-agents/src/sft_agents/tools/registry.py
from langchain_core.tools import BaseTool
from sft_tools import REPLAY_TOOLS, TIMESCALE_TOOLS  # Phase 3 re-export

def export_tool_schemas(tools: list[BaseTool]) -> list[dict]:
    """Esporta JSON schemas OpenAI-compatible per function calling.

    Usa `args_schema.model_json_schema(by_alias=True)` — Pydantic v2 native.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.args_schema.model_json_schema(by_alias=True),
            },
        }
        for tool in tools
    ]
```

### §6 — Memory layer (D-59 — CORE-08)

**Short-term:** già coperto da `AsyncPostgresSaver` (§3).

**Episodic:** `EpisodicReplay` riusa Phase 3 `QueryTimescaleTool` ma punta a `audit.actions` (NOT `sensor_events`). NB: `audit.actions` è hypertable separata; lo schema è diverso (`thread_id`, `evidence_panel JSONB`).

```python
# packages/sft-agents/src/sft_agents/memory/episodic.py
class EpisodicReplay(MemoryStore):
    async def replay_thread(self, thread_id: str, since: datetime | None = None) -> list[AuditRecord]:
        sql = (
            "SELECT * FROM audit.actions "
            "WHERE thread_id = $1 AND ts >= COALESCE($2, '-infinity'::timestamptz) "
            "ORDER BY ts ASC"
        )
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, thread_id, since)
        return [AuditRecord.model_validate(dict(r)) for r in rows]
```

**Long-term stub:** `StubLongTermMemory` ritorna `[]`; Phase 5 sostituisce con `QdrantLongTermMemory`. Interface stabile in Phase 4.

### §7 — Budget tracker middleware (D-60 — CORE-09)

```python
# packages/sft-agents/src/sft_agents/runtime/budget.py
class BudgetTracker:
    """Middleware node che si inserisce PRIMA di ogni LLM call + ToolNode."""

    _UPSERT_SQL = (
        "INSERT INTO budget.executions "
        "(thread_id, agent_id, tokens_total, cost_usd, duration_ms, step_count, started_at, last_step_at) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) "
        "ON CONFLICT (thread_id, agent_id) DO UPDATE SET "
        "tokens_total = budget.executions.tokens_total + EXCLUDED.tokens_total, "
        "cost_usd = budget.executions.cost_usd + EXCLUDED.cost_usd, "
        "duration_ms = budget.executions.duration_ms + EXCLUDED.duration_ms, "
        "step_count = budget.executions.step_count + 1, "
        "last_step_at = EXCLUDED.last_step_at"
    )

    async def increment(self, snapshot: BudgetSnapshot) -> BudgetSnapshot:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(self._UPSERT_SQL + " RETURNING *",
                                      snapshot.thread_id, snapshot.agent_id, ...)
        return BudgetSnapshot.model_validate(dict(row))
```

**Token capture:** UsageMetadata propagata via `langchain_core.callbacks.UsageMetadataCallbackHandler` — passed in `config["callbacks"]`. Funziona con `ChatOpenAI` (vLLM) e `ChatOllama`. **Pitfall §4:** streaming mode con OpenAI può NON emettere usage_metadata sull'ultimo chunk; soluzione = forzare `stream_usage=True` su `ChatOpenAI` (parametro disponibile da langchain-openai 0.2+).

### §8 — Replay tool (CORE-10)

```python
# packages/sft-agents/src/sft_agents/replay/from_checkpoint.py
async def replay_thread(
    thread_id: str,
    target_action_id: UUID | None = None,
    *,
    checkpointer: AsyncPostgresSaver,
    audit_reader: EpisodicReplay,
    mock_tools: bool = True,
) -> ReplayResult:
    """Replay deterministico best-effort (CORE-10).

    Strategy:
    1. Load checkpoints for thread_id via aget_tuple.
    2. Load audit.actions records for thread_id ordered by ts.
    3. Replay graph.ainvoke(start_state, config) with mocked tools that return audit.tool_calls from history.
    4. Compare resulting state[messages][-1] with original final state.
    """
```

**Determinism caveats (verified [vLLM reproducibility docs](https://docs.vllm.ai/en/latest/usage/reproducibility/) + [Thinking Machines paper](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)):**
- Su **stessa hardware + stessa vLLM version + seed fissato + temperature=0**, vLLM è deterministico per richiesta-singola.
- Qwen2.5-7B su Ollama: ~17.6% exact-match across seeds anche a `temperature=0` (testato in [arxiv 2512.12066](https://arxiv.org/html/2512.12066v2)).
- Phase 4 ships "best-effort replay": tool outputs **mock-replayed** dalla audit log (deterministic), LLM responses **rerunned** (probabilistically same se hardware identico).
- Full frozen-output determinism → Phase 11 (cache prompt_hash → response lookup).

### §9 — HITL `interrupt()` + `Command(resume=)` round-trip (HITL-01 + HITL-04 + HITL-07)

```python
# packages/sft-agents/src/sft_agents/hitl/interrupt.py
from langgraph.types import interrupt, Command

async def human_approval_node(state: AgentState, *, approval_queue: ApprovalQueue) -> dict:
    """Node che proporne ApprovalRequest e attende decision via interrupt()."""
    action = state["proposed_actions"][-1]
    # 1) Persist ApprovalRequest in PG + publish NATS notify (D-55)
    request = await approval_queue.enqueue(ApprovalRequest(
        agent_id=state["agent_id"],
        thread_id=state["thread_id"],
        tier=Tier.OPERATOR,  # default; può essere routed per action_type
        action_type=action.action_type,
        payload_json=action.model_dump(),
    ))
    # 2) interrupt() — graph pausa, state persisted via checkpointer
    decision = interrupt({
        "approval_id": str(request.id),
        "tier": request.tier.value,
        "action": action.model_dump(),
        "evidence": state["evidence"].model_dump() if state.get("evidence") else None,
    })
    # 3) Resume — decision è il payload passato a Command(resume=...)
    #    decision shape: {"decision": "approve|reject|escalate", "motivation": str, "decided_by": str}
    assert decision["motivation"], "motivation is mandatory (HITL-07)"
    return {"pending_approval_id": None, "last_decision": decision}
```

**Critical pitfall (Pitfall §6 below):** quando il graph resume, il nodo che ha chiamato `interrupt()` viene **ri-eseguito dall'inizio**. Quindi tutto il codice PRIMA di `interrupt(...)` ri-gira. Significa: l'INSERT in `hitl.approvals` viene chiamato 2 volte se non guardato con idempotency check. Soluzione: `approval_queue.enqueue` deve essere idempotente per `(thread_id, action.id)` (action_id = UUID generato deterministicamente prima dell'interrupt).

### §10 — 4-tier escalation (D-57 — HITL-02)

```python
# packages/sft-agents/src/sft_agents/runtime/escalation.py
async def escalation_supervisor_loop(pool: asyncpg.Pool, nats: Any):
    """Background task: scansiona PG approvals scadute, escalates."""
    while True:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM hitl.approvals "
                "WHERE status='pending' AND sla_deadline < NOW() FOR UPDATE SKIP LOCKED"
            )
            for row in rows:
                next_tier = SLA_CONFIG[row["tier"]]["next_tier"]
                if next_tier is None:
                    # Manager timeout: alert ma no escalation
                    await audit_writer.write(AuditRecord(decision="timed_out", ...))
                else:
                    new_id = await conn.fetchval(
                        "INSERT INTO hitl.approvals (...) VALUES (...) RETURNING id",
                        ...,  # tier=next_tier, escalated_to_id refers original
                    )
                    await conn.execute(
                        "UPDATE hitl.approvals SET status='escalated', escalated_to_id=$1 WHERE id=$2",
                        new_id, row["id"],
                    )
                    await nats.publish(f"hitl.approvals.new.{next_tier}", ...)
        await asyncio.sleep(30)
```

`FOR UPDATE SKIP LOCKED` è essenziale: multipli api-gateway replicas non devono escalare la stessa row.

### §11 — Safety Interlock middleware (D-58 — HITL-03)

```python
# packages/sft-agents/src/sft_agents/policies/safety_interlock.py
import yaml
from pathlib import Path

class SafetyInterlockMiddleware:
    def __init__(self, config_path: Path):
        with config_path.open() as f:
            cfg = yaml.safe_load(f)  # MANDATORY safe_load
        self.forbidden_subjects = cfg.get("forbidden_subjects", [])
        self.forbidden_action_types = set(cfg.get("forbidden_action_types", []))

    async def check_before_tool(self, action: ProposedAction) -> None:
        if action.action_type in self.forbidden_action_types:
            raise SafetyInterlockRejection(action_type=action.action_type)
        for pat in self.forbidden_subjects:
            if subject_match(pat, action.target_subject):
                raise SafetyInterlockRejection(subject=action.target_subject)

class SafetyInterlockRejection(Exception):
    """Raised when an agent attempts a forbidden action. Terminates the graph thread."""
```

Inserito come node che precede ogni `ToolNode` invocation (compose-time wiring). Risultato: audit `decision='interlock_reject'` + ApprovalRequest auto-fails con `status='rejected'`.

### §12 — Audit dual-write (D-56 — HITL-05)

**Pattern (replica `services/ot-bridge/timescale_writer.py + nats_publisher.py`):**

```python
# packages/sft-agents/src/sft_agents/audit/writer.py
class AuditWriter:
    _INSERT_SQL = (
        "INSERT INTO audit.actions "
        "(id, ts, action_id, agent_id, thread_id, cluster, action_type, "
        " evidence_panel, decision, decision_actor, motivation, budget_snapshot, approval_id) "
        "VALUES ($1, NOW(), $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)"
    )

    async def write(self, record: AuditRecord) -> None:
        # 1) PG sync (BLOCKING) — if fails, agent ABORTS
        async with self._pool.acquire() as conn:
            await conn.execute(self._INSERT_SQL, ...)
        # 2) NATS async (fire-and-forget with outbox retry on failure)
        try:
            subject = f"audit.actions.{record.cluster}.{record.agent_id}"
            await self._js.publish(subject, record.model_dump_json().encode())
        except Exception as exc:
            log.warning("audit_nats_publish_failed", error=str(exc), record_id=str(record.id))
            await self._outbox.append(record)  # retry by background task
```

**Immutability PG-side:**
```sql
-- 003_create_audit_actions.sql
CREATE SCHEMA IF NOT EXISTS audit;
CREATE TABLE IF NOT EXISTS audit.actions (...);
SELECT create_hypertable('audit.actions','ts',chunk_time_interval=>INTERVAL '30 days', if_not_exists=>TRUE);
SELECT add_retention_policy('audit.actions', INTERVAL '7 years', if_not_exists=>TRUE);

-- Idempotency safe: revoke if not already revoked
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agent_role') THEN
    REVOKE UPDATE, DELETE ON audit.actions FROM agent_role;
    GRANT INSERT, SELECT ON audit.actions TO agent_role;
  END IF;
END $$;
```

**Outbox pattern:** PG table `audit.actions_outbox (id UUID PK, record_json JSONB, attempts INT DEFAULT 0, last_attempt_at TIMESTAMPTZ)`. Background task ogni 30s retry publish + delete on success.

**Open question §1:** chi crea il ruolo `agent_role`? Phase 4 (in migration 003) o Phase 11 (governance)?  
**Recommendation:** Phase 4 crea il ruolo con `CREATE ROLE IF NOT EXISTS agent_role NOLOGIN` (DO block); Phase 11 gestirà il binding a user reali via SealedSecrets. Phase 4 ships idempotent role creation.

### §13 — Approval rate governor (D-58 — HITL-09)

```python
# packages/sft-agents/src/sft_agents/runtime/governor.py
GOVERNOR_SQL = (
    "SELECT decision, COUNT(*)::int AS n FROM audit.actions "
    "WHERE ts > NOW() - INTERVAL '1 hour' "
    "GROUP BY decision"
)

async def governor_loop(pool, nats, writer):
    while True:
        async with pool.acquire() as conn:
            rows = await conn.fetch(GOVERNOR_SQL)
        counts = {r["decision"]: r["n"] for r in rows}
        total = sum(counts.values())
        if total >= 20:
            auto_rate = counts.get("auto", 0) / total
            if auto_rate > 0.80:
                await nats.publish("hitl.governor.alert", json.dumps({
                    "auto_rate": auto_rate, "sample_size": total, ...
                }).encode())
                await approval_queue.enqueue(ApprovalRequest(
                    tier=Tier.MANAGER, action_type="GOVERNOR_ALERT", ...
                ))
                await writer.write(AuditRecord(decision="governor_alert", ...))
        await asyncio.sleep(60)
```

## Validation Architecture

> Required (config.json `workflow.nyquist_validation` not explicitly false; default enabled). Phase 3 mode pattern: pytest + testcontainers + asyncpg fixtures.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24+ (already configured Phase 3 in tests/conftest.py) |
| Config file | `pyproject.toml` workspace `[tool.pytest.ini_options]` + `tests/conftest.py` (root) |
| Quick run command | `uv run pytest packages/sft-agents/tests -x -k "not integration"` (<30s) |
| Full suite command | `nx run sft-agents:test` (unit + integration with testcontainers) |
| HITL E2E command | `pytest tests/integration/test_hitl_loop.py -m integration` (needs docker) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CORE-01 | sft-agents Public API exports stable | unit | `pytest packages/sft-agents/tests/test_public_api.py -x` | ❌ Wave 0 |
| CORE-02 | Supervisor routes to correct cluster (rules + LLM fallback) | unit | `pytest packages/sft-agents/tests/test_supervisor_routing.py -x` (mock LLM) | ❌ Wave 0 |
| CORE-03 | recursion_limit triggers escalation, not crash | unit | `pytest packages/sft-agents/tests/test_recursion_limit.py -x` | ❌ Wave 0 |
| CORE-04 | Checkpoint survives restart | integration | `pytest tests/integration/test_checkpoint_resume.py -m integration` | ❌ Wave 0 |
| CORE-05 | LLM_BACKEND env var switches adapter | unit | `pytest packages/sft-agents/tests/test_llm_factory.py -x` | ❌ Wave 0 |
| CORE-06 | Default versions resolve via env | unit | covered by CORE-05 | covered |
| CORE-07 | Tool registry exports valid JSON schemas | unit | `pytest packages/sft-agents/tests/test_tool_registry.py -x` | ❌ Wave 0 |
| CORE-08 | EpisodicReplay returns audit records in order | integration | `pytest tests/integration/test_episodic_replay.py -m integration` | ❌ Wave 0 |
| CORE-09 | Budget hard-limit triggers ApprovalRequest | unit | `pytest packages/sft-agents/tests/test_budget.py -x` | ❌ Wave 0 |
| CORE-10 | Replay reconstructs final state from checkpoint+audit | integration | `pytest tests/integration/test_replay.py -m integration` | ❌ Wave 0 |
| HITL-01 | Full interrupt() → Command(resume=) round-trip | integration | `pytest tests/integration/test_hitl_loop.py::test_full_cycle -m integration` | ❌ Wave 0 |
| HITL-02 | Escalation supervisor promotes expired tier | integration | `pytest tests/integration/test_escalation.py -m integration` | ❌ Wave 0 |
| HITL-03 | Safety Interlock blocks forbidden action | unit | `pytest packages/sft-agents/tests/test_safety_interlock.py -x` | ❌ Wave 0 |
| HITL-04 | Approval queue persists across restart | integration | covered by HITL-01 (same fixture chain) | covered |
| HITL-05 | Audit row append-only (REVOKE enforced) | integration | `pytest tests/integration/test_audit_immutability.py -m integration` | ❌ Wave 0 |
| HITL-06 | EvidencePanel attached to every audit row | unit | `pytest packages/sft-agents/tests/test_evidence_panel.py -x` | ❌ Wave 0 |
| HITL-07 | Motivation NOT NULL on hitl_* decisions | unit | `pytest packages/sft-agents/tests/test_audit_constraints.py -x` | ❌ Wave 0 |
| HITL-08 | Replay rolls back via compensating events | integration | covered by CORE-10 (best-effort Phase 4; full Phase 11) | covered |
| HITL-09 | Governor fires alert at >80% auto-rate | integration | `pytest tests/integration/test_governor.py -m integration` | ❌ Wave 0 |
| HITL-10 | UI rate-limit primitive available | unit | `pytest packages/sft-agents/tests/test_rate_limit_audit_query.py -x` (just data query; UI Phase 10) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/sft-agents/tests -x -k "not integration"` (target <30s; mock LLM, mock NATS, mock PG via fakeasyncpg or in-memory)
- **Per wave merge:** `nx affected --target=test` (only changed packages)
- **Phase gate:** Full suite + integration tests green before `/gsd:verify-work`; HITL E2E test required to pass.

### Wave 0 Gaps

- [ ] `packages/sft-agents/tests/conftest.py` — fixtures: `mock_llm`, `mock_checkpointer`, `mock_nats_publisher`, `mock_pool`
- [ ] `tests/integration/test_hitl_loop.py` — fixture chain: testcontainers PG + NATS, real `AsyncPostgresSaver`, mock LLM via `FakeListChatModel`
- [ ] `tests/integration/test_checkpoint_resume.py` — start graph, interrupt(), kill process, restart, resume — verify state identical
- [ ] `tests/integration/test_audit_immutability.py` — assert REVOKE prevents UPDATE/DELETE from agent_role
- [ ] `tests/integration/test_governor.py` — seed 25 audit rows con 22 `decision='auto'`, run governor once, assert alert published
- [ ] Framework install: already done Phase 3; Phase 4 only adds `langchain-fake` o usa `FakeListChatModel` da langchain-core

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | NO (deferred Phase 11 per A-018) | Phase 4 endpoints unauth; CONTEXT.md locked |
| V3 Session Management | partial — thread_id as session | thread_id UUID v4 unguessable; isolation per cluster.agent.session |
| V4 Access Control | YES (DB-side) | REVOKE UPDATE/DELETE on audit.actions; CREATE ROLE agent_role with INSERT only |
| V5 Input Validation | YES | Pydantic v2 frozen + extra=forbid su tutti i modelli; LangChain `args_schema` su Tools |
| V6 Cryptography | minimal | No secrets stored Phase 4 (TIMESCALE_DSN via env, NATS_URL via env) — Phase 11 hardens |

### Known Threat Patterns for {LangGraph + Postgres + NATS stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via f-string in audit/budget INSERT | Tampering | $1..$N placeholders ONLY (replicate Phase 3 idiom); zero f-string SQL — enforce via grep CI check |
| Prompt injection on routing classifier | Tampering | Pydantic structured output (`cluster: Literal[...]`); fallback `ops` on confidence <0.7 ignores arbitrary output |
| Audit log tampering | Repudiation | REVOKE UPDATE/DELETE on audit.actions from agent_role; PG-side append-only enforced |
| Token budget exhaustion DoS | DoS | BudgetTracker hard-limit + per-thread quota PG enforcement |
| LLM hallucinating tool call to forbidden action | Elevation of Privilege | Safety Interlock middleware checks ProposedAction.action_type AND target_subject against whitelist YAML BEFORE ToolNode dispatch |
| PII leak via EvidencePanel.input_summary | Information Disclosure | A-013/A-018: no PII in payloads (synthetic data only Phase 4); Phase 11 adds redactor middleware |
| NATS subject hijack (publish to wrong audit subject) | Spoofing | Subject derivation from enum values + Pydantic validation (no user-controlled string) — replicate Phase 3 `derive_event_subject` pattern |
| Concurrent escalation race | Tampering | `FOR UPDATE SKIP LOCKED` su escalation scanner; idempotency check su enqueue (thread_id, action_id) |
| Approval forgery via decided_by spoofing | Spoofing | Phase 4 documenta: `decided_by` accettato unauthenticated (PoC); Phase 11 binds JWT claim |

## Pitfalls & Constraints

### Pitfall §1 — `GraphRecursionError` swallow-and-crash

**What goes wrong:** Default `recursion_limit=25` su graph con cyclic edges (agent ↔ tool node ping-pong) → `GraphRecursionError` non gestita → 500 al caller, agent termina silenziosamente.

**How to avoid:** Wrap ogni `graph.ainvoke(...)` con try/except per `from langgraph.errors import GraphRecursionError`. Documented [docs.langchain.com](https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT). Convertire in AuditRecord `decision='rolled_back'` + Supervisor-tier ApprovalRequest.

**Warning signs:** test che mocka LLM con response che invoca lo stesso tool ripetutamente → recursion_limit hit. Aggiungere fixture che testa esplicitamente.

### Pitfall §2 — `AsyncPostgresSaver` autocommit + dict_row obbligatori

**What goes wrong:** Se passi una connection PG creata manualmente (vs `from_conn_string`) senza `autocommit=True` AND `row_factory=psycopg.rows.dict_row`, le query `aget_tuple` falliscono silenziosamente (ritornano None invece di la checkpoint row).

**How to avoid:** Usa SEMPRE `AsyncPostgresSaver.from_conn_string(dsn)` context manager — costruisce la pool internamente con il setup corretto. Se DEVI passare connection custom (es. shared con audit writer), usa esattamente:

```python
import psycopg
from psycopg.rows import dict_row
conn = await psycopg.AsyncConnection.connect(dsn, autocommit=True, row_factory=dict_row)
saver = AsyncPostgresSaver(conn=conn)
```

Source: [reference.langchain.com PostgresSaver](https://reference.langchain.com/python/langgraph.checkpoint.postgres/PostgresSaver) + [lordpatil deep-dive](https://blog.lordpatil.com/posts/langgraph-postgres-checkpointer/).

### Pitfall §3 — vLLM `--tool-call-parser hermes` flag missing → silent tool_call=[] 

**What goes wrong:** vLLM server avviato per Qwen2.5 senza `--enable-auto-tool-choice --tool-call-parser hermes`. Le risposte arrivano come plain text `<tool_call>...</tool_call>` invece di `tool_calls: [...]` structured field. `langchain-openai` riceve `response.tool_calls = []` silenziosamente; l'agent loop termina pensando "nessun tool da invocare". HARD to debug.

**How to avoid:** documenta vLLM serve command in `docs/docs/architecture/llm-serving.md`. Phase 4 unit test che mocka `ChatOpenAI` e fa assert sul shape della response. Phase 4 integration test (manual smoke) verifica un vero tool call. Sources: [docs.vllm.ai/features/tool_calling](https://docs.vllm.ai/en/latest/features/tool_calling/), [GitHub vllm/issues/29192](https://github.com/vllm-project/vllm/issues/29192).

### Pitfall §4 — Streaming `ChatOpenAI` non emette `usage_metadata`

**What goes wrong:** Con `streaming=True`, l'ultimo chunk può NON contenere `usage_metadata`; il `UsageMetadataCallbackHandler` riceve 0 tokens. BudgetTracker conta zero → quota check bypassed.

**How to avoid:** `ChatOpenAI(stream_usage=True, ...)` (parametro da langchain-openai 0.2+). Per `ChatOllama`, lo streaming è disabilitato di default in Phase 4 (lo agent loop usa non-streaming per simplicità + token accuracy). Phase 11 può attivare streaming se necessario.

### Pitfall §5 — LLM "determinism" è un'illusione

**What goes wrong:** Tests pass su CI machine, fail su sviluppatore-laptop perché Qwen2.5-7B Ollama produce output diverso anche con `temperature=0, seed=42` (different GPU rounding). Tests flaky.

**How to avoid:** Test unit di routing/decisione NON devono mai usare LLM reale — sempre `FakeListChatModel(responses=[...])`. Integration test usa real LLM solo per smoke (NO exact-match assertion sui contents; verify structural properties: "response has tool_calls", "decision is one of approve|reject|escalate"). Sources: [Thinking Machines paper](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/), [arxiv 2512.12066](https://arxiv.org/html/2512.12066v2).

### Pitfall §6 — `interrupt()` re-runs the node from start on resume

**What goes wrong:** `human_approval_node` chiama `await approval_queue.enqueue(...)` PRIMA di `interrupt(...)`. Al resume, il node ri-esegue dall'inizio → enqueue called twice → duplicate rows in `hitl.approvals` con stesso content.

**How to avoid:** `approval_queue.enqueue` deve essere idempotente per `(thread_id, action_id)` con `ON CONFLICT DO NOTHING` su unique constraint. ProposedAction.id deve essere UUID generato DETERMINISTICAMENTE dal contenuto (es. SHA256 hash dei tool_call args + thread_id), NON `uuid4()`. Source: [Markaicode interrupt analysis](https://markaicode.com/langgraph-interrupt-pause-resume-agent/).

### Pitfall §7 — datetime.now() naive vs aware

**What goes wrong:** `datetime.now()` ritorna timezone-naive; INSERT in `audit.actions ts TIMESTAMPTZ` interpreta il valore come local timezone → off-by-hours.

**How to avoid:** **MANDATORY** `from datetime import datetime, timezone; datetime.now(timezone.utc)` (alias `UTC`). Phase 3 ha già enforced questo con Pydantic `field_validator` che raise se `v.tzinfo is None`. Phase 4 replica lo stesso validator su `EvidencePanel.{ts,started_at,...}`, `AuditRecord.ts`, `ApprovalRequest.{created_at,sla_deadline,...}`. Source: precedent Phase 3 `services/ot-bridge/models.py:60-72`.

### Pitfall §8 — `yaml.load()` instead of `yaml.safe_load()`

**What goes wrong:** Routing policies in `routing.yaml`, escalation in `escalation-sla.yaml`, safety in `safety-interlock.yaml`, budgets in `budgets.yaml` caricati con `yaml.load()` → arbitrary Python execution risk.

**How to avoid:** **MANDATORY** `yaml.safe_load(open(...))` everywhere. Already enforced project-wide (Phase 2 pattern). Add to pre-commit grep check.

### Pitfall §9 — asyncpg `$1..$N` placeholders, NEVER f-string SQL

**What goes wrong:** SQL injection via f-string interpolation in audit/budget INSERT, especially in dynamic WHERE clauses for governor query.

**How to avoid:** Replicate Phase 3 pattern: SQL constants module-level (e.g. `_INSERT_SQL = "INSERT ... VALUES ($1, $2, ...)"`). All dynamic values via positional args. Threat T-V5-sql from STACK.md. Pre-commit check: `grep -E 'f".*INSERT|f".*SELECT|\\.format.*INSERT'` in `packages/sft-agents/` → must be empty.

### Pitfall §10 — `statement_cache_size=0` obbligatorio per asyncpg + TimescaleDB

**What goes wrong:** TimescaleDB hypertables hanno dynamic plan optimization. asyncpg con default `statement_cache_size > 0` cacha prepared statement plans; quando il chunk policy cambia, query falliscono con `cached plan must not change result type`.

**How to avoid:** Phase 4 audit.actions è hypertable (D-56 7y retention via partitioning). Quindi `asyncpg.create_pool(dsn, ..., statement_cache_size=0, command_timeout=10.0)` mandatory. Pattern già in Phase 3 `services/ot-bridge/timescale_writer.py:82-88`.

### Pitfall §11 — Langfuse v3 SDK breaking change vs v2

**What goes wrong:** Tutorial online che mostrano `LangfuseCallbackHandler(session_id=...)` o `LangfuseCallbackHandler(metadata={...})` — quelle API sono Langfuse v2. v3 ha invertito la convention: la metadata deve essere passata in `config["metadata"]` al graph invocation, NON al callback constructor.

**How to avoid:** Phase 4 codice:
```python
config = {
    "configurable": {"thread_id": thread_id},
    "callbacks": [langfuse_handler],
    "metadata": {"langfuse_session_id": thread_id, "langfuse_user_id": user_id, "langfuse_tags": ["phase4"]},
    "recursion_limit": 25,
}
await graph.ainvoke(state, config=config)
```
Source: [langfuse discussion #8125](https://github.com/orgs/langfuse/discussions/8125), [discussion #8159](https://github.com/orgs/langfuse/discussions/8159).

### Pitfall §12 — `conftest.py` `compose_stack` port-5432 issue (Phase 3 documented)

**What goes wrong:** `tests/conftest.py:80-128` ha `compose_stack` fixture che porta `5432:5432`. Se uno sviluppatore ha già un Postgres locale su 5432, fixture fallisce. Phase 3 ha già documentato il problema; deferred.

**How to avoid Phase 4:** Phase 4 testi può:
- (A) RIUSARE `compose_stack` as-is (rischio collision)
- (B) Migrare a `testcontainers-python` (zero port conflict — ephemeral ports + auto-cleanup) — RECOMMENDED
- (C) Defer al Phase 11

**Recommendation:** Plan 04-07 (HITL E2E test) usa `testcontainers-python` per PG + NATS (option B). Plan documenta la migration come bonus che fixa Phase 3 issue. Se runtime budget hit, defer a Phase 11.

## Dependencies & Sequencing

Le 8 decisioni CONTEXT.md determinano il DAG. Suggested wave structure (allineato CONTEXT.md downstream_guidance):

```
Wave 1 (foundation, sequential):
  04-01: sft-agents SDK base — Pydantic models (EvidencePanel, AuditRecord, ApprovalRequest,
         BudgetSnapshot, ProposedAction) + ABC (Agent/Tool/Memory/Policy) + unit tests.
         Atomic. Blocks all subsequent waves.

Wave 2 (3 plans in parallel — each independent):
  04-02: PG migrations 002 (hitl.approvals) + 003 (audit.actions hypertable + REVOKE) +
         004 (budget.executions) + 005 (langgraph.checkpoints via setup script).
         Extends Phase 3 migrate.py runner. Idempotent DO blocks.
  04-03: LLM adapter (factory.py + budgeting wrapper) + Langfuse v3 callback wiring.
         Unit-testable in isolation (mock LLM responses).
  04-04: NATS AUDIT_STREAM setup + extend scripts/nats-bootstrap-streams.py + outbox table init.

Wave 3 (2 plans in parallel):
  04-05: LangGraph supervisor + 5 cluster subgraphs + 16 placeholder child nodes +
         PG checkpointer wiring. depends_on: [04-01, 04-02].
  04-06: HITL middleware (SafetyInterlock + BudgetTracker + EvidencePanel attachment) +
         EscalationSupervisor + Governor background tasks. depends_on: [04-01, 04-02, 04-04].

Wave 4 (integration, sequential):
  04-07: apps/api-gateway/ FastAPI endpoints + HITL E2E test (testcontainers PG + NATS +
         mock LLM via FakeListChatModel). depends_on: [04-05, 04-06].
  04-08: Replay tool + ROADMAP edit (4 → 5 clusters) + Langfuse smoke + docs.
         depends_on: [04-07].
```

**Total:** 8 plans (matches CONTEXT.md downstream_guidance "6-8 plans").

**Conventional commits:** scope `feat(04-NN-slug):` per atomic commit (replicate Phase 1-3).

## Open Questions for Planner (RESOLVED)

1. **`agent_role` PG role creation — Phase 4 or Phase 11?**  
   *CONTEXT.md silent.* Recommendation: Phase 4 creates role `NOLOGIN` in migration 003 (idempotent DO block). Phase 11 binds real users to role. Rationale: REVOKE on audit.actions needs the role to exist *now*.  
   **RESOLVED:** Phase 4 — `agent_role NOLOGIN` created idempotently in Plan 04-02 migration `003_create_audit_actions.sql` (DO $$ IF NOT EXISTS block).

2. **EvidencePanel.input_summary: ≤500 char truncation strategy?**  
   *CONTEXT.md silent (says "≤500 char dell'intent originale").* Options: (a) right-truncate with `...`, (b) summarize via LLM call (cost), (c) raise on >500. Recommendation: (a) truncate with explicit `_truncated: bool` field; LLM summarization Phase 11.  
   **RESOLVED:** Option (a) right-truncation — `EvidencePanel` carries `input_summary: Annotated[str, Field(max_length=500)]` + `input_truncated: bool = False` field (Plan 04-01, `packages/sft-agents/src/sft_agents/models/evidence.py`).

3. **HITL-10 (12 alarms/h per persona) — Phase 4 or Phase 10/11?**  
   *CONTEXT.md doesn't explicitly map.* Recommendation: Phase 4 ships only the DB query primitive (`SELECT count(*) FROM audit.actions WHERE decision_actor=$1 AND ts > NOW()-INTERVAL '1 hour'`). UI rate-limiting (per-persona display) lives Phase 10/11. Update REQUIREMENTS.md traceability if planner agrees.  
   **RESOLVED:** Phase 4 ships data primitive only (DB query in Plan 04-06 audit writer / governor). UI rate-limit alarm rendering deferred to Phase 10. VALIDATION.md `Manual-Only Verifications` row covers the Phase 4 deliverable boundary.

4. **`AUDIT_STREAM` subject pattern — `audit.actions.<cluster>.<agent_id>` vs `audit.actions.<cluster>.<agent_id>.<thread_id>`?**  
   *CONTEXT.md Claude's discretion locks 3-level.* Recommendation: 3-level (per agent) suffices; cluster/agent_id are bounded cardinality (~16 agents), thread_id high cardinality → would explode subject count. Confirmed: keep 3-level.  
   **RESOLVED:** 3-level subject hierarchy `audit.actions.<cluster>.<agent_id>` — confirmed in Plan 04-04 (`AUDIT_STREAM` declaration + `AuditNatsPublisher`).

5. **Outbox table — `audit.actions_outbox` or `hitl.outbox`?**  
   Recommendation: `audit.outbox` (single outbox table for ALL audit-related NATS publishes including governor.alert + approvals.new + approvals.resolved). Reduces table count and unifies retry logic. Schema: `(id UUID PK, subject TEXT, payload_json JSONB, attempts INT, last_attempt_at TIMESTAMPTZ, next_attempt_at TIMESTAMPTZ)`.  
   **RESOLVED:** Single unified `audit.outbox` — created in Plan 04-02 migration `003_create_audit_actions.sql`; retry loop owned by Plan 04-06 (`OutboxRetry` background task).

6. **Langfuse v3 — cloud (langfuse.com) or self-hosted instance?**  
   *CONTEXT.md "ships only client config + cloud-or-stub".* Recommendation: Phase 4 supports both via env `LANGFUSE_HOST` (defaults to none → stub mode = no tracing). Dev sviluppatori possono optare per Langfuse Cloud free tier (10k events/month) o stub. Phase 11 deploys self-hosted.  
   **RESOLVED:** Env-driven dual mode — `LANGFUSE_HOST` unset = stub (no tracing); set = cloud or self-hosted endpoint. Wired in Plan 04-03 LLM adapter via callback registration. Self-hosted deployment in Phase 11.

7. **`apps/api-gateway/` Nx project scaffold — exists or new?**  
   *CONTEXT.md `<scope_boundaries>` says "apps/api-gateway/ FastAPI endpoint" but Phase 1 only scaffolded `apps/agents/{ops,maintenance,knowledge,supply}/`.* Recommendation: Plan 04-07 generates `apps/api-gateway/` Nx project via `nx generate @nxlv/python:uv-project --name=api-gateway --projectType=application`.  
   **RESOLVED:** Plan 04-07 generates `apps/api-gateway/` ex-novo via `@nxlv/python:uv-project` generator (Task 1).

8. **`testcontainers-python` adoption — Phase 4 or Phase 11?**  
   *CONTEXT.md "deferred Phase 11 as bonus".* Recommendation: Phase 4 adopts in Plan 04-07 (HITL E2E test only) — fixes Phase 3 port-5432 issue as bonus. Other integration tests can keep `compose_stack` for now.  
   **RESOLVED:** Phase 4 adopts `testcontainers-python` scoped to Plan 04-07 E2E only — fixes Phase 3 `conftest.py` port-5432 known issue as bonus. Plans 04-02/05/06 unit + integration keep `compose_stack` fixture.

9. **Replay determinism scope — what is "passing"?**  
   *CONTEXT.md "best-effort".* Recommendation: Plan 04-08 defines acceptance: (a) tool outputs MATCH exactly (deterministic from audit log), (b) LLM responses may differ but final state structural shape MUST match (e.g. same `decision`, same number of `tool_calls`, same `pending_approval_id` resolution). Document explicitly in docs/docs/agents/replay.md.  
   **RESOLVED:** Best-effort with structural-match acceptance — tool outputs replayed verbatim from audit log; LLM responses may differ but structural shape (decision, tool_call count, pending_approval resolution) MUST match. Documented in Plan 04-08 `docs/architecture/agents/replay.md`.

10. **ROADMAP edit (4 → 5 clusters) — Phase 4 sign-off blocker?**  
    *CONTEXT.md D-53 mandates edit task.* Recommendation: yes — Plan 04-08 includes ROADMAP.md edit + `.planning/PROJECT.md` sync (if it mentions 4 clusters). Treat as success criterion #1 evidence.  
    **RESOLVED:** Yes — Plan 04-08 Task 3 is `type="checkpoint:human-action"` BLOCKING: edits `.planning/ROADMAP.md` Phase 4 goal text from "four cluster" to "five cluster (Operations, Maintenance, Knowledge-Curation, Knowledge-Training, Supply)" per D-53; treated as success criterion #1 evidence.

## Code Examples

### §1 — `EvidencePanel` Pydantic schema

```python
# packages/sft-agents/src/sft_agents/models/evidence.py
from __future__ import annotations
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

class ToolCall(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    name: Annotated[str, Field(min_length=1)]
    args: dict
    result: dict | None = None
    duration_ms: Annotated[int, Field(ge=0)]
    ts: datetime

    @field_validator("ts")
    @classmethod
    def _tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("ts must be timezone-aware")
        return v

class RagCitation(BaseModel):
    """Phase 5 populates; Phase 4 contract stable."""
    model_config = {"frozen": True, "extra": "forbid"}
    source_uri: str
    snippet: Annotated[str, Field(max_length=2000)]
    score: Annotated[float, Field(ge=0.0, le=1.0)]
    retrieved_at: datetime

class TokenUsage(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    input: Annotated[int, Field(ge=0)]
    output: Annotated[int, Field(ge=0)]
    total: Annotated[int, Field(ge=0)]

class EvidencePanel(BaseModel):
    """Attached to every AI decision (HITL-06)."""
    model_config = {"frozen": True, "extra": "forbid"}
    input_summary: Annotated[str, Field(max_length=500)]
    input_truncated: bool = False
    tool_calls: list[ToolCall] = Field(default_factory=list)
    rag_citations: list[RagCitation] = Field(default_factory=list)
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    model: Annotated[str, Field(pattern=r"^[a-z0-9.\-]+@[a-z0-9.\-]+$")]
    prompt_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    tokens: TokenUsage
    duration_ms: Annotated[int, Field(ge=0)]
```

### §2 — LLM factory with env-var switch

```python
# Tested pattern from §4 Technical Approach — already shown above
```

### §3 — Hybrid Router (D-54)

```python
# packages/sft-agents/src/sft_agents/policies/routing.py
import re
import yaml
from pathlib import Path
from pydantic import BaseModel
from langchain_core.language_models import BaseChatModel

class _RouteResult(BaseModel):
    cluster: Literal["ops","maintenance","knowledge-curation","knowledge-training","supply"]
    confidence: float

class HybridRouter:
    def __init__(self, config_path: Path):
        with config_path.open() as f:
            self._rules = yaml.safe_load(f)

    def match_rules(self, intent: str) -> list[str]:
        intent_lc = intent.lower()
        matches = []
        for cluster, spec in self._rules.items():
            keywords = spec.get("keywords", [])
            patterns = spec.get("patterns", [])
            if any(kw in intent_lc for kw in keywords):
                matches.append(cluster)
            elif any(re.search(p, intent_lc) for p in patterns):
                matches.append(cluster)
        return matches

    async def classify_llm(self, intent: str, llm: BaseChatModel) -> _RouteResult:
        prompt = f"Classify the operator intent into one cluster. Intent: {intent}\n\nClusters: ops, maintenance, knowledge-curation, knowledge-training, supply"
        structured = llm.with_structured_output(_RouteResult)
        return await structured.ainvoke(prompt)
```

### §4 — Safety Interlock middleware

```python
# Inserted as graph node BEFORE every ToolNode invocation
# Already shown in §11 Technical Approach
```

### §5 — EpisodicReplay (D-59)

```python
# Already shown in §6 Technical Approach
```

## State of the Art (versions verified 2026-05-18)

| Old Approach | Current Approach | Source |
|--------------|------------------|--------|
| LangGraph `interrupt_before` / `interrupt_after` (0.2.x style) | `interrupt()` function call inside node + `Command(resume=value)` | [docs.langchain.com/oss/python/langchain/human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) |
| `langgraph-supervisor` factory (auto-LLM routing) | Custom `StateGraph` + `Command(goto=...)` per hybrid routing | D-54 + [langgraph-supervisor-py GitHub](https://github.com/langchain-ai/langgraph-supervisor-py) |
| Langfuse v2 `LangfuseCallbackHandler(session_id=...)` | Langfuse v3 — pass `metadata={"langfuse_session_id": ...}` in graph config | [langfuse/discussions/8125](https://github.com/orgs/langfuse/discussions/8125) |
| vLLM tool calling without parser | vLLM `--tool-call-parser hermes` for Qwen2.5/3 | [docs.vllm.ai/features/tool_calling](https://docs.vllm.ai/en/latest/features/tool_calling/) |
| `get_openai_callback()` for tokens | `UsageMetadataCallbackHandler` + `stream_usage=True` | [forum.langchain.com tokens](https://forum.langchain.com/t/how-to-obtain-token-usage-from-langgraph/1727) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `langgraph-checkpoint-postgres` v3.1.0 stable & not deprecated by Phase 4 execution | Stack | Low — replace with v3.2+ if patch released; idempotent setup() retains compat |
| A2 | Qwen2.5-14B AWQ + vLLM Hermes parser supports all `tool_calls` produced by langchain-openai | §4 | Medium — Phase 4 integration smoke test will reveal; fallback to Ollama 7B for HITL E2E |
| A3 | `interrupt()` re-runs node from beginning on resume (true per docs but library subject to change) | §9, Pitfall §6 | Medium — verified by community sources; integration test validates |
| A4 | `agent_role` PG role can be created in Phase 4 without breaking Phase 11 governance | Open Q §1 | Low — role creation is `IF NOT EXISTS` style; Phase 11 just GRANTs login to it |
| A5 | Langfuse v3 callback API stable across minor releases | §4, Pitfall §11 | Medium — pin `langfuse>=3,<4` |
| A6 | `apps/api-gateway/` Nx project can be generated via `@nxlv/python:uv-project` | Open Q §7 | Low — Phase 1 used same generator for other apps |
| A7 | `testcontainers-python` works in GitHub Actions CI (requires Docker-in-Docker) | Pitfall §12 | Medium — verify in Plan 04-07; fallback `compose_stack` |
| A8 | Subject hierarchy `audit.actions.<cluster>.<agent_id>` does not exceed NATS subject limits (default 1024 char) | §12 | Low — max ~50 char composite |
| A9 | Replay best-effort acceptance (structural match, NOT exact text) is sufficient for CORE-10 sign-off | §8, Open Q §9 | Medium — planner must confirm or escalate |
| A10 | LLM `temperature=0, seed=42` on same hardware is "deterministic enough" for unit-test mock fallback | Pitfall §5 | Low — tests use FakeListChatModel; no real LLM in unit tests |

## Sources

### Primary (HIGH confidence)
- [LangGraph human-in-the-loop docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) — interrupt/Command semantics
- [LangGraph PostgresSaver reference](https://reference.langchain.com/python/langgraph.checkpoint.postgres/aio/AsyncPostgresSaver) — async checkpointer API
- [GRAPH_RECURSION_LIMIT docs](https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT) — recursion error handling
- [vLLM tool calling docs](https://docs.vllm.ai/en/latest/features/tool_calling/) — Hermes parser for Qwen2.5
- [Qwen2.5 function calling docs](https://qwen.readthedocs.io/en/latest/framework/function_call.html) — Hermes-style tools
- [vLLM reproducibility docs](https://docs.vllm.ai/en/latest/usage/reproducibility/) — seed + temperature limits
- [Langfuse LangChain integration](https://langfuse.com/integrations/frameworks/langchain) — v3 callback API
- [Langfuse session_id v3 discussion #8125](https://github.com/orgs/langfuse/discussions/8125) — breaking change v2→v3
- [PyPI langgraph-checkpoint-postgres 3.1.0](https://pypi.org/project/langgraph-checkpoint-postgres/) — version confirmation
- `services/ot-bridge/src/svc_ot_bridge/{timescale_writer.py,nats_publisher.py,main.py}` — Phase 3 dual-write idiom (in-repo precedent)
- `infra/migrations/timescale/001_create_sensor_events.sql` — idempotent DO block pattern (in-repo precedent)

### Secondary (MEDIUM confidence)
- [Internals of LangGraph Postgres Checkpointer — lordpatil.blog](https://blog.lordpatil.com/posts/langgraph-postgres-checkpointer/) — deep-dive table schemas, autocommit notes
- [Hierarchical Agent Teams — LangGraph tutorial](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/) — multi-cluster composition
- [Markaicode interrupt analysis](https://markaicode.com/langgraph-interrupt-pause-resume-agent/) — re-run-from-start pitfall
- [LangGraph supervisor patterns 2026 — Callsphere](https://callsphere.ai/blog/langgraph-supervisor-multi-agent-orchestration-2026)
- [PostgreSQL append-only audit — Supabase blog](https://supabase.com/blog/postgres-audit) — REVOKE/role pattern
- [Postgres audit triggers wiki](https://wiki.postgresql.org/wiki/Audit_trigger_91plus)
- [LangGraph token usage forum](https://forum.langchain.com/t/how-to-obtain-token-usage-from-langgraph/1727) — UsageMetadataCallbackHandler
- [Defeating Non-Determinism — Thinking Machines](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/)
- [LLM stability under temperature 0 — arxiv 2512.12066](https://arxiv.org/html/2512.12066v2)

### Tertiary (LOW confidence — flagged for verification)
- `langgraph-supervisor-py` GitHub repo — version stability not verified; **decision: skip, use custom routing**
- `testcontainers-python` GitHub Actions DinD — empirical CI verification needed in Plan 04-07
- Configurable PG schema for checkpointer — [forum #3274](https://forum.langchain.com/t/feature-request-configurable-postgresql-schema-for-langgraph-checkpoint-postgres-parity-with-langgraphjs/3274) — feature request open; current impl uses `public` schema, no conflict per analysis

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — locked by STACK.md + Phase 3 in-repo precedents
- Architecture (supervisor + clusters + checkpointer): **HIGH** — multiple official sources
- HITL interrupt/resume mechanics: **HIGH** — docs explicit on Command + thread_id
- LLM adapter + vLLM tool calling: **MEDIUM** — Qwen2.5-14B AWQ Hermes parser verified but production-tested only in Phase 11
- Replay determinism: **MEDIUM** — best-effort acceptance documented; LLM non-determinism real but mitigated by mock-tool replay
- Audit immutability via REVOKE: **HIGH** — standard PostgreSQL pattern + Phase 3 precedent
- Budget tracker token capture: **MEDIUM** — streaming usage_metadata pitfall documented but Phase 4 uses non-streaming
- Langfuse v3 callback: **HIGH** — v3 API stable, breaking-change-from-v2 documented
- Pitfalls (12 listed): **HIGH** — 7 of 12 are direct Phase 3 precedent replays; 5 are LangGraph-specific verified docs

**Research date:** 2026-05-18  
**Valid until:** 2026-06-18 (30 days for stable; LangGraph 0.4 → 0.5 transition risk in ~3 months)

---

## RESEARCH COMPLETE

Phase 4 research è chiusa. Le 8 decisioni CONTEXT.md (D-53..D-60) coprono il design space; la ricerca tecnica documenta 12 pitfalls concreti (7 ereditati Phase 3 + 5 LangGraph-specific verified), wave structure 8-plan allineata `downstream_guidance`, e 10 Open Questions per il planner (la maggior parte sono raccomandazioni dirette, non blocker).

Confidence aggregata: **HIGH** per il 70% delle aree (stack, architecture, HITL, audit, pitfalls Phase 3-derivati), **MEDIUM** per il 30% (vLLM Qwen2.5 tool calling parity, replay determinism, Langfuse v3 callback stability fra patch release).

Il planner può procedere con 8 atomic plan files (04-01..04-08) con depends_on graph specificato in §Dependencies & Sequencing. ROADMAP.md edit (4→5 clusters) deve essere incluso come task in Plan 04-08 — è blocking per success criterion #1.
