# Phase 6: Agents — Operations & Production — Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** ~42 file nuovi/modificati
**Analogs found:** 38 / 42 (4 senza analog interno — fixture LLM, APScheduler service, langdetect wrapper, anomaly baseline loader sono novità ma estendono pattern noti)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/sft-agents/src/sft_agents/llm/factory.py` (EXTEND) | factory/config | request-response | self (`factory.py`) — add 3rd branch | exact (self-extend) |
| `packages/sft-agents/src/sft_agents/llm/mock.py` (NEW) | LLM adapter | request-response | `packages/sft-agents/src/sft_agents/llm/factory.py` + LangChain `BaseChatModel` | role-match |
| `packages/sft-agents/src/sft_agents/tools/hitl.py` (NEW) | LangChain tool | request-response | `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` | exact |
| `packages/sft-agents/src/sft_agents/tools/audit.py` (NEW) | LangChain tool | request-response | `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` | exact |
| `packages/sft-agents/src/sft_agents/runtime/rate_limit.py` (NEW) | runtime middleware | CRUD (PG read-only) | `packages/sft-agents/src/sft_agents/runtime/governor.py` | exact |
| `packages/sft-agents/src/sft_agents/runtime/clusters.py` (EXTEND) | runtime builder | event-driven (routing) | self (`build_cluster_subgraph`) | exact (self-extend) |
| `packages/sft-agents/src/sft_agents/models/enums.py` (EXTEND) | model | n/a (enum) | self (`Decision`, `ActionType`) | exact (self-extend) |
| `packages/sft-domain/src/sft_domain/ops/anomaly.py` (NEW) | model + loader | CRUD (YAML read) | `packages/sft-domain/src/sft_domain/failure_modes/models.py` + `_loader.py` | exact |
| `packages/sft-domain/src/sft_domain/ops/quality.py` (NEW) | model | n/a | `packages/sft-domain/src/sft_domain/failure_modes/models.py` | exact |
| `packages/sft-domain/src/sft_domain/ops/schedule.py` (NEW) | model | n/a | `packages/sft-agents/src/sft_agents/models/evidence.py` (RagCitation) | role-match |
| `packages/sft-domain/src/sft_domain/scheduling/heuristic.py` (NEW) | domain algorithm | transform (pure-fn) | nessun analog scheduling — pattern Pydantic frozen from `failure_modes/models.py` | partial |
| `packages/sft-domain/src/sft_domain/scheduling/constraints.py` (NEW) | domain utility | transform | nessun analog — pattern pure-fn module | partial |
| `packages/sft-domain/orders.yaml` (NEW) | config (data) | n/a | `packages/sft-domain/failure_modes.yaml` | exact |
| `packages/sft-domain/asset_capacity.yaml` (NEW) | config (data) | n/a | `packages/sft-assets/src/sft_assets/registry.yaml` | exact |
| `packages/sft-domain/anomaly_baselines.yaml` (NEW) | config (data) | n/a | `packages/sft-domain/failure_modes.yaml` | exact |
| `packages/sft-domain/failure_modes.yaml` (EXTEND) | config | n/a | self | exact (self-extend) |
| `apps/agents/ops/operator-assistant/src/ops_operator_assistant/agent.py` (NEW) | agent (controller) | request-response | nessun analog ReAct — base pattern `RagSearchTool` injection + `human_approval_node` flow | partial |
| `apps/agents/ops/operator-assistant/src/ops_operator_assistant/prompts.py` (NEW) | utility (static strings) | n/a | nessun analog — convenzione struttura |  |
| `apps/agents/ops/operator-assistant/src/ops_operator_assistant/validators.py` (NEW) | utility | transform | nessun analog citation validator |  |
| `apps/agents/ops/operator-assistant/src/ops_operator_assistant/lang_detect.py` (NEW) | utility | transform | nessun analog langdetect — module init pattern |  |
| `apps/agents/ops/operator-assistant/src/ops_operator_assistant/models.py` (NEW) | model | n/a | `apps/api-gateway/src/svc_api_gateway/models/requests.py` | exact |
| `apps/agents/ops/production-planner/src/ops_production_planner/agent.py` (NEW) | agent (service) | transform + LLM call | `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py` | role-match |
| `apps/agents/ops/production-planner/src/ops_production_planner/prompts.py` (NEW) | utility (static) | n/a | n/a |  |
| `apps/agents/ops/production-planner/src/ops_production_planner/models.py` (NEW) | model | n/a | `apps/api-gateway/src/svc_api_gateway/models/requests.py` | exact |
| `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py` (NEW) | agent (handler) | event-driven (NATS) | `packages/sft-agents/src/sft_agents/hitl/interrupt.py` (flow shape) | role-match |
| `apps/agents/ops/quality-inspector/src/ops_quality_inspector/nats_consumer.py` (NEW) | service/consumer | event-driven (pub-sub) | `services/ot-bridge/src/svc_ot_bridge/main.py` (JetStream loop) — referenced in research | partial |
| `apps/agents/ops/quality-inspector/src/ops_quality_inspector/grader.py` (NEW) | service | request-response (LLM call) | nessun analog grading; pattern Pydantic clamp da `proposed_action.py` |  |
| `apps/agents/ops/quality-inspector/src/ops_quality_inspector/prompts.py` (NEW) | utility | n/a | n/a |  |
| `apps/agents/ops/quality-inspector/src/ops_quality_inspector/models.py` (NEW) | model | n/a | `packages/sft-domain/src/sft_domain/failure_modes/models.py` | exact |
| `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py` (NEW) | agent (controller) | batch | `packages/sft-agents/src/sft_agents/runtime/governor.py` (background batch) | role-match |
| `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/baseline.py` (NEW) | domain utility | transform | `packages/sft-domain/src/sft_domain/failure_modes/_loader.py` |  |
| `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/models.py` (NEW) | model | n/a | `packages/sft-agents/src/sft_agents/models/evidence.py` | exact |
| `services/agents-scheduler/pyproject.toml` (NEW) | config | n/a | `services/knowledge-ingest/pyproject.toml` | exact |
| `services/agents-scheduler/src/svc_agents_scheduler/__main__.py` (NEW) | service entrypoint | event-driven (cron) | `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py` + governor loop pattern | role-match |
| `services/agents-scheduler/src/svc_agents_scheduler/scheduler.py` (NEW) | service | event-driven | nessun analog APScheduler |  |
| `services/agents-scheduler/src/svc_agents_scheduler/client.py` (NEW) | service utility | request-response (HTTP) | `apps/api-gateway/src/svc_api_gateway/routers/threads.py` (httpx) |  |
| `services/agents-scheduler/Dockerfile` (NEW) | config | n/a | `services/knowledge-ingest/Dockerfile` (assunto esistere) o `simulators/sim-textile/Dockerfile` | exact |
| `simulators/sim-textile/src/sim_textile/quality_event_generator.py` (NEW) | service (emitter) | event-driven (NATS publish) | `simulators/sim-textile/src/sim_textile/emitter.py` | exact |
| `simulators/sim-textile/src/sim_textile/production_state.py` (NEW) | model + state | n/a (in-process) | `simulators/sim-textile/src/sim_textile/models.py` (EmitterState) | exact |
| `apps/api-gateway/src/svc_api_gateway/routers/quality.py` (NEW) | controller (route) | request-response | `apps/api-gateway/src/svc_api_gateway/routers/approvals.py` | exact |
| `apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py` (NEW) | controller (route) | request-response | `apps/api-gateway/src/svc_api_gateway/routers/threads.py` | exact |
| `tests/fixtures/llm_responses/<agent>/<scenario>.jsonl` (NEW) | test fixture | n/a | nessun analog — formato definito in RESEARCH §Pattern 2 |  |
| `tests/fixtures/ops_scenarios/<agent>/<scenario>.yaml` (NEW) | test fixture | n/a | `packages/sft-domain/failure_modes.yaml` (loader yaml.safe_load) | partial |
| `tests/e2e/ops/test_<agent>_scenarios.py` (NEW) | test | event-driven | `tests/e2e/test_hitl_cycle.py` (assunto esistere — Phase 4) | role-match |
| `tests/conftest.py` (EXTEND) | test fixture | n/a | self | exact (self-extend) |

---

## Pattern Assignments

### `packages/sft-agents/src/sft_agents/llm/factory.py` (EXTEND — add `mock` branch)

**Analog:** self (lines 22-41 + 65-90)

**Existing whitelist + dispatch pattern** (lines 22-41):
```python
LLMBackend = Literal["ollama", "vllm"]
_VALID_BACKENDS = ("ollama", "vllm")

