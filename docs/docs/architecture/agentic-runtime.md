---
title: Core Agentic Runtime
tags: [architecture, phase-04, langgraph, hitl, agents]
---

# Core Agentic Runtime

## Overview

Phase 4 ships the **orchestrator backbone** on which every domain agent
(Phase 6-9) will plug in. The runtime is built on **LangGraph 0.4+** with a
hierarchical **supervisor + 5 cluster subgraphs** topology, full **HITL
interrupt/resume** persistence on PostgreSQL, an immutable **dual-write audit
trail** to PG (sync) + NATS JetStream (async with outbox retry), and a
**replay tool** for deterministic re-execution from checkpoint + audit log.

Phase 4 does **not** implement individual agent business logic (deferred to
Phase 6-9), does not build the Qdrant retrieval pipeline (Phase 5), and does
not ship the operator UI (Phase 10-11). It ships the contracts every Phase 5+
plan can plug into without further scaffolding.

For the HITL cycle (interrupt → approval queue → resume → audit), see
[HITL Cycle](./hitl-cycle.md). For the provider-agnostic LLM adapter, see
[LLM Serving](./llm-serving.md).

---

## Cluster Structure (D-53)

The supervisor routes intents to **5 cluster subgraphs** with 16 placeholder
child agents (matching the Phase 1 monorepo scaffold). Per **decision D-53**
the original ROADMAP 4-cluster plan is split: Knowledge becomes two clusters
with orthogonal SLAs (editorial vs. pedagogical).

| Cluster | Agents | Slugs | Typical SLA |
| --- | ---: | --- | --- |
| **Ops** | 4 | operator-assistant, production-planner, quality-inspector, anomaly-detector | strict, real-time |
| **Maintenance** | 4 | predictive-maintenance, rca-specialist, maintenance-coach, downtime-analyzer | medium, hours-to-days |
| **Knowledge-Curation** | 2 | knowledge-curator, documentation-synthesizer | hours, HITL-driven |
| **Knowledge-Training** | 2 | training-coach, shift-handover | loose, mostly read-only |
| **Supply** | 4 | inventory-manager, energy-optimizer, cost-analyzer, demand-forecaster | loose, batch-oriented |

Total: **16 placeholder child nodes** wired into 5 cluster subgraphs through
`build_supervisor_graph(checkpointer, router)` in
`packages/sft-agents/src/sft_agents/runtime/supervisor.py`.

---

## Supervisor Routing (D-54)

Routing is a **2-stage hybrid** to balance latency and ambiguity tolerance:

1. **Stage 1 — rules (<10ms).** Pattern-match the intent string against
   per-cluster keyword + regex sets in
   `packages/sft-agents/src/sft_agents/policies/routing.yaml`. If exactly one
   cluster matches, route directly with `strategy='rules'` and `confidence=1.0`.
2. **Stage 2 — LLM fallback (~500ms-2s).** When 0 or ≥2 clusters match,
   invoke the LLM classifier with `with_structured_output(RoutingDecision)`
   and 4-shot examples. If `confidence < 0.7`, fall back to the default
   `ops` cluster (`strategy='fallback_default_ops'`).

`HybridRouter.__init__` validates that the routing.yaml clusters match the
authoritative `VALID_CLUSTERS` frozenset — drift detection is mechanical so
silent config corruption surfaces at boot.

Every routing decision emits a Langfuse `supervisor.route` span with strategy
+ confidence so post-hoc analytics can track hit-rate per strategy.

---

## PostgreSQL Checkpointer (CORE-04)

Short-term memory is the **LangGraph state checkpoint** persisted to
PostgreSQL via `langgraph-checkpoint-postgres>=3.1` (psycopg3 driver — _not_
asyncpg; do not add `statement_cache_size=0`). The convention for
`thread_id` is `{cluster}.{agent_id}.{session_uuid}` (D-59):

```
ops.operator-assistant.7c3a1c2e-...   # Ops cluster
maintenance.rca-specialist.4f12...    # Maintenance cluster
```

`get_postgres_checkpointer(dsn)` is an `async with` context manager around
`AsyncPostgresSaver.from_conn_string(dsn)`. The `scripts/langgraph-init.py`
script (idempotent) creates the `public.checkpoint*` tables on first run.

**Success criterion #4 of Phase 4:** a paused HITL approval survives a
`docker compose restart` — covered by the e2e test in Plan 04-07.

---

## LLM Adapter (CORE-05, CORE-06)

The LLM provider is selected by a single environment variable:

| Variable | Default | Values |
| --- | --- | --- |
| `LLM_BACKEND` | `ollama` | `ollama` \| `vllm` |

- **Ollama (dev)** — `langchain-ollama` against `qwen2.5:7b-instruct-q4_K_M`
  on `OLLAMA_HOST=http://localhost:11434`.
- **vLLM (prod)** — `langchain-openai` against `Qwen2.5-14B-Instruct-AWQ` via
  the OpenAI-compatible `/v1` endpoint on `VLLM_BASE_URL`.

Both providers wrap into a `BudgetingChatModel` middleware that updates
`BudgetSnapshot` per call and writes the cumulative state to
`budget.executions`. Langfuse v3 tracing is enabled when `LANGFUSE_HOST`,
`LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY` are all set; otherwise the
callback is a no-op.

Full configuration matrix lives in [LLM Serving](./llm-serving.md).

---

## Tool Registry (CORE-07)

