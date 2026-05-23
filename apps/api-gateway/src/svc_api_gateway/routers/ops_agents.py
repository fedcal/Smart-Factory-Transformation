"""POST /v1/agents/{slug}/{action} — Plan 06-12 (OPS-01/02/03).

Three HTTP entrypoints into the OPS-cluster supervisor graph:

    POST /v1/agents/anomaly-detector/scan      → AnomalyDetector tick
    POST /v1/agents/production-planner/plan    → ProductionPlanner draft
    POST /v1/agents/operator-assistant/chat    → OperatorAssistant chat turn

All three invoke the same compiled ``supervisor_graph`` from
``app.state.supervisor_graph`` and route the request inside the OPS subgraph
via ``state["target_agent"]`` (see ``packages/sft-agents/runtime/clusters.py``
``build_ops_subgraph``).

Threats mitigated:
    * T-V6-injection      — each request body uses the strict
                            ``frozen=True, extra="forbid"`` Pydantic model
                            defined in the agent package (re-exported here
                            via direct import).
    * T-V6-acl-leak       — ``user_roles`` is propagated from the request
                            body into the AgentState verbatim so the agent's
                            RagSearchTool ACL pre-filter fires per-request
                            (Phase 5 D-72). Phase 11 will replace with JWT
                            claims.
    * T-V6-recursion-bomb — ``recursion_limit=5`` is enforced via
                            ``build_invocation_config`` so a misbehaving
                            cluster subgraph cannot starve the supervisor.

Observability:
    Every endpoint tags the Langfuse invocation with
    ``agent.<slug>.invoke`` so traces can be filtered by entrypoint.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import uuid4

import structlog
from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse
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
from svc_api_gateway.models.requests import (
    AnomalyScanRequestBody,
    OperatorChatRequestBody,
    PlanRequestBody,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/agents", tags=["ops-agents"])


# Bound the recursion budget so a misbehaving cluster subgraph cannot run away
# (T-V6-recursion-bomb). 5 is the per-tick budget Phase 6 agents are sized for.
_RECURSION_LIMIT: int = 5


# ---------------------------------------------------------------------------
# /v1/agents/anomaly-detector/scan
# ---------------------------------------------------------------------------


@router.post("/anomaly-detector/scan", status_code=status.HTTP_200_OK)
async def post_anomaly_scan(
    request: Request,
    body: Annotated[AnomalyScanRequestBody, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Run one AnomalyDetector tick via the supervisor graph (OPS-01)."""
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    thread_id = f"ops.anomaly-detector.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.anomaly-detector.invoke"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "anomaly-detector",
        "thread_id": thread_id,
        "window_minutes": body.window_minutes,
        "triggered_by": body.triggered_by,
    }

    result = await supervisor_graph.ainvoke(state, config=config) or {}

    payload = jsonable(
        {
            "anomalies": _jsonable_list(result.get("anomalies", [])),
            "suppressed_count": int(result.get("suppressed_count", 0)),
            "thread_id": thread_id,
        }
    )
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# /v1/agents/production-planner/plan
# ---------------------------------------------------------------------------


@router.post(
    "/production-planner/plan", status_code=status.HTTP_202_ACCEPTED
)
async def post_production_plan(
    request: Request,
    body: Annotated[PlanRequestBody, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Draft a production schedule via ProductionPlanner (OPS-02).

    Returns 202 — the HITL approval is asynchronous; the operator polls
    ``GET /v1/approvals`` (or the existing NATS push) and resolves the draft
    via ``POST /v1/approvals/{id}/decide``.
    """
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return JSONResponse(
            content=cached, status_code=status.HTTP_202_ACCEPTED
        )

    thread_id = f"ops.production-planner.{uuid4()}"
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.production-planner.invoke"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "production-planner",
        "thread_id": thread_id,
        "horizon_days": body.horizon_days,
        "strategy": body.strategy,
        "user_roles": list(body.user_roles),
    }

    result = await supervisor_graph.ainvoke(state, config=config) or {}

    payload = jsonable(
        {
            "thread_id": thread_id,
            "pending_approval_id": _maybe_str(result.get("pending_approval_id")),
            "proposed_actions_count": len(result.get("proposed_actions") or []),
        }
    )
    await store_idempotent_response(
        request,
        cache,
        body_hash,
        payload,
        status_code=status.HTTP_202_ACCEPTED,
    )
    return JSONResponse(
        content=payload, status_code=status.HTTP_202_ACCEPTED
    )


# ---------------------------------------------------------------------------
# /v1/agents/operator-assistant/chat
# ---------------------------------------------------------------------------


@router.post("/operator-assistant/chat", status_code=status.HTTP_200_OK)
async def post_operator_chat(
    request: Request,
    body: Annotated[OperatorChatRequestBody, Body()],
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """One chat turn through the OperatorAssistant ReAct loop (OPS-03)."""
    raw_body = await request.body()
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    # Honour the client-supplied thread_id (multi-turn chat needs the same
    # checkpoint across calls — that's the whole point of the AsyncPostgresSaver).
    thread_id = body.thread_id
    config = build_invocation_config(
        thread_id=thread_id,
        tags=["agent.operator-assistant.invoke"],
        recursion_limit=_RECURSION_LIMIT,
    )

    state: dict[str, Any] = {
        "target_agent": "operator-assistant",
        "thread_id": thread_id,
        "query": body.query,
        "user_roles": list(body.user_roles),
    }

    result = await supervisor_graph.ainvoke(state, config=config) or {}

    payload = jsonable(
        {
            "response_md": str(result.get("response_md", "")),
            "citations": list(result.get("citations") or []),
            "citations_missing": bool(result.get("citations_missing", False)),
            "lang": str(result.get("lang", "it")),
            "tool_calls_count": int(result.get("tool_calls_count", 0)),
            "thread_id": thread_id,
        }
    )
    await store_idempotent_response(
        request, cache, body_hash, payload, status_code=status.HTTP_200_OK
    )
    return payload


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jsonable_list(items: Any) -> list[Any]:
    """Best-effort coerce a list of Pydantic models / dicts to JSON primitives."""
    if not items:
        return []
    out: list[Any] = []
    for item in items:
        dump = getattr(item, "model_dump", None)
        if callable(dump):
            out.append(dump(mode="json"))
        else:
            out.append(item)
    return out


def _maybe_str(v: Any) -> str | None:
    if v is None:
        return None
    return str(v)


__all__ = ["router"]
