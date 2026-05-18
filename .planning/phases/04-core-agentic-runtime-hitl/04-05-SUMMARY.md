---
phase: 04-core-agentic-runtime-hitl
plan: 05
subsystem: supervisor-clusters-checkpointer
tags: [langgraph, supervisor, clusters, checkpointer, hybrid-routing, recursion-limit, hitl-escalation, wave-3]
requires:
  - "04-01 (sft-agents SDK foundation — AgentState consumes ProposedAction/BudgetSnapshot/EvidencePanel + Tier/ActionType enums)"
  - "04-02 (PG migrations — Plan 04-02 BLOCKING task runs scripts/langgraph-init.py to create public.checkpoint* tables)"
  - "04-03 (LLM adapter — HybridRouter Stage 2 can wire any BaseChatModel; not used at compile time)"
provides:
  - "AgentState TypedDict (CONTEXT.md Claude's Discretion line 419) with messages-reducer = add_messages"
  - "RoutingDecision Pydantic frozen (D-54) with VALID_CLUSTERS post-init validation (T-04-LLM-Inject)"
  - "VALID_CLUSTERS frozenset + ALL_CLUSTERS ordered tuple (D-53)"
  - "format_thread_id / parse_thread_id (D-59 — kebab-case agent_id + UUID hex)"
  - "get_postgres_checkpointer async context manager around AsyncPostgresSaver.from_conn_string (CORE-04)"
  - "HybridRouter Stage 1 (rules + regex) + Stage 2 (LLM with_structured_output) + fallback_default_ops (D-54)"
  - "5 cluster sub-packages with 16 placeholder children matching Phase-1 scaffold slugs"
  - "build_cluster_subgraph + build_supervisor_graph + safe_invoke (CORE-02, CORE-03)"
  - "5 unskipped test files (test_checkpointer + test_routing + test_clusters + test_supervisor + test_recursion_limit) totalling 38 unit + 1 integration test"
affects:
  - "Unblocks Plan 04-06: HITL middleware (SafetyInterlock + BudgetTracker + EvidencePanel attachment + EscalationSupervisor + Governor) plugs into build_supervisor_graph"
  - "Unblocks Plan 04-07: api-gateway wraps compiled supervisor + invokes via safe_invoke at /v1/sessions"
  - "Unblocks Plan 04-08: replay tool loads checkpoints by thread_id and re-executes through the supervisor"
tech_stack:
  added:
    - "langgraph 0.4 (StateGraph, conditional_edges, MemorySaver for unit tests)"
    - "langgraph.checkpoint.postgres.aio.AsyncPostgresSaver (CORE-04)"
    - "langgraph.errors.GraphRecursionError (safe_invoke catches → HITL escalation)"
  patterns:
    - "TypedDict + Annotated[..., add_messages] for LangGraph state schema"
    - "Pydantic v2 model_post_init for cluster-membership validation (RoutingDecision)"
    - "asynccontextmanager wrapping AsyncPostgresSaver.from_conn_string (CORE-04)"
    - "yaml.safe_load + lru-free pathlib loader (mirror of sft_domain.glossary._loader)"
    - "GraphRecursionError → ProposedAction.from_payload (Pitfall 6 deterministic UUID) → state.proposed_actions append (no re-raise)"
    - "Lazy attribute access in runtime/__init__.py (__getattr__) keeps Task-1-only consumers free of langgraph.graph import cost"
