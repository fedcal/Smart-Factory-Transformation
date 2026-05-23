---
phase: 7
phase_name: Agents — Maintenance & Reliability
mapped_at: "2026-05-23"
files_classified: 28
analogs_with_exact_match: 22
analogs_with_role_match: 5
files_with_no_analog: 1
---

# Phase 7 — Pattern Map

Mapping di ogni NEW file di Phase 7 al suo analogo più vicino già in repo
(Phase 3–6). Il planner copia direttamente i pattern citati (path + range
righe). Tutti i path sono assoluti dalla repo root.

Convenzione `Match Quality`:
- **exact** = stesso role + stesso data flow + analogo già adottato come
  modello esplicito in 07-CONTEXT.md
- **role-match** = stesso role, data flow leggermente diverso (es. ReAct
  vs deterministico)
- **partial** = solo layout/package skeleton riusabile
- **none** = nessun analogo, planner deve inventare

---

## File Classification

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `packages/sft-agents/src/sft_agents/runtime/clusters.py` (EXTEND `build_maintenance_subgraph`) | runtime / router | request-response | `packages/sft-agents/src/sft_agents/runtime/clusters.py::build_ops_subgraph` (L90-160) | exact |
| `packages/sft-agents/src/sft_agents/tools/hitl.py` (EXTEND `request_help`) | tool | request-response | `packages/sft-agents/src/sft_agents/tools/hitl.py::EscalateToSupervisorTool` (L91-223) | exact |
| `packages/sft-agents/src/sft_agents/models/enums.py` (EXTEND `ActionType`) | model / enum | n/a | `packages/sft-agents/src/sft_agents/models/enums.py::ActionType` (L67-99) Phase 6 extension block | exact |
| `apps/agents/maintenance/predictive-maintenance/` | agent (deterministic ML scoring) | event-driven (NATS consumer) | `apps/agents/ops/anomaly-detector/` (deterministic, no-LLM agent) | exact |
| `apps/agents/maintenance/rca-specialist/` | agent (LLM ReAct + tools) | request-response | `apps/agents/ops/operator-assistant/` (full ReAct toolbelt, citations validator) | role-match |
| `apps/agents/maintenance/maintenance-coach/` | agent (async LangGraph thread w/ checkpoint) | streaming / multi-turn | `apps/agents/ops/quality-inspector/` (LLM + HITL routing); checkpoint pattern from Phase 4 `langgraph_checkpoints` (migration 005) | role-match |
| `apps/agents/maintenance/downtime-analyzer/` | agent (NATS consumer + SQL aggregator) | event-driven + batch | `apps/agents/ops/quality-inspector/` (NATS consumer + audit row writer) | exact |
| `packages/sft-ml/` (NEW package) | ML pipeline package | offline batch | `packages/sft-knowledge/` (only for layout) | partial |
| `packages/sft-ml/src/sft_ml/cmapss/feature_map.py` | utility (feature mapping) | transform | `packages/sft-domain/src/sft_domain/ops/anomaly.py` (`select_baseline` lookup table pattern) | partial |
| `packages/sft-ml/src/sft_ml/cmapss/training.py` | utility (training script) | offline batch | n/a (new flavor) | none |
| `packages/sft-ml/src/sft_ml/cmapss/inference.py` | utility (inference helper) | request-response | `packages/sft-tools/src/sft_tools/query_timescale.py` (tool wrapper pattern) | partial |
| `packages/sft-ml/data/c-mapss-fd001/`, `data/c-mapss-fd003/` | data fixtures | static | `packages/sft-domain/src/sft_domain/failure_modes.yaml` (committed domain data) | partial |
| `packages/sft-ml/models/ridge-fd001-fd003-v1.0.joblib` | model binary artifact | static | none in repo | none |
| `infra/migrations/timescale/008_create_downtime_events.sql` (+ continuous aggregate `maintenance.oee_hourly`) | migration (table + hypertable + caggr) | DDL | `infra/migrations/timescale/001_create_sensor_events.sql` (hypertable pattern) + `infra/migrations/timescale/005_create_langgraph_checkpoints.sql` (PG-only table) | role-match |
| `infra/migrations/timescale/009_extend_audit_mnt.sql` | migration (CHECK extension) | DDL | `infra/migrations/timescale/007_extend_audit_decisions.sql` (L1-108) | exact |
| `infra/migrations/timescale/tests/test_migration_008.py` | integration test (testcontainers) | DDL verification | `infra/migrations/timescale/tests/test_migration_007.py` (L1-120 fixture pattern) | role-match |
| `infra/migrations/timescale/tests/test_migration_009.py` | integration test (testcontainers) | DDL verification | `infra/migrations/timescale/tests/test_migration_007.py` (L1-120 + 6-test matrix) | exact |
| `simulators/sim-textile/src/sim_textile/downtime_event_generator.py` | simulator emitter | event-driven publisher | `simulators/sim-textile/src/sim_textile/quality_event_generator.py` (L1-274) | exact |
| `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py` | HTTP router | request-response | `apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py` (L1-80) | exact |
| `docs/docs/agents/maintenance/{4 agent docs}.md` (+ `en/` mirror) | documentation (bilingue) | static | `docs/docs/agents/operations/anomaly-detector.md` (L1-60 frontmatter + sections) | exact |
| `docs/docs/agents/maintenance/event-taxonomy.md` (+ `en/` mirror) | documentation (bilingue) | static | `docs/docs/agents/operations/anomaly-detector.md` (frontmatter + table structure) | role-match |
| `tests/e2e/maintenance/test_<agent>_scenarios.py` | E2E test | scenario-driven | `tests/e2e/ops/test_anomaly_detector_scenarios.py` (L1-80) | exact |
| `tests/fixtures/mnt_scenarios/<agent>/*.yaml` | test fixtures | static | `tests/fixtures/ops_scenarios/<agent>/*.yaml` (directory layout) | exact |
| `tests/fixtures/llm_responses/<agent>/*.jsonl` | test fixtures (mock LLM) | record/replay | `tests/fixtures/llm_responses/<agent>/*.jsonl` (directory layout) | exact |
| `packages/sft-domain/src/sft_domain/failure_modes.yaml` (EXTEND additive `maintenance:` subkey) | data registry | static | `packages/sft-domain/src/sft_domain/failure_modes.yaml` (L14-49 esistente) | exact |
| `packages/sft-domain/src/sft_domain/failure_modes/models.py` (EXTEND Pydantic) | model / loader | n/a | `packages/sft-domain/src/sft_domain/failure_modes/models.py` (L23-100 Phase 6 extension block L80-100) | exact |