def _resolve_backend(backend: LLMBackend | str | None) -> str:
    """Read LLM_BACKEND env var when arg is None; validate against whitelist."""
    if backend is None:
        backend = os.environ.get("LLM_BACKEND", "ollama")
    if backend not in _VALID_BACKENDS:
        raise RuntimeError(
            f"LLM_BACKEND must be one of ollama|vllm, got {backend!r}"
        )
    return backend
```

**Branch dispatch pattern** (lines 65-90 — adapt third elif for `mock`):
```python
if resolved == "ollama":
    from langchain_ollama import ChatOllama  # local import
    model = os.environ.get("OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL)
    ...
    return ChatOllama(model=model, base_url=base_url, ...)
```

**Adaptations for Phase 6:**
- Expand `_VALID_BACKENDS = ("ollama", "vllm", "mock")` + `LLMBackend = Literal["ollama","vllm","mock"]`.
- Add `if resolved == "mock":` branch — local import `from sft_agents.llm.mock import MockReplayChatModel`; read `MOCK_LLM_FIXTURE` env var (fail-fast if missing — same pattern as `TIMESCALE_DSN` in `pipeline.py`); return `MockReplayChatModel(fixture_path=fixture)`.
- Preserve `temperature`/`seed`/`logger.info("llm_factory_build", ...)` shape for audit consistency.

---

### `packages/sft-agents/src/sft_agents/llm/mock.py` (NEW — MockReplayChatModel)

**Analog:** `packages/sft-agents/src/sft_agents/llm/factory.py` (lines 1-20 module docstring + structlog pattern) + LangChain `BaseChatModel` ABC.

**Module docstring pattern** (factory.py lines 1-10):
```python
"""Provider-agnostic LLM factory (CORE-05, CORE-06).

Env-var dispatch idiom mirrors `services/ot-bridge/src/svc_ot_bridge/main.py:62-71`:
    LLM_BACKEND=ollama → langchain_ollama.ChatOllama (dev — Qwen2.5-7B Q4_K_M)
    ...
"""
```

**Adaptations for Phase 6:**
- Subclass `BaseChatModel` per RESEARCH §Pattern 2 (lines 423-467 of 06-RESEARCH.md).
- `fixture_path: pathlib.Path` come parameter; load JSONL `[json.loads(line) for line in fh if line.strip()]` (mirror `_loader.py` pattern of read_text + parse).
- `_prompt_hash(messages)` SHA-256 over `m.type:m.content` concatenation; fallback ordered replay when hash miss (emit `LangfuseWarning` per Pitfall 10).
- `_generate` raise `NotImplementedError("MockReplayChatModel is async-only")` — mirror `RagSearchTool._run` pattern (rag.py lines 93-98).
- Return `ChatResult(generations=[ChatGeneration(message=AIMessage(...))])` with `tool_calls` + `usage_metadata` from fixture entry.

---

### `packages/sft-agents/src/sft_agents/tools/hitl.py` (NEW — EscalateToSupervisorTool)

**Analog:** `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` (entire file — 126 lines)

**Imports + module docstring pattern** (rag.py lines 1-23):
```python
"""RagSearchTool — LangChain BaseTool for hybrid retrieval with ACL pre-filter.

D-66 LOCKED schema:
    - ``args_schema = RagSearchInput`` (frozen + extra=forbid).
    - Async-only — ``_run`` raises ``NotImplementedError`` (PATTERNS Shared Pattern 7).
    - Pipeline iniettato via ``__init__`` (private attribute ``_pipeline``).
"""
from __future__ import annotations
from typing import Any, Literal
import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
```

**Input schema pattern** (rag.py lines 31-48 — frozen + extra=forbid + range validators):
```python
class RagSearchInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    query: str
    user_roles: list[str]
    category: Literal["sop", "manuals", "troubleshooting", "training"] = "sop"
    k: int = Field(default=5, ge=1, le=20)
```

**Tool class structure** (rag.py lines 55-122):
```python
class RagSearchTool(BaseTool):
    name: str = "rag_search"
    description: str = (
        "Search knowledge base chunks with hybrid retrieval ..."
    )
    args_schema: type[BaseModel] = RagSearchInput
    _pipeline: Any = PrivateAttr()

    def __init__(self, pipeline: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pipeline = pipeline

    def _run(self, *args: Any, **kwargs: Any) -> list[RagCitation]:
        raise NotImplementedError(
            "RagSearchTool is async-only. Use `await tool.ainvoke({...})` instead."
        )

    async def _arun(self, query: str, user_roles: list[str], ...) -> list[RagCitation]:
        return await self._pipeline.search(...)
```

**Adaptations for Phase 6:**
- Replace `RagSearchInput` con `EscalateInput` (3 fields: `reason`, `suggested_action`, `evidence_summary`, all `Field(min_length=10, max_length=2000)`).
- 4 private attrs in `__init__`: `_audit_writer`, `_queue_writer`, `_nats`, `_safety_middleware` (PATTERN della RagSearchTool con 1 attr → estendi a 4).
- `_arun` costruisce `ProposedAction(action_type=ActionType.ESCALATION_REQUEST, args=...)`, chiama `self._safety.check(action)` (Pitfall §9 — Safety Interlock uniformity), poi `from langgraph.types import interrupt` + `decision = interrupt({...})` con payload strutturato. Idempotency Pitfall §3: nessuna audit write prima di interrupt() (vedi `human_approval_node` lines 170-185 → `queue_writer.insert(approval)` PRIMA del interrupt è OK perché ID sha256-deterministic; replica stesso pattern qui).

---

### `packages/sft-agents/src/sft_agents/tools/audit.py` (NEW — LogEventTool)

**Analog:** `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` (stesso scheletro BaseTool)

**Adaptations for Phase 6:**
- Input schema con `event_type: Literal[...]` + `summary: str` + `payload: dict[str, Any]`.
- 1 private attr `_audit_writer: AuditWriter`.
- `_arun` costruisce `AuditRecord(decision=Decision.AUTO, ...)` (no HITL, audit-only).
- **NB:** Decision enum **non** include "logged" — usa `Decision.AUTO` (vedi `models/enums.py` lines 24-39) OR aggiungi `Decision.LOGGED` in enum extension task (research Open Question 1 verifica DB migration richiesta).

---

### `packages/sft-agents/src/sft_agents/runtime/rate_limit.py` (NEW — PG sliding window)

**Analog:** `packages/sft-agents/src/sft_agents/runtime/governor.py` (entire file — 227 lines)

**SQL constants + pool pattern** (governor.py lines 35-55):
```python
# T-V5-sql: constants only. Window + cooldown intervals are server-side literals.
_GOVERNOR_SCAN_SQL: str = (
    "SELECT count(*) FILTER (WHERE decision='auto') AS auto_count, "
    "count(*) AS total "
    "FROM audit.actions "
    "WHERE ts > NOW() - INTERVAL '1 hour' "
    "AND decision NOT IN ('escalated','governor_alert','timed_out')"
)
```

**Class constructor pattern** (governor.py lines 58-82):
```python
class Governor:
    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: "AuditWriter",
        nats_publisher: Any,
        queue_writer: ApprovalQueueWriter,
        scan_interval_s: float = 60.0,
        threshold: float = 0.80,
        min_sample: int = 20,
    ) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool
        ...
```

**Query execution pattern** (governor.py lines 85-95):
```python
async def _scan_once(self) -> bool:
    async with self._pool.acquire() as conn:
        cooldown = await conn.fetchrow(_COOLDOWN_SQL)
        ...
        row = await conn.fetchrow(_GOVERNOR_SCAN_SQL)
        auto_count = int(row["auto_count"] or 0)
        total = int(row["total"] or 0)
```

**Adaptations for Phase 6:**
- Class `RateLimiter` con costruttore keyword-only: `pool`, `agent_id: str`, `limit: int = 12`, `window_minutes: int = 60`.
- SQL constant `_COUNT_RECENT_SQL = "SELECT COUNT(*) FROM audit.actions WHERE agent_id = $1 AND action_type = $2 AND ts >= $3"` — parametrizzato $1..$3 (T-V5-sql).
- Metodo `async def check_and_emit(self, action_type: str) -> tuple[bool, int]` — calcola cutoff `datetime.now(timezone.utc) - self._window`, fetch count, ritorna `(count < limit, count)`.
- **NO background loop** — `RateLimiter` è invocato dal `AnomalyDetector.__call__` (D-AD-03 docstring concurrency note: PG MVCC race accettabile per "approximately 12" semantic).

---

### `packages/sft-agents/src/sft_agents/runtime/clusters.py` (EXTEND — add `build_ops_subgraph`)

**Analog:** self (lines 20-77 `build_cluster_subgraph`)

**Existing linear-builder pattern** (clusters.py lines 53-75):
```python
g: StateGraph = StateGraph(AgentState)

def _make_placeholder(slug: str):
    async def _placeholder_node(_state: AgentState) -> dict:
        _log.info("cluster_child_placeholder", cluster=cluster_name, agent_id=slug, ...)
        return {}
    _placeholder_node.__name__ = f"_placeholder_{slug.replace('-', '_')}"
    return _placeholder_node

for slug in child_agent_slugs:
    g.add_node(slug, _make_placeholder(slug))

# Linear skeleton: START → slug[0] → slug[1] → ... → END.
g.add_edge(START, child_agent_slugs[0])
```

**Adaptations for Phase 6 (D-X OPS routing):**
- New top-level function `build_ops_subgraph(child_callables: dict[str, Callable]) -> StateGraph` per RESEARCH §Pattern 9 (lines 805-823).
- Replace linear `add_edge(START, slug[0])` con `add_conditional_edges(START, _route, {slug: slug for slug in child_callables})`.
- `_route(state) → str` reads `state.get("target_agent") or "operator-assistant"`; warning log su unknown target.
- Each `child_callable` è già il `__call__(state) -> dict` async dell'agente (NOT placeholder — Phase 6 wires real callables).
- Mantenere export `__all__` con sia `build_cluster_subgraph` (placeholder-preserving per altre cluster) sia nuovo `build_ops_subgraph`.

---

### `packages/sft-agents/src/sft_agents/models/enums.py` (EXTEND — add Decision + ActionType values)

**Analog:** self (lines 24-65 — `Decision`, `ActionType`)

**Existing enum pattern** (enums.py lines 24-39):
```python
class Decision(str, Enum):
    AUTO = "auto"
    HITL_OPERATOR = "hitl_operator"
    HITL_SUPERVISOR = "hitl_supervisor"
    HITL_MANAGER = "hitl_manager"
    INTERLOCK_REJECT = "interlock_reject"
    ROLLED_BACK = "rolled_back"
    TIMED_OUT = "timed_out"
    GOVERNOR_ALERT = "governor_alert"
    ESCALATED = "escalated"
```

**Adaptations for Phase 6 (RESEARCH Open Question 1 + A8):**
- Aggiungere `Decision.SUPPRESSED = "suppressed"` (per AnomalyDetector rate-limit D-AD-03).
- Aggiungere `Decision.LOGGED = "logged"` (per `LogEventTool` D-OA-02 #5).
- Aggiungere `ActionType.ESCALATION_REQUEST = "ESCALATION_REQUEST"` (per `EscalateToSupervisorTool` Pitfall §9).
- Aggiungere `ActionType.QUALITY_VERDICT = "QUALITY_VERDICT"`, `ActionType.SCHEDULE_DRAFT = "SCHEDULE_DRAFT"`, `ActionType.ANOMALY_ALERT = "ANOMALY_ALERT"`.
- **Verifica DB migration** (Plan task): `grep -n "CHECK.*decision" infra/migrations/` per scoprire se è TEXT+CHECK o pg_enum. Se TEXT+CHECK → `ALTER TABLE audit.actions DROP CONSTRAINT ... ADD CONSTRAINT ...`; se pg_enum → `ALTER TYPE ... ADD VALUE 'suppressed'`. Migration file: `infra/migrations/timescale/007_extend_audit_decisions.sql`.

---

### `packages/sft-domain/src/sft_domain/ops/anomaly.py` (NEW — Anomaly model + loader)

**Analog:**
- Models: `packages/sft-domain/src/sft_domain/failure_modes/models.py` (lines 17-80)
- Loader: `packages/sft-domain/src/sft_domain/failure_modes/_loader.py` (lines 1-75)

**Pydantic model pattern** (failure_modes/models.py lines 26-50):
```python
class FailureMode(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}  # immutable, strict schema

    id: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^[a-z][a-z0-9_]*$",
            description="Identificatore snake_case lowercase",
        ),
    ]
    name_it: Annotated[str, Field(min_length=1, description="...")]
    severity: Annotated[
        Literal["low", "medium", "high"],
        Field(description="Severita': low | medium | high"),
    ] = "medium"