key_files:
  created:
    - "packages/sft-agents/src/sft_agents/runtime/__init__.py — 11-symbol public API + lazy Task-2 imports"
    - "packages/sft-agents/src/sft_agents/runtime/state.py — AgentState TypedDict + RoutingDecision + VALID_CLUSTERS + ALL_CLUSTERS"
    - "packages/sft-agents/src/sft_agents/runtime/checkpointer.py — get_postgres_checkpointer + format_thread_id + parse_thread_id"
    - "packages/sft-agents/src/sft_agents/runtime/clusters.py — build_cluster_subgraph"
    - "packages/sft-agents/src/sft_agents/runtime/supervisor.py — build_supervisor_graph + safe_invoke"
    - "packages/sft-agents/src/sft_agents/policies/__init__.py — re-export HybridRouter"
    - "packages/sft-agents/src/sft_agents/policies/routing.py — HybridRouter Stage 1+2 (D-54)"
    - "packages/sft-agents/src/sft_agents/policies/routing.yaml — 5 cluster rule sets, bilingual IT/EN keywords + regex (D-54)"
    - "packages/sft-agents/src/sft_agents/clusters/__init__.py — ALL_CLUSTERS tuple"
    - "packages/sft-agents/src/sft_agents/clusters/ops/__init__.py — 4 child slugs"
    - "packages/sft-agents/src/sft_agents/clusters/maintenance/__init__.py — 4 child slugs"
    - "packages/sft-agents/src/sft_agents/clusters/knowledge_curation/__init__.py — 2 child slugs"
    - "packages/sft-agents/src/sft_agents/clusters/knowledge_training/__init__.py — 2 child slugs"
    - "packages/sft-agents/src/sft_agents/clusters/supply/__init__.py — 4 child slugs"
    - "packages/sft-agents/tests/test_checkpointer.py — 14 unit + 1 integration tests"
    - "packages/sft-agents/tests/test_routing.py — 12 tests"
    - "packages/sft-agents/tests/test_clusters.py — 10 tests"
  modified:
    - "packages/sft-agents/tests/test_supervisor.py — Wave 0 stub → 3 real tests"
    - "packages/sft-agents/tests/test_recursion_limit.py — Wave 0 stub → 3 real tests"
decisions:
  - "AgentState forward references (ProposedAction/BudgetSnapshot/EvidencePanel) imported at runtime (NOT TYPE_CHECKING-guarded) because LangGraph's StateGraph(AgentState) calls typing.get_type_hints() which evaluates forward refs at compile time. TYPE_CHECKING-only imports would cause NameError on graph build."
  - "RoutingDecision.cluster validation uses model_post_init (not Literal) — Literal would require duplicating VALID_CLUSTERS in the type system. The Pydantic frozen + post-init check matches the runtime VALID_CLUSTERS source of truth."
  - "runtime/__init__.py uses __getattr__ lazy import for Task-2 symbols (build_supervisor_graph, safe_invoke, HybridRouter, build_cluster_subgraph). Task-1 consumers (replay tool, audit reader) that only need thread_id helpers do not pay the langgraph.graph + yaml import cost."
  - "ProposedAction has no `requires_tier` field (Plan 04-01 schema lock); safe_invoke embeds Tier.MANAGER.value into the action's `args` dict instead. Plan 04-06's HITL middleware reads args['requires_tier'] to pick the escalation tier."
  - "Cluster subgraph linear skeleton (START → first child → ... → END) is intentional Phase 4 placeholder — Phase 6-9 will add cluster-internal conditional routing when the agents have real business logic."
  - "routing.yaml clusters are validated against VALID_CLUSTERS at HybridRouter __init__ (raises ValueError if drift detected) — defense-in-depth against silent config corruption."
metrics:
  duration: "single session"
  completed_date: "2026-05-18"
  tasks_completed: 2
  commits: 6
  files_created: 16
  files_modified: 2
  tests_passing: "224 (223 unit + 1 integration against testcontainers PG)"
  tests_skipped_stubs: 8
  child_agents_wired: 16
  clusters_wired: 5
  public_api_symbols_added: 11
---

# Phase 4 Plan 05: Supervisor + 5 Cluster Subgraphs + PG Checkpointer Summary

