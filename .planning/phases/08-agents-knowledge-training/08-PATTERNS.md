# Phase 8: Agents — Knowledge & Training - Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 28 (new/modified files across 4 agents + infra + gateway)
**Analogs found:** 28 / 28

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `infra/migrations/timescale/010_extend_audit_knw.sql` | migration | CRUD | `009_extend_audit_mnt.sql` | exact |
| `infra/migrations/timescale/tests/test_migration_010.py` | test | CRUD | `tests/test_migration_009.py` | exact |
| `packages/sft-agents/src/sft_agents/models/enums.py` | model | CRUD | same file (extend) | exact |
| `packages/sft-agents/src/sft_agents/runtime/clusters.py` | utility | request-response | same file (extend) | exact |
| `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py` | route | request-response | `routers/maintenance_agents.py` | exact |
| `apps/api-gateway/src/svc_api_gateway/dependencies.py` | utility | request-response | same file (extend) | exact |
| `apps/api-gateway/src/svc_api_gateway/main.py` | config | request-response | same file (extend) | exact |
| `apps/agents/knowledge/shift-handover/src/trn_shift_handover/agent.py` | service | request-response | `mnt_rca_specialist/agent.py` | exact (HITL pattern) |
| `apps/agents/knowledge/shift-handover/src/trn_shift_handover/aggregator.py` | service | CRUD | `mnt_downtime_analyzer/repository.py` | exact (asyncpg pattern) |
| `apps/agents/knowledge/shift-handover/src/trn_shift_handover/models.py` | model | request-response | `mnt_rca_specialist/models.py` | exact |
| `apps/agents/knowledge/shift-handover/src/trn_shift_handover/metadata.py` | utility | request-response | `mnt_rca_specialist/metadata.py` | exact |
| `apps/agents/knowledge/shift-handover/src/trn_shift_handover/prompts.py` | utility | request-response | `mnt_rca_specialist/prompts.py` | role-match |
| `apps/agents/knowledge/shift-handover/tests/test_aggregator.py` | test | CRUD | `mnt_downtime_analyzer/tests/test_repository.py` | exact |
| `apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py` | test | request-response | `mnt_rca_specialist/tests/test_interrupt_audit_lifecycle.py` | exact |
| `apps/agents/knowledge/training-coach/src/trn_training_coach/agent.py` | service | request-response | `mnt_maintenance_coach/agent.py` | exact (HITL pattern) |
| `apps/agents/knowledge/training-coach/src/trn_training_coach/quiz.py` | utility | CRUD | `mnt_maintenance_coach/mttr.py` | role-match (pure computation) |
| `apps/agents/knowledge/training-coach/src/trn_training_coach/difficulty.py` | utility | CRUD | `mnt_maintenance_coach/mttr.py` | role-match |
| `apps/agents/knowledge/training-coach/src/trn_training_coach/models.py` | model | request-response | `mnt_rca_specialist/models.py` | exact |
| `apps/agents/knowledge/training-coach/src/trn_training_coach/metadata.py` | utility | request-response | `mnt_rca_specialist/metadata.py` | exact |
| `apps/agents/knowledge/training-coach/src/trn_training_coach/prompts.py` | utility | request-response | `mnt_maintenance_coach/prompts.py` | role-match |
| `apps/agents/knowledge/training-coach/tests/test_quiz_scoring.py` | test | CRUD | `mnt_downtime_analyzer/tests/test_oee.py` | role-match (pure-function test) |
| `apps/agents/knowledge/training-coach/tests/test_difficulty.py` | test | CRUD | `mnt_downtime_analyzer/tests/test_oee.py` | role-match |
| `apps/agents/knowledge/training-coach/tests/test_hitl_lifecycle.py` | test | request-response | `mnt_rca_specialist/tests/test_interrupt_audit_lifecycle.py` | exact |
| `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/agent.py` | service | CRUD | `mnt_downtime_analyzer/agent.py` | role-match (autonomous, no HITL) |
| `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/dedup.py` | utility | CRUD | `mnt_rca_specialist/validators.py` | role-match (validation logic) |
| `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/staleness.py` | utility | CRUD | `mnt_downtime_analyzer/oee.py` | role-match (pure computation) |
| `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/reuse_rate.py` | utility | CRUD | `mnt_downtime_analyzer/repository.py` | role-match (SQL aggregate) |
| `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/models.py` | model | CRUD | `mnt_rca_specialist/models.py` | exact |
| `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/metadata.py` | utility | CRUD | `mnt_rca_specialist/metadata.py` | exact |
| `apps/agents/knowledge/knowledge-curator/tests/test_dedup.py` | test | CRUD | `mnt_rca_specialist/tests/test_validators.py` | exact |
| `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/agent.py` | service | request-response | `mnt_rca_specialist/agent.py` | exact (HITL pattern) |
| `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/event_aggregator.py` | service | CRUD | `mnt_downtime_analyzer/repository.py` | exact |
| `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/sop_builder.py` | utility | transform | `mnt_maintenance_coach/prompts.py` | role-match |
| `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/translator.py` | utility | transform | `mnt_rca_specialist/validators.py` | role-match |
| `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/validators.py` | utility | CRUD | `mnt_rca_specialist/validators.py` | exact |
| `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/models.py` | model | request-response | `mnt_rca_specialist/models.py` | exact |
| `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/metadata.py` | utility | request-response | `mnt_rca_specialist/metadata.py` | exact |
| `apps/agents/knowledge/documentation-synthesizer/tests/test_translator.py` | test | transform | `mnt_rca_specialist/tests/test_validators.py` | role-match |
| `apps/agents/knowledge/documentation-synthesizer/tests/test_hitl_preindex.py` | test | request-response | `mnt_rca_specialist/tests/test_interrupt_audit_lifecycle.py` | exact |

---

## Pattern Assignments

### `infra/migrations/timescale/010_extend_audit_knw.sql` (migration, CRUD)

**Analog:** `infra/migrations/timescale/009_extend_audit_mnt.sql`