```

**Loader pattern** (_loader.py lines 19-58):
```python
_YAML_PATH = pathlib.Path(__file__).parent.parent / "failure_modes.yaml"

@lru_cache(maxsize=1)
def load_failure_modes() -> tuple[FailureMode, ...]:
    if not _YAML_PATH.exists():
        raise FileNotFoundError(...)
    raw_text = _YAML_PATH.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load (T-05-03-01)
    if not isinstance(raw_data, dict) or "failure_modes" not in raw_data:
        raise ValueError(...)
    entries = raw_data["failure_modes"]
    return tuple(FailureMode.model_validate(entry) for entry in entries)
```

**Adaptations for Phase 6:**
- Crea `AnomalyBaseline` Pydantic frozen con: `asset_family: Literal[...] (da AssetFamily)`, `sensor_id: str`, `low: float`, `high: float`, `unit: str`, `severity_mapping: dict[str, float]` (banda → severity).
- Metodo `is_within_band(value: float) -> bool` + `severity_for(value: float) -> Literal["minor","major","critical"]`.
- Crea `Anomaly` Pydantic frozen: `id: UUID`, `asset_id`, `sensor_id`, `value`, `baseline_low`, `baseline_high`, `timestamp: datetime` (tz-aware via `field_validator` da `evidence.py` lines 17-24), `severity`.
- Loader `load_anomaly_baselines(yaml_path)` con `@lru_cache(maxsize=1)` + `yaml.safe_load`; ritorna `dict[tuple[str,str], AnomalyBaseline]` keyed `(asset_family, sensor_id)`.
- File YAML `packages/sft-domain/anomaly_baselines.yaml` segue convenzione `failure_modes.yaml`: top-level key `anomaly_baselines: [{...}, ...]`.

---

### `packages/sft-domain/src/sft_domain/ops/quality.py` (NEW — QualityEvent + QualityVerdict)

**Analog:** `packages/sft-domain/src/sft_domain/failure_modes/models.py` (model shape) + `packages/sft-agents/src/sft_agents/models/evidence.py` (tz-aware datetime pattern)

**tz-aware validator pattern** (evidence.py lines 17-24):
```python
def _tz_aware(v: datetime) -> datetime:
    """Reject naive datetime (Pitfall 7)."""
    if v.tzinfo is None:
        raise ValueError(
            f"Datetime field must be tz-aware, got naive: {v!r}. "
            "Use datetime.now(timezone.utc) or datetime(..., tzinfo=timezone.utc)."
        )
    return v