Every tool exposed to the LLM is a `langchain_core.tools.BaseTool` subclass
with a Pydantic v2 `args_schema`. The supervisor calls
`tools_to_openai_schema(tool_registry)` once at boot to produce the
OpenAI-function-calling JSON schema attached to LLM calls (works for both
Ollama function-calling and vLLM Hermes mode).

Phase 4 ships the registry plumbing + re-exports of the Phase 3
`sft-tools` package (ReplayCMAPSSTool, ReplayUCITool, QueryTimescaleTool).
Per-agent tool sets are scaffolded in `apps/agents/<cluster>/<agent>/tools.py`
but the implementations are deferred to Phase 6-9.

---

## Memory Layers (D-59)

| Layer | Phase 4 | Phase 5+ | Storage |
| --- | --- | --- | --- |
| Short-term | LangGraph state via PG checkpointer | unchanged | `public.checkpoint*` |
| Episodic | `EpisodicReplay` reads `audit.actions` | unchanged | `audit.actions` (TimescaleDB hypertable, 30d chunks) |
| Long-term | `StubLongTermMemory` returns `[]` | `QdrantLongTermMemory` (BGE-M3 + Qdrant) | Phase 5 |

`EpisodicReplay.replay_thread(thread_id, since=None)` returns an ordered
`list[AuditRecord]` projected from `audit.actions`, bounded at `LIMIT 1000`
per call. It implements the `Memory` ABC but `store()` raises
`NotImplementedError` — episodic memory is a read-only projection of the
immutable audit log; new episodes are created by `AuditWriter`.

The long-term `StubLongTermMemory` is a contract anchor: Phase 5 swaps its
module body with `QdrantLongTermMemory` having identical method signatures
(`query` / `store`) so no downstream Plan needs an import-path change.

---

## Audit Dual-Write (D-56)

Every AI decision writes an `AuditRecord` (EvidencePanel + decision +
motivation + approval_id + budget_snapshot) to **both** PG and NATS:

1. **PG INSERT** into `audit.actions` is **synchronous** and **blocking**.
   On failure the agent aborts — there is _no_ NATS-only audit
   (T-04-Audit-Tamper mitigation: never write a fake audit).
2. **NATS publish** on `audit.actions.<cluster>.<agent_id>` is async and
   fire-and-forget. On failure the row is enqueued in `audit.outbox` and
   replayed later by `OutboxRetry` with exponential backoff (2s..3600s cap).

PG is the source of truth (7-year retention via TimescaleDB partitioning).
NATS is the telemetry replica (90-day retention on `AUDIT_STREAM`).

DB-layer immutability: `REVOKE UPDATE, DELETE ON audit.actions FROM
agent_role` survives accidental future GRANTs. A CHECK constraint enforces
HITL-07 mechanically:

```sql
CHECK (
  (decision NOT LIKE 'hitl_%')
  OR (motivation IS NOT NULL AND char_length(motivation) > 0
      AND approval_id IS NOT NULL)
)
```

The Pydantic `AuditRecord` validates the same rule at the SDK boundary —
defense in depth.

---

## Budget Tracker (D-60)

`BudgetTracker` is a LangGraph middleware node that runs **before** every
LLM call (via `BudgetingChatModel`) and **before** every `ToolNode`. It
maintains `BudgetSnapshot` in `state['budget']` and UPSERTs into
`budget.executions` keyed by `(thread_id, agent_id)`.

Thresholds (D-60):

- `tokens_total > 0.8 * limit_tokens` (soft) → Operator approval
- `cost_usd_simulated > limit_cost_usd` (hard) → Supervisor approval
- `duration_ms > limit_duration_s * 1000` → Operator approval

Limits are configured per cluster + per agent override in
`packages/sft-agents/src/sft_agents/policies/budgets.yaml`. Phase 4 cost is
**simulated** (no real $$/token mapping); Phase 11 wires real pricing.

Langfuse v3 tracks the same metrics independently for analytics; the
BudgetTracker enforces, Langfuse observes.

---

## Replay (CORE-10, HITL-08)

`replay_thread(thread_id, ..., action_id=None, write_audit=False)` in
`packages/sft-agents/src/sft_agents/replay/from_checkpoint.py` re-executes
the agent loop from the audit log:

- **Tool calls are deterministic** — replayed from the recorded
  `evidence_panel.tool_calls`; no real tool execution.
- **LLM calls are best-effort** — with `fake_llm` given, the prompt_hash is
  recomputed (canonical sha256 of `input_summary` + `tool_calls`) and
  compared to the recorded value. Divergence flags the first step where
  re-execution would differ (forensic signal for T-04-LLM-Inject).
- **`action_id` truncation** — replay stops AFTER the matching recorded
  action (inclusive), enabling "rewind to before X" flows (HITL-08).
- **`write_audit=True`** — emits new `audit.actions` rows with
  `action_type='REPLAY:<original>'` + `input_summary='[REPLAY of <id>] ...'`
  so auditors can filter replay-written rows trivially (T-04-Audit-Tamper).

Phase 4 ships **best-effort determinism** (Pitfall §5). Full determinism
with frozen tool outputs end-to-end is deferred to Phase 11.

---

## Cross-references

- [HITL Cycle](./hitl-cycle.md) — interrupt → approval → resume cycle, escalation, safety interlock, governor
- [LLM Serving](./llm-serving.md) — Ollama + vLLM adapter, env-var matrix, Langfuse callback
- [Architecture Overview](./overview.md) — full system C4 diagrams