**Full pattern** (lines 1-52):
```sql
-- Migration 010: extend audit.actions.action_type CHECK constraint for Phase 8 (D-X-01).
-- File: infra/migrations/timescale/010_extend_audit_knw.sql
-- Phase 8 — Plan 08-01
-- Idempotent: safe to re-run.

ALTER TABLE audit.actions
  DROP CONSTRAINT IF EXISTS audit_actions_action_type_chk;

ALTER TABLE audit.actions
  ADD CONSTRAINT audit_actions_action_type_chk CHECK (
    action_type IN (
      -- Phases 1-5 baseline
      'WRITE_PLC_SETPOINT','ACTUATOR_COMMAND','FIRMWARE_DEPLOY',
      'NETWORK_ACL_CHANGE','GRAPH_RECURSION_REVIEW','GOVERNOR_ALERT',
      -- Phase 6
      'ESCALATION_REQUEST','QUALITY_VERDICT','SCHEDULE_DRAFT','ANOMALY_ALERT',
      -- Phase 7
      'RUL_ESTIMATE','RCA_CHAIN','COACH_STEP','DOWNTIME_VERDICT','OEE_REPORT',
      -- Phase 8 (D-X-01) — keep in lockstep with sft_agents.models.enums.ActionType
      'HANDOVER_DRAFT',    -- D-SH-01: draft compiled by ShiftHandover
      'HANDOVER_SIGNOFF',  -- D-SH-03: supervisor sign-off row (2 rows per handover)
      'TRAINING_SESSION',  -- D-TC-01: quiz delivery session record
      'TRAINING_SIGNOFF',  -- D-TC-03: supervisor competency sign-off
      'KNOWLEDGE_DEDUP',   -- D-KC-01: dedup verdict (exact or near-dup)
      'STALE_FLAG',        -- D-KC-02: staleness flag on a document
      'SOP_DRAFT'          -- D-DS-03: synthesized SOP draft before indexing
    )
  );
```

**What to replicate:** DROP IF EXISTS + ADD pattern verbatim. Include all prior phase values unchanged. Add Decision CHECK note (do NOT touch it — same as D-AE-MNT).

**What to change:** Add 7 Phase 8 values. Update filename, comment header.

---

### `infra/migrations/timescale/tests/test_migration_010.py` (test, CRUD)

**Analog:** `infra/migrations/timescale/tests/test_migration_009.py`

**Test matrix pattern** (lines 51-74):
```python
_PHASE8_ACTION_TYPES = (
    "HANDOVER_DRAFT",
    "HANDOVER_SIGNOFF",
    "TRAINING_SESSION",
    "TRAINING_SIGNOFF",
    "KNOWLEDGE_DEDUP",
    "STALE_FLAG",
    "SOP_DRAFT",
)

# Pre-Phase-8 legacy action_types — must still pass after 010 (regression guard).
_LEGACY_ACTION_TYPES = (
    "WRITE_PLC_SETPOINT","ACTUATOR_COMMAND","FIRMWARE_DEPLOY",
    "NETWORK_ACL_CHANGE","GRAPH_RECURSION_REVIEW","GOVERNOR_ALERT",
    "ESCALATION_REQUEST","QUALITY_VERDICT","SCHEDULE_DRAFT","ANOMALY_ALERT",
    "RUL_ESTIMATE","RCA_CHAIN","COACH_STEP","DOWNTIME_VERDICT","OEE_REPORT",
)
```

**Fixture pattern** (lines 137-155): function-scoped `fresh_dsn` with `testcontainers.postgres.PostgresContainer(image="timescale/timescaledb:2.18.0-pg16")`.

**Helper pattern** (lines 77-134):
- `_run_baseline_migrations(dsn)` — applies `[0-9][0-9][0-9]_*.sql` where `f.name < "010"`
- `_apply_010(dsn)` — reads and executes `010_extend_audit_knw.sql`
- `_insert_action(dsn, *, decision="auto", action_type="...")` — minimally valid INSERT

**6+1 test structure to mirror:**
1. `test_pre_migration_rejects_handover_draft` — before 010, new value raises CheckViolationError
2. `test_post_migration_admits_handover_draft` — after 010, inserts successfully
3. `test_post_migration_admits_all_phase8_action_types` — parametrize over `_PHASE8_ACTION_TYPES`
4. `test_post_migration_legacy_action_types_ok` — parametrize over `_LEGACY_ACTION_TYPES`
5. `test_post_migration_decision_enum_unchanged` — read `pg_constraint`, assert Decision CHECK untouched
6. `test_idempotent_double_apply` — re-run 010, must be no-op
7. `test_migrate_runner_picks_up_010` — `migrate()` runner picks it up automatically

**What to change:** `"009"` → `"010"` in all strings, `_PHASE7_ACTION_TYPES` → `_PHASE8_ACTION_TYPES`, `_MIGRATION_009` → `_MIGRATION_010`, update the baseline glob sentinel.

---

### `packages/sft-agents/src/sft_agents/models/enums.py` (model, CRUD — modify)

**Analog:** Same file (in-place extension)

**Existing enum tail** (lines 115-120):
```python
    # Phase 7 additions — keep in lockstep with migration 009 (D-AE-MNT).
    RUL_ESTIMATE = "RUL_ESTIMATE"
    RCA_CHAIN = "RCA_CHAIN"
    COACH_STEP = "COACH_STEP"
    DOWNTIME_VERDICT = "DOWNTIME_VERDICT"
    OEE_REPORT = "OEE_REPORT"
```

**Append pattern — Phase 8 extension:**
```python
    # Phase 8 additions — keep in lockstep with migration 010 (D-X-01).
    HANDOVER_DRAFT = "HANDOVER_DRAFT"       # D-SH-01: draft compiled by ShiftHandover
    HANDOVER_SIGNOFF = "HANDOVER_SIGNOFF"   # D-SH-03: supervisor sign-off row (2 rows per handover)
    TRAINING_SESSION = "TRAINING_SESSION"   # D-TC-01: quiz delivery session record
    TRAINING_SIGNOFF = "TRAINING_SIGNOFF"   # D-TC-03: supervisor competency sign-off
    KNOWLEDGE_DEDUP = "KNOWLEDGE_DEDUP"     # D-KC-01: dedup verdict (exact or near-dup)
    STALE_FLAG = "STALE_FLAG"               # D-KC-02: staleness flag on a document
    SOP_DRAFT = "SOP_DRAFT"                 # D-DS-03: synthesized SOP draft before indexing
```

**What to replicate:** inline comment style `# D-XX-YY: description`, same docstring section header format.

---

### `packages/sft-agents/src/sft_agents/runtime/clusters.py` (utility, request-response — modify)

**Analog:** Same file — append `build_knowledge_subgraph` mirroring `build_maintenance_subgraph` (lines 176-251).