---

## Pattern Assignments

### 1. `packages/sft-agents/src/sft_agents/runtime/clusters.py` — ADD `build_maintenance_subgraph`

**Analog:** `packages/sft-agents/src/sft_agents/runtime/clusters.py::build_ops_subgraph` (L90-160)

**Pattern da copiare** (router + fallback + warning structlog su unknown target):

```python
# clusters.py L126-160 — copia 1:1, cambia _OPS_DEFAULT_AGENT
def build_maintenance_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    if not child_callables:
        raise ValueError("child_callables must be non-empty for the maintenance subgraph")
    _MNT_DEFAULT_AGENT = "downtime-analyzer"  # fallback target da confermare al planner
    if _MNT_DEFAULT_AGENT not in child_callables:
        raise ValueError(...)
    children = dict(child_callables)
    g: StateGraph = StateGraph(AgentState)
    for slug, fn in children.items():
        g.add_node(slug, fn)
    def _route(state: AgentState) -> str:
        target = state.get("target_agent") if isinstance(state, dict) else None
        if not target or target not in children:
            _log.warning("mnt_route_unknown_target", target=target, fallback=_MNT_DEFAULT_AGENT)
            return _MNT_DEFAULT_AGENT
        return str(target)
    g.add_conditional_edges(START, _route, {slug: slug for slug in children})
    for slug in children:
        g.add_edge(slug, END)
    return g
```

**Decisione aperta per planner:** quale dei 4 agenti diventa fallback `_MNT_DEFAULT_AGENT`? In Phase 6 il fallback era `operator-assistant` perché è "primo punto di contatto". In Phase 7 il candidato più ragionevole è `downtime-analyzer` (read-only / informational) o `rca-specialist` (sempre HITL → safe). Da confermare in PLAN.md.

**Risk se pattern non applica:** se il supervisor Phase 4 non popola `target_agent` per il cluster `maintenance`, il fallback viene sempre invocato — verificare con HybridRouter che le decisioni di routing supervisor includano cluster `maintenance`.

---

### 2. `packages/sft-agents/src/sft_agents/tools/hitl.py` — ADD `request_help`

**Analog:** `packages/sft-agents/src/sft_agents/tools/hitl.py::EscalateToSupervisorTool` (L91-223)

**Input schema da copiare** (frozen + extra=forbid + length caps):

```python
# hitl.py L52-76 — input schema bound
class RequestHelpInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    reason: str = Field(min_length=10, max_length=2000, description="...")
    context: str = Field(min_length=10, max_length=2000, description="...")
    # NEW Phase 7 fields (D-MC-02):
    intervention_id: str = Field(min_length=1, max_length=64)
    current_step: int = Field(ge=0, le=100)
```

**Tool body — wrappare `EscalateToSupervisorTool`** invece di duplicare interrupt() logic (D-MC-02 dice esplicitamente "wrappa internamente escalate_to_supervisor"):

```python
# Pattern: il request_help tool NON chiama interrupt() direttamente.
# Costruisce il payload e delega a EscalateToSupervisorTool._arun() che
# già gestisce safety_middleware.check + interrupt() + audit dual-write convention.
class RequestHelpTool(BaseTool):
    name: str = "request_help"
    description: str = "Technician explicit help request (keyword: 'aiuto', 'help', 'stuck'). Wraps escalate_to_supervisor."
    args_schema: type[BaseModel] = RequestHelpInput
    _escalate: EscalateToSupervisorTool = PrivateAttr()

    async def _arun(self, reason, context, intervention_id, current_step, **kw):
        # Compose evidence_summary che include intervention context
        evidence_summary = f"intervention={intervention_id} step={current_step} context={context[:1000]}"
        suggested_action = f"Supervisor: review step {current_step} of intervention {intervention_id}"
        return await self._escalate._arun(
            reason=reason, suggested_action=suggested_action,
            evidence_summary=evidence_summary, **kw,
        )
```

**Pattern critici da NON dimenticare** (esplicitamente documentati in `hitl.py` docstring L17-30):
- **Pitfall §3**: nessun audit/queue/nats write PRIMA di `interrupt()` (il `human_approval_node` fa il dual-write post-resume); `request_help` eredita questa garanzia dal wrapping.
- **Async-only**: `_run` deve raise `NotImplementedError` (L151-156).
- **Audit marker D-MC-02**: il `Decision.HITL_SUPERVISOR + ActionType.COACH_STEP` row deve includere `escalation_trigger: 'technician_request'` nel payload — gestito dal calling node, non dal tool.

**Risk se pattern non applica:** se `EscalateToSupervisorTool` viene rifattorizzato dopo Phase 7, `request_help` rompe in cascata. Mitigazione: contract test che invoca `RequestHelpTool._arun` con mock supervisor e verifica che `interrupt()` venga chiamato esattamente una volta.

---

### 3. `packages/sft-agents/src/sft_agents/models/enums.py` — EXTEND `ActionType`

**Analog:** `packages/sft-agents/src/sft_agents/models/enums.py::ActionType` Phase 6 extension block (L67-99)

**Pattern da copiare** (commento esplicito + lockstep con migration):

```python
# enums.py L67-99 — copia il pattern docstring + commenti
class ActionType(str, Enum):
    # ... Phase 1-5 + Phase 6 valori esistenti ...
    # Phase 6 additions — keep in lockstep with migration 007.
    ESCALATION_REQUEST = "ESCALATION_REQUEST"
    QUALITY_VERDICT = "QUALITY_VERDICT"
    SCHEDULE_DRAFT = "SCHEDULE_DRAFT"
    ANOMALY_ALERT = "ANOMALY_ALERT"
    # Phase 7 additions — keep in lockstep with migration 009.
    RUL_ESTIMATE = "RUL_ESTIMATE"       # D-PM-04: predictive-maintenance audit row
    RCA_CHAIN = "RCA_CHAIN"             # D-RCA-02: rca-specialist 5-Why chain audit
    COACH_STEP = "COACH_STEP"           # D-MC-02: maintenance-coach step audit
    DOWNTIME_VERDICT = "DOWNTIME_VERDICT"  # D-DA-01: downtime-analyzer event audit
    OEE_REPORT = "OEE_REPORT"           # D-DA-03: downtime-analyzer OEE report audit
```