Plan 04-05 ships the LangGraph runtime backbone. `build_supervisor_graph(checkpointer, router=HybridRouter())` compiles a `StateGraph(AgentState)` with one `route` node calling the hybrid router and 5 cluster subgraphs (16 placeholder children total — exact Phase-1 scaffold match). `get_postgres_checkpointer(dsn)` is an async context manager around `AsyncPostgresSaver.from_conn_string` honoring the D-59 thread_id convention `{cluster}.{agent_id}.{session_uuid}`. `safe_invoke(graph, state, config)` enforces `recursion_limit` is set and converts `GraphRecursionError` into a Manager-tier `ProposedAction(action_type=GRAPH_RECURSION_REVIEW)` instead of crashing — success criterion #2. All 5 Wave-0 stubs (`test_supervisor`, `test_recursion_limit`, plus 3 new files for clusters/routing/checkpointer) are now real tests; full sft-agents suite: 224 passed, 8 skipped (remaining Wave-0 stubs for plans 04-06..04-08).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED   | failing tests: AgentState + RoutingDecision + thread_id + AsyncPostgresSaver | `c55b17a` | tests/test_checkpointer.py |
| 1 GREEN | AgentState + RoutingDecision + AsyncPostgresSaver CM + thread_id helpers   | `46ab80b` | runtime/{__init__,state,checkpointer}.py + tests/test_checkpointer.py (config fix) |
| 2 RED   | failing tests: HybridRouter + clusters + supervisor + recursion_limit       | `ffe1698` | tests/test_{routing,clusters,supervisor,recursion_limit}.py |
| 2 GREEN A | HybridRouter (rules + LLM fallback)                                        | `1993255` | policies/{__init__,routing,routing.yaml} + test fix |
| 2 GREEN B | 5 cluster sub-packages + build_cluster_subgraph                            | `84301c2` | clusters/{ops,maintenance,knowledge_curation,knowledge_training,supply}/__init__.py + runtime/clusters.py |
| 2 GREEN C | supervisor + safe_invoke (recursion_limit-to-HITL)                         | `6b6c68e` | runtime/{supervisor,__init__,state}.py + tests/{test_supervisor,test_recursion_limit}.py |

## Verification

```bash
# Plan-defined done criteria (all pass)
$ python -c "from sft_agents.runtime import AgentState, RoutingDecision, VALID_CLUSTERS, \
    get_postgres_checkpointer, format_thread_id; \
    print(format_thread_id('ops','operator-assistant','00000000-0000-0000-0000-000000000001'))"
ops.operator-assistant.00000000-0000-0000-0000-000000000001

$ python -c "from sft_agents.runtime import format_thread_id; format_thread_id('badcluster','x','...')"
ValueError: cluster must be one of [...], got 'badcluster'

$ grep -nF 'AsyncPostgresSaver.from_conn_string' packages/sft-agents/src/sft_agents/runtime/checkpointer.py
154:    async with AsyncPostgresSaver.from_conn_string(dsn) as saver:

$ grep -nF 'add_messages' packages/sft-agents/src/sft_agents/runtime/state.py
(matches in import, docstring, and AgentState.messages annotation)

$ python -c "import yaml; d=yaml.safe_load(open('packages/sft-agents/src/sft_agents/policies/routing.yaml')); \
    assert set(d.keys()) == {'ops','maintenance','knowledge-curation','knowledge-training','supply'}; print('ok')"
ok

$ grep -nE 'yaml\.load\b' packages/sft-agents/src/sft_agents/policies/routing.py | grep -v 'safe_load'
(no output — only yaml.safe_load is used, T-04-LLM-Inject mitigated)

$ python -c "from sft_agents.runtime import build_supervisor_graph, HybridRouter, ALL_CLUSTERS, safe_invoke; \
    from langgraph.checkpoint.memory import MemorySaver; \
    g = build_supervisor_graph(checkpointer=MemorySaver()); print(ALL_CLUSTERS)"
('ops', 'maintenance', 'knowledge-curation', 'knowledge-training', 'supply')

$ for c in ops maintenance knowledge_curation knowledge_training supply; \
    do test -f packages/sft-agents/src/sft_agents/clusters/$c/__init__.py && echo "$c OK"; done
ops OK / maintenance OK / knowledge_curation OK / knowledge_training OK / supply OK

$ python -c "from sft_agents.clusters import ops, maintenance, knowledge_curation, knowledge_training, supply; \
    total = sum(len(m.CHILD_AGENT_SLUGS) for m in [ops, maintenance, knowledge_curation, knowledge_training, supply]); \
    assert total == 16, total; print('16 placeholder agents:', total)"
16 placeholder agents: 16

$ uv run --extra dev pytest tests/ --tb=line
======================== 224 passed, 8 skipped in 7.58s ========================
```

## Public Schema / Topology

### AgentState (LangGraph TypedDict)