**Full function pattern to copy:**
```python
#: Default fallback target for the knowledge router (Plan 08-XX planner decision).
#: KnowledgeCurator is autonomous (D-KC-04) — no HITL, no irreversible side effects.
#: Unknown-target routing to an autonomous agent is the safest fallback.
_KNW_DEFAULT_AGENT: str = "knowledge-curator"


def build_knowledge_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    """Return an *uncompiled* KNOWLEDGE-cluster StateGraph with conditional routing.

    Structural mirror of :func:`build_maintenance_subgraph` (D-X-04 gateway pattern).
    The graph wires:
        START → conditional_edges(_route) → <selected slug> → END

    ``_route(state)`` reads ``state.get("target_agent")``. If the value is
    missing or not in ``child_callables``, routes to ``knowledge-curator``
    (autonomous, D-KC-04) and emits a ``knw_route_unknown_target`` structlog
    warning.

    Parameters
    ----------
    child_callables:
        Mapping of agent slug to async callable. MUST include
        ``knowledge-curator`` (the fallback). Non-empty.

    Raises
    ------
    ValueError
        If ``child_callables`` is empty or does not contain ``knowledge-curator``.
    """
    if not child_callables:
        raise ValueError(
            "child_callables must be non-empty for the knowledge subgraph"
        )
    if _KNW_DEFAULT_AGENT not in child_callables:
        raise ValueError(
            f"child_callables must include {_KNW_DEFAULT_AGENT!r} (the fallback "
            f"target for the knowledge router); got slugs {sorted(child_callables)}"
        )

    children: dict[str, Callable[[AgentState], Awaitable[dict[str, Any]]]] = dict(
        child_callables
    )

    g: StateGraph = StateGraph(AgentState)
    for slug, fn in children.items():
        g.add_node(slug, fn)

    def _route(state: AgentState) -> str:
        target = state.get("target_agent") if isinstance(state, dict) else None
        if not target or target not in children:
            _log.warning(
                "knw_route_unknown_target",
                target=target,
                fallback=_KNW_DEFAULT_AGENT,
            )
            return _KNW_DEFAULT_AGENT
        return str(target)

    g.add_conditional_edges(START, _route, {slug: slug for slug in children})
    for slug in children:
        g.add_edge(slug, END)

    return g
```

**`__all__` update:** add `"build_knowledge_subgraph"` to the list.

---

### `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py` (route, request-response)

**Analog:** `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py`

**Module header pattern** (lines 1-41):
```python
"""POST /v1/agents/{slug}/{action} — Plan 08-XX (TRN-02/03/04/05).

Knowledge cluster HTTP surface. Mirrors Phase 7 07-10 maintenance_agents.py
routing pattern; supervisor routes via target_agent into build_knowledge_subgraph
(08-XX). Each endpoint sets state["target_agent"] in the AgentState.

Endpoints
---------
POST /v1/agents/shift-handover/compile         202  Compile + dual HITL (TRN-03)
POST /v1/agents/training-coach/session         200  Quiz session (TRN-02)
POST /v1/agents/training-coach/resume          200  Resume after competency HITL (TRN-02)
POST /v1/agents/knowledge-curator/ingest       200  Autonomous dedup + stale flag (D-KC-04)
POST /v1/agents/documentation-synthesizer/draft  202  SOP draft + pre-index HITL (TRN-04)
"""
```

**Imports pattern** (lines 42-70):
```python
from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import uuid4

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sft_agents.llm.langfuse_callback import build_invocation_config

from svc_api_gateway.dependencies import (
    get_idempotency_cache,
    get_supervisor_graph,
)
from svc_api_gateway.idempotency import IdempotencyCache
from svc_api_gateway.idempotency_middleware import (
    check_idempotency_cache,
    jsonable,
    store_idempotent_response,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/agents", tags=["knowledge-agents"])
_RECURSION_LIMIT: int = 5
_RETRY_AFTER_SECONDS: int = 5
```

**Request model pattern** (lines 87-113):
```python
class ShiftHandoverCompileRequest(BaseModel):
    """Request body for POST /v1/agents/shift-handover/compile (TRN-03)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    shift_start: datetime = Field(description="Shift window start (tz-aware UTC)")
    shift_end: datetime = Field(description="Shift window end (tz-aware UTC)")
    user_roles: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_window_order(self) -> "ShiftHandoverCompileRequest":
        if self.shift_end <= self.shift_start:
            raise ValueError("shift_end must be after shift_start")
        return self
```

**Endpoint pattern** (lines 277-324 — copy from `post_pm_score` or `post_rca_analyze`):
```python
@router.post(
    "/shift-handover/compile",
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_shift_handover_compile(
    request: Request,
    body: Annotated[ShiftHandoverCompileRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return JSONResponse(content=cached, status_code=status.HTTP_202_ACCEPTED)

    thread_id = f"knowledge.shift-handover.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.shift-handover.compile"],
        recursion_limit=_RECURSION_LIMIT,
    )
    state: dict[str, Any] = {
        "target_agent": "shift-handover",
        "shift_start": body.shift_start,
        "shift_end": body.shift_end,
        "user_roles": list(body.user_roles),
    }
    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:
        return _handle_agent_error(exc, thread_id)

    payload = jsonable({"thread_id": thread_id, "hitl_status": "supervisor_pending"})
    await store_idempotent_response(request, cache, body_hash, payload, status_code=status.HTTP_202_ACCEPTED)
    return JSONResponse(content=payload, status_code=status.HTTP_202_ACCEPTED)
```

**Error helpers** (lines 244-270) — copy `_handle_recursion_error` and `_handle_agent_error` verbatim from `maintenance_agents.py`, changing the log event key prefix from `maintenance_agent_` to `knowledge_agent_`.

---

### `apps/api-gateway/src/svc_api_gateway/dependencies.py` (utility, request-response — modify)

**Analog:** Same file — add `get_knowledge_children` mirroring `get_maintenance_children` (lines 76-90).

**Pattern to copy:**
```python
def get_knowledge_children(request: Request) -> Any:
    """Return ``app.state.knowledge_children`` (dict[str, callable]) or 503.

    The dict maps knowledge agent slugs to their async __call__ callables:
        {
            'shift-handover': ShiftHandover.__call__,
            'training-coach': TrainingCoach.__call__,
            'knowledge-curator': KnowledgeCurator.__call__,
            'documentation-synthesizer': DocumentationSynthesizer.__call__,
        }

    Populated by :func:`svc_api_gateway.lifespan.lifespan` during app startup.
    Used with build_knowledge_subgraph (08-XX) for direct DI wiring.
    """
    return _require_state(request, "knowledge_children")
```

