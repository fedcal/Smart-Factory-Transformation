---
phase: 04-core-agentic-runtime-hitl
plan: 05
type: execute
wave: 3
depends_on: ["04-01", "04-02", "04-03"]
files_modified:
  - packages/sft-agents/src/sft_agents/runtime/__init__.py
  - packages/sft-agents/src/sft_agents/runtime/state.py
  - packages/sft-agents/src/sft_agents/runtime/checkpointer.py
  - packages/sft-agents/src/sft_agents/runtime/supervisor.py
  - packages/sft-agents/src/sft_agents/runtime/clusters.py
  - packages/sft-agents/src/sft_agents/policies/__init__.py
  - packages/sft-agents/src/sft_agents/policies/routing.py
  - packages/sft-agents/src/sft_agents/policies/routing.yaml
  - packages/sft-agents/src/sft_agents/clusters/__init__.py
  - packages/sft-agents/src/sft_agents/clusters/ops/__init__.py
  - packages/sft-agents/src/sft_agents/clusters/maintenance/__init__.py
  - packages/sft-agents/src/sft_agents/clusters/knowledge_curation/__init__.py
  - packages/sft-agents/src/sft_agents/clusters/knowledge_training/__init__.py
  - packages/sft-agents/src/sft_agents/clusters/supply/__init__.py
  - packages/sft-agents/tests/test_supervisor.py
  - packages/sft-agents/tests/test_clusters.py
  - packages/sft-agents/tests/test_checkpointer.py
  - packages/sft-agents/tests/test_recursion_limit.py
  - packages/sft-agents/tests/test_routing.py
autonomous: true
requirements: [CORE-02, CORE-03, CORE-04, CORE-07]
threat_refs: [T-04-LLM-Inject, T-04-Checkpoint-PII, T-04-Budget-Exhaust]