```

**Adaptations for Phase 6 (RESEARCH §Pattern 10 + D-QI-01..04):**
- `DefectType = Literal["broken_end","mispick","slub","neppy","selvage_fault","shade_deviation","unlevel_dyeing"]` (Phase 2 taxonomy).
- `Severity = Literal["minor","major","critical"]` (D-QI-03).
- `QualityEvent` frozen + extra=forbid: `event_id: UUID`, `asset_id: str`, `dye_lot_id: Annotated[str, Field(pattern=r"^DL-[A-Z0-9-]+-\d{8}-[0-9a-f]+$")]` (D-QI-04 regex), `defect_type: DefectType`, `defect_length_inches: Annotated[float, Field(ge=0.0)]`, `full_width: bool = False`, `position_meters: float`, `timestamp: datetime` (with `_tz_aware` validator), `source: Literal["simulator","operator"]`.
- `QualityVerdict` frozen + extra=forbid: `score: Annotated[int, Field(ge=0, le=4)]`, `severity: Severity`, `rationale_md: str`, `citations: list[RagCitation]` (import from `sft_agents.models.evidence`).

---

### `packages/sft-domain/src/sft_domain/ops/schedule.py` (NEW — ScheduleDraft + OrderSpec + AssetCapacity)

**Analog:** `packages/sft-agents/src/sft_agents/models/evidence.py` (RagCitation + tz-aware validator)

**Adaptations for Phase 6 (CONTEXT D-PP-03):**
- `OrderSpec` frozen: `order_id`, `sku`, `quantity_meters: float`, `due_at: datetime`, `processing_minutes: int`, `priority: int`, `compatible_families: list[str]`, `dye_lot_id: str | None`.
- `AssetCapacity` frozen: `asset_id`, `asset_family`, `max_meters_per_hour: float`, `max_concurrent_dye_lots: int = 1`, `dye_lot_changeover_minutes: int = 30`, `downtime_windows: list[...]` (opzionale).
- `ScheduleDraftItem` frozen: `order_id`, `asset_id`, `start_at`, `end_at`, `dye_lot_id: str | None`, `sequence: int`.
- `ScheduleDraft` frozen: `schedule_id: UUID`, `strategy: Literal["spt","edd"]`, `horizon_start`, `horizon_end`, `items: list[ScheduleDraftItem]`, `unscheduled_orders: list[str] = []` (Pitfall §8 surface gap), `rationale_md: str`, `citations: list[RagCitation]`, `created_at: datetime`.
- Loader functions `load_orders()` + `load_asset_capacity()` con `@lru_cache(maxsize=1)` + `yaml.safe_load` — mirror `_loader.py`.

---

### `packages/sft-domain/src/sft_domain/scheduling/heuristic.py` (NEW — SPT/EDD pure-fn)

**Analog:** nessun analog scheduling — Phase 6 introduce nuovo dominio. Pattern Pydantic immutability inherited from `failure_modes/models.py`.

**Adaptations for Phase 6 (RESEARCH §Pattern 5 lines 595-651):**
- Pure functions `schedule_spt(orders, capacity, failure_modes, horizon_start, horizon_end) -> ScheduleDraft` + `schedule_edd(...)`.
- Sort key differenzia SPT (`processing_minutes`) vs EDD (`due_at`).
- Helper `_earliest_slot(timeline, order, cap, failure_modes, horizon_start) -> datetime` con setup-time + dye_lot compatibility.
- **Output immutabile** (CONTEXT D-PP-03): tutti i `ScheduleDraftItem` via `.model_validate(...)` (no mutation); `timeline` interno è list append solo dentro function scope.
- **Determinismo**: `datetime.now(UTC)` per `created_at`; UUID4 con seed 42 NON è deterministico — accettato perché `schedule_id` è solo handle, contenuto deterministico from `(orders, capacity, strategy)`.
- LLM rationale è **out-of-scope** per `heuristic.py` (pure-fn). LLM call happens in `production-planner/src/.../agent.py` post-scheduling (RESEARCH lines 656-666).

---

### `packages/sft-domain/orders.yaml` + `asset_capacity.yaml` + `anomaly_baselines.yaml` (NEW)

**Analog:** `packages/sft-domain/failure_modes.yaml` (formato top-level list) + `packages/sft-assets/src/sft_assets/registry.yaml` (asset_id riferimenti).

**Convention:** top-level key plural snake_case (`orders:`, `asset_capacity:`, `anomaly_baselines:`); ogni entry è dict che `.model_validate()` produce Pydantic frozen.

**CI validator** (Pitfall §8): nuovo `packages/sft-domain/tests/test_yaml_validators.py` verifica cross-ref `orders.yaml.compatible_families ⊆ asset_capacity.yaml.asset_family` e `asset_capacity.yaml.asset_id ⊆ packages/sft-assets/registry.yaml.asset_id`.

---

### `packages/sft-domain/failure_modes.yaml` (EXTEND — add hitl_tier + setup_minutes + severity_band)

**Analog:** self + `packages/sft-domain/src/sft_domain/failure_modes/models.py` (extend `FailureMode` model).

**Adaptations for Phase 6 (D-QI-03 + D-PP-01):**
- Add optional fields a `FailureMode`: `hitl_tier: Literal["auto-log","supervisor","manager+safety"] = "supervisor"`, `setup_minutes: int = 0`, `severity_band: dict[Literal["minor","major","critical"], dict[str, Any]]` (override per defect-frequency / size / etc.).
- YAML entries esistenti rimangono valide (campi opzionali con default).

---

### `apps/agents/ops/operator-assistant/src/ops_operator_assistant/agent.py` (NEW — ReAct wrapper)

**Analog:**
- ReAct loop: RESEARCH §Pattern 1 (lines 352-395 di 06-RESEARCH.md) — no internal analog yet.
- Tool injection + ACL: `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` lines 83-91 (`__init__(pipeline, **kw)`).
- HITL safety wrapping: `packages/sft-agents/src/sft_agents/hitl/interrupt.py` lines 88-260 (full `human_approval_node`).

**Tool instantiation pattern** (Pitfall §2 — per-request, NOT singleton) deriva da RagSearchTool init:
```python
def __init__(self, pipeline: Any, **kwargs: Any) -> None:
    super().__init__(**kwargs)
    self._pipeline = pipeline