---

### `apps/api-gateway/src/svc_api_gateway/main.py` (config, request-response — modify)

**Analog:** Same file — add one `include_router` call in `build_app()`.

**Pattern to copy** (lines 43-65):
```python
    from svc_api_gateway.routers import knowledge_agents as knowledge_agents_router  # noqa: PLC0415
    # ...
    app.include_router(knowledge_agents_router.router)  # Plan 08-XX — TRN-01/02/03/04
```

Add after the existing `maintenance_agents_router.router` include.

---

### `apps/agents/knowledge/shift-handover/src/trn_shift_handover/agent.py` (service, request-response)

**Analog:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py`

**Imports pattern** (lines 38-75):
```python
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

import structlog
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision, Tier
from sft_agents.models.evidence import EvidencePanel, TokenUsage, ToolCall

try:
    from langgraph.types import interrupt
except ImportError:
    def interrupt(value: Any) -> Any:
        raise NotImplementedError("langgraph.types.interrupt is not available")

from trn_shift_handover.metadata import AGENT_ID as _AGENT_ID
from trn_shift_handover.metadata import build_trn05_evidence_panel
from trn_shift_handover.models import HandoverReport, ShiftWindow

logger = structlog.get_logger("agent.shift-handover")

AGENT_ID: str = "shift-handover"
CLUSTER: str = "knowledge"
```

**Constructor pattern** (lines 132-175 analog):
```python
class ShiftHandover:
    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: Any,
        llm: Any,
    ) -> None:
        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
```

**CRITICAL: Dual-supervisor HITL pattern** — new for Phase 8; no prior analog exists in codebase. The pattern from RESEARCH.md is the authoritative source:

```python
async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
    report = await self._compile_report(state)

    # First interrupt — outgoing supervisor (CR-02 pattern: interrupt() DIRECTLY)
    decision_outgoing = interrupt({
        "tier": Tier.SUPERVISOR.value,
        "handover_step": "outgoing_approval",
        "payload": report.model_dump(mode="json"),
    })

    # Write first audit AFTER first interrupt() returns (CR-02 fix)
    await self._write_audit(
        report=report,
        action_type=ActionType.HANDOVER_SIGNOFF,
        motivation=f"Outgoing supervisor decision: {decision_outgoing}",
    )

    # Second interrupt — incoming supervisor (sequential, not parallel)
    decision_incoming = interrupt({
        "tier": Tier.SUPERVISOR.value,
        "handover_step": "incoming_confirmation",
        "payload": report.model_dump(mode="json"),
    })

    # Write second audit AFTER second interrupt() returns
    await self._write_audit(
        report=report,
        action_type=ActionType.HANDOVER_SIGNOFF,
        motivation=f"Incoming supervisor decision: {decision_incoming}",
    )

    return {"handover_report": report, "shift_status": "signed_off"}
```

**`_write_audit` pattern** (lines 337-405 analog) — copy from `mnt_rca_specialist/agent.py` with:
- `ActionType.HANDOVER_SIGNOFF` or `ActionType.HANDOVER_DRAFT`
- `cluster="knowledge"`
- `approval_id=None` (CR-03 fix)

---

### `apps/agents/knowledge/shift-handover/src/trn_shift_handover/aggregator.py` (service, CRUD)

**Analog:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/repository.py`

**SQL ClassVar pattern** (lines 78-137):
```python
from typing import ClassVar
from datetime import datetime
import structlog

logger = structlog.get_logger("agent.shift-handover.aggregator")

class ShiftAggregator:
    """Cross-cluster asyncpg aggregator for ShiftHandover (D-SH-02).

    Reads audit.actions across all clusters for the shift window.
    All SQL uses $N parameterized placeholders (T-V5-sql). ClassVar
    SQL constants enable meta-test inspection.
    """

    # Cross-cluster audit query for shift window (D-SH-02).
    # WR-03 fix: pass datetime objects directly to asyncpg (never .isoformat()).
    _SQL_AUDIT_WINDOW: ClassVar[str] = (
        "SELECT ts, agent_id, cluster, action_type, thread_id, "
        "evidence_panel, decision "
        "FROM audit.actions "
        "WHERE ts BETWEEN $1 AND $2 "
        "ORDER BY ts ASC"
    )

    # Downtime events for the shift window (maintenance.downtime_events, migration 008).
    _SQL_DOWNTIME_WINDOW: ClassVar[str] = (
        "SELECT event_id, asset_id, reason_code, duration_min, severity, "
        "work_order_id, timestamp "
        "FROM maintenance.downtime_events "
        "WHERE timestamp BETWEEN $1 AND $2 "
        "ORDER BY timestamp ASC"
    )

    def __init__(self, *, pool: Any) -> None:
        self._pool = pool

    async def fetch_audit_window(
        self,
        shift_start: datetime,
        shift_end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch all audit.actions rows in the shift window.

        WR-03 fix: shift_start and shift_end are datetime objects passed
        directly to asyncpg — never call .isoformat() before passing.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                self._SQL_AUDIT_WINDOW,
                shift_start,   # datetime object — WR-03 fix
                shift_end,     # datetime object — WR-03 fix
            )
        return [dict(row) for row in rows]
```

**What to replicate:** ClassVar SQL constants, asyncpg pool.acquire() context manager, WR-03 datetime pattern (no `.isoformat()`), structlog at module level.

---

### `apps/agents/knowledge/shift-handover/src/trn_shift_handover/models.py` (model, request-response)

**Analog:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/models.py`

**Frozen Pydantic pattern** (lines 29-60):
```python
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ShiftWindow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    shift_start: datetime = Field(description="Shift window start (tz-aware UTC)")
    shift_end: datetime = Field(description="Shift window end (tz-aware UTC)")
    boundary_label: str = Field(description="e.g. '06:00-14:00'")

    @field_validator("shift_start", "shift_end")
    @classmethod
    def _check_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError(f"Field must be tz-aware, got naive: {v!r}")
        return v
```

**What to replicate:** `frozen=True, extra="forbid"` on all models, tz-aware validator for any datetime field (Pattern S-6), `list[RagCitation]` from `sft_agents.models.evidence` for citation fields.

---

### `apps/agents/knowledge/shift-handover/src/trn_shift_handover/metadata.py` (utility, request-response)

**Analog:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/metadata.py`

