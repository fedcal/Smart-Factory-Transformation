# Phase 6: Agents — Operations & Production — Research

**Researched:** 2026-05-23
**Domain:** Agentic OPS cluster — ReAct loops, hybrid retrieval, scheduling heuristics, real-time anomaly scoring, textile QC reasoning, HITL routing
**Confidence:** HIGH (LangGraph + Phase 4/5 contracts + locked decisions); MEDIUM (mock LLM fixture format — Phase 4 ships partial pattern, Phase 6 extends); MEDIUM (BGE-reranker + APScheduler choices verified via official docs).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**AnomalyDetector**
- **D-AD-01** — Nodo LangGraph standard del subgraph `clusters/ops`; invocato dal supervisor con `window_minutes` (default 15). Su `__call__`, legge ultimi `window_minutes` di sample da TimescaleDB usando `query_timescale` tool, batch-scoring, ritorna `list[Anomaly]`.
- **D-AD-02** — Baseline statico YAML per-asset (`packages/sft-domain/anomaly_baselines.yaml`) con threshold/banda per `(asset_family, tag)`; override opzionale per `machine_id`. Loader Pydantic `AnomalyBaseline`.
- **D-AD-03** — Rate limit per-agent global 12 alert/h (no per-machine partition Phase 6). `RateLimiter` in `packages/sft-agents/src/sft_agents/runtime/rate_limit.py` (nuovo) con stato persistito in PG `audit.actions` (count query su sliding window). Suppress + hourly summary alert `suppressed_count`.
- **D-AD-04** — Scheduler esterno cron-like `services/agents-scheduler/` (Python APScheduler + asyncio loop) che invoca `POST /v1/agents/anomaly-detector/scan?window_minutes=15` ogni 5 min. Dockerfile + compose entry + Helm chart. Audit `triggered_by: scheduler|operator|agent`.

**QualityInspector**
- **D-QI-01** — Input dual: sim-textile `quality_event_generator.py` emette QC events su NATS `quality.events.<asset_id>` (`source: simulator`) + endpoint `POST /v1/quality/events` (`source: operator`). QualityInspector ascolta NATS subject via durable consumer JetStream `qi-consumer` e processa uniformemente.
- **D-QI-02** — 4-point grading via LLM Qwen2.5 reasoning + grading rules in prompt (ASTM tabulari + esempi + tassonomia Phase 2). JSON strutturato `{score: int [0..4], rationale_md: str, citations: [RagCitation]}`. Validator Pydantic + range check `[0..4]`.
- **D-QI-03** — HITL tier routing per defect severity, tabella `hitl_tier` per `(defect_type, severity_band)` aggiunta a `packages/sft-domain/failure_modes.yaml`:
  - `minor` → `auto-log` (audit + PG, no HITL)
  - `major` → `supervisor` (HITL tier 2)
  - `critical` → `manager + safety-interlock` (HITL tier 3 + SafetyInterlockMiddleware)
  - Severity LLM-prodotta + Pydantic `Literal['minor','major','critical']`; fallback `major` se LLM produce out-of-range.
- **D-QI-04** — `dye_lot_id` gestito da sim-textile `ProductionState` per asset (formato `DL-<asset_id>-<YYYYMMDD>-<seq>`), ruota ogni 60 min sim-time (configurabile per fault profile). Stato in-process simulator (no PG persistence Phase 6). Operator API richiede `dye_lot_id` esplicito (regex Pydantic).

**ProductionPlanner**
- **D-PP-01** — Greedy heuristic SPT/EDD in `packages/sft-domain/scheduling/`:
  - `heuristic.py` con `schedule_spt(orders, capacity) -> ScheduleDraft` + `schedule_edd(orders, capacity) -> ScheduleDraft`.
  - Vincoli: capacity per `asset_family`, due-date hard cap, setup-time da `failure_modes.yaml setup_minutes`, no-overlap per asset, dye_lot compatibility.
  - LLM Qwen2.5 invocato post-scheduling per `rationale_md` + citations SOP via `rag_search`.
- **D-PP-02** — Input YAML in `packages/sft-domain/`:
  - `orders.yaml` (~20 ordini Mantis sintetici)
  - `asset_capacity.yaml` (derivato da `packages/sft-assets` 30 asset)
  - Loader Pydantic `OrderSpec` + `AssetCapacity`. CI validator verifica referenze.
- **D-PP-03** — Output Pydantic `ScheduleDraft` (frozen + extra=forbid):
  ```python
  class ScheduleDraftItem: order_id, asset_id, start_at, end_at, dye_lot_id, sequence
  class ScheduleDraft: schedule_id (UUID4), strategy ('spt'|'edd'),
                       horizon_start, horizon_end, items, rationale_md,
                       citations: list[RagCitation], created_at
  ```
  Draft serializzato in `audit.actions` payload + `interrupt()` HITL Phase 4. Supervisor approve → audit log `decision: approved` + read-only state. No publish NATS Phase 6.
- **D-PP-04** — Trigger on-demand via `POST /v1/agents/production-planner/plan` body `{horizon_days, strategy: 'spt'|'edd'}`.

**OperatorAssistant**
- **D-OA-01** — `langgraph.prebuilt.create_react_agent(model, tools)` con `LLM_BACKEND` factory Phase 4 (default Qwen2.5-7B Ollama). `recursion_limit=5` via Phase 4 `safe_invoke`; eccedenza → HITL escalation D-53. Audit Langfuse callback. Stato include `messages`, `tool_results`, `iteration_count`, `evidence_citations`.
- **D-OA-02** — Toolbelt completo:
  1. `rag_search` (Phase 5, ACL via `user_roles`)
  2. `traverse_graph` (Phase 5)
  3. `query_timescale` (Phase 3)
  4. `escalate_to_supervisor` (NEW, in `packages/sft-agents/src/sft_agents/tools/hitl.py`)
  5. `log_event` (NEW, in `packages/sft-agents/src/sft_agents/tools/audit.py`)
  Audit ogni tool_call in Langfuse span + `audit.actions` se action-bearing.
- **D-OA-03** — Lingua risposta = lingua query (detect `langdetect` con `DetectorFactory.seed=42`); `rag_search` con `lang=None` (cross-lingual via BGE-M3 Phase 5 D-64); citations preserve source lang.
- **D-OA-04** — `escalate_to_supervisor` wrappa `interrupt()` Phase 4 con payload strutturato + audit dual-write. Citation validator post-LLM: se `rag_search` invocato MA `response_md` senza `[N]` reference OR `citations` vuoto → `MissingCitationError` → replan con prompt augmentation (max 1 retry) → warning logged + `citations_missing: true` in audit.

**Cross-cutting**
- **D-X-01** — Test E2E: mock LLM (`LLM_BACKEND=mock` Phase 4 factory) + record/replay JSONL in `tests/fixtures/llm_responses/<agent>/<scenario>.jsonl`; scenario YAML in `tests/fixtures/ops_scenarios/<agent>/<scenario>.yaml`. Marker `@pytest.mark.e2e` + `@pytest.mark.integration`. Opt-in real LLM: `@pytest.mark.real-llm`. Knowledge layer (Qdrant + Neo4j + NATS + PG) via testcontainers fixture (estensione Phase 5 `tests/conftest.py`).

### Claude's Discretion

- Naming convention agent slug per file (`apps/agents/ops/operator-assistant/` kebab dir, snake_case Python package `ops_operator_assistant`).
- Pydantic model file organization: ogni agent ha `src/<pkg>/models.py`; types cross-agent (`Anomaly`, `QualityEvent`, `ScheduleDraft`) in `packages/sft-domain/src/sft_domain/ops/`.
- Logging structlog: `agent.<slug>`, `event.<type>`, `decision.<action>`, snake_case fields.
- Test naming: `test_<concern>.py` (unit) vs `test_<scenario>_e2e.py` (E2E).
- OPS cluster subgraph routing: field `target_agent` nello state subgraph (popolato da supervisor LLM via HybridRouter Phase 4); fallback su `operator-assistant` quando ambiguo.

### Deferred Ideas (OUT OF SCOPE)

- AnomalyDetector auto-tuning baseline statistical → Phase 11
- AnomalyDetector per-machine + per-anomaly-type rate limiting → Phase 11
- ProductionPlanner OR-tools CP-SAT → Phase 9
- ProductionPlanner auto-publish NATS schedule → Phase 9
- ProductionPlanner cron daily / event-driven replan → Phase 11/10
- QualityInspector hybrid deterministic+LLM grading → Phase 11
- QualityInspector PG `production.dye_lots` schema → Phase 9
- QualityInspector publish `quality.alerts.*` cross-cluster → Phase 7
- OperatorAssistant `output_lang` API parameter → Phase 10
- Real-LLM golden path E2E (`@pytest.mark.real-llm`) → Phase 11
- Long-running NATS consumer per AnomalyDetector → Phase 11
- OperatorAssistant proactive engagement → Phase 10

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPS-01 | `OperatorAssistant` — guida runtime, risponde Q contestuali, suggerisce next-best-action | §1 `create_react_agent`, §2 mock LLM, §7 citation validator, §12 pitfalls |
| OPS-02 | `ProductionPlanner` — ottimizza scheduling ordini su linee/macchine con vincoli capacità | §5 SPT/EDD heuristic, §3 HITL routing for ScheduleDraft approval |
| OPS-03 | `QualityInspector` — valuta segnali QC, applica tassonomia difetti tessili + 4-point grading | §6 4-point ASTM, §3 NATS durable consumer, §10 sim-textile extension |
| OPS-04 | `AnomalyDetector` — anomalie real-time su streaming sensori con baseline per-machine | §4 APScheduler trigger, §8 rate limiter, §9 OPS subgraph routing |
| OPS-05 | Ogni agente OPS dichiara: tool usati, fonti dati, livello HITL, KPI impattati | Documented in each agent's prompt header + EvidencePanel (HITL-06) |
| OPS-06 | Test end-to-end per ciascun agente OPS su scenario simulato con verità nota | §11 testcontainers + §2 mock LLM + scenario YAML matrix |

</phase_requirements>

## Summary

Phase 6 popola la business logic dei 4 agenti `ops` sopra il runtime Phase 4 (LangGraph supervisor + HITL + LLM adapter + AuditWriter), il knowledge layer Phase 5 (Qdrant + Neo4j + `rag_search` + `traverse_graph` + ACL) e il simulator Phase 3 (NATS + TimescaleDB + `query_timescale`). Le decisioni più impegnative — algoritmo scheduling, taxonomy difetti, HITL routing, formato Anomaly baseline, scheduler infrastruttura, mock LLM per CI — sono già lockate in `06-CONTEXT.md`. La ricerca qui sotto verifica le 12 aree non-locked che il planner deve trasformare in task atomici: contratti API esatti di `create_react_agent` per LangGraph v1, formato JSONL mock LLM compatibile con il `LLM_BACKEND` factory di Phase 4 (oggi mancante — `factory.py` accetta solo `ollama|vllm`), pattern durable consumer JetStream, struttura APScheduler + Docker, espressione greedy heuristic textile, prompt 4-point ASTM, validator citazioni post-LLM, rate limiter PG-based, routing intra-cluster ops, estensione sim-textile, fixture testcontainers, pitfalls LangGraph 2025.