```
→ Phase 6 lo invoca per-request nel handler API: `tools = [RagSearchTool(pipeline=rag_pipeline), TraverseGraphTool(...), QueryTimescaleTool(), EscalateToSupervisorTool(audit_writer=aw, ...), LogEventTool(...)]` (RESEARCH lines 365-371).

**Adaptations for Phase 6 (D-OA-01..04 + safe_invoke Phase 4):**
- Classe `OperatorAssistantAgent` con `__init__(self, *, rag_pipeline, neo4j_client, pool, audit_writer, queue_writer, nats, safety, checkpointer)`.
- Method `_build_react_runnable()` chiama `langgraph.prebuilt.create_react_agent(model=build_chat_model(), tools=self._build_tools(...), checkpointer=self._checkpointer, prompt=SYSTEM_PROMPT_BILINGUAL)`.
- Method `async __call__(self, state) -> dict`: lang detect (chiamata a `lang_detect.detect_language(state["query"])`), then `safe_invoke(self._runnable, {"messages": [HumanMessage(...)]}, config={"recursion_limit": 5, "configurable": {"thread_id": state["thread_id"]}, "callbacks": [langfuse]})`, then `await validate_or_replan(state, response)`.
- **NEVER instantiate tools as module-level singletons** (Pitfall §2) — costruiscili per-call con `user_roles` from state.

---

### `apps/agents/ops/operator-assistant/src/ops_operator_assistant/validators.py` (NEW — citation validator)

**Analog:** nessun analog citation validator — convenzione presa da RESEARCH §Pattern 7 (lines 723-754).

**Adaptations:** funzione `async def validate_or_replan(state, response, *, react_agent, config, retries=0, max_retries=1)`:
- `used_rag = any(isinstance(m, ToolMessage) and m.name == "rag_search" for m in state["messages"])`.
- `has_inline = bool(re.search(r"\[\d+\]", response.content))`.
- Se mancano citation → augmented prompt → recursive call con `retries+1`.
- Su `retries >= max_retries`: log `citation_missing_after_replan` warning, return response con `additional_kwargs["citations_missing"] = True` (immutable copy: `response.copy(update={...})` — Pydantic v2 idiom).

---

### `apps/agents/ops/operator-assistant/src/ops_operator_assistant/lang_detect.py` (NEW)

**Analog:** nessun analog. Convenzione module-level init (Pitfall §6 lines 936-941).

**Adaptations:**
```python
from langdetect import DetectorFactory, detect

# Single seed at module import — never reset (Pitfall §6).
DetectorFactory.seed = 42

def detect_language(text: str) -> Literal["it", "en"]:
    try:
        lang = detect(text)
    except Exception:
        return "en"  # fallback
    return "it" if lang.startswith("it") else "en"
```

---

### `apps/agents/ops/operator-assistant/src/ops_operator_assistant/models.py` (NEW — Request/Response Pydantic)

**Analog:** `apps/api-gateway/src/svc_api_gateway/models/requests.py` (assunto esistere — riferimento approvals.py line 51).

**Adaptations:**
- `OperatorChatRequest` frozen + extra=forbid: `query: Annotated[str, Field(min_length=1, max_length=2000)]`, `user_roles: list[str]`, `thread_id: str`, `target_agent: str | None = None`.
- `OperatorChatResponse` frozen: `response_md: str`, `citations: list[RagCitation]`, `citations_missing: bool = False`, `tool_calls: list[ToolCall]`, `lang: Literal["it","en"]`.

---

### `apps/agents/ops/production-planner/src/ops_production_planner/agent.py` (NEW)

**Analog:** `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py` (orchestrator pattern: collaborators injected, compose pure-fn + side-effect calls).

**Orchestrator pattern** (pipeline.py lines 31-77 module docstring + collaborator composition):
```python
"""Pipeline orchestrator (Plan 05-10 Task 1).

Chains the Phase 5 SDK primitives into the end-to-end ingest flow per D-67 + D-68:
    parse → (content_hash gate) → chunk → embed → Neo4j MERGE first → Qdrant upsert
"""
# Collaborators passed in — backend-agnostic (testable)
```

**Adaptations for Phase 6 (D-PP-01 + D-PP-03):**
- Classe `ProductionPlannerAgent` con costruttore keyword-only: `rag_pipeline`, `audit_writer`, `queue_writer`, `nats`, `safety`.
- `async __call__(state) -> dict`:
  1. `orders = load_orders(); capacity = load_asset_capacity(); fms = load_failure_modes()`.
  2. `draft = schedule_spt(...)` or `schedule_edd(...)` based on `state["strategy"]` (deterministic algo).
  3. `citations = await self._rag_pipeline.search(query="textile scheduling SOPs", ...)`.
  4. `rationale_response = await build_chat_model().ainvoke(build_rationale_prompt(draft, citations))`.
  5. Update draft: `final_draft = draft.model_copy(update={"rationale_md": ..., "citations": citations})` (immutable Pydantic v2).
  6. `proposed_action = ProposedAction(action_type=ActionType.SCHEDULE_DRAFT, args=final_draft.model_dump(mode="json"))`.
  7. Trigger `human_approval_node(state, proposed_action=..., tier=Tier.SUPERVISOR, ...)` — riusa `hitl/interrupt.py`.

---

### `apps/agents/ops/quality-inspector/src/ops_quality_inspector/nats_consumer.py` (NEW)

**Analog:** RESEARCH §Pattern 3 (lines 506-540) — no exact internal analog (Phase 3 ot-bridge is OPC-UA→NATS publisher, not durable consumer).

**Adaptations for Phase 6 (D-QI-01):**
- Module-level `_log = structlog.get_logger("agent.quality-inspector.consumer")` (convention).
- Function `async def run_qi_consumer(js, qi_handler, shutdown: asyncio.Event)` con loop pattern stesso shape di `governor.py` lines 205-225 (background asyncio + shutdown event).
- `psub = await js.pull_subscribe(subject="quality.events.>", durable="qi-consumer", stream="QUALITY_STREAM")`.
- For each msg: `QualityEvent.model_validate_json(msg.data)` → `if already_processed(event.event_id): await msg.ack(); continue` → `await qi_handler(event)` → `await msg.ack()`. `ValidationError → msg.term()`; transient → `msg.nak()`.
- Idempotency check via SQL constant: `_DEDUP_SQL = "SELECT 1 FROM audit.actions WHERE action_id = $1 LIMIT 1"` (T-V5-sql).

---

### `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py` + `grader.py` (NEW)

**Analog:** `packages/sft-agents/src/sft_agents/hitl/interrupt.py` (HITL routing shape — lines 130-260).

**Adaptations for Phase 6 (D-QI-02 + D-QI-03):**
- `grader.py`: `async def grade_quality_event(event, rag_pipeline, audit_writer) -> QualityVerdict`. Sequence: rag_tool.ainvoke({"query": f"4-point grading {event.defect_type}", ...}) → `build_chat_model().ainvoke(prompt)` → `QualityVerdict.model_validate_json(raw.content)` con try/except `ValidationError → fallback severity="major"` (Pitfall §7).
- `agent.py`: classe wrapper che orchestra `nats_consumer` + `grader` + HITL routing (severity → `tier_for = {"minor": None, "major": Tier.SUPERVISOR, "critical": Tier.MANAGER}`); per `severity=minor` → `audit_writer.write_auto(...)` (riusa `Decision.AUTO`); per `major`/`critical` → `human_approval_node(...)`.

---

### `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py` (NEW)

**Analog:** `packages/sft-agents/src/sft_agents/runtime/governor.py` (batch scan + audit write pattern + class structure).

**Class init pattern** (governor.py lines 58-82) → AnomalyDetector con `pool`, `baselines_path`, `asset_registry`, `RateLimiter(pool, agent_id="anomaly-detector", limit=12)`.

**Adaptations for Phase 6 (D-AD-01..03):**
- `__init__`: `self._tool = QueryTimescaleTool()`; `self._baselines = load_anomaly_baselines(...)`; `self._limiter = RateLimiter(...)`.
- `async __call__(state) -> dict`:
  - `window_minutes = state.get("window_minutes", 15)`.
  - Loop over `self._assets`: `df = await self._tool._arun(asset_id=asset.asset_id, time_range=(now - timedelta(minutes=window_minutes), now))`.
  - Per row: lookup `baseline = self._baselines.get((asset.asset_family.value, row.sensor_id))`; se outside band → `(allowed, count) = await self._limiter.check_and_emit("anomaly")`; if `not allowed` → log `anomaly_suppressed` + audit row `Decision.SUPPRESSED`; else append a `anomalies` + audit row `ActionType.ANOMALY_ALERT`.
- Return `{"anomalies": anomalies}` (state delta — no in-place mutation).

---

### `services/agents-scheduler/` (NEW container)

**Analog:**
- `pyproject.toml`: `services/knowledge-ingest/pyproject.toml` (lines 1-54)
- `__main__.py`: `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py` (lines 1-65 structlog + Typer scaffold)
- Loop pattern: `packages/sft-agents/src/sft_agents/runtime/governor.py` lines 205-225 (shutdown event + asyncio loop)

**pyproject.toml pattern** (knowledge-ingest lines 1-30):
```toml
[project]
name = "svc-knowledge-ingest"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
  "asyncpg>=0.29",
  "typer>=0.12",
  "click>=8.1",
  "structlog>=24.4",
  "pydantic>=2.7",
  "sft-knowledge",
  ...
]
[tool.uv.sources]
sft-knowledge = { workspace = true }
[project.scripts]
knowledge-ingest = "svc_knowledge_ingest.__main__:app"
```

**structlog + Typer pattern** (__main__.py lines 30-62):
```python
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)
logger = structlog.get_logger("svc-knowledge-ingest")
app = typer.Typer(...)
```

**Adaptations for Phase 6 (D-AD-04 + RESEARCH §Pattern 4):**
- `pyproject.toml`: package `svc-agents-scheduler`; dependencies = `["APScheduler>=3.10.4", "httpx>=0.28", "structlog>=24.4", "typer>=0.12", "fastapi"]` (no PG; reads only env vars). Workspace ref `sft-agents` per audit dual-write helper if needed.
- `__main__.py`: replica struttura ma con `asyncio.run(main())` invece di typer commands. Setup `AsyncIOScheduler(timezone="UTC")` + `sched.add_job(trigger_anomaly_scan, CronTrigger.from_crontab(cron), kwargs={...}, id="anomaly-detector-scan", coalesce=True, max_instances=1, misfire_grace_time=300)` (Pitfall §5).
- `client.py`: `httpx.AsyncClient(timeout=60, transport=httpx.AsyncHTTPTransport(retries=3))` chiama `POST {API_GATEWAY_URL}/v1/agents/anomaly-detector/scan` con body `{"window_minutes": ..., "triggered_by": "scheduler"}`.
- Shutdown handler con `loop.add_signal_handler(SIGINT|SIGTERM, stop.set)`.

---

### `simulators/sim-textile/src/sim_textile/quality_event_generator.py` + `production_state.py` (NEW)

**Analog:** `simulators/sim-textile/src/sim_textile/emitter.py` (lines 38-100) — asyncio task + fault chain + structlog.

**Emitter pattern** (emitter.py lines 38-77):
```python
async def asset_emitter(asset, profile, vars_map, *, time_scale=1.0):
    state = EmitterState()
    dt = (1.0 / profile.sample_rate_hz) / time_scale
    asset_family = asset.asset_family.value
    asset_id = asset.asset_id
    logger.info("emitter_started", asset_id=asset_id, family=asset_family, ...)
    try:
        while True:
            now = datetime.now(UTC)  # SEMPRE tz-aware
            for tag_ref in asset.tags:
                ...