**Full pattern** (lines 20-118):
```python
from __future__ import annotations
from typing import Any

TOOL_INVENTORY: tuple[str, ...] = (
    "fetch_audit_window",
    "fetch_downtime_events",
    "escalate_to_supervisor",
)
DATA_SOURCES: tuple[str, ...] = (
    "audit.actions (all clusters)",
    "maintenance.downtime_events",
    # D-SH-02 (resolved post-research): NO ops.alerts / ops.work_orders tables —
    # alerts derive from audit.actions WHERE action_type='ANOMALY_ALERT'.
)
KPIS_IMPACTED: tuple[str, ...] = (
    "shift_handover_completeness",
    "cross_shift_continuity",
)
HITL_TIER_DEFAULT: str = "supervisor"
AGENT_ID: str = "shift-handover"

def build_trn05_evidence_panel(
    input_summary: str,
    *,
    model_version: str,
    tool_calls: list[dict[str, Any]],
    decision: str,
    prompt_hash: str,
    tokens: dict[str, int] | None = None,
    duration_ms: int = 0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # ... same structure as build_ops05_evidence_panel, agent_id="shift-handover"
```

**What to replicate:** tuple constants for `TOOL_INVENTORY`, `DATA_SOURCES`, `KPIS_IMPACTED`; `build_*_evidence_panel` helper with same signature; caller-supplied `extra` keys never overwrite the 5 required keys.

---

### `apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py` (test, request-response)

**Analog:** `apps/agents/maintenance/rca-specialist/tests/test_interrupt_audit_lifecycle.py`

**Key test pattern** (lines 209-323):

The CR-02 lifecycle test structure for dual-supervisor:

```python
@pytest.mark.asyncio
async def test_dual_supervisor_signoff_audit_ordering() -> None:
    """Two sequential interrupt() calls; audit rows written between and after.

    Contract:
    1. After first interrupt (outgoing): first audit row written, second NOT yet.
    2. After second interrupt (incoming): second audit row written.
    3. Total: exactly 2 audit rows, written in order.
    """
    interrupt_call_count = 0

    def _simulated_interrupt(value: Any) -> Any:
        nonlocal interrupt_call_count
        interrupt_call_count += 1
        if interrupt_call_count in (1, 3):  # first runs of each interrupt
            raise GraphInterrupt(value)
        return {"approved": True, "decision": "proceed"}

    # ... patch "trn_shift_handover.agent.interrupt", count audit.write calls
```

**What to replicate:** `patch("<module>.agent.interrupt", _simulated_interrupt)` pattern, `AsyncMock` for `audit_writer.write`, `pytest.raises(GraphInterrupt)` for first-run simulation, call count assertions.

---

### `apps/agents/knowledge/training-coach/src/trn_training_coach/agent.py` (service, request-response)

**Analog:** `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py`

**Single-supervisor HITL pattern** (lines 254-330 from maintenance-coach):

TrainingCoach uses the simpler single-interrupt pattern (not dual). The quiz scoring happens before the interrupt:

```python
async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
    # 1. Extract session parameters
    # 2. RAG retrieval for quiz generation (RetrievalPipeline.search)
    # 3. Generate and freeze quiz (QuizBank + MCQSession — no LLM in scoring path)
    # 4. Deliver quiz deterministically (no LLM judge)
    # 5. Compute score (operator_answer_index == correct_answer_index — Pitfall §3)
    # 6. Write TRAINING_SESSION audit row (autonomous — no HITL)

    # Only on pass (score >= threshold): HITL for competency sign-off
    if session.score >= self._pass_threshold:
        decision = interrupt({   # CR-02 pattern: DIRECTLY in __call__
            "tier": Tier.SUPERVISOR.value,
            "payload": session.model_dump(mode="json"),
        })
        # Write TRAINING_SIGNOFF audit AFTER interrupt() returns
        await self._write_audit(action_type=ActionType.TRAINING_SIGNOFF, ...)

    return {"training_session": session, "hitl_status": ...}
```

**Constructor pattern** (MaintenanceCoach lines 366-410):
```python
class TrainingCoach:
    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: Any,
        llm: Any,
        retrieval_pipeline: Any,  # RetrievalPipeline (Phase 5)
        escalate_tool: Any,
        pass_threshold: float = 0.80,  # D-TC-03 configurable default
    ) -> None:
        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
        self._retrieval = retrieval_pipeline
        self._escalate = escalate_tool
        self._pass_threshold = pass_threshold
```

---

### `apps/agents/knowledge/training-coach/src/trn_training_coach/quiz.py` (utility, CRUD)

**Analog:** `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/mttr.py` (pure computation module)

**Deterministic scoring pattern** (D-TC-01 — Pitfall §3 prevention):
```python
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

class MCQQuestion(BaseModel):
    """Multiple-choice question with frozen correct answer index."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    question_text: str
    options: list[str] = Field(min_length=2, max_length=6)
    correct_answer_index: int = Field(ge=0)  # frozen at generation time
    source_uri: str  # TRN-05 citation
    difficulty: str  # "easy" | "medium" | "hard"

class MCQSession(BaseModel):
    """Frozen quiz session — no LLM in scoring path (D-TC-01)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str
    persona_role: str
    questions: list[MCQQuestion]
    answers: list[int] = Field(default_factory=list)

def score_session(session: MCQSession) -> float:
    """Deterministic score: correct answers / total questions.

    Scoring is operator_answer_index == correct_answer_index comparison only.
    No LLM judge in this path (D-TC-01 + Pitfall §3 avoidance).
    """
    if not session.questions:
        return 0.0
    correct = sum(
        1
        for q, a in zip(session.questions, session.answers)
        if a == q.correct_answer_index
    )
    return correct / len(session.questions)
```

**What to replicate:** immutable Pydantic models, pure function for score (no async, no LLM), `correct_answer_index` frozen at generation.

---

### `apps/agents/knowledge/training-coach/src/trn_training_coach/difficulty.py` (utility, CRUD)

**Analog:** `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/mttr.py` (stateless computation)