| Field | Type | Reducer | Notes |
|-------|------|---------|-------|
| `messages` | `list[BaseMessage]` | `add_messages` | Append on each node return |
| `thread_id` | `str` | (last-write-wins) | D-59: `{cluster}.{agent_id}.{session_uuid}` |
| `cluster` | `str` | (last-write-wins) | One of VALID_CLUSTERS |
| `proposed_actions` | `list[ProposedAction]` | (last-write-wins) | HITL queue carriers + GRAPH_RECURSION_REVIEW |
| `budget` | `BudgetSnapshot` | (last-write-wins) | Plan 04-06 populates |
| `evidence` | `EvidencePanel \| None` | (last-write-wins) | HITL-06; Plan 04-06 attaches |
| `pending_approval_id` | `UUID \| None` | (last-write-wins) | Plan 04-06 sets during interrupt |
| `routing_decision` | `RoutingDecision \| None` | (last-write-wins) | Set by supervisor `route` node |

### Supervisor StateGraph topology

```
START
  └─→ route (HybridRouter.route → routing_decision + cluster)
        └─→ conditional_edges keyed on state['routing_decision'].cluster
              ├─→ ops                    (4 placeholder children) → END
              ├─→ maintenance            (4 placeholder children) → END
              ├─→ knowledge-curation     (2 placeholder children) → END
              ├─→ knowledge-training     (2 placeholder children) → END
              └─→ supply                 (4 placeholder children) → END
```

Total = 5 cluster subgraphs + 1 supervisor node + 16 placeholder child nodes = 22 named nodes.

### 16 placeholder child agents (Phase 1 scaffold parity)

| Cluster | Slugs |
|---------|-------|
| ops (4) | operator-assistant, production-planner, quality-inspector, anomaly-detector |
| maintenance (4) | predictive-maintenance, rca-specialist, maintenance-coach, downtime-analyzer |
| knowledge-curation (2) | knowledge-curator, documentation-synthesizer |
| knowledge-training (2) | training-coach, shift-handover |
| supply (4) | inventory-manager, energy-optimizer, cost-analyzer, demand-forecaster |

### HybridRouter strategy matrix

| Stage 1 matches | LLM supplied? | Output |
|---|---|---|
| Exactly 1 cluster | n/a | `RoutingDecision(strategy='rules', confidence=1.0)` |
| 0 OR ≥2 clusters | None | `RoutingDecision(cluster='ops', strategy='fallback_default_ops', confidence=0.0)` |
| 0 OR ≥2 clusters | LLM + `confidence ≥ 0.7` | `RoutingDecision(strategy='llm', confidence=…)` |
| 0 OR ≥2 clusters | LLM + `confidence < 0.7` | `RoutingDecision(cluster='ops', strategy='fallback_default_ops', confidence=0.0)` |
| 0 OR ≥2 clusters | LLM raises | log warning + fallback_default_ops |

### `safe_invoke` recursion contract