```

**Adaptations for Phase 6 (D-QI-01 + D-QI-04 + RESEARCH §Pattern 10):**
- `production_state.py`: `ProductionState` dataclass con `asset_id`, `current_dye_lot_id`, `rotation_interval`, `_last_rotation`; method `maybe_rotate(now)` ruota a `f"DL-{asset_id}-{ymd}-{seq}"` con `secrets.token_hex(2)` (no PG persistence — in-process Phase 6).
- `quality_event_generator.py`: `async def quality_event_emitter(asset, profile, production_state, nc, *, time_scale=1.0)` — stessa shape di `asset_emitter` (asyncio task + while True + datetime.now(UTC)); ogni iterazione: `production_state.maybe_rotate(now)`; con probabilità stocastica (configurabile, default ≤10 events/min/asset — Security threat lines 1279-1280) costruisce `QualityEvent(...)` + `await nc.publish(f"quality.events.{asset.asset_id}", event.model_dump_json().encode())`.

---

### `apps/api-gateway/src/svc_api_gateway/routers/quality.py` (NEW)

**Analog:** `apps/api-gateway/src/svc_api_gateway/routers/approvals.py` (lines 1-110) — full router pattern.

**Router init + SQL constants pattern** (approvals.py lines 25-65):
```python
import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from langgraph.types import Command