```python
from __future__ import annotations

_DIFFICULTY_LEVELS = ("easy", "medium", "hard")

def next_difficulty(current: str, *, answered_correctly: bool) -> str:
    """Dynamic difficulty adaption (D-TC-02).

    Rise on correct answer, fall on incorrect, capped at extremes.
    Returns a new string — never mutates current value (immutability).
    """
    idx = _DIFFICULTY_LEVELS.index(current) if current in _DIFFICULTY_LEVELS else 1
    if answered_correctly:
        new_idx = min(idx + 1, len(_DIFFICULTY_LEVELS) - 1)
    else:
        new_idx = max(idx - 1, 0)
    return _DIFFICULTY_LEVELS[new_idx]
```

**What to replicate:** pure function, returns new value (immutability), capped at valid range.

---

### `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/agent.py` (service, CRUD)

**Analog:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py` (autonomous, no HITL)

**Autonomous agent pattern:**
```python
class KnowledgeCurator:
    """Autonomous KnowledgeCurator (D-KC-04 — no HITL, no irreversible action).

    Dedup + stale flag are read/flag operations only.
    Audit rows written immediately (no interrupt() call).
    """

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        # Dedup check (D-KC-01)
        dedup_result = await self._dedup.check(state["document_text"])

        # Staleness check (D-KC-02)
        staleness_result = self._staleness.check(
            doc_type=state["doc_type"],
            last_updated=state["last_updated"],
        )

        # Write audit IMMEDIATELY (no interrupt — autonomous agent D-KC-04)
        if dedup_result.is_duplicate:
            await self._write_audit(action_type=ActionType.KNOWLEDGE_DEDUP, ...)
        if staleness_result.is_stale:
            await self._write_audit(action_type=ActionType.STALE_FLAG, ...)

        return {"curation_report": report}
```

**What to replicate:** no `interrupt()` call anywhere. Audit writes are immediate (before return), NOT after interrupt. This is the one agent pattern that differs from HITL agents — correct for autonomous D-KC-04.

---

### `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/dedup.py` (utility, CRUD)

**Analog:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/validators.py`

**Class structure pattern** (lines 106-194):
```python
from __future__ import annotations
import hashlib
from typing import ClassVar
import structlog

logger = structlog.get_logger("mnt_knowledge_curator.dedup")

class DedupResult:
    """Result of a deduplication check (immutable dataclass-style)."""
    __slots__ = ("is_duplicate", "dup_type", "source_uri", "score")
    # ...

class ExactDedupChecker:
    """SHA-256 exact-duplicate checker (D-KC-01 fast path).

    _NORMALIZE applies lower() + whitespace collapse before hashing.
    """
    _NORMALIZE_SQL: ClassVar[str] = "SELECT source_uri FROM documents WHERE sha256_hash = $1 LIMIT 1"

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for SHA-256 comparison (D-KC-01)."""
        return " ".join(text.lower().split())

    @staticmethod
    def sha256(normalized: str) -> str:
        return hashlib.sha256(normalized.encode()).hexdigest()


class NearDedupChecker:
    """BGE-M3 cosine near-duplicate checker (D-KC-01 slow path).

    Uses direct Qdrant query_points with score_threshold (not RetrievalPipeline).
    See RESEARCH.md RF-1 for exact API pattern.
    """
    # Configurable threshold per Pitfall §6 — default 0.92
    _DEFAULT_COSINE_THRESHOLD: float = 0.92

    def __init__(
        self,
        *,
        qdrant_client: Any,
        embedder: Any,  # BgeM3Embedder
        cosine_threshold: float = _DEFAULT_COSINE_THRESHOLD,
        collection_name: str = "sop",
    ) -> None:
        self._client = qdrant_client
        self._embedder = embedder
        self._threshold = cosine_threshold
        self._collection = collection_name

    async def check(self, normalized_text: str) -> DedupResult:
        output = self._embedder.encode(
            [normalized_text], return_dense=True, return_sparse=False
        )
        dense_vec = output.dense_vecs[0]
        result = await self._client.query_points(
            collection_name=self._collection,
            query=dense_vec.tolist(),
            using="dense",
            limit=5,
            with_payload=False,
            score_threshold=self._threshold,
        )
        is_near_dup = len(result.points) > 0
        # ...
```

**What to replicate:** ClassVar SQL for test inspection, `pool=None` degraded fallback with structlog ERROR (not WARNING), parameterized SQL (`$1`, never f-string interpolation).

---

### `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/staleness.py` (utility, CRUD)

**Analog:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py` (pure computation)

```python
from __future__ import annotations
from datetime import datetime, timezone, timedelta

# D-KC-02: per-document-type configurable thresholds (defaults)
_DEFAULT_THRESHOLDS: dict[str, int] = {
    "sop": 365,      # days
    "runbook": 180,
    "note": 90,
}

def is_stale(
    *,
    doc_type: str,
    last_updated: datetime,
    thresholds: dict[str, int] | None = None,
    now: datetime | None = None,
) -> bool:
    """Return True if the document is past its type-specific staleness threshold.

    Args:
        doc_type: Document type key (e.g. "sop", "runbook", "note").
        last_updated: UTC tz-aware datetime of last document update.
        thresholds: Per-type threshold in days; uses _DEFAULT_THRESHOLDS if None.
        now: Reference datetime (UTC tz-aware); uses datetime.now(UTC) if None.

    Returns:
        True when (now - last_updated).days > threshold[doc_type].
    """
    effective_thresholds = thresholds if thresholds is not None else _DEFAULT_THRESHOLDS
    threshold_days = effective_thresholds.get(doc_type, 90)
    effective_now = now if now is not None else datetime.now(timezone.utc)
    age_days = (effective_now - last_updated).days
    return age_days > threshold_days
```

**What to replicate:** pure function (testable without mocks), accepts `now` override for deterministic testing, defaults injectable via parameter.

---

### `apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/reuse_rate.py` (utility, CRUD)

**Analog:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/repository.py`

**SQL aggregate pattern** (lines 95-137):
```python
from typing import ClassVar

class ReuseRateKPI:
    """Compute knowledge reuse-rate KPI (D-KC-03).

    reuse_rate = distinct_documents_cited / total_indexed_documents
    Source: source_uri citations in audit.actions.evidence_panel (rolling window).
    """
    # SQL queries citations from evidence_panel JSONB across all agent audit rows.
    _SQL_DISTINCT_CITED: ClassVar[str] = (
        "SELECT COUNT(DISTINCT ep_citation->>'source_uri') "
        "FROM audit.actions, "
        "     jsonb_array_elements(evidence_panel->'rag_citations') AS ep_citation "
        "WHERE ts BETWEEN $1 AND $2 "
        "AND ep_citation->>'source_uri' IS NOT NULL"
    )
    _SQL_TOTAL_INDEXED: ClassVar[str] = (
        "SELECT COUNT(*) FROM documents WHERE indexed = true"
    )

    def __init__(self, *, pool: Any) -> None:
        self._pool = pool

    async def compute(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> float:
        """Return reuse_rate in [0.0, 1.0]. Returns 0.0 when no docs indexed."""
        async with self._pool.acquire() as conn:
            cited_count = await conn.fetchval(
                self._SQL_DISTINCT_CITED, window_start, window_end
            )
            total_count = await conn.fetchval(self._SQL_TOTAL_INDEXED)
        if not total_count:
            return 0.0
        return float(cited_count or 0) / float(total_count)
```

