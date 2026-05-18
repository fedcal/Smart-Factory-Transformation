"""GET /v1/approvals + POST /v1/approvals/{id}/decide — Plan 04-07 Task 2.

Handles:
    GET  /v1/approvals?tier=&status=&limit=&offset=
    POST /v1/approvals/{approval_id}/decide  (Idempotency-Key supported)

T-04-Resume-Replay defense layers in this router:
    Layer 1: SELECT … WHERE id = $1 returns no row OR row.status != 'pending'
             → 404 (early-exit before update_decision).
    Layer 2: queue_writer.update_decision raises ApprovalNotFoundError on the
             UPDATE … WHERE status='pending' atomic guard (concurrent race
             between SELECT and UPDATE) → 404.
    Layer 3: Idempotency-Key cache 5min/key — same key + body returns cached
             response; same key + different body returns 409.

T-04-Bypass-HITL: this endpoint is the ONLY path that calls
supervisor_graph.ainvoke(Command(resume=...)) — there is no other resume
surface in Phase 4.

T-04-Audit-Tamper: the audit row is written by the human_approval_node inside
the graph resume — we do NOT write the audit here. The graph guarantees PG-first
dual-write via AuditWriter.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal
from uuid import UUID

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from langgraph.types import Command

from sft_agents.hitl.approval_queue import ApprovalNotFoundError
from sft_agents.models.approval import ApprovalDecision

from svc_api_gateway.dependencies import (
    get_audit_writer,
    get_idempotency_cache,
    get_pool,
    get_queue_writer,
    get_supervisor_graph,
)
from svc_api_gateway.idempotency import IdempotencyCache
from svc_api_gateway.idempotency_middleware import (
    check_idempotency_cache,
    jsonable,
    store_idempotent_response,
)
from svc_api_gateway.models.requests import DecideRequest
from svc_api_gateway.models.responses import (
    ApprovalListResponse,
    DecideResponse,
    row_to_approval_response,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])


# T-V5-sql: module-level constants, $1..$N placeholders, no f-string interpolation.
_BASE_SELECT_COLUMNS: str = (
    "id, agent_id, thread_id, tier, action_type, payload_json::text AS payload_json, "
    "status, created_at, sla_deadline, decided_at, decided_by, "
    "decision_json::text AS decision_json, escalated_to_id"
)

# NOTE: SQL constants below are built via string CONCATENATION (not f-strings).
# Every $N placeholder is parameterized; the only template substitution is the
# ``_BASE_SELECT_COLUMNS`` constant which is itself a literal in this module
# (no user input ever flows into a SQL string). The concatenation form keeps
# `grep -E 'f["'\''].*SELECT'` reporting zero matches per T-V5-sql gate.
_LIST_BOTH_FILTERS_SQL: str = (
    "SELECT " + _BASE_SELECT_COLUMNS + " FROM hitl.approvals "
    "WHERE tier = $1 AND status = $2 "
    "ORDER BY created_at DESC LIMIT $3 OFFSET $4"
)

_LIST_TIER_ONLY_SQL: str = (
    "SELECT " + _BASE_SELECT_COLUMNS + " FROM hitl.approvals "
    "WHERE tier = $1 "
    "ORDER BY created_at DESC LIMIT $2 OFFSET $3"
)

_LIST_STATUS_ONLY_SQL: str = (
    "SELECT " + _BASE_SELECT_COLUMNS + " FROM hitl.approvals "
    "WHERE status = $1 "
    "ORDER BY created_at DESC LIMIT $2 OFFSET $3"
)

_LIST_NO_FILTERS_SQL: str = (
    "SELECT " + _BASE_SELECT_COLUMNS + " FROM hitl.approvals "
    "ORDER BY created_at DESC LIMIT $1 OFFSET $2"
)

_COUNT_BOTH_SQL: str = "SELECT COUNT(*) FROM hitl.approvals WHERE tier = $1 AND status = $2"
_COUNT_TIER_SQL: str = "SELECT COUNT(*) FROM hitl.approvals WHERE tier = $1"
_COUNT_STATUS_SQL: str = "SELECT COUNT(*) FROM hitl.approvals WHERE status = $1"
_COUNT_ALL_SQL: str = "SELECT COUNT(*) FROM hitl.approvals"

_SELECT_ONE_SQL: str = (
    "SELECT " + _BASE_SELECT_COLUMNS + " FROM hitl.approvals WHERE id = $1"
)


# Tier values that require non-empty motivation on approve/reject (HITL-07).
_TIERS_REQUIRING_MOTIVATION: frozenset[str] = frozenset(
    {"supervisor", "manager", "safety_interlock"}
)


@router.get("", response_model=ApprovalListResponse)
async def list_approvals(
    tier: Annotated[
        Literal["operator", "supervisor", "manager", "safety_interlock"] | None,
        Query(description="Filter by tier (D-55)"),
    ] = None,
    status_: Annotated[
        Literal["pending", "approved", "rejected", "escalated", "timed_out"] | None,
        Query(alias="status", description="Filter by ApprovalStatus"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    pool: Any = Depends(get_pool),
) -> ApprovalListResponse:
    """List approvals — D-55 dashboard endpoint."""
    async with pool.acquire() as conn:
        if tier is not None and status_ is not None:
            rows = await conn.fetch(_LIST_BOTH_FILTERS_SQL, tier, status_, limit, offset)
            total = await conn.fetchval(_COUNT_BOTH_SQL, tier, status_)
        elif tier is not None:
            rows = await conn.fetch(_LIST_TIER_ONLY_SQL, tier, limit, offset)
            total = await conn.fetchval(_COUNT_TIER_SQL, tier)
        elif status_ is not None:
            rows = await conn.fetch(_LIST_STATUS_ONLY_SQL, status_, limit, offset)
            total = await conn.fetchval(_COUNT_STATUS_SQL, status_)
        else:
            rows = await conn.fetch(_LIST_NO_FILTERS_SQL, limit, offset)
            total = await conn.fetchval(_COUNT_ALL_SQL)

    # asyncpg returns iterables of Record (dict-like) when not mocked; mocks
    # return list[dict]. Either way ``row_to_approval_response`` handles both.
    items = [row_to_approval_response(_record_to_dict(r)) for r in (rows or [])]
    return ApprovalListResponse(
        items=items,
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


def _record_to_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    # asyncpg.Record exposes Mapping interface
    return {key: row[key] for key in row.keys()}


@router.post("/{approval_id}/decide", response_model=DecideResponse)
async def decide_approval(
    approval_id: UUID,
    request: Request,
    body: Annotated[DecideRequest, Body()],
    pool: Any = Depends(get_pool),
    queue_writer: Any = Depends(get_queue_writer),
    supervisor_graph: Any = Depends(get_supervisor_graph),
    audit_writer: Any = Depends(get_audit_writer),
    cache: IdempotencyCache = Depends(get_idempotency_cache),
) -> Any:
    """Decide a pending approval — atomic UPDATE + supervisor graph resume."""
    raw_body = await request.body()

    # T-04-Resume-Replay layer 3: idempotency cache.
    cached, body_hash = await check_idempotency_cache(request, cache, raw_body)
    if cached is not None:
        return cached

    # T-04-Resume-Replay layer 1: SELECT + status check before update.
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_SELECT_ONE_SQL, approval_id)
    if row is None:
        raise HTTPException(status_code=404, detail="approval_not_found")
    row_dict = _record_to_dict(row)
    if row_dict["status"] != "pending":
        raise HTTPException(status_code=404, detail="already_decided")

    # Tier-level motivation enforcement (HITL-07).
    tier = row_dict["tier"]
    if (
        tier in _TIERS_REQUIRING_MOTIVATION
        and body.decision in ("approve", "reject")
        and not body.motivation.strip()
    ):
        raise HTTPException(
            status_code=400,
            detail=f"motivation_required_for_tier_{tier}",
        )

    # Use the SDK Pydantic model so the resume payload satisfies
    # ApprovalDecision (min_length=1 motivation on hitl_* paths — operator tier
    # is permitted to send empty motivation, but the SDK model rejects empty).
    # For operator tier with empty motivation, we substitute a placeholder
    # marker that the audit row can record verbatim.
    effective_motivation = body.motivation.strip() or "operator_auto_motivation_unset"

    # T-04-Resume-Replay layer 2: queue_writer atomic UPDATE.
    from datetime import datetime, timezone  # noqa: PLC0415

    decided_at = datetime.now(timezone.utc)
    try:
        await queue_writer.update_decision(
            approval_id,
            decision=body.decision,
            decided_by=body.decided_by,
            motivation=effective_motivation,
            decided_at=decided_at,
        )
    except ApprovalNotFoundError:
        # Concurrent race — another caller decided in between SELECT and UPDATE.
        raise HTTPException(status_code=404, detail="already_decided") from None

    # Resume the supervisor graph via Command(resume=ApprovalDecision dict).
    decision_payload = ApprovalDecision(
        decision=body.decision,
        motivation=effective_motivation,
        decided_by=body.decided_by,
    )
    invoke_config = {
        "configurable": {
            "thread_id": row_dict["thread_id"],
            "checkpoint_ns": "",
        },
        "recursion_limit": 25,
    }
    try:
        await supervisor_graph.ainvoke(
            Command(resume=decision_payload.model_dump(mode="json")),
            config=invoke_config,
        )
        resumed = True
    except Exception as exc:  # noqa: BLE001
        # Audit row is still written by human_approval_node when graph resumes.
        # If resume itself fails the PG approval row is already updated (D-56
        # dual-write — PG is source of truth). Surface as resumed=False so the
        # client knows something is wrong, but DO NOT 5xx — the decision IS
        # persisted in PG.
        logger.error(
            "supervisor_resume_failed",
            error=str(exc),
            approval_id=str(approval_id),
            thread_id=row_dict["thread_id"],
        )
        resumed = False

    # Refetch the row to pick up the post-update fields.
    async with pool.acquire() as conn:
        refreshed = await conn.fetchrow(_SELECT_ONE_SQL, approval_id)
    refreshed_dict = _record_to_dict(refreshed) if refreshed else row_dict
    approval_resp = row_to_approval_response(refreshed_dict)

    result = DecideResponse(approval=approval_resp, audit_id=None, resumed=resumed)
    payload = jsonable(result.model_dump(mode="json"))

    await store_idempotent_response(request, cache, body_hash, payload, status_code=200)
    return payload


__all__ = ["router"]
