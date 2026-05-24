"""POST /v1/agents/{slug}/{action} — Plan 09-06 (SCM-01/02/03/04).

Supply cluster HTTP surface. Mirrors Phase 8 08-08 knowledge_agents.py routing
pattern; supervisor routes via target_agent into build_supply_subgraph (09-01).
Each endpoint sets ``state["target_agent"]`` in the AgentState passed to the
supervisor graph; the supervisor's HybridRouter dispatches into the supply
subgraph which routes to the named child callable.

Endpoints
---------
POST /v1/agents/inventory-manager/check    202  Reorder recommendation + HITL (SCM-01)
POST /v1/agents/inventory-manager/resume   200  Resume after supervisor sign-off (SCM-01)
POST /v1/agents/energy-optimizer/optimize  202  Off-peak scheduling proposal + HITL (SCM-02)
POST /v1/agents/energy-optimizer/resume    200  Resume after supervisor sign-off (SCM-02)
POST /v1/agents/cost-analyzer/analyze      200  Autonomous cost analysis + OEPV (SCM-03)
POST /v1/agents/demand-forecaster/forecast 202  Demand forecast + HITL (SCM-04)
POST /v1/agents/demand-forecaster/resume   200  Resume after supervisor sign-off (SCM-04)

Design notes
------------
* cost-analyzer/analyze is fully autonomous (Decision.AUTO, D-SCM-AUTO):
  returns 200 synchronously, NO resume endpoint.
* Idempotency-Key applies to all HITL endpoints (202 responses).
  cost-analyzer/analyze is excluded — deterministic autonomous operation.
* user_roles propagated verbatim into AgentState (Phase 6 dev-mode ACL
  convention; Phase 11 will replace with JWT-derived claims — WR-03).

Threats mitigated (T-09-22..T-09-24 register in 09-06 PLAN):
    * T-09-22 Tampering     — frozen+extra=forbid on all Pydantic models; tz-aware
                              @field_validator on datetime fields (WR-02).
    * T-09-23 Info Disclosure — generic 500 body; str(exc) only server-side log (WR-05).
    * T-09-24 Denial of Service — recursion_limit=5 + RecursionError → 503.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
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

router = APIRouter(prefix="/v1/agents", tags=["supply-agents"])

# Bound the recursion budget so a misbehaving cluster subgraph cannot run away
# (T-09-24). 5 is the per-tick budget per Plan 09-06 contract.
_RECURSION_LIMIT: int = 5

# Retry-After value (seconds) returned on 503 GraphRecursionError (mirror 06-12).
_RETRY_AFTER_SECONDS: int = 5


# ---------------------------------------------------------------------------
# Shared tz-aware validator
# ---------------------------------------------------------------------------


def _require_tz(v: datetime) -> datetime:
    """Reject naive datetimes at the HTTP boundary (WR-02)."""
    if v.tzinfo is None:
        raise ValueError(
            f"Il campo datetime deve essere tz-aware (UTC). "
            f"Ricevuto naive: {v!r}. Aggiungere 'Z' o '+00:00' alla stringa ISO."
        )
    return v


# ---------------------------------------------------------------------------
# Request models (frozen + extra=forbid — T-09-22)
# ---------------------------------------------------------------------------


class InventoryCheckRequest(BaseModel):
    """Request body for POST /v1/agents/inventory-manager/check (SCM-01).

    Manual trigger for InventoryManager single-supervisor HITL flow.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sku_ids: list[str] | None = Field(
        default=None,
        description="Optional list of SKU identifiers to check; None means all SKUs",
    )
    user_roles: list[str] = Field(
        default_factory=list,
        description="Caller roles for ACL enforcement (Phase 11 — WR-03)",
    )