---

### `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/agent.py` (service, request-response)

**Analog:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py`

**Single-supervisor HITL pattern** with LLM-in-path (not retry loop). The critical difference from RCASpecialist is that the Qdrant indexing happens AFTER `interrupt()` returns (the HITL gates the indexing):

```python
async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
    # 1. Fetch historical events (event_aggregator — D-DS-02)
    events = await self._event_aggregator.fetch(
        failure_mode=state["failure_mode"],
        asset_id=state["asset_id"],
        window_days=state.get("window_days", 180),
    )

    # 2. RAG grounding citations (RetrievalPipeline.search)
    citations = await self._retrieval.search(
        query=state["failure_mode"],
        user_roles=state.get("user_roles", ["technician"]),
        category="sop",
        k=5,
        asset_family=state.get("asset_family"),
    )

    # 3. LLM: generate IT SOP with [SRC:N] anchors (Pitfall §1 mitigation)
    sop_it, anchor_map = await self._generate_it_sop(events, citations)

    # 4. LLM: translate to EN, re-anchor citations (D-DS-01)
    sop_en = await self._translate_en(sop_it, anchor_map)

    # 5. Validate citations (validators.py — TRN-05)
    validated = self._validator.validate(sop_it, sop_en, anchor_map)

    # 6. HITL gate BEFORE Qdrant indexing (D-DS-03, CR-02 fix)
    decision = interrupt({
        "tier": Tier.SUPERVISOR.value,
        "payload": validated.model_dump(mode="json"),
    })

    # 7. Qdrant indexing AFTER interrupt returns (on resume)
    await self._indexer.upsert(validated)

    # 8. Audit row AFTER interrupt (CR-02 fix)
    await self._write_audit(
        action_type=ActionType.SOP_DRAFT,
        motivation=f"Supervisor approved: {decision}",
    )

    return {"sop_draft": validated}
```

---

### `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/event_aggregator.py` (service, CRUD)

**Analog:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/repository.py`

**Cross-cluster JSONB query pattern** (lines 118-137 analog):
```python
class HistoricalEventAggregator:
    """Fetches historical RCA/downtime/coach audit events for SOP synthesis (D-DS-02).

    Reads audit.actions WHERE action_type IN (RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT)
    filtered by evidence_panel->>'failure_mode' + evidence_panel->>'asset_id' + window.
    No schema change needed — uses existing JSONB operators.
    """
    _SQL_HISTORY: ClassVar[str] = (
        "SELECT ts, agent_id, action_type, evidence_panel "
        "FROM audit.actions "
        "WHERE action_type IN ('RCA_CHAIN', 'COACH_STEP', 'DOWNTIME_VERDICT') "
        "AND ts >= NOW() - INTERVAL '$1 days' "   # ← use parameterized approach below
        "AND ($2::TEXT IS NULL OR evidence_panel->>'failure_mode' = $2) "
        "AND ($3::TEXT IS NULL OR evidence_panel->>'asset_id' = $3) "
        "ORDER BY ts DESC "
        "LIMIT 100"
    )
```

Note: INTERVAL cannot be parameterized in asyncpg; use `NOW() - ($1 * INTERVAL '1 day')` or compute the start datetime in Python and pass as `$1 TIMESTAMPTZ`.

---

### `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/validators.py` (utility, CRUD)

**Analog:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/validators.py`

**Exception + validator class pattern** (lines 66-194):
```python
class MissingAnchorError(Exception):
    """Raised when an [SRC:N] anchor from IT text is missing in EN text (Pitfall §1)."""
    def __init__(self, *, anchor_id: str) -> None:
        self.anchor_id = anchor_id
        super().__init__(f"Citation anchor {anchor_id!r} missing from EN translation.")

class CitationDriftError(Exception):
    """Raised when anchor_map has no entry for an anchor found in IT text."""
    ...

class SOPCitationValidator:
    """Post-translation validator: all IT [SRC:N] anchors must survive in EN text.

    TRN-05 citation provenance enforcement.
    Mirrors RCAChainValidator structure (same error pattern, same pool injection).
    """
    def validate(
        self,
        sop_draft: "SOPDraft",
        anchor_map: dict[str, str],
    ) -> "SOPDraft":
        """Validate anchor presence in EN sections matches anchor_map.

        Raises MissingAnchorError if any [SRC:N] from sections_it is absent
        from sections_en. Fail-fast (first missing anchor).
        """
        import re
        it_anchors = set(re.findall(r"\[SRC:\d+\]", " ".join(sop_draft.sections_it.values())))
        en_anchors = set(re.findall(r"\[SRC:\d+\]", " ".join(sop_draft.sections_en.values())))
        for anchor in it_anchors:
            if anchor not in en_anchors:
                raise MissingAnchorError(anchor_id=anchor)
        return sop_draft
```

---

### `apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/models.py` (model, request-response)

**Analog:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/models.py`

**SOPDraft model pattern** (from RESEARCH.md §Code Examples):
```python
from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sft_agents.models.evidence import RagCitation

SECTION_KEYS_IT: tuple[str, ...] = ("Scopo", "Prerequisiti", "Passi", "Sicurezza", "Riferimenti")

class SOPDraft(BaseModel):
    """Fixed-section SOP with IT primary + EN translation (D-DS-01/02/03)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    sop_id: str
    failure_mode: str
    asset_id: str
    title_it: str
    title_en: str
    lang_primary: Literal["it"] = "it"
    sections_it: dict[str, str]   # section_key → content with [SRC:N] anchors
    sections_en: dict[str, str]   # translated, anchors preserved
    citations: list[RagCitation]  # source_uri + timestamp for every anchor (TRN-05)
    anchor_map: dict[str, str]    # anchor_id "[SRC:N]" → source_uri
    generated_at: datetime
    approved: bool = False

    @field_validator("sections_it", "sections_en")
    @classmethod
    def _check_sections(cls, v: dict[str, str]) -> dict[str, str]:
        missing = [k for k in SECTION_KEYS_IT if k not in v]
        if missing:
            raise ValueError(f"Missing required sections: {missing}")
        return v
```