must_haves:
  truths:
    - "LangGraph supervisor StateGraph compiles with 5 cluster subgraph nodes: ops, maintenance, knowledge-curation, knowledge-training, supply (D-53)"
    - "Each cluster subgraph contains placeholder child nodes matching the 16 Phase 1 agent slugs (no business logic — Phase 6-9 fills)"
    - "HybridRouter Stage 1 rules in routing.yaml deterministically routes pure-keyword inputs (<10ms); Stage 2 LLM classifier handles ambiguity with confidence threshold 0.7 default ops fallback (D-54)"
    - "AsyncPostgresSaver wires from TIMESCALE_DSN; thread_id convention is `{cluster}.{agent_id}.{session_uuid}` (D-59)"
    - "Every `graph.ainvoke(..., config={'recursion_limit': N, ...})` enforces recursion_limit; exceeding it does NOT crash — instead the supervisor emits a ProposedAction with action_type=GRAPH_RECURSION_REVIEW that escalates to HITL Manager tier (success criterion #2)"
    - "AgentState TypedDict matches CONTEXT.md Claude's Discretion shape (messages, thread_id, cluster, proposed_actions, budget, evidence, pending_approval_id)"
  artifacts:
    - path: packages/sft-agents/src/sft_agents/runtime/state.py
      provides: "AgentState TypedDict + reducers"
      contains: "class AgentState"
    - path: packages/sft-agents/src/sft_agents/runtime/checkpointer.py
      provides: "get_postgres_checkpointer(dsn) async context manager"
      contains: "AsyncPostgresSaver"
    - path: packages/sft-agents/src/sft_agents/runtime/supervisor.py
      provides: "build_supervisor_graph(checkpointer, router) → compiled StateGraph"
      contains: "def build_supervisor_graph"
    - path: packages/sft-agents/src/sft_agents/runtime/clusters.py
      provides: "build_cluster_subgraph(cluster_name, child_agent_slugs) → compiled subgraph"
      contains: "def build_cluster_subgraph"
    - path: packages/sft-agents/src/sft_agents/policies/routing.py
      provides: "HybridRouter Stage 1 rules + Stage 2 LLM fallback"
      contains: "class HybridRouter"
    - path: packages/sft-agents/src/sft_agents/policies/routing.yaml
      provides: "D-54 keywords/patterns per cluster"
      contains: "ops:"
  key_links:
    - from: packages/sft-agents/src/sft_agents/runtime/supervisor.py
      to: packages/sft-agents/src/sft_agents/clusters/*/
      via: "add_node(cluster_name, build_cluster_subgraph(...).compile())"
      pattern: "add_node"
    - from: packages/sft-agents/src/sft_agents/runtime/supervisor.py
      to: packages/sft-agents/src/sft_agents/policies/routing.py
      via: "supervisor node calls router.route(state)"
      pattern: "HybridRouter|route"
    - from: packages/sft-agents/src/sft_agents/runtime/checkpointer.py
      to: langgraph.checkpoint.postgres.aio.AsyncPostgresSaver
      via: "from_conn_string context manager"
      pattern: "AsyncPostgresSaver"
---

<objective>
Wave 3 Plan A: ship the LangGraph runtime backbone — AgentState TypedDict, AsyncPostgresSaver wiring, supervisor StateGraph with hybrid routing, 5 cluster subgraph builders with 16 placeholder child nodes, and explicit recursion_limit enforcement that escalates to HITL (NOT crash) per success criterion #2.

Purpose: deliver CORE-02 (supervisor + 5 cluster subgraphs per D-53), CORE-03 (recursion_limit with HITL escalation), CORE-04 (PG checkpointer wired for cross-session resume), and CORE-07 partial (tool registry — Plan 04-03 finished, this plan wires it into AgentState).

Output: 7 Python modules in `sft_agents/runtime/` + `sft_agents/policies/` + 5 cluster packages with empty placeholder subgraphs + routing.yaml + 5 unskipped tests covering supervisor compile, cluster wiring, checkpointer round-trip, hybrid routing dispatch, and recursion_limit-to-HITL escalation.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md
@.planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md
@.planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md
@.planning/phases/04-core-agentic-runtime-hitl/04-VALIDATION.md
@packages/sft-tools/src/sft_tools/timescale/query.py
@packages/sft-domain/src/sft_domain/glossary/_loader.py
@services/ot-bridge/src/svc_ot_bridge/timescale_writer.py

<interfaces>
AgentState shape (CONTEXT.md Claude's Discretion line 419):
```
class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str
    cluster: str                                  # one of 5 VALID_CLUSTERS
    proposed_actions: list[ProposedAction]
    budget: BudgetSnapshot
    evidence: EvidencePanel | None
    pending_approval_id: UUID | None
    routing_decision: RoutingDecision | None
```

RoutingDecision (Pydantic frozen):
- cluster: str (one of 5)
- strategy: Literal["rules", "llm", "fallback_default_ops"]
- confidence: float (1.0 for rules, 0..1 for llm)

HybridRouter contract (D-54):
- `__init__(self, llm: BaseChatModel | None = None, routing_yaml_path: Path | None = None)`
- `async def route(self, state: AgentState) -> RoutingDecision`: Stage 1 attempts keyword+regex match across 5 clusters; if exactly 1 match → return rules decision with confidence=1.0; else Stage 2 invokes LLM classifier (if llm given) with 4-shot examples and structured_output schema `RoutingDecision`; if confidence<0.7 → return fallback decision cluster="ops", strategy="fallback_default_ops", confidence=0.0.

AsyncPostgresSaver wiring (CORE-04):
- `async def get_postgres_checkpointer(dsn: str)` returns async context manager yielding `AsyncPostgresSaver` instance ready to attach to `graph.compile(checkpointer=saver)`
- thread_id format: `{cluster}.{agent_id}.{session_uuid}` per D-59

Supervisor StateGraph topology:
- Nodes: `route` (supervisor entry), 5 cluster nodes (compiled subgraphs), `recursion_review` (sink for recursion_limit-exceeded escalation), END
- Edges: START → route; route → conditional_edge keyed on `state["routing_decision"].cluster` → one of 5 cluster nodes; each cluster node → END (Phase 4 has no inter-cluster routing per CONTEXT.md scope_boundaries)
- recursion_limit handling: graph.compile() does NOT take recursion_limit; it's passed at invoke time in config; the supervisor intercepts `GraphRecursionError` at the surrounding caller (api-gateway in Plan 04-07) and emits a ProposedAction routed to HITL Manager tier

Cluster subgraph layout (D-53 + PATTERNS §3.3):
- ops:                  [operator-assistant, production-planner, quality-inspector, anomaly-detector]
- maintenance:          [predictive-maintenance, rca-specialist, maintenance-coach, downtime-analyzer]
- knowledge-curation:   [knowledge-curator, documentation-synthesizer]
- knowledge-training:   [training-coach, shift-handover]
- supply:              [inventory-manager, energy-optimizer, cost-analyzer, demand-forecaster]
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <id>04-05-01</id>
  <name>Task 1: AgentState + AsyncPostgresSaver wiring + checkpointer test</name>
  <files>packages/sft-agents/src/sft_agents/runtime/__init__.py, packages/sft-agents/src/sft_agents/runtime/state.py, packages/sft-agents/src/sft_agents/runtime/checkpointer.py, packages/sft-agents/tests/test_checkpointer.py</files>
  <read_first>
    packages/sft-tools/src/sft_tools/timescale/query.py (asyncpg connect lifecycle lines 108-126)
    services/ot-bridge/src/svc_ot_bridge/timescale_writer.py (pool start/stop lifecycle lines 74-91)
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (Claude's Discretion AgentState shape line 419; D-59 thread_id convention)
    .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md (§3 AsyncPostgresSaver.from_conn_string + setup pattern; Pitfall §2 statement_cache_size=0 and dict_row when passing manual conn)
    packages/sft-agents/src/sft_agents/models/audit.py (Plan 04-01 — RoutingDecision Pydantic v2 frozen template)
  </read_first>
  <behavior>
    - `AgentState` is a TypedDict with all 9 keys; `messages` field is annotated with `add_messages` reducer from langgraph
    - `get_postgres_checkpointer(dsn)` is an async context manager yielding AsyncPostgresSaver
    - Inside the CM, `await saver.aput(...)` and `await saver.aget_tuple(...)` round-trip a checkpoint by thread_id (integration test against testcontainers PG)
    - `format_thread_id(cluster, agent_id, session_uuid)` returns `f"{cluster}.{agent_id}.{session_uuid}"`; cluster must be in VALID_CLUSTERS else ValueError
    - `parse_thread_id(thread_id)` returns tuple `(cluster, agent_id, session_uuid:UUID)`; malformed input raises ValueError
    - `RoutingDecision` Pydantic frozen model with `cluster` (str), `strategy` (Literal), `confidence` (float ge=0 le=1)
  </behavior>
  <action>
    `runtime/state.py`: defines `AgentState(TypedDict, total=False)` with the 9 fields above. `messages` typed as `Annotated[list[BaseMessage], add_messages]` importing `add_messages` from `langgraph.graph.message`. `proposed_actions` defaults to empty list semantically (TypedDict can't have defaults — runtime helpers in supervisor.py populate). Also defines `RoutingDecision(BaseModel)` with `model_config = {"frozen": True, "extra": "forbid"}`, fields cluster:str, strategy:Literal["rules","llm","fallback_default_ops"], confidence:float (ge=0,le=1), matched_keyword:str|None (debug aid for rules strategy). Module constants: `VALID_CLUSTERS = frozenset({"ops","maintenance","knowledge-curation","knowledge-training","supply"})` (mirrors audit/subjects.py).
    `runtime/checkpointer.py`: imports `from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver` and `from contextlib import asynccontextmanager`. `@asynccontextmanager async def get_postgres_checkpointer(dsn: str)`: `async with AsyncPostgresSaver.from_conn_string(dsn) as saver: yield saver`. Optional `await saver.setup()` is called only if env `SFT_LANGGRAPH_AUTO_SETUP=1` (default: scripts/langgraph-init.py was already run by Plan 04-02 [BLOCKING] task). Add structlog log on enter/exit. Add `format_thread_id(cluster: str, agent_id: str, session_uuid: UUID | str) -> str` validating cluster ∈ VALID_CLUSTERS and agent_id matches kebab-case regex `^[a-z0-9-]+$` per the 16 Phase 1 slugs; UUID stringified. Add `parse_thread_id(thread_id: str) -> tuple[str, str, UUID]`: split on `.` (exactly 3 parts after handling kebab-case agent_id that contains no `.`); raise ValueError if malformed.
    `runtime/__init__.py` re-exports `AgentState, RoutingDecision, VALID_CLUSTERS, get_postgres_checkpointer, format_thread_id, parse_thread_id`.
    `tests/test_checkpointer.py` (UPGRADE from W0 stub): `@pytest.mark.integration` test using testcontainers PG (reuse fixture pattern from Plan 04-02). Test 1: format_thread_id happy path returns expected string; invalid cluster raises ValueError; invalid agent_id (contains `.`) raises ValueError. Test 2: parse_thread_id round-trip. Test 3: integration test — bring up testcontainers PG, run `scripts/timescale-migrate.py` + `scripts/langgraph-init.py`, then `async with get_postgres_checkpointer(dsn) as saver`: build minimal `Checkpoint` per langgraph schema (use `langgraph.checkpoint.base.empty_checkpoint()` helper), call `await saver.aput(config={"configurable":{"thread_id":"ops.operator-assistant.<uuid>"}}, checkpoint=ckpt, metadata={}, new_versions={})`, then `await saver.aget_tuple(config={"configurable":{"thread_id":"ops.operator-assistant.<uuid>"}})` returns the checkpoint. Assert round-trip equality on a marker field.

    Conventional commits: (1) `feat(04-05-supervisor-clusters-checkpointer-01): agent state typeddict + routing decision model`, (2) `feat(04-05-supervisor-clusters-checkpointer-01): postgres checkpointer context manager + thread_id helpers + integration test`.
  </action>
  <pattern_ref>packages/sft-tools/src/sft_tools/timescale/query.py:108-126 (DSN + asyncpg connect with statement_cache_size=0; replicated semantic for AsyncPostgresSaver) ; services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:74-91 (pool lifecycle pattern)</pattern_ref>
  <threat_ref>T-04-Checkpoint-PII (checkpoint snapshots embed EvidencePanel; Plan 04-06 will wire GDPR redactor pre-write per A-013..A-018)</threat_ref>
  <verify>
    <automated>nx test sft-agents --testNamePattern=test_checkpointer</automated>
  </verify>
  <done>
    - `python -c "from sft_agents.runtime import AgentState, RoutingDecision, VALID_CLUSTERS, get_postgres_checkpointer, format_thread_id; print(format_thread_id('ops','operator-assistant','00000000-0000-0000-0000-000000000001'))"` outputs `ops.operator-assistant.00000000-0000-0000-0000-000000000001`
    - `python -c "from sft_agents.runtime import format_thread_id; format_thread_id('badcluster','x','...')"` exits non-zero with ValueError
    - `grep -nF 'AsyncPostgresSaver.from_conn_string' packages/sft-agents/src/sft_agents/runtime/checkpointer.py` returns 1 match
    - `nx test sft-agents --testNamePattern=test_checkpointer` exits 0 against testcontainers PG
    - `grep -nF 'add_messages' packages/sft-agents/src/sft_agents/runtime/state.py` returns 1 match
    - AgentState + RoutingDecision + checkpointer context manager + thread_id helpers shipped; integration test green; downstream supervisor builder can use checkpointer.
  </done>
  <commit_scope>feat(04-05-supervisor-clusters-checkpointer)</commit_scope>
</task>

<task type="auto" tdd="true">
  <id>04-05-02</id>
  <name>Task 2: HybridRouter + routing.yaml + supervisor + 5 cluster subgraphs with 16 placeholder children</name>
  <files>packages/sft-agents/src/sft_agents/policies/__init__.py, packages/sft-agents/src/sft_agents/policies/routing.py, packages/sft-agents/src/sft_agents/policies/routing.yaml, packages/sft-agents/src/sft_agents/runtime/supervisor.py, packages/sft-agents/src/sft_agents/runtime/clusters.py, packages/sft-agents/src/sft_agents/clusters/__init__.py, packages/sft-agents/src/sft_agents/clusters/ops/__init__.py, packages/sft-agents/src/sft_agents/clusters/maintenance/__init__.py, packages/sft-agents/src/sft_agents/clusters/knowledge_curation/__init__.py, packages/sft-agents/src/sft_agents/clusters/knowledge_training/__init__.py, packages/sft-agents/src/sft_agents/clusters/supply/__init__.py, packages/sft-agents/tests/test_supervisor.py, packages/sft-agents/tests/test_clusters.py, packages/sft-agents/tests/test_routing.py</files>
  <read_first>
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-53 + D-54 — keywords/patterns table lines 101-110)
    .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md (§2 Supervisor + Subgraph composition; §3.4 hybrid routing)
    .planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md (§3.2 supervisor — no in-repo analog; §3.3 cluster subgraph layout — 16 agent slugs; §4.3 yaml loader pattern)
    packages/sft-domain/src/sft_domain/glossary/_loader.py (yaml.safe_load + pathlib + lru_cache pattern lines 21-80)
    packages/sft-agents/src/sft_agents/runtime/state.py (AgentState + RoutingDecision from Task 1)
    packages/sft-agents/src/sft_agents/llm/factory.py (Plan 04-03 — build_chat_model for Stage 2 LLM classifier)
  </read_first>
  <behavior>
    - `routing.yaml` contains 5 top-level keys (ops, maintenance, knowledge-curation, knowledge-training, supply); each has `keywords:` list and optional `patterns:` list (regex strings) per CONTEXT.md D-54 table
    - `HybridRouter(routing_yaml_path=None, llm=None)` loads routing.yaml via yaml.safe_load (default path: package-relative)
    - `await router.route(state)` Stage 1: token-match input from state.messages[-1].content against keywords + regex patterns per cluster; if exactly 1 cluster matches → return RoutingDecision(cluster=that, strategy="rules", confidence=1.0, matched_keyword=...)
    - Stage 2 trigger (0 matches OR ≥2 matches): if llm is None → return fallback RoutingDecision(cluster="ops", strategy="fallback_default_ops", confidence=0.0); else invoke `llm.with_structured_output(RoutingDecision).ainvoke(prompt)` with 4-shot examples; if returned confidence<0.7 → return fallback
    - `build_cluster_subgraph(cluster_name, child_agent_slugs)` returns a `StateGraph(AgentState)` (compiled separately by supervisor); contains one placeholder node per child slug that simply passes state through with structlog log message indicating "placeholder for {agent_id} — implemented in Phase 6-9"; routing within subgraph: START → first child → END (Phase 4 placeholder; Phase 6-9 will add conditional routing)
    - `build_supervisor_graph(checkpointer, router)` returns compiled StateGraph with: 1 `route` node calling `router.route()`, 5 cluster subgraph nodes (each compiled separately), conditional edge from route → cluster based on `state["routing_decision"].cluster`, recursion_limit handler (see recursion_review below)
    - The compiled graph supports `await graph.ainvoke(initial_state, config={"configurable":{"thread_id":...},"recursion_limit":25})` and persists checkpoint via supplied checkpointer
    - For success criterion #2: when graph exceeds recursion_limit, the `GraphRecursionError` is caught by a wrapper `safe_invoke(graph, state, config)` (in supervisor.py) which appends a ProposedAction with `action_type=ActionType.GRAPH_RECURSION_REVIEW` and `requires_tier=Tier.MANAGER` to state.proposed_actions, then returns the state (does NOT raise); HITL Manager tier picks it up via Plan 04-06 interrupt middleware
  </behavior>
  <action>
    Create `policies/routing.yaml` with exactly the 5 cluster blocks per CONTEXT.md D-54 (lines 101-110). Use snake_case keys. Add small expansion of keywords to cover bilingual Italian/English (per RESEARCH §3.4): ops keywords include `operator, turno, allarme, produzione, qualita, defetto, alert, shift, quality`. Patterns include the regex from CONTEXT for ops (`macchina (\d+|[A-Z]+-\d+)`, `anomalia`). Maintenance, supply, knowledge-curation, knowledge-training analogously per CONTEXT.

    Create `policies/routing.py`: imports yaml, re, lru_cache, pathlib.Path. `class HybridRouter`: `__init__(self, *, llm: BaseChatModel | None = None, routing_yaml_path: Path | None = None)`: path defaults to `Path(__file__).parent / "routing.yaml"`; loads via `yaml.safe_load(path.read_text(encoding="utf-8"))`; stores `self._rules: dict[str, dict] = data`; precompiles regex patterns. `async def route(self, state: AgentState) -> RoutingDecision`: extract last user message text (`state["messages"][-1].content` if any, else empty string); lowercase; for each cluster scan keywords (substring match) and patterns (regex.search); collect set of matched clusters; if len(matched) == 1 → return RoutingDecision(cluster=cluster, strategy="rules", confidence=1.0, matched_keyword=...); else go to Stage 2. Stage 2: if self._llm is None → return RoutingDecision(cluster="ops", strategy="fallback_default_ops", confidence=0.0); else build 4-shot prompt (system + few-shot user/assistant pairs hardcoded in module constant `_FEWSHOT_EXAMPLES`); call `await self._llm.with_structured_output(RoutingDecision).ainvoke(prompt)`; if decision.confidence < 0.7 → return fallback. Add `_log_routing(decision)` calling structlog with `supervisor.route` event (D-54 — analytics post-hoc via Langfuse). `policies/__init__.py` re-exports HybridRouter.

    Create `runtime/clusters.py`: imports `StateGraph, START, END` from langgraph.graph; `def build_cluster_subgraph(cluster_name: str, child_agent_slugs: list[str]) -> StateGraph`: build a StateGraph(AgentState); for each slug add a node `slug` that is an async function `async def _placeholder_node(state: AgentState) -> dict`: structlog.info("cluster_child_placeholder", cluster=cluster_name, agent_id=slug, message="Phase 6-9 will implement business logic"); return `{}` (no state mutation — Phase 4 wiring only); add edges START → first slug → END (simple linear placeholder; real cluster routing comes Phase 6+). Return the StateGraph (NOT compiled — supervisor compiles).

    Create 5 cluster package directories: `packages/sft-agents/src/sft_agents/clusters/{ops,maintenance,knowledge_curation,knowledge_training,supply}/__init__.py` (Python module names use underscores; cluster_name strings use hyphens). Each `__init__.py` exports `CHILD_AGENT_SLUGS: list[str]` matching the 16-agent split from PATTERNS §3.3:
    - ops: `["operator-assistant", "production-planner", "quality-inspector", "anomaly-detector"]`
    - maintenance: `["predictive-maintenance", "rca-specialist", "maintenance-coach", "downtime-analyzer"]`
    - knowledge_curation: `["knowledge-curator", "documentation-synthesizer"]`
    - knowledge_training: `["training-coach", "shift-handover"]`
    - supply: `["inventory-manager", "energy-optimizer", "cost-analyzer", "demand-forecaster"]`
    And `CLUSTER_NAME: str` (the hyphenated form: ops, maintenance, knowledge-curation, knowledge-training, supply).
    Also `clusters/__init__.py` exports `ALL_CLUSTERS = ("ops","maintenance","knowledge-curation","knowledge-training","supply")` matching VALID_CLUSTERS.

    Create `runtime/supervisor.py`: imports StateGraph, START, END from langgraph.graph; AgentState, VALID_CLUSTERS, RoutingDecision from runtime.state; HybridRouter from policies.routing; build_cluster_subgraph from runtime.clusters; 5 cluster modules for CHILD_AGENT_SLUGS + CLUSTER_NAME.

    `def build_supervisor_graph(*, checkpointer, router: HybridRouter | None = None) -> CompiledGraph`:
    1. Instantiate router if not provided: `router = router or HybridRouter()`
    2. Build supervisor StateGraph(AgentState).
    3. Add node `route`: async fn that calls `decision = await router.route(state)`; return `{"routing_decision": decision, "cluster": decision.cluster}`.
    4. Add 5 cluster nodes: for each (cluster_name, cluster_module) build subgraph via `build_cluster_subgraph(cluster_name, cluster_module.CHILD_AGENT_SLUGS).compile()` then `g.add_node(cluster_name, compiled_subgraph)`.
    5. Edges: `g.add_edge(START, "route")`; `g.add_conditional_edges("route", lambda s: s["routing_decision"].cluster, {c: c for c in ALL_CLUSTERS})`; for each cluster name `g.add_edge(cluster_name, END)`.
    6. `compiled = g.compile(checkpointer=checkpointer)`; return compiled.

    `async def safe_invoke(graph, initial_state: AgentState, *, config: dict) -> AgentState`: wrap `await graph.ainvoke(initial_state, config)` in try/except GraphRecursionError (import from langgraph.errors); on catch, log structlog warning + return state augmented with `proposed_actions += [ProposedAction(action_type=ActionType.GRAPH_RECURSION_REVIEW, requires_tier=Tier.MANAGER, target_subject=None, args={"thread_id": config["configurable"]["thread_id"], "recursion_limit": config.get("recursion_limit",25)}, reason="recursion_limit exceeded — Plan 04-06 HITL middleware will route to Manager tier")]`. Validate `config["recursion_limit"]` is set (raise ValueError if missing — success criterion #2 requires explicit recursion_limit on every invoke).

    Update `runtime/__init__.py` to also export `build_supervisor_graph, safe_invoke, build_cluster_subgraph, HybridRouter, ALL_CLUSTERS`.

    Unskip tests:
    `tests/test_routing.py` (NEW): import HybridRouter, RoutingDecision; test rule-based match for each of 5 clusters with one canonical input; test 0-match input returns fallback when llm=None; test ambiguous input (matches 2 clusters) returns fallback when llm=None; test routing.yaml loads via yaml.safe_load (NOT yaml.load).
    `tests/test_clusters.py` (NEW): test each cluster module exports CHILD_AGENT_SLUGS with correct count (4/4/2/2/4) and CLUSTER_NAME with hyphenated form; test build_cluster_subgraph returns a StateGraph with N+2 nodes (N children + START + END are implicit) and compiles successfully.
    `tests/test_supervisor.py` (UPGRADE from W0 stub): mock checkpointer via `langgraph.checkpoint.memory.MemorySaver` (in-process, for unit tests); build_supervisor_graph(checkpointer=memsaver) returns compiled graph; `await graph.ainvoke({"messages":[HumanMessage("Allarme su macchina T-12")], "proposed_actions":[]}, config={"configurable":{"thread_id":"ops.operator-assistant.<uuid>"},"recursion_limit":25})` succeeds and returns state with `cluster=="ops"` (routed by rules — "allarme" + "macchina T-12" regex both match ops).
    `tests/test_recursion_limit.py` (UPGRADE from W0 stub): build a tiny subgraph with intentional cycle, attach to a fake supervisor; call `safe_invoke(graph, state, config={"recursion_limit":3,"configurable":{"thread_id":"..."}})`; assert no exception raised; assert returned state.proposed_actions has 1 entry with `action_type==ActionType.GRAPH_RECURSION_REVIEW` and `requires_tier==Tier.MANAGER`. Second test: omitting recursion_limit from config raises ValueError.

    Conventional commits: (1) `feat(04-05-supervisor-clusters-checkpointer-02): hybrid router with rules + LLM fallback`, (2) `feat(04-05-supervisor-clusters-checkpointer-02): 5 cluster subgraphs with 16 placeholder children (D-53)`, (3) `feat(04-05-supervisor-clusters-checkpointer-02): supervisor stategraph + recursion_limit-to-hitl safe_invoke`.
  </action>
  <pattern_ref>packages/sft-domain/src/sft_domain/glossary/_loader.py:21-80 (yaml.safe_load + pathlib + lru_cache — replica for HybridRouter init) ; PATTERNS §3.3 (16-agent slug list mapping to 5 clusters)</pattern_ref>
  <threat_ref>T-04-LLM-Inject (HybridRouter Stage 2 LLM output passes through structured_output → Pydantic frozen RoutingDecision → enum-bounded cluster field, defense-in-depth against prompt injection trying to route to arbitrary cluster) ; T-04-Budget-Exhaust (recursion_limit-to-HITL prevents unbounded LLM token consumption per success criterion #2)</threat_ref>
  <verify>
    <automated>nx test sft-agents --testNamePattern='test_supervisor|test_clusters|test_routing|test_recursion_limit'</automated>
  </verify>
  <done>
    - `packages/sft-agents/src/sft_agents/policies/routing.yaml` exists; `python -c "import yaml; d=yaml.safe_load(open('packages/sft-agents/src/sft_agents/policies/routing.yaml')); assert set(d.keys()) == {'ops','maintenance','knowledge-curation','knowledge-training','supply'}; print('ok')"` exits 0
    - `grep -nE 'yaml\.load\b' packages/sft-agents/src/sft_agents/policies/routing.py | grep -v 'safe_load'` returns no matches (yaml.load forbidden — must be safe_load)
    - `python -c "from sft_agents.runtime import build_supervisor_graph, HybridRouter, ALL_CLUSTERS, safe_invoke; from langgraph.checkpoint.memory import MemorySaver; g = build_supervisor_graph(checkpointer=MemorySaver()); print(ALL_CLUSTERS)"` exits 0 and prints the 5 clusters
    - All 5 cluster modules exist: `for c in ops maintenance knowledge_curation knowledge_training supply; do test -f packages/sft-agents/src/sft_agents/clusters/$c/__init__.py; done` exits 0
    - Total child agent slugs across 5 clusters = 16: `python -c "from sft_agents.clusters import ops, maintenance, knowledge_curation, knowledge_training, supply; total = sum(len(m.CHILD_AGENT_SLUGS) for m in [ops, maintenance, knowledge_curation, knowledge_training, supply]); assert total == 16, total; print('ok', total)"` exits 0
    - `nx test sft-agents --testNamePattern='test_supervisor|test_clusters|test_routing|test_recursion_limit'` exits 0
    - safe_invoke without recursion_limit raises ValueError (asserted in test_recursion_limit.py)
    - HybridRouter loads yaml + 2-stage routing; 5 cluster packages with correct slug counts; build_supervisor_graph compiles with checkpointer; safe_invoke wraps GraphRecursionError into HITL Manager-tier ProposedAction; 4 unskipped test files green.
  </done>
  <commit_scope>feat(04-05-supervisor-clusters-checkpointer)</commit_scope>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User message text → HybridRouter Stage 1/2 | Untrusted natural-language input drives cluster routing; rule-based Stage 1 is keyword-bounded; Stage 2 LLM output funneled through Pydantic structured_output |
| LLM routing decision → state.cluster | LLM-supplied cluster value validated against ALL_CLUSTERS frozenset by Pydantic Literal/enum |
| graph invoke → checkpoint write | AgentState (including EvidencePanel) serialized to PG; Plan 04-06 wires GDPR redactor pre-write |
| Recursion overflow → state mutation | GraphRecursionError caught at boundary; state augmented with HITL Manager ProposedAction (no crash) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-LLM-Inject | Tampering | HybridRouter Stage 2 | mitigate | structured_output → RoutingDecision Pydantic frozen + Literal cluster field; confidence<0.7 forces fallback to ops; injection cannot route to arbitrary cluster |
| T-04-Budget-Exhaust | DoS | safe_invoke wrapper | mitigate | recursion_limit enforced at invoke time (ValueError if missing); GraphRecursionError → HITL Manager ProposedAction (no infinite token spend) |
| T-04-Checkpoint-PII | Info Disclosure | get_postgres_checkpointer | accept (this plan) | Surface created here; redactor middleware lands Plan 04-06 (HITL/audit) — checkpointer plan only wires the saver |
</threat_model>

<verification>
- `routing.yaml` parses via yaml.safe_load; HybridRouter loads it
- 5 cluster packages with 16 total child slugs match Phase 1 layout
- build_supervisor_graph compiles with checkpointer (MemorySaver in unit test; AsyncPostgresSaver against testcontainers in integration)
- safe_invoke catches GraphRecursionError and emits Manager-tier ProposedAction (success criterion #2)
- All Wave 0 stubs for supervisor/clusters/routing/recursion_limit/checkpointer unskipped
</verification>

<success_criteria>
- CORE-02 satisfied: 5 cluster subgraphs (D-53 override of ROADMAP "4")
- CORE-03 satisfied: recursion_limit explicit on every invoke (via safe_invoke ValueError if missing) and escalates to HITL instead of crashing
- CORE-04 satisfied: AsyncPostgresSaver wired with thread_id convention D-59
- D-54 hybrid routing operational (rules first, LLM fallback when ambiguous, default ops on low confidence)
- 16 placeholder agent child nodes match Phase 1 scaffold slugs exactly
</success_criteria>

<output>
Create `.planning/phases/04-core-agentic-runtime-hitl/04-05-SUMMARY.md`. Include: 5 cluster modules + slug counts, supervisor graph node list, recursion_limit-to-HITL behavior, downstream consumers (Plan 04-06 wires HITL middleware into this graph; Plan 04-07 wraps in api-gateway).
</output>