class InventoryResumeRequest(BaseModel):
    """Request body for POST /v1/agents/inventory-manager/resume (SCM-01).

    Resume an inventory check after supervisor reorder sign-off.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    thread_id: str = Field(
        min_length=1,
        max_length=256,
        description="LangGraph thread_id from the original check (supply.inventory-manager.<uuid>)",
    )
    decision: str = Field(
        min_length=1,
        max_length=64,
        description="Supervisor reorder decision (e.g. 'approved', 'rejected')",
    )
    decision_actor: str = Field(
        min_length=1,
        max_length=128,
        description="Identity of the supervisor who made the decision",
    )


class EnergyOptimizeRequest(BaseModel):
    """Request body for POST /v1/agents/energy-optimizer/optimize (SCM-02).

    Triggers EnergyOptimizer off-peak scheduling HITL flow.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    process: str | None = Field(
        default=None,
        max_length=128,
        description="Factory process to analyse (e.g. 'dyeing', 'spinning'); None means all",
    )
    ts_from: datetime | None = Field(
        default=None,
        description="Time-window start (tz-aware UTC) for energy readings",
    )
    ts_to: datetime | None = Field(
        default=None,
        description="Time-window end (tz-aware UTC) for energy readings",
    )
    user_roles: list[str] = Field(
        default_factory=list,
        description="Caller roles for ACL enforcement (Phase 11 — WR-03)",
    )

    @field_validator("ts_from", "ts_to")
    @classmethod
    def _require_tz(cls, v: datetime | None) -> datetime | None:
        """Reject naive datetimes at the HTTP boundary (WR-02)."""
        if v is not None:
            return _require_tz(v)
        return v


class EnergyResumeRequest(BaseModel):
    """Request body for POST /v1/agents/energy-optimizer/resume (SCM-02).

    Resume an energy optimization after supervisor off-peak sign-off.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    thread_id: str = Field(
        min_length=1,
        max_length=256,
        description="LangGraph thread_id from the original optimize (supply.energy-optimizer.<uuid>)",
    )
    decision: str = Field(
        min_length=1,
        max_length=64,
        description="Supervisor off-peak proposal decision (e.g. 'approved', 'rejected')",
    )
    decision_actor: str = Field(
        min_length=1,
        max_length=128,
        description="Identity of the supervisor who made the decision",
    )


class CostAnalyzeRequest(BaseModel):
    """Request body for POST /v1/agents/cost-analyzer/analyze (SCM-03, D-SCM-AUTO).

    Triggers the fully autonomous CostAnalyzer (no HITL, Decision.AUTO).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ribasso_pct: float = Field(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Ribasso percentage for OEPV simulation (0–100)",
    )
    pt: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Punteggio tecnico for OEPV simulation (0–100)",
    )
    oepv_config: dict[str, Any] | None = Field(
        default=None,
        description="Optional OepvConfig overrides (alpha, beta, gamma, delta weights)",
    )
    ts_from: datetime | None = Field(
        default=None,
        description="Cost aggregation window start (tz-aware UTC)",
    )
    ts_to: datetime | None = Field(
        default=None,
        description="Cost aggregation window end (tz-aware UTC)",
    )
    window_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Cost aggregation window in days (fallback when ts_from/ts_to not set)",
    )
    user_roles: list[str] = Field(
        default_factory=list,
        description="Caller roles for ACL enforcement (Phase 11 — WR-03)",
    )

    @field_validator("ts_from", "ts_to")
    @classmethod
    def _require_tz(cls, v: datetime | None) -> datetime | None:
        """Reject naive datetimes at the HTTP boundary (WR-02)."""
        if v is not None:
            return _require_tz(v)
        return v


class DemandForecastRequest(BaseModel):
    """Request body for POST /v1/agents/demand-forecaster/forecast (SCM-04).

    Triggers DemandForecaster Holt-Winters HITL flow.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sku_groups: list[str] | None = Field(
        default=None,
        description="SKU groups to forecast (e.g. ['jersey', 'twill']); None means defaults",
    )
    horizon: int = Field(
        default=6,
        ge=1,
        le=36,
        description="Forecast horizon in months (1–36)",
    )
    months_back: int = Field(
        default=24,
        ge=6,
        le=120,
        description="Historical months to use for training (6–120)",
    )
    user_roles: list[str] = Field(
        default_factory=list,
        description="Caller roles for ACL enforcement (Phase 11 — WR-03)",
    )


class DemandResumeRequest(BaseModel):
    """Request body for POST /v1/agents/demand-forecaster/resume (SCM-04).

    Resume demand forecasting after supervisor plan sign-off.
    Publishes demand_plan to ProductionPlanner via returned state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    thread_id: str = Field(
        min_length=1,
        max_length=256,
        description="LangGraph thread_id from the original forecast (supply.demand-forecaster.<uuid>)",
    )
    decision: str = Field(
        min_length=1,
        max_length=64,
        description="Supervisor demand-plan decision (e.g. 'approved', 'rejected')",
    )
    decision_actor: str = Field(
        min_length=1,
        max_length=128,
        description="Identity of the supervisor who made the decision",
    )