---

## Shared Patterns

### Pattern A: HITL interrupt()-then-audit (CR-02 fix)

**Source:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py` lines 550-584
**Apply to:** `agent.py` files for ShiftHandover, TrainingCoach (on pass), DocumentationSynthesizer
**Pattern:**
```python
# CORRECT (CR-02 fixed) — interrupt() DIRECTLY in __call__
decision = interrupt({
    "tier": Tier.SUPERVISOR.value,
    "payload": output.model_dump(mode="json"),
})
# audit write AFTER interrupt() returns (on resume execution only)
await self._write_audit(
    action_type=ActionType.SOP_DRAFT,
    decision=Decision.HITL_SUPERVISOR,
    approval_id=None,   # CR-03 fix: never fabricate UUID
    motivation=f"Supervisor decision: {decision}",
)
```

### Pattern B: Saver lifecycle (CR-01 fix)

**Source:** `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py` lines 419-449
**Apply to:** ShiftHandover agent (uses LangGraph checkpoint for dual-interrupt)
**Pattern:**
```python
# CORRECT — saver injected via lifespan, NOT opened inside agent
if saver is None:
    raise RuntimeError(
        "Saver must be injected at construction. "
        "See api-gateway lifespan.py for the correct DI pattern."
    )
```

### Pattern C: asyncpg datetime objects (WR-03 fix)

**Source:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/repository.py` lines 165-235
**Apply to:** All asyncpg queries in `aggregator.py`, `event_aggregator.py`, `reuse_rate.py`
**Pattern:**
```python
# CORRECT — pass datetime objects directly
rows = await conn.fetch(sql, window_start, window_end)

# WRONG — never call .isoformat()
rows = await conn.fetch(sql, window_start.isoformat(), window_end.isoformat())
```

### Pattern D: Frozen Pydantic models (immutability)

**Source:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/models.py` lines 29-63
**Apply to:** All `models.py` files across 4 agents
**Pattern:**
```python
class AnyModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    # All fields use Field() with explicit constraints
```

### Pattern E: ClassVar SQL constants for parameterization gate

**Source:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/repository.py` lines 78-137
**Apply to:** `aggregator.py`, `event_aggregator.py`, `reuse_rate.py`, `dedup.py`
**Pattern:**
```python
class MyRepository:
    _SQL_QUERY: ClassVar[str] = (
        "SELECT ... FROM table WHERE col = $1 AND ts BETWEEN $2 AND $3"
    )
    # All SQL uses $N parameterized placeholders — NEVER f-string or %-format
```

### Pattern F: structlog module-level logger

**Source:** All agent files (universal pattern)
**Apply to:** All new Python files
**Pattern:**
```python
import structlog
logger = structlog.get_logger("agent.<slug>")  # or "mnt_<module>.<submodule>"
```

### Pattern G: langgraph.types.interrupt graceful fallback

**Source:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py` lines 55-63
**Apply to:** All agent files with HITL
**Pattern:**
```python
try:
    from langgraph.types import interrupt
except ImportError:
    def interrupt(value: Any) -> Any:
        raise NotImplementedError("langgraph.types.interrupt is not available")
```

### Pattern H: approval_id=None for pending HITL (CR-03 fix)

**Source:** RESEARCH.md §RF-2 and all Phase 7 agent `_write_audit` calls
**Apply to:** All HITL audit writes in ShiftHandover, TrainingCoach, DocumentationSynthesizer
**Pattern:**
```python
record = AuditRecord(
    ...
    approval_id=None,   # CR-03 fix: never fabricate UUID for pending HITL
)
```

### Pattern I: Module-level AGENT_ID + CLUSTER constants

**Source:** `mnt_rca_specialist/agent.py` lines 79-82
**Apply to:** All 4 agent `agent.py` files
**Pattern:**
```python
AGENT_ID: str = "shift-handover"   # kebab-case slug
CLUSTER: str = "knowledge"          # all 4 knowledge agents share this cluster
```

### Pattern J: Test — mock interrupt + count audit writes

**Source:** `mnt_rca_specialist/tests/test_interrupt_audit_lifecycle.py` lines 209-323
**Apply to:** `test_dual_signoff.py`, `test_hitl_lifecycle.py`, `test_hitl_preindex.py`
**Pattern:**
```python
with patch("<package>.agent.interrupt", _simulated_interrupt):
    with pytest.raises(GraphInterrupt):
        await agent(state=_STATE)
    assert audit_writer.write.call_count == 0  # not fired on first run

    with patch.object(agent, "_write_audit", side_effect=_spy):
        await agent(state=_STATE)  # resume

assert len(write_calls) == N  # exact count per agent HITL contract
```

---

## No Analog Found

All files have at least a role-match analog. However, some patterns are new for Phase 8:

| File | Role | Data Flow | Reason / Guidance |
|------|------|-----------|-------------------|
| `trn_shift_handover/agent.py` dual-interrupt | service | request-response | Dual sequential `interrupt()` calls have no prior codebase precedent. Follow RESEARCH.md §RF-2 exactly for the two-interrupt-two-audit-row ordering. |
| `trn_documentation_synthesizer/translator.py` | utility | transform | IT→EN translation + citation re-anchoring has no prior analog. Use RESEARCH.md §Pitfall 1 pattern: `[SRC:N]` markers embedded in IT, preserved through translation, validated in EN. |
| `trn_training_coach/difficulty.py` | utility | CRUD | Dynamic difficulty adaption is new. Pure function, no async needed — see Pattern D (immutability). |
| `trn_knowledge_curator/dedup.py` `NearDedupChecker` | utility | CRUD | BGE-M3 direct Qdrant query pattern is documented in RESEARCH.md §RF-1 with exact API. No prior agent uses this path directly (Phase 5 uses it internally). |

---

## Metadata

**Analog search scope:** `apps/agents/maintenance/`, `packages/sft-agents/src/`, `apps/api-gateway/src/`, `infra/migrations/timescale/`
**Files scanned:** ~52 Python files + 9 SQL migration files
**Pattern extraction date:** 2026-05-24