**Primary recommendation:** Phase 6 deve aggiungere `LLM_BACKEND=mock` come terza branch del factory esistente (D-X-01 lo dà per scontato ma il codice non lo supporta), espandere `models/enums.py` con `ActionType.QUALITY_VERDICT|SCHEDULE_DRAFT|ANOMALY_ALERT`, e introdurre un nuovo modulo `packages/sft-agents/src/sft_agents/runtime/rate_limit.py` PG-backed sliding window 12/h. La compilazione del subgraph ops sostituisce i 4 placeholder Phase 4 (`build_cluster_subgraph` accetta callables, non builders separati) con `__call__(state) -> dict` async nodes che incapsulano i 4 agenti.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ReAct loop (OperatorAssistant) | API/Backend (LangGraph node) | — | Sta nel orchestrator process; UI è Phase 10 |
| Greedy SPT/EDD scheduling | Domain library (`packages/sft-domain/scheduling/`) | API/Backend (LangGraph node calls it) | Pure-function algorithm; testable in isolation; agent invokes |
| 4-point LLM grading | API/Backend (LangGraph node + LLM call) | — | Agent business logic; prompt is the algorithm |
| Anomaly baseline check | Domain library (`packages/sft-domain/anomaly/`) | API/Backend (LangGraph node) | Pure baseline comparator + agent orchestrates |
| Rate limiter (12/h) | Runtime middleware (`packages/sft-agents/runtime/rate_limit.py`) | Database (PG `audit.actions` query) | PG sliding window count survives restart |
| Cron scheduler (5min trigger) | Service container (`services/agents-scheduler/`) | API/Backend (HTTP POST) | Lifecycle ≠ agent process; APScheduler in own container |
| NATS QC consumer | API/Backend (orchestrator subprocess) | Event bus (NATS JetStream durable) | Long-lived consumer task within orchestrator |
| Citation validator | API/Backend (post-LLM step in OperatorAssistant) | — | Runs in-process before audit write |
| HITL severity routing | Domain config (`failure_modes.yaml hitl_tier` mapping) | Runtime (Phase 4 `interrupt()`) | Config-driven mapping table |
| sim-textile QC event generator | Simulator (`simulators/sim-textile/`) | Event bus (NATS publish) | Extension of existing emitter process |
| Operator chat endpoint | API/Backend (`apps/api-gateway/`) | — | New REST route forwards to orchestrator |
| HITL escalate tool | Runtime middleware (`packages/sft-agents/tools/hitl.py`) | API/Backend (interrupt invoker) | New LangChain BaseTool wrapping interrupt() |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langgraph` | 0.4+ (≥0.4.0) | Agent runtime — already locked Phase 4 | `create_react_agent` lives in `langgraph.prebuilt`; checkpoints + `interrupt()` already wired [CITED: docs.langchain.com] |
| `langchain-core` | 0.3+ | `BaseTool`, `ChatModel`, `BaseMessage` (already locked Phase 4) | Tool ABC for `rag_search` + new `escalate_to_supervisor`, `log_event` [VERIFIED: Phase 4 pyproject] |
| `langchain-ollama` | 0.3+ | Dev LLM (Qwen2.5-7B Q4_K_M) — locked Phase 4 | Backend for mock-free integration smoke tests [VERIFIED: factory.py] |
| `langchain-openai` | 0.3+ | vLLM (Qwen2.5-14B AWQ) — locked Phase 4 | Production backend; OpenAI-compatible API [VERIFIED: factory.py] |
| `langfuse` | v3+ | Callback already wired Phase 4 | Span hierarchy supervisor → ops cluster → agent → LLM/tool [CITED: langfuse.com/integrations] |
| `pydantic` | 2.7+ | Validation — locked stack | All models frozen + extra=forbid [VERIFIED: existing models] |
| `nats-py` | ≥2.6 | JetStream client — locked Phase 3 | Used by QC consumer for `quality.events.<asset_id>` [CITED: github.com/nats-io/nats.py] |
| `asyncpg` | ≥0.29 | Async PG driver — locked Phase 3 | Used by rate limiter sliding-window query + audit [VERIFIED: existing code] |
| `httpx` | ≥0.28 | Async HTTP — locked Phase 4 | scheduler → api-gateway POST + FastAPI test client [VERIFIED: existing test deps] |
| `langdetect` | ≥1.0.9 | Language detection for D-OA-03 | Deterministic with `DetectorFactory.seed=42`; MIT license; pure-Python no native deps [CITED: pypi.org/project/langdetect] |
| `APScheduler` | 3.10.4+ | Cron scheduler in `services/agents-scheduler/` | `AsyncIOScheduler` integrates with asyncio FastAPI app [CITED: apscheduler.readthedocs.io] |
| `typer` | 0.12+ | CLI scaffolding for ops services (consistent with Phase 5 `services/knowledge-ingest`) | Same pattern, low-friction [VERIFIED: Phase 5 deps] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dateutil` | ≥2.9 | RFC datetime parsing in schedule horizons | Already transitively present |
| `dataclasses-json` | (avoid) | — | Don't use — Pydantic v2 covers serialization |
| `pyyaml` | ≥6.0 | YAML loading for `orders.yaml`, `asset_capacity.yaml`, `anomaly_baselines.yaml`, `failure_modes.yaml` (extension) | `yaml.safe_load` only (Phase 1+ convention) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `langgraph.prebuilt.create_react_agent` | Custom plan-then-execute StateGraph | Custom is more code, less audit-friendly; user already locked `create_react_agent` (D-OA-01) |
| APScheduler `AsyncIOScheduler` | Linux cron + container exec | cron requires host integration; APScheduler stays in-container, testable, simple Helm shipping |
| OR-tools CP-SAT | Greedy SPT/EDD | OR-tools = 30+MB binary + GLPK deps; Phase 6 PoC doesn't need optimality (locked D-PP-01) |
| Custom HTTP scheduler | `httpx.AsyncClient` to POST `/v1/agents/anomaly-detector/scan` | httpx already in stack (api-gateway tests use it); zero added deps |
| `langchain-community.ChatFake` | Custom mock factory branch | ChatFake doesn't support tool_call schema replay; custom JSONL replay is more flexible |

**Installation deltas (new in Phase 6):**
```bash
# packages/sft-agents — extend pyproject.toml
uv add langdetect>=1.0.9

# services/agents-scheduler (NEW)
uv add APScheduler>=3.10.4 httpx>=0.28 structlog typer fastapi
uv add sft-agents  # workspace ref for audit dual-write helper

# apps/agents/ops/*/ — each gets sft-knowledge, sft-tools, sft-domain workspace refs
# (already exist as workspace packages)
```