**Docstring extension** — aggiungere blocco "Phase 7 extensions" prima di "Migration ...":
- Pattern esatto come Phase 6 block L73-86 (docstring spiega cosa rappresenta ogni nuovo valore).

**Risk se pattern non applica:** drift tra enum.value strings e CHECK constraint in migration 009 → runtime PG CHECK violation. Mitigazione obbligatoria: round-trip test `tests/test_audit_constraints.py` (mirror dell'esistente Phase 6) che enumera `ActionType.*.value` e verifica che ogni valore sia ammesso dal CHECK constraint post-migration.

---

### 4. `apps/agents/maintenance/predictive-maintenance/` (NEW package)

**Analog:** `apps/agents/ops/anomaly-detector/` (intero package — directory layout, agent class, audit pattern)

**Riferimenti chiave:**

| Aspetto | File analogo | Range |
|---------|-------------|-------|
| Directory layout | `apps/agents/ops/anomaly-detector/{src/ops_anomaly_detector/{agent.py,baseline.py,metadata.py,models.py,__init__.py},tests/,pyproject.toml,README.md,project.json}` | tutto |
| Agent class shape | `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py::AnomalyDetector` | L96-247 |
| Module-level constants | idem | L67-93 (`AGENT_ID`, `CLUSTER`, `_NO_LLM_MODEL`, `_NO_PROMPT_HASH`, `_DEFAULT_WINDOW_MINUTES`, `_EMPTY_BUDGET`) |
| `__call__(state) -> dict` signature | idem | L160-246 |
| `_write_audit` helper | idem | L252-319 |

**Pattern key da copiare:**

```python
# agent.py L67-93 — module constants (cambia AGENT_ID="predictive-maintenance",
# CLUSTER="maintenance", _NO_LLM_MODEL="ridge-fd001-fd003-v1.0@predictive-maintenance")
AGENT_ID: str = "predictive-maintenance"
CLUSTER: str = "maintenance"
_MODEL_VERSION: str = "ridge-fd001-fd003-v1.0"  # joblib model
_LLM_MODEL: str = f"{_MODEL_VERSION}@predictive-maintenance"  # for EvidencePanel.model (regex name@runtime)
_NO_PROMPT_HASH: str = "0" * 64  # no LLM prompt
_EMPTY_BUDGET = BudgetSnapshot(...)
```

```python
# agent.py L160-246 — __call__ stub Phase 7
async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
    asset_id = state["asset_id"]  # set by NATS consumer or supervisor
    triggered_by_action_id = state.get("triggered_by_action_id")  # AD→PM audit chain link
    now = datetime.now(UTC)
    # 1. Pull sensor window from TimescaleDB (riusa query_timescale tool)
    df = await self._query._arun(asset_id=asset_id, time_range=(now - timedelta(minutes=60), now))
    # 2. Map textile sensors → C-MAPSS proxy features (feature_map.py)
    features = self._feature_map.transform(df)
    # 3. Inference (deterministic, random_state fissato)
    rul_cycles, ci_low, ci_high = self._model.predict_with_ci(features)
    # 4. Build RULEstimate Pydantic
    estimate = RULEstimate(estimate_id=str(uuid4()), asset_id=asset_id, ...)
    # 5. HITL gate su health_index < 0.3 → interrupt() via escalate_to_supervisor
    # 6. Audit row Decision.AUTO + ActionType.RUL_ESTIMATE
    await self._write_audit(estimate=estimate, decision=Decision.AUTO, ...)
    return {"rul_estimate": estimate}
```

**Audit helper** — copiare struttura da `_write_audit` (anomaly-detector L252-319), sostituendo:
- `anomaly` → `estimate`
- `synthetic_call.name` da `"anomaly_detect"` a `"rul_predict"`
- `synthetic_call.args` con feature vector + model_version
- `action_type` da `ANOMALY_ALERT` a `RUL_ESTIMATE`
- `thread_id` da `f"{CLUSTER}.{AGENT_ID}.{anomaly.id}"` a `f"{CLUSTER}.{AGENT_ID}.{estimate.estimate_id}"`

**Pattern S-6 obbligatori** (cross-cutting, vedi `agent.py` docstring L30-41):
- `datetime.now(UTC)` sempre tz-aware
- `_ensure_utc(value, fallback=now)` helper (anomaly-detector L322-339) — DIRETTO REUSE se DataFrame contiene timestamp pandas
- Rate-limiter pattern (`packages/sft-agents/src/sft_agents/runtime/rate_limit.py`) — opzionale per Phase 7, da decidere se PM serve cap (probabilmente no, trigger AD è già rate-limitato a 12/h).

**Risk se pattern non applica:** RUL inference su CPU container può eccedere `recursion_limit=5` o budget; mitigazione: pre-load model in `__init__`, inference < 100ms target.

---

### 5. `apps/agents/maintenance/rca-specialist/` (NEW package)

**Analog primario (LLM ReAct + citations validator):** `apps/agents/ops/operator-assistant/` (intero package)

**Analog secondario (HITL routing pattern):** `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py` (L1-80) per il pattern severity → tier resolver.

**Riferimenti chiave:**

| Aspetto | File analogo | Range |
|---------|-------------|-------|
| Directory layout | `apps/agents/ops/operator-assistant/src/ops_operator_assistant/{agent.py,prompts.py,validators.py,models.py,metadata.py,lang_detect.py,__init__.py}` | tutto |
| Citations validator post-LLM (D-OA-04 → D-RCA-01) | `apps/agents/ops/operator-assistant/src/ops_operator_assistant/validators.py` | tutto |
| Prompts module pattern | `apps/agents/ops/operator-assistant/src/ops_operator_assistant/prompts.py` | tutto |
| HITL always-supervisor (D-RCA-02 mirror QI tier dispatch but no severity branch) | `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py::_resolve_tier` | L76-100 |

**Pattern da copiare:**

```python
# Mirror operator-assistant validators.py + adatta per RCAChain
# D-RCA-01: 5 WhyStep esatti + len(citations) >= 1 per step + source_uri PG-resolvable
class RCAChainValidator:
    def validate(self, chain: RCAChain) -> RCAChain:
        # Pydantic già enforce 5 step (why_1..why_5 obbligatori)
        for i, step in enumerate([chain.why_1, chain.why_2, chain.why_3, chain.why_4, chain.why_5], 1):
            if not step.citations or len(step.citations) < 1:
                raise MissingCitationError(f"why_{i} missing citation")
            for c in step.citations:
                if not c.source_uri:
                    raise MissingCitationError(f"why_{i} citation has null source_uri")
        # Retry max 1 (mirror Phase 6 D-QI-02 pattern)
        return chain
```

```python
# Mirror quality-inspector L76-100 ma SENZA severity branch
# D-RCA-02: always supervisor (literal success criterion #2)
def _resolve_tier(self, chain: RCAChain) -> Tier:
    return Tier.SUPERVISOR  # always — literal success criterion
```

**Tool registration** — usa `rag_search` + `traverse_graph` + `escalate_to_supervisor` (riusa Phase 5/6 tools direttamente, NO duplicazione).

**Risk se pattern non applica:** LLM hallucination su citation source_uri (Pitfall §11 Phase 5/6). Mitigazione: PG lookup verifica `source_uri` esiste in `documents` table prima di accettare la WhyStep (D-RCA-01 / open question #5 risolta come "full PG lookup"). Il validator deve fallire chiusi (rigetta chain piuttosto che approvare con citation orfana).

---

### 6. `apps/agents/maintenance/maintenance-coach/` (NEW package)

**Analog primario (LangGraph thread + HITL):** `apps/agents/ops/quality-inspector/` (HITL routing + audit dual-write)

**Analog secondario (checkpoint reuse):** `infra/migrations/timescale/005_create_langgraph_checkpoints.sql` (DIRETTO REUSE — nessuna nuova migration per Coach)

**Riferimenti chiave:**

| Aspetto | File analogo | Range |
|---------|-------------|-------|
| Directory layout | `apps/agents/ops/quality-inspector/src/ops_quality_inspector/{agent.py,grader.py,prompts.py,models.py,nats_consumer.py,__init__.py}` | tutto |
| HITL dispatch (3-tier) | `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py::_resolve_tier` + `human_approval_node` invocation | L76-100 + body |
| Checkpoint table | `infra/migrations/timescale/005_create_langgraph_checkpoints.sql` | NO new migration — DIRECT REUSE |
| Pattern S-6 / Pitfall §3 (no audit before interrupt) | docstring `hitl.py` | L17-30 |

**Pattern Coach-specifico** (D-MC-01 — thread state cross-shift):

```python
# State schema condiviso per checkpoint replay
class CoachThreadState(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    intervention_id: str
    asset_id: str
    sop_id: str
    technician_id: str
    current_step: int
    completed_steps: list[StepReport]
    messages: list[BaseMessage]
    mttr_start: datetime
    mttr_end: datetime | None
```

```python
# Pattern resume — LangGraph runtime gestisce checkpoint replay automaticamente
# via langgraph_checkpoints table (no codice nuovo per persistence)
graph = StateGraph(CoachThreadState)
graph.add_node("coach_step", coach_step_node)
graph.add_node("hitl_request_help", human_approval_node)
checkpointer = AsyncPostgresSaver(pool=pg_pool)  # esistente Phase 4
app = graph.compile(checkpointer=checkpointer)
# Resume: app.ainvoke(None, config={"configurable": {"thread_id": intervention_id}})
```

**Risk se pattern non applica:**
1. **Checkpoint size blowup** (open question #3) — state con `messages: list[BaseMessage]` cresce O(N) con conversation turn. Mitigazione: target `compress_state` post-step (trim messages > 50 turn), o usa `langgraph.checkpoint.postgres.AsyncPostgresSaver` con compressione gzip nativa.
2. **MTTR drift** — se technician dimentica di chiudere thread, MTTR si gonfia. Mitigazione: TTL warning su thread aperti > 48h (può emergere Phase 11).

---

### 7. `apps/agents/maintenance/downtime-analyzer/` (NEW package)

**Analog:** `apps/agents/ops/quality-inspector/` (NATS durable consumer + PG write + audit row)

**Riferimenti chiave:**

| Aspetto | File analogo | Range |
|---------|-------------|-------|
| NATS consumer pattern | `apps/agents/ops/quality-inspector/src/ops_quality_inspector/nats_consumer.py` | tutto |
| PG event persistence | nuovo: usa migration 008 (vedi sotto) |
| Agent skeleton | `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py` | L1-100 |
| Cross-cluster audit query (OEE.Quality from QUALITY_VERDICT rows) | nuovo pattern, ma query SQL via `asyncpg $1..$N` placeholders (Pattern S-5) |

**OEE query pattern** (D-DA-02):

```python
# SQL su audit.actions WHERE action_type='QUALITY_VERDICT' per finestra
# Riusa asyncpg pool esistente (Phase 4)
async def compute_oee_quality(self, asset_id: str, window_start: datetime, window_end: datetime) -> float:
    sql = """
        SELECT evidence_panel->'tool_calls'->0->'result'->>'good_parts' AS good,
               evidence_panel->'tool_calls'->0->'result'->>'total_parts' AS total
          FROM audit.actions
         WHERE cluster = 'ops'
           AND action_type = 'QUALITY_VERDICT'
           AND ts BETWEEN $1 AND $2
           AND evidence_panel->>'asset_id' = $3
    """
    async with self._pool.acquire() as conn:
        rows = await conn.fetch(sql, window_start, window_end, asset_id)
    if not rows:
        # Fallback a sim-textile production_state metrics
        return await self._sim_fallback_quality(asset_id, window_start, window_end)
    good = sum(int(r["good"]) for r in rows)
    total = sum(int(r["total"]) for r in rows)
    return good / total if total > 0 else 1.0
```

**Risk se pattern non applica:** se evidence_panel payload schema cambia (Phase 6 → Phase 7), JSONB path expressions si rompono silenziosamente. Mitigazione: contract test in `tests/integration/test_oee_cross_cluster.py` che inserisce un QUALITY_VERDICT row mock e verifica che `compute_oee_quality` estrae i campi giusti.

---

### 8. `packages/sft-ml/` (NEW package) — ML pipeline

**Analog (solo layout):** `packages/sft-knowledge/` (layout pyproject + src/ + tests/ + project.json)

**Riferimenti:**
- `packages/sft-knowledge/pyproject.toml` (layout pyproject Hatch)
- `packages/sft-knowledge/project.json` (Nx project descriptor)
- `packages/sft-knowledge/src/sft_knowledge/__init__.py` (package init)

**Pattern da copiare:** layout package + dependency pinning convention. Per il contenuto ML stesso non esiste analogo — vedi sezione "No Analog Found" sotto.

**Risk:** scikit-learn pin (open question #6) — `joblib` serialization NON è garantito compat across Python minor versions. Mitigazione: pin esplicito `joblib>=1.3,<2` + `scikit-learn>=1.4,<2` in `packages/sft-ml/pyproject.toml`, + smoke test in CI che ricarica il joblib model e fa una predict.

---

### 9. `infra/migrations/timescale/008_create_downtime_events.sql`

**Analog primario (hypertable):** `infra/migrations/timescale/001_create_sensor_events.sql`
**Analog secondario (PG-only table layout):** `infra/migrations/timescale/005_create_langgraph_checkpoints.sql`

**Pattern da copiare:**
1. Schema creation: `CREATE SCHEMA IF NOT EXISTS maintenance;`
2. Table DDL con tutti i campi del payload Pydantic D-DA-01
3. `SELECT create_hypertable('maintenance.downtime_events', 'timestamp', ...)` (mirror 001)
4. Continuous aggregate `maintenance.oee_hourly` — NEW pattern, basato su TimescaleDB docs:
   ```sql
   CREATE MATERIALIZED VIEW maintenance.oee_hourly
     WITH (timescaledb.continuous) AS
   SELECT
     asset_id,
     time_bucket('1 hour', timestamp) AS hour_bucket,
     SUM(duration_min) AS total_downtime_min,
     COUNT(*) AS event_count,
     ...  -- Availability/Performance computed in window
   FROM maintenance.downtime_events
   GROUP BY asset_id, hour_bucket;

   SELECT add_continuous_aggregate_policy('maintenance.oee_hourly',
     start_offset => INTERVAL '2 hours',
     end_offset => INTERVAL '5 minutes',
     schedule_interval => INTERVAL '5 minutes');
   ```
5. Idempotency: `CREATE TABLE IF NOT EXISTS ...` + `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$;` pattern per la continuous aggregate.

**Risk se pattern non applica:** refresh_policy 5min su 30 asset × 5 sensor 1Hz può sovra-caricare TimescaleDB (open question #2). Mitigazione: research deve confermare il refresh interval; planner deve includere benchmark test (`tests/perf/test_caggr_refresh.py`).

---

### 10. `infra/migrations/timescale/009_extend_audit_mnt.sql`

**Analog:** `infra/migrations/timescale/007_extend_audit_decisions.sql` (L1-108) — exact mirror

**Pattern da copiare (1:1 con sostituzione valori):**

```sql
-- Migration 009: extend audit.actions.action_type CHECK constraint for Phase 7
-- File: infra/migrations/timescale/009_extend_audit_mnt.sql
-- Phase 7 — Plan 07-NN (D-AE-MNT)
-- Idempotent: safe to re-run.
--
-- Source: Phase 7 ActionType labels (RUL_ESTIMATE, RCA_CHAIN, COACH_STEP,
--         DOWNTIME_VERDICT, OEE_REPORT) — see 07-PATTERNS.md.
--
-- Strategy: identico a migration 007 (drop named constraint + add con valori estesi).
-- Decision enum NON cambia (riusa AUTO, HITL_SUPERVISOR, etc.).

ALTER TABLE audit.actions
  DROP CONSTRAINT IF EXISTS audit_actions_action_type_chk;

ALTER TABLE audit.actions
  ADD CONSTRAINT audit_actions_action_type_chk CHECK (
    action_type IN (
      -- Phases 1-5 baseline
      'WRITE_PLC_SETPOINT', 'ACTUATOR_COMMAND', 'FIRMWARE_DEPLOY',
      'NETWORK_ACL_CHANGE', 'GRAPH_RECURSION_REVIEW', 'GOVERNOR_ALERT',
      -- Phase 6 extensions
      'ESCALATION_REQUEST', 'QUALITY_VERDICT', 'SCHEDULE_DRAFT', 'ANOMALY_ALERT',
      -- Phase 7 extensions
      'RUL_ESTIMATE',       -- D-PM-04
      'RCA_CHAIN',          -- D-RCA-02
      'COACH_STEP',         -- D-MC-02
      'DOWNTIME_VERDICT',   -- D-DA-01
      'OEE_REPORT'          -- D-DA-03
    )
  );
```

**Risk se pattern non applica:** se in futuro `audit.actions.action_type` viene normalizzato in tabella `action_types` (lookup), 009 va riscritto. Phase 7 non corre questo rischio (Phase 11 può proporlo).

---

### 11. `infra/migrations/timescale/tests/test_migration_008.py` + `test_migration_009.py`

**Analog:** `infra/migrations/timescale/tests/test_migration_007.py` (L1-120)

**Pattern da copiare**:

```python
# test_migration_007.py L26-46 — setup
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path: sys.path.insert(0, str(_REPO_ROOT))
from infra.migrations.timescale.migrate import migrate
_MIGRATION_009 = Path(__file__).parent.parent / "009_extend_audit_mnt.sql"
```

**Test matrix per `test_migration_009.py`** (mirror 007's 6-test pattern):
1. `test_pre_migration_rejects_rul_estimate` — INSERT 'RUL_ESTIMATE' raises CheckViolationError before 009
2. `test_post_migration_admits_rul_estimate` — INSERT 'RUL_ESTIMATE' succeeds after 009
3. `test_post_migration_admits_all_phase7_action_types` — RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT, OEE_REPORT
4. `test_post_migration_legacy_action_types_ok` — Phase 1-5 + Phase 6 action types still admitted (regression)
5. `test_post_migration_decision_enum_unchanged` — sanity check: no new Decision values added
6. `test_idempotent_double_apply` — re-running 009 is a no-op

**Test matrix per `test_migration_008.py`** (NEW shape, no perfect mirror — caggr richiede asserzioni custom):
1. `test_post_migration_creates_downtime_events_table`
2. `test_post_migration_creates_hypertable` (verifica `hypertable_name` in `timescaledb_information.hypertables`)
3. `test_post_migration_creates_oee_hourly_caggr` (verifica view in `timescaledb_information.continuous_aggregates`)
4. `test_post_migration_insert_downtime_event_then_refresh_caggr` (workflow happy)
5. `test_idempotent_double_apply`

**Fixture pattern** (riuso esatto da `test_migration_007.py` L108-130): `fresh_dsn` fixture function-scoped + `_run_baseline_migrations(dsn)` per applicare 001..007 prima di 008.

**Risk se pattern non applica:** testcontainers Timescale image deve essere `timescale/timescaledb:2.18.0-pg16` (pin da `test_migration_007.py` L118). Se Phase 7 usa image diversa, le caggr DDL può variare.

---

### 12. `simulators/sim-textile/src/sim_textile/downtime_event_generator.py`

**Analog:** `simulators/sim-textile/src/sim_textile/quality_event_generator.py` (L1-274) — exact mirror

**Pattern da copiare 1:1**, sostituzioni:
- `DefectType` → `DowntimeReasonCode` (da `failure_modes.yaml` `maintenance.reason_code`)
- `_FAMILY_DEFECT_BIAS` → `_FAMILY_REASON_BIAS` (LOOM → mechanical_wear, DYEING → dye_chamber_contamination, etc.)
- `_RATE_NOMINAL_PER_MIN = 10` → più basso (downtime sono rari; suggerito `2` nominal / `8` faulted)
- NATS subject `quality.events.<asset>` → `maintenance.downtime.<asset>`
- Pydantic `QualityEvent` → nuovo `DowntimeEvent` con `{event_id, asset_id, reason_code, duration_min, severity, work_order_id?, dye_lot_id?, source: 'simulator', timestamp}` (D-DA-01)

**Pattern S-6 obbligatori** (vedi `quality_event_generator.py` docstring L4-6):
- `datetime.now(UTC)` sempre tz-aware (L27, L189)
- Per-asset `random.Random(asset.asset_id)` seeded (L172) — no global random.seed pollution
- `asyncio.CancelledError` handler graceful (L222-224)

**Risk se pattern non applica:** se `nc.publish` fallisce in burst (NATS slow consumer), il logging-only error handler (L213-219) potrebbe nascondere event loss. Mitigazione: counter Prometheus `sim_textile_downtime_publish_errors_total` (può essere Phase 11).

---

### 13. `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py`

**Analog:** `apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py` (L1-80) — exact mirror

**Pattern da copiare:**

```python
# ops_agents.py L33-66 — router setup
from fastapi import APIRouter, Body, Depends, Request, status
from sft_agents.llm.langfuse_callback import build_invocation_config

router = APIRouter(prefix="/v1/agents", tags=["maintenance-agents"])
_RECURSION_LIMIT: int = 5
```

**Endpoint da implementare** (mirror del pattern `post_anomaly_scan` L74-80):

| Endpoint | Body schema | Target agent |
|----------|-------------|--------------|
| `POST /v1/agents/predictive-maintenance/predict` | `{asset_id, triggered_by_action_id?}` | predictive-maintenance |
| `POST /v1/agents/rca-specialist/analyze` | `{problem_statement, downtime_event_id?, user_roles}` | rca-specialist |
| `POST /v1/agents/maintenance-coach/start` | `{intervention_id, asset_id, sop_id, technician_id}` | maintenance-coach |
| `POST /v1/agents/maintenance-coach/resume` | `{intervention_id, message}` | maintenance-coach |
| `POST /v1/agents/downtime-analyzer/report` | `{window_start, window_end, by_asset?, top_n_pareto?}` | downtime-analyzer |

**Threat model — copia commenti da L14-30 di `ops_agents.py`:**
- T-V6-injection → `frozen=True, extra="forbid"` su tutti i body Pydantic
- T-V6-acl-leak → `user_roles` propagato in `AgentState`
- T-V6-recursion-bomb → `recursion_limit=5` via `build_invocation_config`

**Risk se pattern non applica:** Maintenance-Coach `/resume` è semanticamente diverso (resume del checkpoint, no fresh state). Planner deve aggiungere `thread_id` esplicito al config e usare `app.ainvoke(None, config={"configurable": {"thread_id": intervention_id}})` invece del pattern fresh-state. Riferimento: D-MC-01 + checkpoint table 005.

---

### 14. `docs/docs/agents/maintenance/{4 agent docs}.md` + `event-taxonomy.md` (+ `en/` mirror)

**Analog:** `docs/docs/agents/operations/anomaly-detector.md` (L1-60+) — exact mirror

**Pattern da copiare:**

```yaml
---
lang: it
agent: predictive-maintenance
requirements:
  - MNT-01
tags:
  - agents
  - maintenance
  - MNT-01
---

# PredictiveMaintenance

## Panoramica
[descrizione 1 paragrafo]

## Strumenti Utilizzati
| Tool | Origine | Funzione |
|------|---------|----------|
| ... | ... | ... |

## Fonti Dati
- ...

## HITL Tier
[tabella 3 colonne: Decisione | Tier | Approvatore]

## KPI Impattati
- ...
```

**Path layout** (mirror esatto del pattern Phase 6):
- IT: `docs/docs/agents/maintenance/{predictive-maintenance,rca-specialist,maintenance-coach,downtime-analyzer,event-taxonomy}.md`
- EN: `docs/docs/en/agents/maintenance/{...stesso elenco...}.md`

**Risk se pattern non applica:** docs site (MkDocs / Docusaurus, da confermare in Phase 1 setup) potrebbe richiedere `nav` entry esplicita in `mkdocs.yml`. Mirror del pattern Phase 6 — controllare se quel nav entry esiste già per `operations` e replicare per `maintenance`.

---

### 15. `tests/e2e/maintenance/test_<agent>_scenarios.py` + `tests/fixtures/mnt_scenarios/<agent>/*.yaml` + `tests/fixtures/llm_responses/<agent>/*.jsonl`

**Analog:** `tests/e2e/ops/test_anomaly_detector_scenarios.py` (L1-80) + `tests/fixtures/ops_scenarios/<agent>/` + `tests/fixtures/llm_responses/<agent>/`

**Pattern da copiare:**

```python
# test_anomaly_detector_scenarios.py L21-48 — header + skip gate + scenarios list
import pytest
pytest.importorskip(
    "mnt_predictive_maintenance.agent",  # cambia per ogni agent
    reason="Plan 07-NN implements mnt_predictive_maintenance.agent",
)
from mnt_predictive_maintenance.agent import PredictiveMaintenance

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

_SCENARIOS = [
    "predictive-maintenance/happy",
    "predictive-maintenance/degraded",
    "predictive-maintenance/failure",
]
```

**Determinism convention** (D-X-01 / 06-13):
- `LLM_BACKEND=mock` env legge response da `tests/fixtures/llm_responses/<agent>/<scenario>.jsonl`
- Per `predictive-maintenance`: `random_state` fissato nel joblib model → output deterministico anche senza LLM mock
- Per `maintenance-coach`: scenario multi-turn richiede LangGraph checkpoint replay → fixture include sequenza di message + `thread_id` stabile

**Risk se pattern non applica:** `MockReplayChatModel` (Phase 6 06-03) assume formato `.jsonl` con un response per riga; per RCASpecialist che fa 5+ LLM call (uno per WhyStep), serve un response per call sequenziale. Pattern già provato in Phase 6 `tests/fixtures/llm_responses/quality-inspector/*.jsonl` (multi-call scenario).

---

### 16. `packages/sft-domain/src/sft_domain/failure_modes.yaml` (EXTEND additive)

**Analog:** `packages/sft-domain/src/sft_domain/failure_modes.yaml` esistente (L14-49 broken_end + mispick entries)

**Pattern da copiare** (additive, no breaking change — D-MNT-TAX):

```yaml
# Per ogni failure mode esistente, aggiungere sub-key `maintenance:`
- id: broken_end
  name_it: rottura filo ordito
  name_en: broken end
  asset_families: [weaving]
  parts: [warp, heddle]
  severity: medium
  hitl_tier: supervisor
  setup_minutes: 15
  severity_band:
    minor: {max_frequency_per_meter: 5}
    major: {max_frequency_per_meter: 20}
    critical: {safety_risk: true}
  # NEW Phase 7 (D-MNT-TAX):
  maintenance:
    reason_code: WEAVING-BE-001
    mttr_target_minutes: 30
    intervention_steps_sop_id: SOP-LOOM-001
    preventive_check_interval_hours: 168  # optional
```

**Validator CI extension** — script `scripts/validate-failure-modes.py` (esistente Phase 5) deve essere esteso per verificare:
- `reason_code` univoco cross-entry
- `intervention_steps_sop_id` esiste nel corpus Phase 5 (SOP corpus path)

**Risk se pattern non applica:** loader Pydantic esistente (`failure_modes/models.py` L23-100) usa `extra="forbid"`. Aggiungere `maintenance:` sub-key SENZA estendere il Pydantic model rompe il loader. → vedi sezione 17 sotto (obbligatorio in lockstep).

---

### 17. `packages/sft-domain/src/sft_domain/failure_modes/models.py` (EXTEND Pydantic)

**Analog:** lo stesso file, Phase 6 extension block (L80-100 `hitl_tier` + `setup_minutes`)

**Pattern da copiare** (mirror Phase 6 extension — backward-compatible optional con default):

```python
# models.py L80-100 — mirror del pattern Phase 6
# Aggiungere DENTRO la classe FailureMode esistente:

# ------------------------------------------------------------------
# Phase 7 (plan 07-NN) extension — backward-compatible (optional + default)
# ------------------------------------------------------------------
class MaintenanceSpec(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    reason_code: Annotated[str, Field(min_length=1, pattern=r"^[A-Z][A-Z0-9-]+$")]
    mttr_target_minutes: Annotated[int, Field(ge=0, le=10080)]  # max 1 week
    intervention_steps_sop_id: Annotated[str, Field(min_length=1, pattern=r"^SOP-[A-Z0-9-]+$")]
    preventive_check_interval_hours: Annotated[int | None, Field(default=None, ge=1)] = None

class FailureMode(BaseModel):
    # ... existing fields ...
    maintenance: Annotated[
        MaintenanceSpec | None,
        Field(default=None, description="Maintenance metadata (D-MNT-TAX Phase 7, optional)"),
    ] = None
```

**Risk se pattern non applica:** se Phase 7 marca `maintenance` come required (non None), tutti gli entry esistenti in `failure_modes.yaml` falliscono il load. Mantenere `default=None` è obbligatorio (additive non-breaking).

---

## Shared Patterns

### Shared Pattern A — Module-level constants per agent

**Source:** `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py` (L67-93)
**Apply to:** TUTTI i 4 maintenance agents (predictive-maintenance, rca-specialist, maintenance-coach, downtime-analyzer)

```python
AGENT_ID: str = "<agent-slug-kebab>"   # matches audit.actions.agent_id
CLUSTER: str = "maintenance"            # matches audit.actions.cluster
_LLM_MODEL: str = "<model_name>@<agent-slug>"  # EvidencePanel.model regex name@runtime
_NO_PROMPT_HASH: str = "0" * 64  # se no LLM (predictive-maintenance)
_EMPTY_BUDGET = BudgetSnapshot(...)  # se no LLM o per fallback
```

### Shared Pattern B — Async-only tool convention

**Source:** `packages/sft-agents/src/sft_agents/tools/hitl.py` (L151-156) + `packages/sft-agents/src/sft_agents/tools/audit.py` (docstring L23-24)
**Apply to:** `request_help` tool + qualunque nuovo tool LangChain in Phase 7

```python
def _run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
    raise NotImplementedError(
        "ToolName is async-only. Use `await tool.ainvoke({...})` instead."
    )
```

### Shared Pattern C — UTC-aware datetime + Pitfall §3 (no audit before interrupt)

**Source:** `packages/sft-agents/src/sft_agents/tools/hitl.py` docstring (L17-30) + `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py` (L30-41)
**Apply to:** TUTTI i 4 maintenance agents + tools + sim extension

- `datetime.now(UTC)` mandatorio (Pattern S-6, T-V6-naive-datetime)
- Nessun `audit_writer.write` / `nats.publish` / `queue_writer.write` PRIMA di `interrupt()` (per RCASpecialist + MaintenanceCoach che usano HITL)

### Shared Pattern D — Pydantic v2 frozen + extra=forbid + length caps

**Source:** `packages/sft-agents/src/sft_agents/tools/hitl.py::EscalateInput` (L52-76)
**Apply to:** TUTTI i nuovi Pydantic model di Phase 7 (RULEstimate, RCAChain, WhyStep, OEEReport, ParetoEntry, DowntimeEvent, CoachThreadState, MaintenanceSpec)

```python
class XxxModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    field: str = Field(min_length=N, max_length=M, description="...")
```

### Shared Pattern E — Audit row pattern (Decision + ActionType + EvidencePanel)

**Source:** `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py::_write_audit` (L252-319)
**Apply to:** TUTTI i 4 maintenance agents (RUL_ESTIMATE, RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT, OEE_REPORT)

Key invariants:
- `thread_id = f"{CLUSTER}.{AGENT_ID}.{entity_id}"` (forensic correlazione)
- `evidence_panel.model` deve matchare regex `^[a-z0-9_.-]+@[a-z0-9_.-]+$`
- `evidence_panel.tool_calls` carry payload strutturato per query JSONB downstream (no ad-hoc scan)
- `await self._audit.write(record)` — dual-write PG + NATS gestito dall'AuditWriter (Phase 4)

### Shared Pattern F — Cross-cluster audit chain link (triggered_by_action_id)

**Source:** Phase 6 D-AD-01 audit row (anomaly-detector); estensione D-PM-04 Phase 7
**Apply to:** PredictiveMaintenance (triggered da AnomalyDetector) + qualunque agente con upstream trigger

Il campo `triggered_by_action_id` va incluso nell'evidence_panel payload (NON è una colonna PG, sta in JSONB) per ricostruire la catena AD → PM forensicamente.

### Shared Pattern G — Test markers convention

**Source:** Phase 1-6 standard (codificato in 06-CONTEXT.md L209)
**Apply to:** TUTTI i test Phase 7

```python
pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]  # E2E
# o
pytestmark = [pytest.mark.integration, pytest.mark.testcontainers]  # migration / DB
# o
@pytest.mark.real-llm  # opt-in real LLM, skip in CI default
```

### Shared Pattern H — asyncpg parameterized queries ($1..$N)

**Source:** Phase 3 T-V5-sql threat model; rinforzato in `apps/agents/ops/quality-inspector/` SQL writes
**Apply to:** DowntimeAnalyzer cross-cluster query (OEE.Quality from QUALITY_VERDICT rows) + qualunque altra SQL in Phase 7

```python
# CORRETTO
await conn.fetch(
    "SELECT ... WHERE ts BETWEEN $1 AND $2 AND asset_id = $3",
    window_start, window_end, asset_id,
)
# VIETATO
await conn.fetch(f"SELECT ... WHERE asset_id = '{asset_id}'")  # SQL injection
```

---

## No Analog Found

I seguenti file/aspetti non hanno un analogo close nel codebase. Il planner deve usare RESEARCH.md / external references (NASA C-MAPSS papers, TimescaleDB docs) come guida.

| File / Concern | Reason | Suggested approach |
|----------------|--------|---------------------|
| `packages/sft-ml/src/sft_ml/cmapss/training.py` | Nessuna training pipeline scikit-learn in repo. Phase 6 ProductionPlanner usa pure heuristic Python (`packages/sft-domain/scheduling/`), zero ML. | RESEARCH.md deve raccomandare standard scikit-learn skeleton: `train_test_split` → `Pipeline([StandardScaler, Ridge])` → `joblib.dump`. Pin `random_state` ovunque (D-PM-01 determinism). |
| `packages/sft-ml/models/ridge-fd001-fd003-v1.0.joblib` | Nessun model binary in repo (PoC è LLM-only finora). | Committare in repo (5-10MB target). Git LFS opzionale ma probabilmente non necessario. Pinned versioning via filename. |
| TimescaleDB continuous aggregate DDL | Phase 1-6 ha hypertables ma NESSUNA continuous aggregate. Le 7 migration esistenti sono table-only. | RESEARCH.md deve linkare TimescaleDB docs `add_continuous_aggregate_policy`. Test in `test_migration_008.py` deve verificare `timescaledb_information.continuous_aggregates` row presente. Open question #2 (refresh policy 5min) va risolta in research. |
| LangGraph checkpoint replay test (MaintenanceCoach) | Phase 4 ship `langgraph_checkpoints` migration (005) ma nessun test E2E che esercita resume cross-shift. | Mirror del Phase 6 `tests/e2e/ops/test_quality_inspector_scenarios.py` per la parte LLM mock, ma aggiungere step esplicito: invocare graph, pausare (interrupt), riavviare graph con stesso `thread_id`, verificare che state riprende dal checkpoint. |
| MaintenanceCoach `compress_state` strategy | Open question #3 — checkpoint size on long intervention (4h, 30 step) può esplodere PG payload. | Decisione planner: applicare trim a `messages > 50` o usare `langgraph.checkpoint.postgres.AsyncPostgresSaver` con compressione (verificare se feature disponibile). |

---

## Metadata

**Analog search scope:**
- `packages/sft-agents/` (Phase 4-6 runtime + tools + models)
- `packages/sft-domain/` (Phase 2-6 domain models + failure_modes + scheduling)
- `packages/sft-knowledge/` (Phase 5 layout reference)
- `packages/sft-tools/` (Phase 3 query_timescale)
- `apps/agents/ops/{anomaly-detector,quality-inspector,operator-assistant,production-planner}/` (Phase 6 agents)
- `apps/api-gateway/src/svc_api_gateway/routers/` (Phase 4-6 routers)
- `simulators/sim-textile/src/sim_textile/` (Phase 3-6 emitter + production_state + quality_event_generator)
- `infra/migrations/timescale/` (Phase 1-6 migrations 001-007 + tests/)
- `tests/e2e/ops/` (Phase 6 E2E pattern)
- `tests/fixtures/ops_scenarios/` + `tests/fixtures/llm_responses/` (Phase 6 fixture layout)
- `docs/docs/agents/operations/` + `docs/docs/en/agents/operations/` (Phase 6 docs bilingue)

**Files Read for pattern extraction:**
1. `packages/sft-agents/src/sft_agents/runtime/clusters.py` (163 L)
2. `packages/sft-agents/src/sft_agents/tools/hitl.py` (227 L)
3. `packages/sft-agents/src/sft_agents/models/enums.py` (99 L)
4. `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py` (343 L)
5. `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py` (head 80 L)
6. `infra/migrations/timescale/007_extend_audit_decisions.sql` (108 L)
7. `infra/migrations/timescale/tests/test_migration_007.py` (head 120 L)
8. `simulators/sim-textile/src/sim_textile/quality_event_generator.py` (274 L)
9. `simulators/sim-textile/src/sim_textile/production_state.py` (head 60 L)
10. `packages/sft-agents/src/sft_agents/tools/audit.py` (head 60 L)
11. `apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py` (head 80 L)
12. `tests/e2e/ops/test_anomaly_detector_scenarios.py` (head 80 L)
13. `docs/docs/agents/operations/anomaly-detector.md` (head 60 L)
14. `packages/sft-domain/src/sft_domain/failure_modes/models.py` (head 100 L)
15. `packages/sft-domain/src/sft_domain/failure_modes.yaml` (head 60 L)

**Pattern extraction date:** 2026-05-23