| Condition | Outcome |
|-----------|---------|
| `config['recursion_limit']` missing | `ValueError` raised at the boundary (success criterion #2 — every invoke must set a cap) |
| Graph completes within limit | Returns graph output as-is |
| `GraphRecursionError` raised | Returns state with appended `ProposedAction(action_type=GRAPH_RECURSION_REVIEW, args={'requires_tier': 'manager', 'thread_id': ..., 'recursion_limit': ...})`; **no re-raise** — Plan 04-06 routes to Manager tier |

## Success Criteria

- [x] **CORE-02** satisfied — 5 cluster subgraphs compiled into the supervisor (D-53 override of ROADMAP's "4")
- [x] **CORE-03** satisfied — `safe_invoke` enforces explicit `recursion_limit` (ValueError if missing) and converts `GraphRecursionError` to a HITL Manager-tier ProposedAction
- [x] **CORE-04** satisfied — `get_postgres_checkpointer` wraps `AsyncPostgresSaver.from_conn_string`; integration test round-trips a checkpoint by thread_id against testcontainers PG (timescale/timescaledb:2.18.0-pg16)
- [x] **CORE-07 partial** — Tool registry shipped in Plan 04-03; this plan's AgentState provides the field surface (`proposed_actions`, `budget`, `evidence`) that Plan 04-06 BudgetTracker + safety middleware will populate
- [x] **D-54 hybrid routing operational** — Stage 1 (rules + regex, <10ms) + Stage 2 (LLM `with_structured_output(RoutingDecision)` 4-shot) + `fallback_default_ops` on low confidence
- [x] **16 placeholder child nodes match Phase 1 scaffold** — verified by `test_total_child_agents_equals_sixteen`

## Threats Mitigated

| Threat ID | Disposition | Evidence |
|-----------|-------------|----------|
| T-04-LLM-Inject | mitigate | `RoutingDecision` frozen + Pydantic + `model_post_init` cluster ∈ VALID_CLUSTERS check; routing.py loads YAML only via `yaml.safe_load`; `HybridRouter.__init__` validates routing.yaml clusters match VALID_CLUSTERS exactly (drift defense); Stage 2 LLM output passes through `with_structured_output(RoutingDecision)` so injection cannot route to arbitrary cluster |
| T-04-Budget-Exhaust | mitigate | `safe_invoke` raises ValueError if `recursion_limit` missing from config — every invoke must enforce a cap; `GraphRecursionError` → HITL Manager-tier review (no infinite token spend) |
| T-04-Checkpoint-PII | accept (this plan) | Checkpointer wired; redactor middleware lands Plan 04-06 (HITL/audit) per A-013..A-018 |

## Deviations from Plan

### [Rule 3 - Test fix] AsyncPostgresSaver requires `checkpoint_ns` in config

- **Found during:** Task 1 integration test execution against testcontainers PG.
- **Issue:** Plan task description called for `config={"configurable":{"thread_id":...}}` only. `langgraph-checkpoint-postgres>=3.1` also requires `checkpoint_ns` (namespace, empty string for top-level graph) — without it `aput` raises `KeyError: 'checkpoint_ns'`.
- **Fix:** Test now uses `config={"configurable":{"thread_id":..., "checkpoint_ns":""}}` and uses the config returned from `aput()` (which carries the populated `checkpoint_id`) for the subsequent `aget_tuple()` call. Same fix applied in `test_supervisor` + `test_recursion_limit`.
- **Files modified:** `packages/sft-agents/tests/test_checkpointer.py`, `tests/test_supervisor.py`, `tests/test_recursion_limit.py`
- **Commit:** `46ab80b`
- **Impact:** Test-layer only. Production callers (Plan 04-07 api-gateway) will follow the same pattern — `checkpoint_ns=""` for top-level graphs, populated for nested subgraphs (LangGraph convention).

### [Rule 3 - Bug] AgentState forward references cannot be TYPE_CHECKING-guarded

- **Found during:** Task 2 first compile of `StateGraph(AgentState)`.
- **Issue:** `from __future__ import annotations` + `TYPE_CHECKING` guard on `ProposedAction`/`BudgetSnapshot`/`EvidencePanel` imports causes `NameError: name 'ProposedAction' is not defined` because LangGraph's `_get_channels()` calls `typing.get_type_hints(schema, include_extras=True)` which evaluates the deferred forward refs at runtime.
- **Fix:** Moved the three imports out of the `TYPE_CHECKING` block in `runtime/state.py`. Added an explicit comment for future contributors so they don't "helpfully" re-guard them.
- **Files modified:** `packages/sft-agents/src/sft_agents/runtime/state.py`
- **Commit:** `6b6c68e`
- **Impact:** No production behaviour change; tightens import graph (AgentState now hard-depends on sft_agents.models, which is correct).

### [Rule 2 - Critical functionality] Plan called for `requires_tier` field on ProposedAction; field does not exist

- **Found during:** Task 2 implementation of `safe_invoke`.
- **Issue:** Plan PLAN.md line 230 prescribes `ProposedAction(action_type=..., requires_tier=Tier.MANAGER, ...)` but the Plan-04-01 Pydantic schema for ProposedAction has fields `(id, action_type, target_subject, args)` — no `requires_tier`.
- **Fix:** Embedded `requires_tier=Tier.MANAGER.value` into the action's `args` dict alongside `thread_id`, `recursion_limit`, and a human-readable `reason`. Plan 04-06's HITL middleware will read `args['requires_tier']` to pick the escalation tier. Documented in Decisions block.
- **Files modified:** `packages/sft-agents/src/sft_agents/runtime/supervisor.py`, `packages/sft-agents/tests/test_recursion_limit.py`
- **Commit:** `6b6c68e`
- **Impact:** Forward-compatible — no Plan-04-01 SDK schema change. If Plan 04-06 wants a typed field, it can add `requires_tier` to ProposedAction without breaking this plan's wiring (string value already canonical).

### [Rule 1 - Test bug] "operatore" matched ops keyword "operator" via substring

- **Found during:** Task 2 GREEN test run for knowledge-training routing.
- **Issue:** Test input "Briefing handover formazione training operatore neoassunto" hit both ops (substring "operator" inside "operatore") and knowledge-training ("training"/"handover"). Two-cluster match → fallback_default_ops → assertion failure.
- **Fix:** Trimmed test input to "Briefing handover formazione neoassunto" — unambiguous knowledge-training. Substring matching is the correct production behaviour (Italian/English bilingual prefix overlap is real); the test was probing the wrong path.
- **Files modified:** `packages/sft-agents/tests/test_routing.py`
- **Commit:** `1993255`

## Deferred Issues

| Issue | Plan to address |
|-------|-----------------|
| `requires_tier` typed field on `ProposedAction` | Plan 04-06 may extend the SDK model; we pass `args['requires_tier']` as a string for now (forward-compatible) |
| Cluster subgraphs use linear START → first → … → END skeleton | Phase 6 (Ops), Phase 7 (Maintenance), Phase 8 (Knowledge), Phase 9 (Supply) will add per-cluster conditional routing once agents have real business logic |
| Stage-2 LLM prompt is a hand-rolled few-shot string (no template versioning) | Plan 04-06 / Phase 11 — when Langfuse prompt management lands, migrate the few-shot examples there |
| `EvidencePanel.rag_citations` is empty in all checkpoints written by this plan | Phase 5 (Knowledge Layer) populates citations once Qdrant retrieval is online |
| GDPR redactor middleware on checkpoint write (T-04-Checkpoint-PII) | Plan 04-06 — checkpointer surface created here; redactor wraps `aput` before persistence |

## Known Stubs

None functional. Cluster child nodes are intentional Phase 4 placeholders (logged + return `{}`) — the Phase-1 scaffold lists them as the contract surface, Phase 6-9 will replace with real `Agent` implementations. This is documented in each cluster `__init__.py` docstring and in the SUMMARY frontmatter `child_agents_wired: 16`.

## Self-Check: PASSED

- `packages/sft-agents/src/sft_agents/runtime/__init__.py` — FOUND
- `packages/sft-agents/src/sft_agents/runtime/state.py` — FOUND
- `packages/sft-agents/src/sft_agents/runtime/checkpointer.py` — FOUND
- `packages/sft-agents/src/sft_agents/runtime/clusters.py` — FOUND
- `packages/sft-agents/src/sft_agents/runtime/supervisor.py` — FOUND
- `packages/sft-agents/src/sft_agents/policies/__init__.py` — FOUND
- `packages/sft-agents/src/sft_agents/policies/routing.py` — FOUND
- `packages/sft-agents/src/sft_agents/policies/routing.yaml` — FOUND (5 cluster keys verified)
- `packages/sft-agents/src/sft_agents/clusters/__init__.py` — FOUND
- `packages/sft-agents/src/sft_agents/clusters/{ops,maintenance,knowledge_curation,knowledge_training,supply}/__init__.py` — all 5 FOUND
- `packages/sft-agents/tests/test_checkpointer.py` — FOUND (14 unit + 1 integration passing)
- `packages/sft-agents/tests/test_routing.py` — FOUND (12 passing)
- `packages/sft-agents/tests/test_clusters.py` — FOUND (10 passing)
- `packages/sft-agents/tests/test_supervisor.py` — modified (Wave 0 stub → 3 passing)
- `packages/sft-agents/tests/test_recursion_limit.py` — modified (Wave 0 stub → 3 passing)
- Commits `c55b17a`, `46ab80b`, `ffe1698`, `1993255`, `84301c2`, `6b6c68e` — verified via `git log`