**Version verification:**
- `langgraph` 0.4+ confirmed in `STACK.md`; `create_react_agent` deprecated in LangGraph v1 (Oct 2025) in favor of `create_agent` per [reference.langchain.com](https://reference.langchain.com/python/langgraph.prebuilt/chat_agent_executor/create_react_agent), but **D-OA-01 locks `create_react_agent`** — accept deprecation warning; Phase 11 may migrate.
- `APScheduler` 3.10.4 is the current stable release per [apscheduler.readthedocs.io](https://apscheduler.readthedocs.io/en/3.x/userguide.html) [ASSUMED — registry not verified in research session].
- `langdetect` 1.0.9 last release 2021, still maintained, MIT license [ASSUMED].

## Package Legitimacy Audit

Phase 6 adds **2 new packages** (`langdetect`, `APScheduler`); rest are workspace refs or already-locked Phase 1-5 deps. slopcheck was not executed in this session — both new packages must therefore be tagged `[ASSUMED]` and the planner SHALL insert a `checkpoint:human-verify` task before install.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `langdetect` | PyPI | 14 yrs | ~5M/month | github.com/Mimino666/langdetect | n/a | [ASSUMED] — planner verifies + tags `[ASSUMED]` install task |
| `APScheduler` | PyPI | 14 yrs | ~30M/month | github.com/agronholm/apscheduler | n/a | [ASSUMED] — planner verifies + tags `[ASSUMED]` install task |

**Packages removed due to slopcheck [SLOP] verdict:** none (no checks run).
**Packages flagged as suspicious [SUS]:** none.

*Both packages are well-known mainstream — manual verification by the executor pre-install is sufficient; the gate documented above prevents accidental slop injection while staying KISS.*

## Architecture Patterns

### System Architecture Diagram

```
                                ┌─────────────────────────────────────┐
                                │       Supervisor StateGraph         │
                                │   (Phase 4 D-53 + HybridRouter)     │
                                └──────────────┬──────────────────────┘
                                               │  route → cluster="ops"
                                               ▼
                              ┌─────────────────────────────────────┐
                              │       OPS Cluster Subgraph          │
                              │  (Phase 6 fills 4 placeholders)     │
                              │                                     │
                              │   START → target_agent_router →     │
                              │                                     │
                              │   ┌──OA───┐ ┌──PP───┐ ┌──QI───┐    │
                              │   │ReAct  │ │Greedy │ │LLM 4pt│    │
                              │   │loop≤5 │ │SPT/EDD│ │grading│    │
                              │   └───┬───┘ └───┬───┘ └───┬───┘    │
                              │       │         │         │         │
                              │   ┌───┴─────────┴─────────┴───┐    │
                              │   │ HITL gate (Phase 4 D-55)  │    │
                              │   └───────────┬───────────────┘    │
                              │               ▼ END                 │
                              │   ┌──AD───┐                         │
                              │   │baseline                         │
                              │   │+rate  │                         │
                              │   │limit  │                         │
                              │   └───────┘                         │
                              └─────────────────────────────────────┘

Triggers (external):
  ┌────────────────────────┐         ┌────────────────────────┐
  │ agents-scheduler       │ ────→   │  POST /agents/         │
  │ APScheduler 5min cron  │  HTTP   │  anomaly-detector/scan │
  └────────────────────────┘         └───────────┬────────────┘
                                                 │
                                                 ▼
                                         orchestrator invokes AD node

  ┌────────────────────────┐         ┌────────────────────────┐
  │ sim-textile            │ ────→   │  NATS quality.events.* │
  │ quality_event_generator│  pub    └───────────┬────────────┘
  └────────────────────────┘                     │
  ┌────────────────────────┐                     │
  │ POST /quality/events   │ ────→   ────────────┘
  │ (operator)             │  pub                │
  └────────────────────────┘                     ▼
                                       qi-consumer (durable JetStream)
                                       → QualityInspector node

Tools used (existing Phase 3/4/5):
  rag_search ───→ Qdrant + BGE-reranker + ACL filter
  traverse_graph ─→ Neo4j Machine → Part → FailureMode → SOP
  query_timescale ─→ TimescaleDB sensor_events (used by AD + OA data Qs)

New tools (Phase 6):
  escalate_to_supervisor ──→ wraps Phase 4 interrupt() with structured payload
  log_event ─────────────→ AuditWriter.write(decision=LOGGED), no HITL
```

### Recommended Project Structure

```
apps/agents/ops/
├── operator-assistant/src/ops_operator_assistant/
│   ├── __init__.py                # exports build_agent(state) callable
│   ├── agent.py                   # create_react_agent(model, tools) + recursion_limit=5
│   ├── prompts.py                 # system prompt IT/EN with citation rules + tool inventory
│   ├── validators.py              # citation validator (post-LLM replan loop)
│   ├── lang_detect.py             # langdetect wrapper, seed=42
│   └── models.py                  # OperatorChatRequest, OperatorChatResponse
├── production-planner/src/ops_production_planner/
│   ├── agent.py                   # __call__(state) → ScheduleDraft + LLM rationale
│   ├── prompts.py
│   └── models.py                  # OperatorPlannerRequest, PlanResponse
├── quality-inspector/src/ops_quality_inspector/
│   ├── agent.py                   # consumer/handler unified for nats + api source
│   ├── nats_consumer.py           # JetStream durable consumer (qi-consumer)
│   ├── grader.py                  # LLM 4-point grading + Pydantic validator
│   ├── prompts.py                 # ASTM rules + taxonomy + examples
│   └── models.py                  # QualityEvent, QualityVerdict
└── anomaly-detector/src/ops_anomaly_detector/
    ├── agent.py                   # __call__(state) → list[Anomaly]
    ├── baseline.py                # compare sample vs band; return outliers
    └── models.py                  # Anomaly, AnomalyScanRequest

packages/sft-domain/src/sft_domain/
├── ops/
│   ├── __init__.py
│   ├── anomaly.py                 # Anomaly Pydantic + baseline loader
│   ├── quality.py                 # QualityEvent, QualityVerdict, DefectType enum, Severity
│   └── schedule.py                # ScheduleDraft, ScheduleDraftItem, OrderSpec, AssetCapacity
├── scheduling/
│   ├── __init__.py
│   ├── heuristic.py               # schedule_spt(orders, capacity), schedule_edd(...)
│   └── constraints.py             # dye_lot_compatibility, setup_time apply
├── orders.yaml                    # NEW — 20 synthetic Mantis orders
├── asset_capacity.yaml            # NEW — derived from sft-assets 30 asset
├── anomaly_baselines.yaml         # NEW — per-(asset_family,tag) thresholds
└── failure_modes.yaml             # EXTENDED — adds hitl_tier, setup_minutes, severity

packages/sft-agents/src/sft_agents/
├── tools/
│   ├── hitl.py                    # NEW — escalate_to_supervisor BaseTool
│   └── audit.py                   # NEW — log_event BaseTool
├── runtime/
│   └── rate_limit.py              # NEW — PG sliding window 12/h
└── llm/
    └── factory.py                 # EXTENDED — add LLM_BACKEND=mock branch

services/agents-scheduler/         # NEW (CLI + APScheduler service container)
├── pyproject.toml
├── project.json
├── Dockerfile
└── src/svc_agents_scheduler/
    ├── __main__.py                # entrypoint, lifespan, structlog config
    ├── scheduler.py               # AsyncIOScheduler.add_job(cron, trigger_anomaly_scan)
    └── client.py                  # httpx wrapper for POST /v1/agents/.../scan

simulators/sim-textile/src/sim_textile/
├── quality_event_generator.py     # NEW — stochastic QC event emitter, NATS publish
└── production_state.py            # NEW — ProductionState model + dye_lot_id rotation

apps/api-gateway/src/svc_api_gateway/
└── routers/
    ├── quality.py                 # NEW — POST /v1/quality/events
    ├── ops_agents.py              # NEW — POST /v1/agents/{slug}/scan|plan|chat
    └── ...                         # existing /v1/approvals, /v1/threads

tests/
├── fixtures/
│   ├── ops_scenarios/
│   │   ├── operator-assistant/{happy,degraded,failure}.yaml
│   │   ├── production-planner/{happy,degraded,failure}.yaml
│   │   ├── quality-inspector/{happy,degraded,failure}.yaml
│   │   └── anomaly-detector/{happy,degraded,failure}.yaml
│   └── llm_responses/
│       ├── operator-assistant/{happy,degraded,failure}.jsonl
│       ├── production-planner/{happy,degraded,failure}.jsonl
│       ├── quality-inspector/{happy,degraded,failure}.jsonl
│       └── anomaly-detector/{happy,degraded,failure}.jsonl
└── e2e/ops/
    ├── test_operator_assistant_scenarios.py
    ├── test_production_planner_scenarios.py
    ├── test_quality_inspector_scenarios.py
    └── test_anomaly_detector_scenarios.py
```

### Pattern 1: `create_react_agent` with pluggable model + tools list

**What:** LangGraph prebuilt factory that wires a ReAct loop (think → tool_call → observe → think → answer) with built-in `ToolNode` and message reducer. Returns a compiled `StateGraph` (or `Pregel` runnable in v1).

**When to use:** Conversational tool-using agent (OperatorAssistant). NOT for ProductionPlanner (deterministic algo first, LLM only for rationale), NOT for AnomalyDetector (deterministic baseline, no tool reasoning).

**Example (D-OA-01 locked):**
```python
# Source: https://reference.langchain.com/python/langgraph.prebuilt/chat_agent_executor/create_react_agent
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sft_agents.llm import build_chat_model
from sft_knowledge.tools import RagSearchTool, TraverseGraphTool
from sft_tools.timescale.query import QueryTimescaleTool
from sft_agents.tools.hitl import EscalateToSupervisorTool
from sft_agents.tools.audit import LogEventTool

model = build_chat_model()  # Phase 4 factory

tools = [
    RagSearchTool(pipeline=rag_pipeline),       # Phase 5
    TraverseGraphTool(graph_client=neo4j),      # Phase 5
    QueryTimescaleTool(),                       # Phase 3 — reads $TIMESCALE_DSN env
    EscalateToSupervisorTool(audit_writer=aw, queue_writer=qw, nats=nc),  # NEW
    LogEventTool(audit_writer=aw),                                          # NEW
]

# checkpointer is the AsyncPostgresSaver Phase 4 wired
checkpointer = AsyncPostgresSaver.from_conn_string(os.environ["LANGGRAPH_PG_DSN"])

react_runnable = create_react_agent(
    model=model,
    tools=tools,
    checkpointer=checkpointer,
    prompt=SYSTEM_PROMPT_BILINGUAL,  # str or SystemMessage; Phase 6 ships IT+EN system msg
    # state_schema=AgentState — accepts custom TypedDict; we use the prebuilt MessagesState
    # then merge results into ops AgentState at the cluster boundary.
)

# Invocation via safe_invoke (Phase 4) — enforces recursion_limit + escalates to HITL on overflow
result = await safe_invoke(
    react_runnable,
    {"messages": [HumanMessage(content=query)]},
    config={
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 5,                         # D-OA-01: max 5 iterations
        "callbacks": [langfuse_callback],
    },
)
```

**Key API surface (from [reference.langchain.com](https://reference.langchain.com/python/langgraph.prebuilt/chat_agent_executor/create_react_agent)):**
- `model`: `BaseChatModel | str | Callable[[state, runtime], BaseChatModel]` — dynamic model selection per state allowed
- `tools`: `list[BaseTool | Callable] | ToolNode`
- `checkpointer`: optional `BaseCheckpointSaver` (PG saver Phase 4 wired)
- `prompt`: `str | SystemMessage | Callable` — system prompt
- `state_schema`: `TypedDict` — customize state shape (default `MessagesState`)
- `interrupt_before` / `interrupt_after`: list of node names where to interrupt (use for HITL on specific tool nodes)
- Returns a compiled runnable; invoke with `.ainvoke` / `.astream`

**Tool result format (LangGraph v0.4+):** `ToolNode` automatically appends `ToolMessage` entries with `name=<tool_name>, content=<result>, tool_call_id=<id>` to `state.messages`. For our purposes, RagCitation lists serialize via `model_dump_json()` and the LLM reads them as JSON strings — they are intercepted by the citation validator before the final response is emitted.

**Injecting `user_roles` for ACL on `rag_search`:** Two strategies — (a) closure over the BaseTool instance at construction time (`RagSearchTool(pipeline, user_roles=state['user_roles'])` — but tools are instantiated once at startup, so this requires recreating tools per session, which is acceptable for Phase 6 since orchestrator threads are short-lived), OR (b) pass `user_roles` as a tool argument via the LLM (the model is prompted to always include it from `state`). **Decision:** option (a) — re-instantiate tools per request (cost negligible, simpler), and the request handler injects `user_roles` from JWT claims when Phase 11 auth lands. Until then, request body carries `user_roles: list[str]` directly.

### Pattern 2: Mock LLM backend (record/replay JSONL) for CI determinism

**What:** A third branch of `build_chat_model()` that reads a fixture file `tests/fixtures/llm_responses/<agent>/<scenario>.jsonl` and replays canned `AIMessage` / `ToolCall` responses in sequence keyed by `prompt_hash` (sha256 of incoming messages).

**Why needed:** D-X-01 locks the mock LLM but Phase 4 `factory.py` only knows `ollama|vllm`. Phase 6 must extend it.

**JSONL fixture format:**
```jsonl
{"prompt_hash":"<sha256-64chars>","response":{"content":"","tool_calls":[{"id":"call_1","name":"rag_search","args":{"query":"rottura filo ordito","user_roles":["technician"]}}],"usage_metadata":{"input_tokens":120,"output_tokens":15,"total_tokens":135}}}
{"prompt_hash":"<sha256>","response":{"content":"In base al SOP [1]…","usage_metadata":{"input_tokens":250,"output_tokens":80,"total_tokens":330}}}
```

**Implementation sketch (NEW `packages/sft-agents/src/sft_agents/llm/mock.py`):**
```python
import hashlib, json, os, pathlib
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.language_models.chat_models import BaseChatModel

class MockReplayChatModel(BaseChatModel):
    """LLM_BACKEND=mock — replay JSONL fixture keyed on prompt_hash."""
    fixture_path: pathlib.Path
    _entries: list[dict]
    _index: int = 0

    def __init__(self, fixture_path: str | pathlib.Path):
        super().__init__()
        self.fixture_path = pathlib.Path(fixture_path)
        with self.fixture_path.open() as fh:
            self._entries = [json.loads(line) for line in fh if line.strip()]

    def _prompt_hash(self, messages: list[BaseMessage]) -> str:
        body = "\n".join(f"{m.type}:{m.content}" for m in messages)
        return hashlib.sha256(body.encode()).hexdigest()

    async def _agenerate(self, messages, stop=None, run_manager=None, **kw):
        # Strict mode: by prompt_hash; fallback ordered if no hash match (smoke test)
        ph = self._prompt_hash(messages)
        entry = next((e for e in self._entries if e["prompt_hash"] == ph), None)
        if entry is None:
            entry = self._entries[self._index]
            self._index += 1
        resp = entry["response"]
        msg = AIMessage(
            content=resp.get("content", ""),
            tool_calls=resp.get("tool_calls", []),
            usage_metadata=resp.get("usage_metadata"),
        )
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _generate(self, *a, **k):
        raise NotImplementedError("MockReplayChatModel is async-only")

    @property
    def _llm_type(self) -> str:
        return "mock-replay"
```

**Extend factory.py:**
```python
if resolved == "mock":
    fixture = os.environ["MOCK_LLM_FIXTURE"]  # planner asserts in test fixture
    return MockReplayChatModel(fixture_path=fixture)
```

**Tool-call replay nuance:** The fixture must alternate `tool_calls` entries with the subsequent natural-language entry. For OperatorAssistant the typical sequence is: query → `[tool_call rag_search]` → tool result (deterministic from Phase 5 mock collection) → final response with citations. Each LLM "round" consumes exactly one fixture entry.

**Determinism guarantees:**
- Set `LLM_BACKEND=mock`, `MOCK_LLM_FIXTURE=<path>` env vars in test
- `langdetect.DetectorFactory.seed = 42` ensures language detection is deterministic
- `random.seed(42)` + `np.random.seed(42)` in any scenario that needs stochastic baseline draws

### Pattern 3: NATS JetStream durable consumer for quality.events

**What:** `qi-consumer` durable consumer on the `QUALITY_STREAM` stream (NEW; analogous to Phase 3 `SENSOR_STREAM` and Phase 4 `AUDIT_STREAM`). `AckExplicit` + idempotency on `event_id` ensures the QualityInspector processes each QC event exactly once.

**Stream + consumer setup (extend `scripts/nats-bootstrap-streams.py`):**
```python
# Source: docs.nats.io/nats-concepts/jetstream/consumers
await js.add_stream(StreamConfig(
    name="QUALITY_STREAM",
    subjects=["quality.events.>"],
    retention=RetentionPolicy.LIMITS,
    max_age=7 * 24 * 3600,            # 7 days retention
    storage=StorageType.FILE,
))
await js.add_consumer("QUALITY_STREAM", ConsumerConfig(
    durable_name="qi-consumer",
    ack_policy=AckPolicy.EXPLICIT,
    max_deliver=5,                     # bounded redelivery
    ack_wait=30,                       # 30s ack wait
    deliver_subject=None,              # pull-based
    filter_subject="quality.events.>",
))
```

**Python consumer task (in `apps/agents/ops/quality-inspector/src/.../nats_consumer.py`):**
```python
# Source: github.com/nats-io/nats.py + docs.nats.io
import nats
from nats.js.api import ConsumerConfig

async def run_consumer(js, qi_handler):
    psub = await js.pull_subscribe(
        subject="quality.events.>",
        durable="qi-consumer",
        stream="QUALITY_STREAM",
    )
    while True:
        try:
            msgs = await psub.fetch(batch=10, timeout=5)
        except nats.errors.TimeoutError:
            continue
        for msg in msgs:
            try:
                event = QualityEvent.model_validate_json(msg.data)
                # Idempotency: query audit.actions for action_id == event.event_id
                if await already_processed(event.event_id):
                    await msg.ack()
                    continue
                await qi_handler(event)
                await msg.ack()
            except ValidationError:
                # Poison message — terminate (no redelivery on permanent failure)
                await msg.term()
            except Exception:
                # Transient error — let redelivery retry (no ack)
                await msg.nak()
```

**Integration with LangGraph node:** The consumer task lives in the orchestrator process (or a sidecar `services/quality-inspector-consumer/`). When it dequeues a `QualityEvent`, it invokes the QualityInspector subgraph via `graph.ainvoke({...event...}, config={"configurable": {"thread_id": f"qi.{event.event_id}"}})`. The graph runs to completion (including HITL via `interrupt()` if severity demands), then the consumer acks.

### Pattern 4: APScheduler in a dedicated container

**What:** `services/agents-scheduler/` is a single-process container running `AsyncIOScheduler` that fires a cron job every 5 minutes calling `httpx.AsyncClient().post(...)` against the api-gateway.

**Why a separate container:** Lifecycle separation (scheduler restart ≠ orchestrator restart) + horizontal-scaling clarity (we never want N orchestrator replicas all firing the same cron — multi-worker gotcha documented [here](https://browniantech.com/blog/post/Better-FastAPI-Background-Jobs)).

**Skeleton (`services/agents-scheduler/src/svc_agents_scheduler/__main__.py`):**
```python
import asyncio, os, signal, structlog, httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = structlog.get_logger("agents-scheduler")

async def trigger_anomaly_scan(gateway_url: str, window_minutes: int):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{gateway_url}/v1/agents/anomaly-detector/scan",
            json={"window_minutes": window_minutes, "triggered_by": "scheduler"},
        )
        log.info("scheduler_invoked", status=r.status_code, window_minutes=window_minutes)

async def main():
    gw = os.environ["API_GATEWAY_URL"]
    window = int(os.environ.get("ANOMALY_WINDOW_MINUTES", "15"))
    cron = os.environ.get("ANOMALY_CRON", "*/5 * * * *")

    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(
        trigger_anomaly_scan, CronTrigger.from_crontab(cron),
        kwargs={"gateway_url": gw, "window_minutes": window},
        id="anomaly-detector-scan", coalesce=True, max_instances=1,
    )
    sched.start()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, stop.set)
    log.info("scheduler_started", cron=cron, window_minutes=window)
    await stop.wait()
    sched.shutdown(wait=True)

if __name__ == "__main__":
    asyncio.run(main())
```

**Dockerfile:** multi-stage `python:3.12-slim` base + `uv pip install -e .` consistent with other services.
**Compose entry:** `agents-scheduler` service `depends_on: api-gateway` (no health probe required since scheduler retries indefinitely on transient HTTP failure).
**Single instance constraint:** `max_instances=1` + `coalesce=True` in APScheduler config prevents overlap; Helm chart pins `replicas: 1`.

### Pattern 5: Greedy SPT/EDD heuristic with textile constraints

**What:** Pure-function algorithm that orders pending orders by `processing_time` (SPT) or `due_date` (EDD), then iteratively assigns each order to the first available slot on an eligible asset given `(capacity, setup_time, dye_lot compatibility, no-overlap)` constraints.

**Pseudocode (Source: usersolutions.com glossary + Phase 6 textile constraints):**
```python
# packages/sft-domain/scheduling/heuristic.py

def schedule_spt(orders: list[OrderSpec], capacity: dict[str, AssetCapacity],
                 failure_modes: dict[str, FailureMode],
                 horizon_start: datetime, horizon_end: datetime) -> ScheduleDraft:
    # Sort by processing_time asc — SPT minimizes mean flow time
    pending = sorted(orders, key=lambda o: o.processing_minutes)
    timelines: dict[str, list[ScheduleDraftItem]] = {a: [] for a in capacity}
    items: list[ScheduleDraftItem] = []
    seq = 0

    for order in pending:
        # Eligible assets: capacity.asset_family supports order.required_family
        eligible = [a for a, cap in capacity.items()
                    if cap.asset_family in order.compatible_families]
        # Pick asset with earliest available slot
        candidates = [(a, _earliest_slot(timelines[a], order, capacity[a],
                                         failure_modes, horizon_start)) for a in eligible]
        asset_id, slot_start = min(candidates, key=lambda x: x[1])
        slot_end = slot_start + timedelta(minutes=order.processing_minutes)
        if slot_end > horizon_end:
            continue  # Cannot fit — defer order; surfaces in rationale_md
        if slot_end > order.due_at:
            order_overdue = True  # surfaces in audit.payload + rationale
        item = ScheduleDraftItem(
            order_id=order.order_id, asset_id=asset_id,
            start_at=slot_start, end_at=slot_end,
            dye_lot_id=order.dye_lot_id, sequence=seq,
        )
        timelines[asset_id].append(item)
        items.append(item)
        seq += 1

    return ScheduleDraft(
        schedule_id=uuid4(), strategy="spt",
        horizon_start=horizon_start, horizon_end=horizon_end,
        items=items, rationale_md="",  # LLM populates later
        citations=[], created_at=datetime.now(UTC),
    )

def _earliest_slot(timeline, order, cap, failure_modes, horizon_start) -> datetime:
    """Find first gap respecting setup_minutes + dye_lot compatibility."""
    candidates = [horizon_start]
    for prev in timeline:
        setup = failure_modes.get(prev.asset_id, FailureMode(setup_minutes=0)).setup_minutes
        # Dye-lot compatibility: same dye_lot_id → no setup; different → setup
        if prev.dye_lot_id != order.dye_lot_id:
            setup = max(setup, cap.dye_lot_changeover_minutes or 30)
        candidates.append(prev.end_at + timedelta(minutes=setup))
    return max(candidates)  # earliest slot ≥ horizon_start AND ≥ last_end+setup
```

EDD differs only in the initial sort key: `pending = sorted(orders, key=lambda o: o.due_at)`. Everything else is identical.

**LLM rationale generation (post-scheduling):**
```python
# Agent invokes Qwen2.5 with the ScheduleDraft + rag_search results
prompt = f"""Sei un planner di produzione tessile. Spiega in {n} bullet point la logica della seguente schedulazione (strategia: {strategy}):

{schedule_draft.model_dump_json(indent=2)}

Cita le SOP rilevanti tra:
{rag_citations_block}

Output JSON: {{ "rationale_md": "...", "citations": [...] }}.
"""
```

The LLM's role here is **explanatory only** — the scheduling decisions are deterministic. This separation ensures the schedule itself is reproducible from `(orders.yaml, asset_capacity.yaml, failure_modes.yaml, strategy)` even when the LLM rationale is mocked.

### Pattern 6: 4-point ASTM prompt for textile QC grading

**What:** A system prompt + few-shot examples that walk Qwen2.5 through the ASTM D5430 point assignment rules:

```
ASTM D5430 — 4-Point System (binding rules):
1. Defect ≤ 3 inches (≤ 7.6 cm) → 1 point
2. Defect > 3 in, ≤ 6 in (≤ 15.2 cm) → 2 points
3. Defect > 6 in, ≤ 9 in (≤ 22.8 cm) → 3 points
4. Defect > 9 in (> 22.8 cm) → 4 points
5. Full-width defect (any size, spans selvedge to selvedge) → 4 points
6. Any obvious + noticeable + severe defect (e.g., hole, broken_end with safety risk) → 4 points/m regardless of size
7. Max 4 points per linear meter regardless of count or size
```

**JSON output schema (LLM is forced to produce this via prompt):**
```json
{
  "score": 0..4,
  "severity": "minor|major|critical",
  "rationale_md": "Markdown explanation",
  "citations": [{"source_uri": "...", "snippet": "...", "score": 0.0-1.0, "retrieved_at": "..."}]
}
```

**Validator (Pydantic):**
```python
class QualityVerdict(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    score: Annotated[int, Field(ge=0, le=4)]
    severity: Literal["minor", "major", "critical"]
    rationale_md: str
    citations: list[RagCitation]

# If LLM emits invalid severity → fallback to "major" (D-QI-03 conservative default)
# If score outside [0..4] → reject + replan once
```

**Severity mapping (drives HITL routing per D-QI-03):**
| Defect type | Default severity | Override conditions |
|-------------|------------------|---------------------|
| slub (isolated) | minor | frequency > 5/m → major |
| neppy (low freq) | minor | freq > 3/m → major |
| mispick (single) | major | recurring same row → critical |
| broken_end | major | safety_risk flag → critical |
| selvage_fault | major | full-width → critical |
| shade_deviation | major | ΔE > 3 → critical |
| unlevel_dyeing | major | premium lot → critical |

**Prompt language:** keep prompt in **English** (LLM grounding is more consistent in EN per Qwen2.5 docs); allow `rationale_md` in **operator's language** (auto-detected from incoming inspection note).

### Pattern 7: Citation validator post-LLM (replan loop)

**What:** After `create_react_agent` returns, intercept the final `AIMessage.content` and check:
1. Did the LLM invoke `rag_search` in this thread (look at `state.messages` for `ToolMessage(name="rag_search")`)? If no → skip validation (no factual claim to cite).
2. If yes: does `response_md` contain at least one `[N]` reference?
3. If yes (1): does the `citations` list (also produced by LLM in structured output, OR derived from `ToolMessage.content`) have ≥ 1 entry?
4. If both 2 and 3 pass: emit response with `citations_validated: true` flag.

**Replan logic (max 1 retry):**
```python
async def validate_or_replan(state, response, retries=0, max_retries=1):
    used_rag = any(isinstance(m, ToolMessage) and m.name == "rag_search" for m in state["messages"])
    has_inline = bool(re.search(r"\[\d+\]", response.content))
    has_citations = bool(response.additional_kwargs.get("citations"))

    if not used_rag:
        return response  # No claim → no citation required

    if has_inline and has_citations:
        return response  # Valid

    if retries >= max_retries:
        log.warning("citation_missing_after_replan", agent="operator-assistant")
        # Audit with flag — do NOT block the response
        return response.copy(update={"additional_kwargs": {**response.additional_kwargs, "citations_missing": True}})

    # Replan with prompt augmentation
    augmented = state["messages"] + [SystemMessage(content=(
        "Your previous response missed inline citations. Re-emit the same answer "
        "but cite each factual claim with [N] referring to the rag_search results."
    ))]
    new_response = await react_agent.ainvoke({"messages": augmented}, config=cfg)
    return await validate_or_replan(state, new_response, retries=retries + 1)
```

**Why not a LangGraph node loop:** Replan loop via LangGraph adds a graph-level cycle and complicates `recursion_limit=5` accounting (we'd need 6 to allow one replan). Out-of-graph wrapper is simpler and audit-friendly (the retry is logged as a separate Langfuse span).

### Pattern 8: Rate limiter PG-backed sliding window 12/h

**What:** `RateLimiter` in `packages/sft-agents/src/sft_agents/runtime/rate_limit.py`. Implementation queries `audit.actions` with a count over the last hour; if `count >= 12`, suppress.

**Implementation:**
```python
import asyncpg
from datetime import datetime, timedelta, timezone

class RateLimiter:
    """PG-backed sliding window rate limiter (D-AD-03)."""

    def __init__(self, pool: asyncpg.Pool, *, agent_id: str, limit: int = 12, window_minutes: int = 60):
        self._pool = pool
        self._agent_id = agent_id
        self._limit = limit
        self._window = timedelta(minutes=window_minutes)

    async def check_and_emit(self, action_type: str) -> tuple[bool, int]:
        """Return (allowed, current_count). Uses audit.actions as source of truth.

        Concurrency safety:
            We rely on PG MVCC + a single Postgres transaction. Two concurrent
            calls might both read count=11 and both decide allowed=True; the
            window is forgiving by design (12/h means "approximately 12") so
            occasional N=13 is acceptable per D-AD-03 intent. If exact bound
            is needed in Phase 11, add SELECT ... FOR UPDATE on a counter row.
        """
        cutoff = datetime.now(timezone.utc) - self._window
        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM audit.actions "
                "WHERE agent_id = $1 AND action_type = $2 AND ts >= $3",
                self._agent_id, action_type, cutoff,
            )
        return (count < self._limit, count)
```

**Suppress + hourly summary (per CONTEXT D-AD-03):** When `allowed=False`, AnomalyDetector node still writes an `audit.actions` row with `decision: SUPPRESSED` (NEW Decision enum value) + `payload: {original_anomaly, current_count}`. Once per hour (driven by APScheduler same container), a summary alert publishes `alerts.anomalies.summary` with `suppressed_count`.

**Why PG over Redis:** Survives restart (D-AD-03 explicit); no extra infra; audit log already has the data — single source of truth.

### Pattern 9: OPS cluster intra-subgraph routing

**What:** Phase 4 `build_cluster_subgraph` currently wires children **linearly** (`operator-assistant → production-planner → quality-inspector → anomaly-detector → END`). Phase 6 must convert this to a **router**: read `state.target_agent` populated by the supervisor's HybridRouter (or by request handler from API call), branch to the chosen child, then END.

**Implementation (extend `packages/sft-agents/runtime/clusters.py` — or per-cluster override):**
```python
def build_ops_subgraph(child_callables: dict[str, Callable]) -> StateGraph:
    """Ops cluster: route by state.target_agent, fallback to operator-assistant."""
    g = StateGraph(AgentState)
    for slug, fn in child_callables.items():
        g.add_node(slug, fn)

    def _route(state: AgentState) -> str:
        target = state.get("target_agent") or "operator-assistant"
        if target not in child_callables:
            log.warning("ops_route_unknown_target", target=target, fallback="operator-assistant")
            return "operator-assistant"
        return target

    g.add_conditional_edges(START, _route, {slug: slug for slug in child_callables})
    for slug in child_callables:
        g.add_edge(slug, END)
    return g
```

Each `child_callable` is the agent's `__call__(state) -> dict` — for OperatorAssistant it wraps `create_react_agent.ainvoke()`; for ProductionPlanner it calls the heuristic + LLM; for QualityInspector it grades; for AnomalyDetector it scores.

### Pattern 10: sim-textile QualityEvent generator + ProductionState

**What:** Two new modules in `simulators/sim-textile/src/sim_textile/`:

**`production_state.py`:**
```python
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import secrets

@dataclass
class ProductionState:
    asset_id: str
    current_dye_lot_id: str
    rotation_interval: timedelta = timedelta(minutes=60)
    _last_rotation: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def maybe_rotate(self, now: datetime) -> bool:
        if (now - self._last_rotation) >= self.rotation_interval:
            ymd = now.strftime("%Y%m%d")
            seq = secrets.token_hex(2)
            self.current_dye_lot_id = f"DL-{self.asset_id}-{ymd}-{seq}"
            self._last_rotation = now
            return True
        return False
```

**`quality_event_generator.py`:** subscribes to the existing emitter loop, emits a stochastic QC event with probability proportional to the fault profile's active fault types. Subject: `quality.events.<asset_id>`. Payload Pydantic schema:

```python
class QualityEvent(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    event_id: UUID
    asset_id: str
    dye_lot_id: Annotated[str, Field(pattern=r"^DL-[A-Z0-9-]+-\d{8}-[0-9a-f]+$")]
    defect_type: Literal["broken_end","mispick","slub","neppy","selvage_fault","shade_deviation","unlevel_dyeing"]
    defect_length_inches: Annotated[float, Field(ge=0.0)]
    full_width: bool = False
    position_meters: float
    timestamp: datetime  # UTC tz-aware
    source: Literal["simulator", "operator"]
```

**Hook into existing emitter:** in `simulators/sim-textile/src/sim_textile/emitter.py`, after each sample loop iteration, the generator decides if a QC event should fire (e.g., 1% chance per minute per asset under faulted profile; 0.1% under nominal). It publishes via the existing NATS connection (already part of the simulator process via `services/ot-bridge` pattern — Phase 6 may add a direct publisher inside sim-textile).

### Anti-Patterns to Avoid

- **Don't call `create_react_agent` inside the cluster subgraph node body.** Build it once at startup; the subgraph node is a thin wrapper that invokes the compiled runnable. Otherwise tool initialization (Qdrant client, Neo4j driver) happens per-request.
- **Don't make AnomalyDetector a long-running NATS consumer Phase 6.** Locked D-AD-01 — node-on-demand only.
- **Don't hard-code `recursion_limit` per-node.** Use `safe_invoke` Phase 4 — already escalates to HITL on overflow.
- **Don't let LLM produce numeric `score` without Pydantic clamp + replan.** LLMs hallucinate integers; Pitfall §17 + D-QI-02 explicitly demands range validation.
- **Don't bypass NATS for the operator-API QC submission.** D-QI-01 routes both sources through the same JetStream subject for uniformity; the api-gateway endpoint publishes to NATS, never invokes the inspector directly.
- **Don't mutate `state["messages"]` in-place.** Always return a dict that LangGraph reducers merge.
- **Don't propagate raw `user_roles` from request body into Qdrant filter without validation.** Wrap in `Literal[...]`-typed enum (Phase 5 D-72 `ROLE_TO_ACL` map already exists).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ReAct loop (LLM ↔ tool ↔ LLM) | Custom while-loop with manual tool dispatch | `langgraph.prebuilt.create_react_agent` | Already handles tool-call schema, ToolMessage formatting, recursion limit, checkpointing [CITED: reference.langchain.com] |
| Cron scheduling | Background asyncio task with `await asyncio.sleep(300)` | `APScheduler.AsyncIOScheduler` + `CronTrigger.from_crontab("*/5 * * * *")` | Proper shutdown, missed-run coalescing, signal handling [CITED: apscheduler.readthedocs.io] |
| Mock LLM | LiteLLM stub or custom completion server | `MockReplayChatModel(BaseChatModel)` subclass | LangChain's `BaseChatModel` ABC enforces the right interface; tests stay decoupled from network |
| NATS durable consumer | Manual ack tracking + dedup table | JetStream `AckExplicit` + `Nats-Msg-Id` header + `max_deliver` | Server-side idempotency primitive [CITED: docs.nats.io/using-nats/developer/develop_jetstream/model_deep_dive] |
| Sliding-window rate counter | In-memory deque per process | PG `COUNT(*)` query over `audit.actions WHERE ts >= NOW() - INTERVAL '1h'` | Survives restart; audit log is source of truth; no Redis dep |
| Language detection | Heuristic on bigram frequency | `langdetect.detect(text)` with `DetectorFactory.seed=42` | Battle-tested, MIT, deterministic with seed |
| HTTP retry / circuit breaker for scheduler→gateway | Custom retry loop | `httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(retries=3))` + APScheduler `coalesce=True` | Avoids missed-run pileup |
| 4-point grading deterministic mapper | Lookup table per defect_length | LLM JSON-mode with Pydantic validator (locked D-QI-02) | User explicitly chose flexibility over rigidity |
| Schedule optimality solver | OR-tools CP-SAT | Greedy SPT/EDD (locked D-PP-01) | Phase 6 PoC scope; OR-tools deferred to Phase 9 |
| Document parser for inspection notes | Custom Markdown parsing | If needed, reuse Phase 5 `MarkdownParser`; operator notes are plain-text initially | YAGNI |

**Key insight:** Phase 6 is mostly composition over invention. Every heavy lifter (`create_react_agent`, `interrupt()`, `AsyncPostgresSaver`, `RagSearchTool`, `QueryTimescaleTool`, `AuditWriter`, `SafetyInterlockMiddleware`) already exists. The 4 agents are thin orchestration on top.

## Common Pitfalls

### Pitfall 1: `recursion_limit` config not propagated through `create_react_agent`

**What goes wrong:** LangGraph's `recursion_limit` is read from `config["recursion_limit"]` at `.ainvoke` time, NOT from the compiled graph. A typo (`recursion_limits`, `recursionLimit`) silently defaults to 25 — way more than D-OA-01's 5.
**Why it happens:** No type checking on config dict keys.
**How to avoid:** Use `safe_invoke` (Phase 4) which validates the config dict + escalates on overflow. Unit-test the actual config dict shape against a schema.
**Warning signs:** OperatorAssistant thread takes > 60s, or audit shows ≥ 6 `tool_call` events in a single thread.

### Pitfall 2: Tool list closures hold stale `user_roles`

**What goes wrong:** If `RagSearchTool(pipeline, user_roles=req.user_roles)` is instantiated once at startup, subsequent requests reuse the first request's roles → privilege escalation OR over-restriction.
**Why it happens:** LangChain BaseTool instances are typically singletons.
**How to avoid:** Build tool list **per request** in the agent's `__call__` (cheap — tool objects are dataclasses, no heavy init). Alternative: tool reads `user_roles` from a `ContextVar` set at request boundary (more idiomatic but harder to test).
**Warning signs:** Two concurrent requests share retrieval results that don't match their roles.

### Pitfall 3: `interrupt()` re-execution corrupts double-write

**What goes wrong:** When LangGraph resumes from a checkpoint, the node re-runs from its **start**. If the node calls `audit_writer.write()` *before* `interrupt()`, the write happens twice — once on initial pause, once on resume.
**Why it happens:** Documented in Phase 4 `hitl/interrupt.py` docstring (§"Pitfall §6 note"). New code paths in Phase 6 (escalate_to_supervisor tool) must follow same idempotency pattern.
**How to avoid:** Audit writes that happen *after* `interrupt()` resume (Phase 4 idiom). For the `escalate_to_supervisor` tool, make the approval ID sha256-deterministic from `(thread_id, action_id)` (Phase 4 already does this — Phase 6 reuses).
**Warning signs:** `audit.actions` table has duplicate rows with same `(action_id, decision)` and timestamps a few seconds apart.

### Pitfall 4: NATS QC events arrive before `qi-consumer` is created

**What goes wrong:** sim-textile publishes to `quality.events.LOOM-01` at t=0; consumer is created at t=2. JetStream stream config controls retention — if `max_age` is shorter than catch-up time, events are lost.
**Why it happens:** Race between simulator startup and consumer startup.
**How to avoid:** Bootstrap script creates `QUALITY_STREAM` *before* sim-textile starts (`scripts/nats-bootstrap-streams.py` already runs before compose `up` on Phase 3). Stream retention = 7 days (generous). Consumer is durable so once created, picks up from stream's earliest unacked.
**Warning signs:** Initial test run misses first few QC events.

### Pitfall 5: APScheduler missed-fire on container restart

**What goes wrong:** Scheduler container is restarted at t=04:33; next scheduled fire was at t=04:30. Without coalescing, APScheduler may fire 1 catch-up job per missed window; without `misfire_grace_time`, it skips entirely.
**Why it happens:** Default `misfire_grace_time=1` second is tiny.
**How to avoid:** Set `misfire_grace_time=300` (5 min) + `coalesce=True` + `max_instances=1`. Helm chart pins `replicas: 1`. Document in compose file.
**Warning signs:** Gap of > 5 min between AnomalyDetector scans during deploy.

### Pitfall 6: Concurrent OperatorAssistant threads share `langdetect.DetectorFactory.seed` state

**What goes wrong:** `langdetect.DetectorFactory.seed = 42` is a module-level global; concurrent detections in parallel asyncio tasks can race. Empirically the lib uses thread-local state but asyncio task switches mid-detection are not documented.
**Why it happens:** Module global mutation.
**How to avoid:** Seed once at module import (in `lang_detect.py` top-level); never reset; never call from multiple threads simultaneously (asyncio is single-threaded → safe). Add a unit test that runs N=100 sequential detects and asserts deterministic output.
**Warning signs:** Flaky CI failure where same input produces different lang detection.

### Pitfall 7: LLM produces severity outside `Literal[minor,major,critical]`

**What goes wrong:** LLM emits `"high"` or `"medium"` — Pydantic raises ValidationError, agent returns 500.
**Why it happens:** Prompt drift; out-of-distribution defect descriptions.
**How to avoid:** Try/except around `QualityVerdict.model_validate` → fallback to severity=`major` (conservative; D-QI-03 prescribes this). Log a Langfuse warning span for telemetry.
**Warning signs:** Langfuse shows > 1% rate of "severity_fallback_triggered" events.

### Pitfall 8: Greedy heuristic produces infeasible schedule (no asset for an order)

**What goes wrong:** `orders.yaml` has an order whose `compatible_families` doesn't intersect `asset_capacity.yaml` — no eligible asset. Algorithm skips it silently.
**Why it happens:** No CI validator covers this cross-file constraint.
**How to avoid:** CI validator (NEW Phase 6 task) iterates over `orders.yaml × asset_capacity.yaml`, asserts every order has ≥ 1 eligible asset. ScheduleDraft includes `unscheduled_orders: list[OrderRef]` so the LLM rationale can surface the gap.
**Warning signs:** ScheduleDraft has fewer items than orders + no audit explanation.

### Pitfall 9: `escalate_to_supervisor` tool invoked inside ReAct loop bypasses Safety Interlock

**What goes wrong:** OperatorAssistant LLM decides to escalate but the resulting `interrupt()` doesn't go through SafetyInterlockMiddleware (which is wired only on `proposed_actions`, not on tool calls).
**Why it happens:** Architectural ambiguity — Phase 4 SafetyInterlockMiddleware gates `ProposedAction.target_subject`, but `escalate_to_supervisor` is "just an HITL request, not a write."
**How to avoid:** `escalate_to_supervisor` tool internally constructs a `ProposedAction` with `action_type=ESCALATION_REQUEST` (NEW enum) and passes it through `SafetyInterlockMiddleware.check()` before calling `interrupt()`. SafetyInterlock will accept (subject doesn't match forbidden globs) but the explicit pass ensures uniform audit shape.
**Warning signs:** `audit.actions` entries from `escalate_to_supervisor` missing `evidence_panel` or `decision_actor`.

### Pitfall 10: Mock LLM fixture drift — fixture stale after prompt edit

**What goes wrong:** Engineer tweaks the citation-validation prompt, but the mock JSONL still encodes the old `prompt_hash` → all e2e tests pass against a non-existent prompt path.
**Why it happens:** Mock keyed on hash; manual fixture updates aren't enforced.
**How to avoid:** When `prompt_hash` mismatch, mock can fall back to *ordered* replay (Pattern 2 above does this), BUT emit a `LangfuseWarning` span + CI flag. CI gate: count of fallback events > 0 → fail PR with "fixture needs refresh." Maintain a `regenerate-fixtures.py` script (Phase 6 ships skeleton) that re-records JSONL against a real Qwen2.5-7B run.
**Warning signs:** Long-running tests pass but later real-LLM run fails on the same scenario.

## Code Examples

### Example 1: `escalate_to_supervisor` BaseTool (NEW Phase 6)

```python
# Source: derived from Phase 4 packages/sft-agents/src/sft_agents/hitl/interrupt.py
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

class EscalateInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    reason: str = Field(min_length=10, max_length=2000)
    suggested_action: str = Field(min_length=10, max_length=2000)
    evidence_summary: str = Field(min_length=10, max_length=2000)

class EscalateToSupervisorTool(BaseTool):
    name: str = "escalate_to_supervisor"
    description: str = (
        "Pause the agent and route the current decision to a human supervisor "
        "for explicit approval. Use when the user's request requires authority "
        "the agent doesn't have (e.g., production stop, safety override). "
        "Required args: reason, suggested_action, evidence_summary."
    )
    args_schema: type[BaseModel] = EscalateInput
    _audit_writer: object = PrivateAttr()
    _queue_writer: object = PrivateAttr()
    _nats: object = PrivateAttr()
    _safety: object = PrivateAttr()

    def __init__(self, audit_writer, queue_writer, nats, safety_middleware, **kw):
        super().__init__(**kw)
        self._audit_writer = audit_writer
        self._queue_writer = queue_writer
        self._nats = nats
        self._safety = safety_middleware

    def _run(self, *a, **kw): raise NotImplementedError("async-only")

    async def _arun(self, reason, suggested_action, evidence_summary, **kw):
        from sft_agents.hitl.interrupt import human_approval_node
        from sft_agents.models.enums import Tier, ActionType
        from sft_agents.models.proposed_action import ProposedAction
        # Construct a synthetic ProposedAction for audit + safety check
        action = ProposedAction(
            action_type=ActionType.ESCALATION_REQUEST,   # NEW enum value
            args={"reason": reason, "suggested_action": suggested_action,
                  "evidence_summary": evidence_summary},
            target_subject=None,
        )
        self._safety.check(action)  # raises SafetyInterlockRejection if forbidden
        # Hand off to the standard HITL approval node via interrupt()
        # NOTE: this tool runs inside a ReAct loop — the interrupt() pauses the
        # WHOLE create_react_agent runnable; on resume the tool returns the
        # supervisor's decision back to the LLM as a ToolMessage.
        from langgraph.types import interrupt
        decision = interrupt({
            "tool": "escalate_to_supervisor",
            "tier": Tier.SUPERVISOR.value,
            "payload": action.model_dump(mode="json"),
        })
        return decision  # dict — LLM receives as ToolMessage content
```

### Example 2: AnomalyDetector node body (D-AD-01 + D-AD-02 + D-AD-03)

```python
# apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py
from datetime import datetime, timedelta, timezone
import structlog
from sft_tools.timescale.query import QueryTimescaleTool
from sft_domain.ops.anomaly import Anomaly, load_anomaly_baselines
from sft_agents.runtime.rate_limit import RateLimiter

log = structlog.get_logger("agent.anomaly-detector")

class AnomalyDetector:
    def __init__(self, pool, baselines_path, asset_registry):
        self._tool = QueryTimescaleTool()
        self._baselines = load_anomaly_baselines(baselines_path)
        self._assets = asset_registry
        self._limiter = RateLimiter(pool, agent_id="anomaly-detector", limit=12, window_minutes=60)

    async def __call__(self, state: dict) -> dict:
        window_minutes = state.get("window_minutes", 15)
        now = datetime.now(timezone.utc)
        anomalies: list[Anomaly] = []
        for asset in self._assets:
            df = await self._tool._arun(
                asset_id=asset.asset_id,
                time_range=(now - timedelta(minutes=window_minutes), now),
            )
            for row in df.itertuples():
                baseline = self._baselines.get((asset.asset_family.value, row.sensor_id))
                if baseline and not baseline.is_within_band(row.value):
                    a = Anomaly(
                        asset_id=row.asset_id, sensor_id=row.sensor_id,
                        value=row.value, baseline_low=baseline.low, baseline_high=baseline.high,
                        timestamp=row.timestamp, severity=baseline.severity_for(row.value),
                    )
                    allowed, count = await self._limiter.check_and_emit("anomaly")
                    if not allowed:
                        log.info("anomaly_suppressed", count=count, anomaly_id=str(a.id))
                        continue
                    anomalies.append(a)
        log.info("anomaly_scan_complete", emitted=len(anomalies), window_minutes=window_minutes)
        return {"anomalies": anomalies}
```

### Example 3: QualityInspector grading flow (D-QI-02 + D-QI-03)

```python
# apps/agents/ops/quality-inspector/src/ops_quality_inspector/grader.py
from pydantic import ValidationError
from sft_agents.llm.factory import build_chat_model
from sft_knowledge.tools.rag import RagSearchTool

async def grade_quality_event(event, rag_pipeline, audit_writer):
    rag_tool = RagSearchTool(pipeline=rag_pipeline)
    citations = await rag_tool.ainvoke({
        "query": f"4-point grading {event.defect_type}",
        "user_roles": ["technician"],
        "category": "sop",
        "k": 5,
    })

    model = build_chat_model(temperature=0.0, seed=42)
    prompt = build_grading_prompt(event, citations)
    raw = await model.ainvoke(prompt)
    try:
        verdict = QualityVerdict.model_validate_json(raw.content)
    except ValidationError:
        # Fallback conservative — D-QI-03
        verdict = QualityVerdict(
            score=4, severity="major",
            rationale_md="LLM produced invalid output; conservative fallback.",
            citations=citations,
        )
    # HITL routing per severity
    tier_for = {"minor": None, "major": Tier.SUPERVISOR, "critical": Tier.MANAGER}
    if verdict.severity == "minor":
        await audit_writer.write_auto(event, verdict)
    else:
        await trigger_hitl(event, verdict, tier=tier_for[verdict.severity])
    return verdict
```

## Runtime State Inventory

> Phase 6 is greenfield agent business logic — no rename/refactor; this section is **not required**. The only "extension" of existing data is `failure_modes.yaml` (adds 3 fields: `hitl_tier`, `setup_minutes`, `severity`) which is a backward-compatible YAML schema change. No PG data migration. Section omitted per researcher guidance.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `create_react_agent` from `langgraph.prebuilt` | `create_agent` from `langchain` package (with middleware system) | LangGraph v1, Oct 2025 | D-OA-01 locks the older API; deprecation warning OK; Phase 11 may migrate |
| Single combined Knowledge cluster | Split `knowledge-curation` + `knowledge-training` | Phase 4 D-53 | Doesn't affect Phase 6 directly, but ops subgraph routing must respect 5-cluster topology |
| BM25 + dense hybrid client-side | Qdrant Query API + `Prefetch` + `Fusion.RRF` server-side | Qdrant 1.10+ | Phase 5 D-63 already locked; Phase 6 just consumes |
| Polling cron via bash | `AsyncIOScheduler` in own container | 2023→2026 industry pattern | Phase 6 ships this as `services/agents-scheduler/` |

**Deprecated / outdated:**
- `python-opcua` (sync, deprecated) → already replaced by `asyncua` Phase 3
- `langchain.agents.AgentExecutor` (legacy) → replaced by `create_react_agent` (and now `create_agent`)
- In-memory `MemorySaver` for production → replaced by `AsyncPostgresSaver` Phase 4

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `APScheduler` 3.10.4 is stable on PyPI as of 2026-05 | Standard Stack | Wrong → planner pins different version; low risk (mainstream) |
| A2 | `langdetect` MIT license is unchanged | Standard Stack | Wrong → licensing block in `pip-licenses` CI (Phase 1 license scanner catches) |
| A3 | LangGraph 0.4 still ships `create_react_agent` (not removed entirely in v1) | §1 | Wrong → planner must switch to `create_agent`; same shape, minor adapter work |
| A4 | Qwen2.5-7B Q4_K_M reliably produces JSON-mode output for 4-point grading | Pattern 6 + Pitfall 7 | Wrong → severity fallback fires often; D-QI-03 already designed for this |
| A5 | `langdetect` with `seed=42` is reproducible across asyncio task switches | Pitfall 6 | Wrong → flaky test; mitigation = single-thread asyncio, top-level seed |
| A6 | `nats-py` JetStream consumer creation is idempotent across stream restart | Pattern 3 | Wrong → bootstrap script must DELETE then CREATE (already standard Phase 3 idiom) |
| A7 | Existing Phase 4 `safe_invoke` wraps `recursion_limit` properly for `create_react_agent` runnables (which expose `.ainvoke(config=...)`) | Pattern 1 | Wrong → Phase 6 plan needs adapter wrapper task |
| A8 | The audit `Decision` enum can be extended without DB migration | §8 Rate Limiter | Wrong → if `Decision` is a PG CHECK constraint, ADD VALUE migration required; verify against Phase 4 `audit.actions` schema (likely needs `ALTER TYPE` migration if PG enum, or no-op if TEXT+CHECK; planner must check) |
| A9 | The OPS cluster subgraph in Phase 4 can be overridden per-cluster (build_cluster_subgraph is currently generic-linear) | §9 routing | Confirmed — Phase 4 code admits override via custom `build_ops_subgraph`; D-X in CONTEXT explicitly says Claude implements via `target_agent` field |
| A10 | sim-textile NATS publish in addition to OPC-UA emission is acceptable scope-wise | §10 generator | CONTEXT D-QI-01 explicitly locks dual-source; no risk |
| A11 | The Phase 4 LLM factory accepts `mock` as a third backend value (currently locked to `ollama|vllm`) | §2 mock | **Phase 6 PLAN must add this branch** — explicit task |
| A12 | Mock JSONL fixtures can be hand-authored for the 12 scenarios (3 × 4 agents) | §2 + D-X-01 | Wrong → need generator script; CONTEXT mentions opt-in real-llm but not auto-record. Plan should include a `regenerate-fixtures.py` helper. |

**Decisions assumed and needing user confirmation before plan execution:** A8 (audit Decision enum extensibility) — planner runs `grep -n "CHECK.*decision" infra/migrations/` to verify; A11 (factory must be extended) — plan task explicit; A12 (fixture authoring) — plan ships skeleton + sample.

## Open Questions

1. **Audit Decision enum extension — DB migration or just YAML/Pydantic?**
   - What we know: Phase 4 introduced `Decision` enum with values `auto|hitl_operator|...|governor_alert|escalated`.
   - What's unclear: Whether the PG `audit.actions.decision` column is `TEXT + CHECK ('a','b','c')` or `pg_enum`. The Phase 4 SQL fragment in CONTEXT shows `CHECK (decision IN (...))` — text+check.
   - Recommendation: Phase 6 plan task **explicitly verifies** then adds `'suppressed'` + `'escalation_request'` (if needed) values via migration `007_extend_audit_decisions.sql` (idempotent ADD VALUE pattern).

2. **Where does `target_agent` come from in the supervisor → ops handoff?**
   - What we know: HybridRouter Phase 4 D-54 routes to cluster but not to intra-cluster agent.
   - What's unclear: Does the LLM stage 2 router also emit the agent slug, or does the request handler (api-gateway endpoint) pre-populate `state["target_agent"]`?
   - Recommendation: Plan ships **two paths** — (a) explicit API endpoint `POST /v1/agents/<slug>/...` pre-populates `target_agent`; (b) supervisor LLM routing for natural-language intents extends Stage-2 prompt to emit `cluster_and_agent` tuple. Fallback to `operator-assistant` (CONTEXT D-X explicit).

3. **Citation validator interaction with `interrupt()` mid-ReAct.**
   - What we know: D-OA-04 validator runs **after** LLM final response.
   - What's unclear: If the LLM calls `escalate_to_supervisor` mid-loop (which itself calls `interrupt()`), does the validator run? Probably not — `interrupt()` returns a `ToolMessage` and the loop continues with a new LLM turn.
   - Recommendation: Validator only runs at final emission; intermediate tool calls (`escalate_to_supervisor`) don't trigger validation; this is the desired behavior (escalation is itself a decision; the actual response generation happens after resume).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL+TimescaleDB | All agents (audit, checkpointer) | ✓ (Phase 3) | 16+TS2.18 | — |
| Qdrant | OperatorAssistant rag_search | ✓ (Phase 5) | 1.16.1 | — |
| Neo4j | OperatorAssistant traverse_graph | ✓ (Phase 5) | 5.24 Community | — |
| NATS JetStream | QualityInspector consumer, AuditWriter | ✓ (Phase 3) | 2.10+ | — |
| Ollama / vLLM | Real-LLM tests + dev runs | ✓ (Phase 4) | Qwen2.5-7B / 14B | mock backend always available |
| Langfuse | Tracing | ✓ (Phase 4 client; server self-host Phase 11) | v3 | callbacks no-op if unconfigured |
| BGE-M3 / BGE-reranker | rag_search Phase 5 | ✓ (Phase 5) | latest | — |
| `langdetect` | OperatorAssistant lang detection | ✗ (new dep) | ≥1.0.9 | English-only default if unavailable |
| `APScheduler` | agents-scheduler service | ✗ (new dep) | ≥3.10.4 | — (blocking; no fallback) |
| `httpx` | scheduler → gateway | ✓ (Phase 4 test deps) | 0.28+ | — |
| `nats-py` | QualityInspector consumer | ✓ (Phase 3) | 2.6+ | — |
| `asyncpg` | rate limiter, queue writer | ✓ (Phase 3) | 0.29+ | — |
| `pandas` | query_timescale return type | ✓ (Phase 3) | latest | — |

**Missing dependencies with no fallback:**
- `APScheduler` — must be installed before scheduler container can run.

**Missing dependencies with fallback:**
- `langdetect` — if absent, default `lang="en"` for response language (degrades UX in IT but not blocking).

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24+ |
| Config file | `pyproject.toml` per-package + root `pytest.ini`/`pyproject.toml` (existing Phase 3/4/5 pattern) |
| Quick run command | `nx affected --target=test` (Nx affected) OR `pytest -m "not e2e and not real-llm" -x` |
| Full suite command | `pytest -m "not real-llm"` (includes integration + e2e with mock LLM) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| OPS-01 | OperatorAssistant retrieves correct loom procedure from RAG and cites inline (IT query) | e2e | `pytest tests/e2e/ops/test_operator_assistant_scenarios.py::test_happy_it -m e2e` | ❌ Wave 0 |
| OPS-01 | OperatorAssistant gracefully degrades when Qdrant returns 0 hits | e2e | `pytest tests/e2e/ops/test_operator_assistant_scenarios.py::test_degraded -m e2e` | ❌ Wave 0 |
| OPS-01 | OperatorAssistant escalates to supervisor when LLM emits `escalate_to_supervisor` tool call | e2e | `pytest tests/e2e/ops/test_operator_assistant_scenarios.py::test_failure_escalation -m e2e` | ❌ Wave 0 |
| OPS-01 | Citation validator detects missing `[N]` and replans (mock) | unit | `pytest apps/agents/ops/operator-assistant/tests/test_validators.py -x` | ❌ Wave 0 |
| OPS-02 | ProductionPlanner emits ScheduleDraft routed to supervisor HITL before release | e2e | `pytest tests/e2e/ops/test_production_planner_scenarios.py -m e2e` | ❌ Wave 0 |
| OPS-02 | Greedy SPT/EDD algorithms produce same schedule given same seed | unit | `pytest packages/sft-domain/tests/test_scheduling.py -x` | ❌ Wave 0 |
| OPS-02 | CI validator: every order has ≥ 1 eligible asset | integration | `pytest packages/sft-domain/tests/test_yaml_validators.py::test_orders_assets_cross_ref -x` | ❌ Wave 0 |
| OPS-03 | QualityInspector applies textile taxonomy + 4-point grading + dye_lot routing | e2e | `pytest tests/e2e/ops/test_quality_inspector_scenarios.py -m e2e` | ❌ Wave 0 |
| OPS-03 | QualityInspector NATS consumer is idempotent (replay same event_id → single audit row) | integration | `pytest apps/agents/ops/quality-inspector/tests/test_nats_consumer.py::test_idempotency -m integration` | ❌ Wave 0 |
| OPS-03 | Severity → HITL tier mapping from failure_modes.yaml | unit | `pytest packages/sft-domain/tests/test_failure_modes_hitl_tier.py -x` | ❌ Wave 0 |
| OPS-04 | AnomalyDetector scores per-machine, no false-positives on loom-vibration baseline | e2e | `pytest tests/e2e/ops/test_anomaly_detector_scenarios.py::test_loom_vibration_no_fp -m e2e` | ❌ Wave 0 |
| OPS-04 | AnomalyDetector enforces 12-alert/hour rate limit | integration | `pytest apps/agents/ops/anomaly-detector/tests/test_rate_limit.py::test_12h_window -m integration` | ❌ Wave 0 |
| OPS-04 | Scheduler triggers `POST /v1/agents/anomaly-detector/scan` every 5 min | integration | `pytest services/agents-scheduler/tests/test_scheduler.py -m integration` | ❌ Wave 0 |
| OPS-05 | Every agent's EvidencePanel includes tool inventory + data sources + HITL level + KPI | unit (per agent) | `pytest apps/agents/ops/*/tests/test_evidence_panel.py -x` | ❌ Wave 0 |
| OPS-06 | 3 scenarios × 4 agents = 12 e2e tests pass | e2e suite | `pytest tests/e2e/ops/ -m e2e` | ❌ Wave 0 |
| OPS-06 | Real-LLM smoke (opt-in) — 1 happy path per agent | e2e | `pytest tests/e2e/ops/ -m real-llm` | ❌ Wave 0 (opt-in, no CI gate) |

### Sampling Rate
- **Per task commit:** `nx affected --target=test` (excludes e2e + real-llm)
- **Per wave merge:** `pytest -m "not real-llm" -x` (all unit + integration + e2e mock)
- **Phase gate:** `pytest -m "not real-llm"` green + manual real-llm smoke (`pytest -m real-llm`) green on dev machine

### Wave 0 Gaps
- [ ] `tests/conftest.py` — extend with `mock_llm_backend` fixture (record/replay JSONL loader) + `ops_scenario` parametrize loader
- [ ] `tests/e2e/ops/__init__.py` + 4 scenario files (one per agent), 3 scenarios each
- [ ] `tests/fixtures/ops_scenarios/{agent}/{happy,degraded,failure}.yaml` — 12 deterministic scenario inputs
- [ ] `tests/fixtures/llm_responses/{agent}/{happy,degraded,failure}.jsonl` — 12 mock LLM trace files
- [ ] `packages/sft-domain/tests/test_scheduling.py` — unit tests for SPT/EDD heuristic
- [ ] `packages/sft-domain/tests/test_yaml_validators.py` — orders/capacity/baselines/failure_modes cross-refs
- [ ] `packages/sft-domain/tests/test_failure_modes_hitl_tier.py` — mapping table coverage
- [ ] `apps/agents/ops/operator-assistant/tests/test_validators.py` — citation validator unit tests
- [ ] `apps/agents/ops/quality-inspector/tests/test_nats_consumer.py` — idempotency + ack policy
- [ ] `apps/agents/ops/anomaly-detector/tests/test_rate_limit.py` — 12/h window enforcement
- [ ] `services/agents-scheduler/tests/test_scheduler.py` — cron trigger fires + retries on HTTP 5xx
- [ ] Per-agent `tests/test_evidence_panel.py` — EvidencePanel shape validation
- [ ] Framework install: none (pytest already configured Phase 1)

## Security Domain

> `security_enforcement` setting absent in config — treat as enabled. Section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | partial (Phase 11 lands JWT auth on api-gateway) | Phase 6 ships endpoints unauthenticated dev-only; pre-existing A-018 boundary |
| V3 Session Management | yes | LangGraph `thread_id = {cluster}.{agent_id}.{session_uuid}` (Phase 4 D-59) |
| V4 Access Control | **yes (critical)** | `RagSearchTool` ACL pre-filter via `user_roles` (Phase 5 D-72); per-tool `safety_interlock` whitelist enforced (Phase 4 D-58) |
| V5 Input Validation | **yes (critical)** | All API inputs Pydantic-validated (`extra=forbid`); NATS payloads validated with `QualityEvent.model_validate_json`; LLM outputs validated with `QualityVerdict` / `ScheduleDraft` |
| V6 Cryptography | no (no new crypto; PG TLS + JWT signing in Phase 11) | — |
| V7 Error Handling | yes | `structlog` JSON logs; never log raw user input PII (Phase 4 GDPRRedactor) |
| V8 Data Protection | yes | `EvidencePanel.input_summary` 500-char cap + `input_truncated` flag (Phase 4 T-04-Checkpoint-PII) |
| V9 Communication | partial | Internal NATS unauthenticated dev; mTLS Phase 11 |
| V10 Malicious Code | yes | `yaml.safe_load` only (orders.yaml, baselines.yaml, etc.); no `eval`/`exec` |
| V12 Files | partial | YAML files validated against Pydantic schemas at load time |

### Known Threat Patterns for OPS Cluster

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via QC event note from operator API | Tampering | Strip control characters + length-cap; LLM prompt frames operator text in fenced block; never instructs LLM "follow operator instructions" — only "grade the defect described below"; pre-existing Pitfall 5 from PITFALLS.md |
| Privilege escalation via `user_roles` spoofing in request body | Spoofing | Phase 6 dev-mode accepts roles from body; Phase 11 will replace with JWT-derived roles. Document this as known limitation in `assumptions/register.yaml` (NEW entry) |
| HITL queue flood from runaway QC events (DoS) | Denial of Service | `qi-consumer` `max_deliver=5` + ack timeout; QualityInspector severity routing means `minor` defects auto-log (no HITL spam) |
| AnomalyDetector alert storm | Denial of Service | Rate limiter D-AD-03 12/h |
| LLM tool-call injection (LLM asks to call forbidden tool) | Elevation of Privilege | `SafetyInterlockMiddleware` Phase 4 gates `target_subject`; OPS agents use only allowlisted tools; new tools (`escalate_to_supervisor`, `log_event`) explicitly pass through safety check |
| Audit log tampering | Repudiation | Phase 4 `REVOKE UPDATE,DELETE ON audit.actions FROM agent_role` already enforced |
| Schedule manipulation (LLM hallucination of orders not in YAML) | Tampering | ScheduleDraft items contain only `order_id`s validated against loaded `OrderSpec`; CI test catches drift |
| Cross-tenant data leak via Qdrant ACL bypass | Information Disclosure | Phase 5 D-72 `ROLE_TO_ACL` map + payload pre-filter in `RagSearchTool._arun`; Phase 6 must NOT call Qdrant client directly bypassing the tool |
| `escalate_to_supervisor` tool used to bypass scope (LLM auto-escalates for non-actionable Qs) | Elevation of Privilege | Tool description explicitly states "use when human authority required"; budget tracker Phase 4 caps escalation count per thread |
| sim-textile QC event publisher floods NATS | Denial of Service | `quality_event_generator` rate-limited (configurable per fault profile, default ≤ 10 events/min/asset) |

## Sources

### Primary (HIGH confidence)
- [LangGraph `create_react_agent` API reference](https://reference.langchain.com/python/langgraph.prebuilt/chat_agent_executor/create_react_agent) — signature, deprecation notice in v1
- [LangGraph durable execution + interrupt/resume](https://docs.langchain.com/oss/python/langgraph/durable-execution) — checkpoint semantics, replay behavior
- [LangGraph v1 release notes](https://docs.langchain.com/oss/javascript/releases/langgraph-v1) — v1 GA October 2025
- [NATS JetStream Consumers](https://docs.nats.io/nats-concepts/jetstream/consumers) — durable, ack policies
- [NATS JetStream Model Deep Dive](https://docs.nats.io/using-nats/developer/develop_jetstream/model_deep_dive) — idempotency via Nats-Msg-Id
- [nats-py GitHub](https://github.com/nats-io/nats.go/jetstream) — Python pull_subscribe + ack/nak/term
- [APScheduler User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) — AsyncIOScheduler + CronTrigger
- [ASTM D5430 4-point system reference](https://dqctex.com/4-point-system) — defect length → points rules
- Phase 4 `06-CONTEXT.md` (this project) — locked decisions D-AD-01..04, D-QI-01..04, D-PP-01..04, D-OA-01..04, D-X-01
- Phase 4 `04-CONTEXT.md` + existing `packages/sft-agents` code — interrupt/resume + audit dual-write + safe_invoke + LLM factory
- Phase 5 `05-CONTEXT.md` + `packages/sft-knowledge/tools/{rag,graph}.py` — RagSearchTool + TraverseGraphTool contracts

### Secondary (MEDIUM confidence)
- [LangGraph ReAct tutorial 2026 (Medium)](https://medium.com/@mzeynali01/from-react-loop-to-production-agent-a-hands-on-langgraph-tutorial-ffd2649706ad) — ReAct loop + production patterns
- [APScheduler + FastAPI gotchas](https://browniantech.com/blog/post/Better-FastAPI-Background-Jobs) — multi-worker duplication problem motivating separate container
- [SPT/EDD heuristics overview](https://usersolutions.com/blog/glossary/heuristic-scheduling) — scheduling rule semantics
- [4-point system primer (textilestudycenter.com)](https://textilestudycenter.com/fabric-inspection/) — visual inspection workflow

### Tertiary (LOW confidence)
- [APScheduler logs in Docker issue](https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker/issues/227) — log capture gotcha
- [LangGraph v1 ReAct migration guide (agentsindex.ai)](https://agentsindex.ai/blog/langgraph-tutorial) — v1 API examples (informational only)
- [LangGraph checkpointing best practices 2025 (sparkco.ai)](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025) — checkpoint persistence modes

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libs already locked Phase 1-5; only `APScheduler` + `langdetect` are new and well-established.
- Architecture (subgraph composition, mock LLM, scheduler container): HIGH — patterns are direct extensions of Phase 4 idioms.
- Citation validator replan loop: MEDIUM — design clear but exact integration with `create_react_agent`'s message reducer is verified only via docs, not in Phase 6 code yet.
- 4-point ASTM + greedy heuristic: HIGH (domain rules well-documented); MEDIUM on LLM compliance (Qwen2.5-7B JSON-mode reliability — Pitfall 7 mitigation present).
- NATS durable consumer pattern: HIGH (official docs + Phase 3 idiom).
- Rate limiter PG sliding window: HIGH (audit table already has data; query is trivial COUNT).
- Pitfalls: HIGH — drawn from existing PITFALLS.md + Phase 4 docstrings + LangGraph re-execution semantics.

**Research date:** 2026-05-23
**Valid until:** 2026-06-23 (30 days — stable stack; LangGraph v1 migration window is the most volatile factor).

---

## RESEARCH COMPLETE

Phase 6 implementation requires extending the Phase 4 LLM factory with a `mock` backend, building 4 thin agent wrappers (1 ReAct + 1 algo+LLM + 1 NATS-consumer+LLM + 1 baseline+rate-limit), adding 1 new scheduler service container, extending sim-textile with QC event generation, and shipping 12 mock-LLM e2e scenarios — all on top of pre-existing Phase 4/5 contracts.