from svc_api_gateway.dependencies import (
    get_audit_writer, get_idempotency_cache, get_pool, get_queue_writer, get_supervisor_graph,
)
from svc_api_gateway.idempotency import IdempotencyCache
from svc_api_gateway.idempotency_middleware import check_idempotency_cache, jsonable, store_idempotent_response

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/approvals", tags=["approvals"])
```

**Endpoint pattern with idempotency** (approvals.py lines 161-180):
```python
@router.post("/{approval_id}/decide", response_model=DecideResponse)
async def decide_approval(
    approval_id: UUID,
    request: Request,
    body: Annotated[DecideRequest, Body()],
    pool: Any = Depends(get_pool),
    ...
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached
```

**Adaptations for Phase 6 (D-QI-01):**
- `router = APIRouter(prefix="/v1/quality", tags=["quality"])`.
- `POST /events`: accetta `QualityEvent` payload (from `sft_domain.ops.quality`); forza `source="operator"`; valida regex `dye_lot_id` (D-QI-04); publish a NATS `quality.events.{asset_id}` (NON invoca QualityInspector direttamente — D-QI-01 routes through NATS for uniformity); restituisce `202 Accepted`.
- Inject `nc` (NATS client) via `Depends(get_nats_client)` (nuova dependency da aggiungere a `dependencies.py`).
- Idempotency-Key cache supportata (riusa `check_idempotency_cache`).

---

### `apps/api-gateway/src/svc_api_gateway/routers/ops_agents.py` (NEW)

**Analog:** `apps/api-gateway/src/svc_api_gateway/routers/threads.py` (lines 1-105) — single resume-style endpoint, graph invocation pattern.

**Graph invocation pattern** (threads.py lines 80-90):
```python
state_after = await supervisor_graph.ainvoke(
    Command(resume=decision_payload.model_dump(mode="json")),
    config=config,
) or {}
```

**Adaptations for Phase 6 (D-AD-04 + D-PP-04 + D-OA endpoint exposure):**
- `router = APIRouter(prefix="/v1/agents", tags=["ops-agents"])`.
- 3 endpoints:
  - `POST /anomaly-detector/scan` body `{window_minutes: int, triggered_by: Literal["scheduler","operator","agent"]}` → invoca `supervisor_graph.ainvoke({"target_agent": "anomaly-detector", "window_minutes": ...}, config={"configurable": {"thread_id": f"ops.anomaly-detector.{uuid4()}"}, "recursion_limit": 5})`.
  - `POST /production-planner/plan` body `{horizon_days: int, strategy: Literal["spt","edd"]}` → invoca con `target_agent="production-planner"` + HITL await via `Command(resume=...)` flow (long-poll o async-202+webhook? Plan decides).
  - `POST /operator-assistant/chat` body `OperatorChatRequest` → invoca con `target_agent="operator-assistant"`.

---

### `tests/fixtures/llm_responses/<agent>/<scenario>.jsonl` (NEW)

**Analog:** nessun analog interno — formato definito in RESEARCH §Pattern 2 (lines 415-419 di 06-RESEARCH.md).

**Format:**
```jsonl
{"prompt_hash":"<sha256-64chars>","response":{"content":"","tool_calls":[{"id":"call_1","name":"rag_search","args":{"query":"...","user_roles":["technician"]}}],"usage_metadata":{"input_tokens":120,"output_tokens":15,"total_tokens":135}}}
{"prompt_hash":"<sha256>","response":{"content":"In base al SOP [1]...","usage_metadata":{...}}}
```

**Adaptations:**
- 12 file (4 agenti × 3 scenari `happy|degraded|failure`).
- Plan task: `scripts/regenerate-fixtures.py` per ri-registrare via real Qwen2.5 (Pitfall §10 mitigation).

---

### `tests/fixtures/ops_scenarios/<agent>/<scenario>.yaml` (NEW)

**Analog:** `packages/sft-domain/failure_modes.yaml` (formato YAML deterministico + `yaml.safe_load` loader convention).

**Adaptations:** 12 file YAML strutturati con:
- `query` o `event` o `request` payload deterministico
- `expected.target_agent`, `expected.tier`, `expected.action_type`, `expected.citations_min_count`, etc.

---

### `tests/e2e/ops/test_<agent>_scenarios.py` (NEW)

**Analog:** `tests/e2e/test_hitl_cycle.py` (Phase 4, assunto esistere — pattern parametrize + testcontainers).

**Markers + parametrize pattern** (`tests/conftest.py` lines 50-80):
```python
config.addinivalue_line("markers", "integration: ...")
config.addinivalue_line("markers", "e2e: ...")
```

**Adaptations:** 4 file (uno per agente), ogni file usa `@pytest.mark.parametrize("scenario", ["happy","degraded","failure"])` + fixture `ops_scenario_loader(agent_name, scenario)` (extension di `conftest.py`); marker `@pytest.mark.e2e`. Real-LLM opt-in via `@pytest.mark.real-llm` ignored unless explicit pytest flag.

---

### `tests/conftest.py` (EXTEND — add `mock_llm_backend` + `ops_scenario` fixtures)

**Analog:** self (lines 50-130).

**Adaptations:**
- Add markers: `real-llm: opt-in real Qwen2.5 smoke tests` (Phase 6 D-X-01).
- Add fixture `mock_llm_backend(scenario_file)`: sets `LLM_BACKEND=mock` + `MOCK_LLM_FIXTURE=<path>` env via `monkeypatch.setenv`.
- Add fixture `ops_scenario(request, agent_name)`: loads YAML from `tests/fixtures/ops_scenarios/{agent_name}/{request.param}.yaml`.

---

## Shared Patterns

### Pydantic v2 immutability (frozen + extra=forbid)

**Source:** `packages/sft-domain/src/sft_domain/failure_modes/models.py` line 26
**Apply to:** TUTTI i modelli Phase 6 (Anomaly, QualityEvent, QualityVerdict, ScheduleDraft, ScheduleDraftItem, OrderSpec, AssetCapacity, AnomalyBaseline, OperatorChatRequest/Response, EscalateInput, LogEventInput).

```python
class FailureMode(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}  # immutable, strict schema
```

### tz-aware datetime validator (Pitfall 7)

**Source:** `packages/sft-agents/src/sft_agents/models/evidence.py` lines 17-24
**Apply to:** ogni Pydantic model con campo datetime (QualityEvent.timestamp, Anomaly.timestamp, ScheduleDraftItem.start_at/end_at, ScheduleDraft.horizon_start/horizon_end/created_at).

```python
def _tz_aware(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError(f"Datetime field must be tz-aware, got naive: {v!r}.")
    return v

@field_validator("retrieved_at")
@classmethod
def _check_tz(cls, v: datetime) -> datetime:
    return _tz_aware(v)
```

### LangChain BaseTool async-only convention

**Source:** `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` lines 93-122
**Apply to:** `EscalateToSupervisorTool`, `LogEventTool`.

```python
def _run(self, *args: Any, **kwargs: Any) -> ...:
    raise NotImplementedError(
        "<ToolName> is async-only. Use `await tool.ainvoke({...})` instead."
    )

async def _arun(self, ...) -> ...:
    ...
```

### YAML loader with lru_cache + safe_load (T-05-03-01 / T-03-01-yaml)

**Source:** `packages/sft-domain/src/sft_domain/failure_modes/_loader.py` lines 22-58
**Apply to:** `load_anomaly_baselines`, `load_orders`, `load_asset_capacity`.

```python
@lru_cache(maxsize=1)
def load_X() -> tuple[X, ...]:
    if not _YAML_PATH.exists():
        raise FileNotFoundError(...)
    raw_text = _YAML_PATH.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load
    if not isinstance(raw_data, dict) or "X" not in raw_data:
        raise ValueError(...)
    return tuple(X.model_validate(entry) for entry in raw_data["X"])
```

### structlog JSON logging + agent context binding

**Source:** `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py` lines 42-53
**Apply to:** ogni nuovo modulo Phase 6.

```python
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)

logger = structlog.get_logger("agent.<slug>")  # convention from D-X discretion
log = logger.bind(agent_id="anomaly-detector", thread_id=state["thread_id"])
log.info("anomaly_scan_complete", emitted=len(anomalies), ...)
```

### SQL constants only + $N placeholders (T-V5-sql)

**Source:** `packages/sft-agents/src/sft_agents/runtime/governor.py` lines 35-55 + `apps/api-gateway/.../approvals.py` lines 63-105
**Apply to:** `RateLimiter._COUNT_RECENT_SQL`, `nats_consumer._DEDUP_SQL`, any new SQL in api-gateway routers.

```python
# T-V5-sql: module-level constants, $1..$N placeholders, no f-string interpolation.
_COUNT_RECENT_SQL: str = (
    "SELECT COUNT(*) FROM audit.actions "
    "WHERE agent_id = $1 AND action_type = $2 AND ts >= $3"
)

async with self._pool.acquire() as conn:
    count = await conn.fetchval(_COUNT_RECENT_SQL, agent_id, action_type, cutoff)
```

### asyncpg.connect with statement_cache_size=0 (TimescaleDB Pitfall 6)

**Source:** `packages/sft-tools/src/sft_tools/timescale/query.py` lines 9-16 + `apps/api-gateway/.../approvals.py` (pool usage)
**Apply to:** any direct asyncpg usage in Phase 6 (RateLimiter, scheduler audit writes).

### datetime.now(UTC) mandatory (Pitfall 7 / T-03-03-tz-naive)

**Source:** `simulators/sim-textile/src/sim_textile/emitter.py` line 76
**Apply to:** ogni `datetime.now()` call in Phase 6.

```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc)  # MAI datetime.now() senza tz
```

### Background asyncio loop with shutdown event (governor + escalation idiom)

**Source:** `packages/sft-agents/src/sft_agents/runtime/governor.py` lines 205-225
**Apply to:** `nats_consumer.run_qi_consumer`, `services/agents-scheduler/__main__.main`.

```python
async def run(self) -> None:
    try:
        while not self._shutdown.is_set():
            try:
                await asyncio.wait_for(self._shutdown.wait(), timeout=self._scan_interval_s)
                break
            except asyncio.TimeoutError:
                pass
            try:
                await self._scan_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("scan_error", error=str(exc))
    except asyncio.CancelledError:
        logger.info("cancelled")
        raise
