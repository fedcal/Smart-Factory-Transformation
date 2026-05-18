"""POST /v1/threads/{thread_id}/resume — Plan 04-07 Task 2.

Same resume semantics as POST /v1/approvals/{id}/decide but routed by
``thread_id`` rather than approval id. Useful when the caller (e.g. an
operator UI poll loop) has lost track of the approval id but still has the
LangGraph thread context.

T-04-Resume-Replay defense:
    Layer 1: checkpointer.aget_tuple(config) returns None → 404 immediately.
    Layer 2: Idempotency-Key cache (5min).

The actual hitl.approvals UPDATE happens inside human_approval_node when the
graph resumes via Command(resume=...).
"""

from __future__ import annotations

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from langgraph.types import Command

from sft_agents.models.approval import ApprovalDecision

from svc_api_gateway.dependencies import (
    get_checkpointer,
    get_idempotency_cache,
    get_supervisor_graph,
)
from svc_api_gateway.idempotency import IdempotencyCache
from svc_api_gateway.idempotency_middleware import (
    check_idempotency_cache,
    jsonable,
    store_idempotent_response,
)
from svc_api_gateway.models.requests import ResumeRequest
from svc_api_gateway.models.responses import ResumeResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/threads", tags=["threads"])


@router.post("/{thread_id}/resume", response_model=ResumeResponse)
async def resume_thread(
    thread_id: str,
    request: Request,
    body: Annotated[ResumeRequest, Body()],
    checkpointer: Any = Depends(get_checkpointer),
    supervisor_graph: Any = Depends(get_supervisor_graph),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    raw_body = await request.body()

    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    # Verify the checkpoint exists before invoking the graph (avoid the graph
    # going through the route node when there is no thread to resume).
    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id, "checkpoint_ns": ""},
        "recursion_limit": 25,
    }
    cp_tuple = await checkpointer.aget_tuple(config)
    if cp_tuple is None:
        raise HTTPException(status_code=404, detail="thread_checkpoint_not_found")

    # Build the resume payload. The Pydantic model enforces non-empty
    # motivation — operator-tier callers using this endpoint must still pass
    # SOMETHING (the operator UI substitutes a marker for "no comment").
    effective_motivation = body.motivation.strip() or "operator_auto_motivation_unset"
    decision_payload = ApprovalDecision(
        decision=body.decision,
        motivation=effective_motivation,
        decided_by=body.decided_by,
    )

    state_after: dict[str, Any] = {}
    completed = False
    try:
        state_after = await supervisor_graph.ainvoke(
            Command(resume=decision_payload.model_dump(mode="json")),
            config=config,
        ) or {}
        completed = True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "supervisor_thread_resume_failed",
            error=str(exc),
            thread_id=thread_id,
            approval_id=str(body.approval_id),
        )
        completed = False

    response = ResumeResponse(
        thread_id=thread_id,
        state_after=_jsonable_state(state_after),
        audit_ids=[],
        completed=completed,
    )
    payload = jsonable(response.model_dump(mode="json"))
    await store_idempotent_response(request, cache, body_hash, payload, status_code=200)
    return payload


def _jsonable_state(state: Any) -> dict[str, Any]:
    """Best-effort coerce graph state to a JSON-serialisable dict."""
    if not isinstance(state, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in state.items():
        try:
            jsonable(v)
            out[str(k)] = v
        except (TypeError, ValueError):
            out[str(k)] = str(v)
    return out


__all__ = ["router"]