# ---------------------------------------------------------------------------
# Helpers: surface agent invocation errors (WR-05, T-09-23, T-09-24)
# ---------------------------------------------------------------------------


def _handle_recursion_error(exc: RecursionError, thread_id: str) -> JSONResponse:
    """Return 503 with Retry-After header (mirror 06-12 escalation pattern — T-09-24)."""
    logger.warning(
        "supply_agent_recursion_overflow",
        thread_id=thread_id,
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": "recursion_limit_exceeded", "thread_id": thread_id},
        headers={"Retry-After": str(_RETRY_AFTER_SECONDS)},
    )


def _handle_agent_error(exc: Exception, thread_id: str) -> JSONResponse:
    """Surface unexpected agent invocation errors as 500 (WR-05 — never str(exc) in body).

    The raw exception detail is logged server-side only (T-09-23 — information
    disclosure prevention).
    """
    logger.error(
        "supply_agent_invocation_error",
        thread_id=thread_id,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_agent_error", "thread_id": thread_id},
    )


# ---------------------------------------------------------------------------
# POST /v1/agents/inventory-manager/check — InventoryManager HITL (SCM-01)
# ---------------------------------------------------------------------------


@router.post(
    "/inventory-manager/check",
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_inventory_check(
    request: Request,
    body: Annotated[InventoryCheckRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Trigger inventory reorder check with HITL supervisor sign-off (SCM-01).

    Returns 202 Accepted — HITL async. Thread_id identifies the LangGraph thread
    for subsequent supervisor approval via /approvals endpoints.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return JSONResponse(content=cached, status_code=status.HTTP_202_ACCEPTED)

    thread_id = f"supply.inventory-manager.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.inventory-manager.check"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "inventory-manager",
        "sku_ids": body.sku_ids,
        "user_roles": list(body.user_roles),
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable({"thread_id": thread_id, "hitl_status": "supervisor_pending"})
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_202_ACCEPTED
    )
    return JSONResponse(content=payload, status_code=status.HTTP_202_ACCEPTED)


# ---------------------------------------------------------------------------
# POST /v1/agents/inventory-manager/resume — InventoryManager resume (SCM-01)
# ---------------------------------------------------------------------------


@router.post(
    "/inventory-manager/resume",
    status_code=status.HTTP_200_OK,
)
async def post_inventory_resume(
    request: Request,
    body: Annotated[InventoryResumeRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Resume inventory reorder check after supervisor HITL resolution (SCM-01).

    Uses the original thread_id so LangGraph replays the checkpoint and continues
    from the interrupt() point. Returns the final reorder_recommendation.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    thread_id = body.thread_id
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.inventory-manager.resume"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "inventory-manager",
        "action": "resume",
        "thread_id": thread_id,
        "decision": body.decision,
        "decision_actor": body.decision_actor,
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable(
        {
            "thread_id": thread_id,
            "reorder_recommendation": result.get("reorder_recommendation"),
            "reorder_alert": result.get("reorder_alert"),
        }
    )
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# POST /v1/agents/energy-optimizer/optimize — EnergyOptimizer HITL (SCM-02)
# ---------------------------------------------------------------------------


@router.post(
    "/energy-optimizer/optimize",
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_energy_optimize(
    request: Request,
    body: Annotated[EnergyOptimizeRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Trigger energy off-peak scheduling proposal with HITL supervisor sign-off (SCM-02).

    Returns 202 Accepted — HITL async. Thread_id identifies the LangGraph thread
    for subsequent supervisor approval.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return JSONResponse(content=cached, status_code=status.HTTP_202_ACCEPTED)

    thread_id = f"supply.energy-optimizer.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.energy-optimizer.optimize"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "energy-optimizer",
        "process": body.process,
        "ts_from": body.ts_from,
        "ts_to": body.ts_to,
        "user_roles": list(body.user_roles),
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable({"thread_id": thread_id, "hitl_status": "supervisor_pending"})
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_202_ACCEPTED
    )
    return JSONResponse(content=payload, status_code=status.HTTP_202_ACCEPTED)


# ---------------------------------------------------------------------------
# POST /v1/agents/energy-optimizer/resume — EnergyOptimizer resume (SCM-02)
# ---------------------------------------------------------------------------


@router.post(
    "/energy-optimizer/resume",
    status_code=status.HTTP_200_OK,
)
async def post_energy_resume(
    request: Request,
    body: Annotated[EnergyResumeRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Resume energy optimization after supervisor off-peak sign-off (SCM-02).

    Uses the original thread_id so LangGraph replays the checkpoint and continues
    from the interrupt() point. Returns the final energy_proposal.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    thread_id = body.thread_id
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.energy-optimizer.resume"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "energy-optimizer",
        "action": "resume",
        "thread_id": thread_id,
        "decision": body.decision,
        "decision_actor": body.decision_actor,
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable(
        {
            "thread_id": thread_id,
            "energy_proposal": result.get("energy_proposal"),
            "energy_alert": result.get("energy_alert"),
        }
    )
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# POST /v1/agents/cost-analyzer/analyze — CostAnalyzer autonomous (SCM-03)
# ---------------------------------------------------------------------------


@router.post(
    "/cost-analyzer/analyze",
    status_code=status.HTTP_200_OK,
)
async def post_cost_analyze(
    request: Request,
    body: Annotated[CostAnalyzeRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
) -> Any:
    """Autonomous cost analysis + OEPV simulation (SCM-03, D-SCM-AUTO).

    NO Idempotency-Key required — fully autonomous deterministic operation;
    Decision.AUTO, no HITL interrupt. Returns 200 synchronously.
    NO resume endpoint (cost-analyzer is read-only, always autonomous).
    """
    thread_id = f"supply.cost-analyzer.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.cost-analyzer.analyze"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "cost-analyzer",
        "ribasso_pct": body.ribasso_pct,
        "pt": body.pt,
        "oepv_config": body.oepv_config,
        "ts_from": body.ts_from,
        "ts_to": body.ts_to,
        "window_days": body.window_days,
        "user_roles": list(body.user_roles),
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    return jsonable(
        {
            "thread_id": thread_id,
            "cost_breakdown": result.get("cost_breakdown"),
            "oepv_report": result.get("oepv_report"),
        }
    )


# ---------------------------------------------------------------------------
# POST /v1/agents/demand-forecaster/forecast — DemandForecaster HITL (SCM-04)
# ---------------------------------------------------------------------------


@router.post(
    "/demand-forecaster/forecast",
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_demand_forecast(
    request: Request,
    body: Annotated[DemandForecastRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Trigger Holt-Winters demand forecast with HITL supervisor sign-off (SCM-04).

    Returns 202 Accepted — HITL async. Thread_id identifies the LangGraph thread
    for subsequent supervisor approval. On resume, publishes demand_plan to
    ProductionPlanner via state['demand_plan'] (Open Question 2 resolution).
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return JSONResponse(content=cached, status_code=status.HTTP_202_ACCEPTED)

    thread_id = f"supply.demand-forecaster.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.demand-forecaster.forecast"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "demand-forecaster",
        "sku_groups": body.sku_groups,
        "horizon": body.horizon,
        "months_back": body.months_back,
        "user_roles": list(body.user_roles),
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable({"thread_id": thread_id, "hitl_status": "supervisor_pending"})
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_202_ACCEPTED
    )
    return JSONResponse(content=payload, status_code=status.HTTP_202_ACCEPTED)


# ---------------------------------------------------------------------------
# POST /v1/agents/demand-forecaster/resume — DemandForecaster resume (SCM-04)
# ---------------------------------------------------------------------------


@router.post(
    "/demand-forecaster/resume",
    status_code=status.HTTP_200_OK,
)
async def post_demand_resume(
    request: Request,
    body: Annotated[DemandResumeRequest, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Resume demand forecast after supervisor plan sign-off (SCM-04).

    Uses the original thread_id so LangGraph replays the checkpoint and continues
    from the interrupt() point. Returns the final demand_plan which the gateway
    routes to ProductionPlanner via state['demand_plan'] (Open Question 2 resolution).
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    thread_id = body.thread_id
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.demand-forecaster.resume"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "demand-forecaster",
        "action": "resume",
        "thread_id": thread_id,
        "decision": body.decision,
        "decision_actor": body.decision_actor,
    }

    try:
        result = await supervisor_graph.ainvoke(state, config=config) or {}
    except RecursionError as exc:
        return _handle_recursion_error(exc, thread_id)
    except Exception as exc:  # noqa: BLE001
        return _handle_agent_error(exc, thread_id)

    payload = jsonable(
        {
            "thread_id": thread_id,
            "demand_plan": result.get("demand_plan"),
            "mape_report": result.get("mape_report"),
        }
    )
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


__all__ = ["router"]