```

### HITL interrupt + idempotent ID (Pitfall §3 — Phase 4 dual-write idiom)

**Source:** `packages/sft-agents/src/sft_agents/hitl/interrupt.py` lines 14-19 (Pitfall note) + lines 78-85 (sha256 approval ID derivation)
**Apply to:** `EscalateToSupervisorTool._arun`, `QualityInspector` HITL trigger, `ProductionPlanner` ScheduleDraft approval.

```python
def _derive_approval_id(thread_id: str, action_id: UUID) -> UUID:
    """sha256-deterministic id so re-execution after interrupt() is idempotent."""
    import hashlib
    digest = hashlib.sha256(
        f"{thread_id}|approval|{action_id}".encode("utf-8")
    ).hexdigest()
    return UUID(hex=digest[:32])
```

### Module docstring with reference to canonical decisions

**Source:** ogni modulo Phase 4/5 — es. `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` lines 1-11, `packages/sft-agents/src/sft_agents/hitl/interrupt.py` lines 1-19
**Apply to:** ogni nuovo modulo Phase 6.

Convention: prima riga summary; sezione `Contract (CONTEXT.md D-XX):` con bullet point lockati; sezione `Pitfall §N note:` se rilevante.

---

## No Analog Found

Files con no close internal match (planner usa RESEARCH.md patterns esterni):

| File | Role | Data Flow | Reason | Use Instead |
|------|------|-----------|--------|-------------|
| `packages/sft-domain/src/sft_domain/scheduling/heuristic.py` | algorithm | transform | Phase 6 introduce dominio scheduling (no prior algo) | RESEARCH §Pattern 5 lines 595-651 + Pydantic immutability shared |
| `apps/agents/ops/operator-assistant/src/.../validators.py` | utility | transform | Citation validator è novità (LLM output validation post-loop) | RESEARCH §Pattern 7 lines 723-754 |
| `apps/agents/ops/operator-assistant/src/.../lang_detect.py` | utility | transform | langdetect è nuova dep + Pitfall §6 init pattern | RESEARCH §Pitfall 6 lines 936-941 |
| `services/agents-scheduler/src/.../scheduler.py` | service | event-driven | APScheduler è nuova dep, no prior cron container | RESEARCH §Pattern 4 lines 549-588 |
| `apps/agents/ops/quality-inspector/src/.../grader.py` | service | request-response (LLM) | LLM JSON-mode + Pydantic clamp è novità | RESEARCH §Pattern 6 lines 685-707 + Pydantic immutability shared |
| `apps/agents/ops/anomaly-detector/src/.../baseline.py` | domain utility | transform | Banda numerica check è novità | RESEARCH §Pattern 8 lines 763-794 (rate limit) + AnomalyBaseline model |
| `tests/fixtures/llm_responses/<agent>/<scenario>.jsonl` | test fixture | n/a | JSONL format è novità Phase 6 | RESEARCH §Pattern 2 lines 415-419 |
| `tests/fixtures/ops_scenarios/<agent>/<scenario>.yaml` | test fixture | n/a | Scenario YAML è novità (deterministic test inputs) | YAML loader pattern + RESEARCH §11 lines 1207-1245 |

---

## Cross-cutting Plan Hints

**Plan composition guidance per planner:**

1. **Plan groups by package** (parallelizable):
   - Group A (sft-domain): `ops/{anomaly,quality,schedule}.py` + `scheduling/{heuristic,constraints}.py` + 3 YAML + extend `failure_modes` (1 plan, ~8 files).
   - Group B (sft-agents shared): `llm/{factory.py EXTEND, mock.py NEW}` + `tools/{hitl,audit}.py` + `runtime/{rate_limit.py, clusters.py EXTEND}` + `models/enums.py EXTEND` (1 plan, ~7 files; depends on Group A models).
   - Group C (4 agent apps): 4 plans (uno per agente), ognuno depends on B.
   - Group D (sim-textile extension): 1 plan (depends on Group A QualityEvent model).
   - Group E (services/agents-scheduler): 1 plan (depends on Group F router).
   - Group F (api-gateway routers): 1 plan (depends on Group C agents wired in supervisor).
   - Group G (tests + fixtures + CI): 1 plan (depends on all above).
   - Group H (DB migration `007_extend_audit_decisions.sql`): 1 plan, runs BEFORE Group B enum extension (gating).

2. **Critical sequencing constraints:**
   - Migration H **must** land before Group B (otherwise `Decision.SUPPRESSED` + `Decision.LOGGED` writes fail PG CHECK constraint).
   - `LLM_BACKEND=mock` (Group B) must land before Group G tests (E2E depends on it).
   - QUALITY_STREAM NATS bootstrap (extend `scripts/nats-bootstrap-streams.py`) must land before Group C quality-inspector test (Pitfall §4).

3. **Verify-before-implement checkpoints (assumed packages from RESEARCH):**
   - `[ASSUMED]` `APScheduler>=3.10.4` — planner adds `checkpoint:human-verify` task pre-install (Group E).
   - `[ASSUMED]` `langdetect>=1.0.9` — planner adds `checkpoint:human-verify` task pre-install (Group C operator-assistant plan).
   - Open Question 1: `grep -n "CHECK.*decision" infra/migrations/timescale/` task in Group H plan before writing migration.

---

## Metadata

**Analog search scope:**
- `packages/sft-agents/`, `packages/sft-knowledge/`, `packages/sft-domain/`, `packages/sft-tools/`, `packages/sft-assets/`
- `apps/agents/ops/*` (scaffold-only verification)
- `apps/api-gateway/src/svc_api_gateway/`
- `services/knowledge-ingest/`, `services/ot-bridge/`
- `simulators/sim-textile/`
- `tests/`, `tests/conftest.py`

**Files scanned:** ~25 (full read on key analogs: factory.py, clusters.py, governor.py, rag.py, graph.py, interrupt.py, evidence.py, enums.py, approvals.py, threads.py, _loader.py, failure_modes/models.py, knowledge-ingest/__main__.py + pipeline.py, sim-textile/emitter.py, query.py).

**Pattern extraction date:** 2026-05-23

---

## PATTERN MAPPING COMPLETE

**Phase:** 6 — Agents — Operations & Production
**Files classified:** 44
**Analogs found:** 38 / 44 (38 exact/role-match; 6 partial → use RESEARCH external patterns)

### Coverage
- Files with exact analog: 22
- Files with role-match analog: 16
- Files with partial analog: 6
- Files with no internal analog: 6 (use RESEARCH §Pattern N references)

### Key Patterns Identified
- **Pydantic v2 frozen + extra=forbid** è universale — applicato a ~15 nuovi modelli.
- **LangChain BaseTool async-only** (RagSearchTool template) si replica letteralmente per 2 nuovi tools (`escalate_to_supervisor`, `log_event`).
- **SQL constants $1..$N + asyncpg pool** (governor + approvals) si replica per RateLimiter + NATS consumer dedup.
- **YAML + lru_cache + safe_load** (failure_modes/_loader.py) si replica per 3 nuovi loader (orders, capacity, baselines).
- **Background asyncio loop + shutdown event** (governor.py + escalation.py) si replica per NATS consumer + agents-scheduler service.
- **HITL idempotent ID via sha256(thread_id|action_id)** (Pitfall §3 + interrupt.py) si replica per EscalateToSupervisorTool + ProductionPlanner ScheduleDraft + QualityInspector verdict.
- **FastAPI router con dependency injection + Idempotency-Key cache** (approvals.py + threads.py) si replica per /v1/quality/events + /v1/agents/{slug}/{action}.
- **LLM factory whitelist + branch dispatch** (factory.py) si estende con 3rd branch `mock` per CI determinism.
- **structlog JSON + agent.<slug> context bind** è convenzione cross-cutting Phase 1-5 e Phase 6 la perpetua.

### Ready for Planning

PATTERNS.md scritto in `.planning/phases/06-agents-operations-production/06-PATTERNS.md`. Planner può ora comporre PLAN.md files referenziando analog patterns concreti per ognuno dei 44 nuovi/estesi file di Phase 6.
