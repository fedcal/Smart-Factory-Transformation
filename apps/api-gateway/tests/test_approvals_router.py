"""Unit tests for GET /v1/approvals + POST /v1/approvals/{id}/decide.

Covers (Plan 04-07 Task 2 acceptance set):
    1. GET happy path — filtered list returns shape with items/total/limit/offset
    2. POST happy path — valid body returns 200, calls queue_writer.update_decision
       + supervisor_graph.ainvoke(Command(resume=...))
    3. Missing motivation on hitl_supervisor tier with decision=approve → 400
    4. Non-existent approval id → 404
    5. queue_writer.update_decision raises ApprovalNotFoundError → 404
    6. Idempotency-Key replay with SAME body returns cached response (1 call)
    7. Idempotency-Key replay with DIFFERENT body → 409
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest


UTC = timezone.utc

# Reusable canned approval row + audit_id used across tests.
_APPROVAL_ID = UUID("11111111-2222-3333-4444-555555555555")
_THREAD_ID = "ops.operator-assistant.66666666-7777-8888-9999-000000000001"
_NOW = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)


def _canned_row(*, tier: str = "operator", status: str = "pending") -> dict:
    return {
        "id": _APPROVAL_ID,
        "agent_id": "operator-assistant",
        "thread_id": _THREAD_ID,
        "tier": tier,
        "action_type": "WRITE_PLC_SETPOINT",
        "payload_json": '{"target_subject":"line.A","args":{"v":1}}',
        "status": status,
        "created_at": _NOW,
        "sla_deadline": _NOW + timedelta(minutes=2),
        "decided_at": None,
        "decided_by": None,
        "decision_json": None,
        "escalated_to_id": None,
    }


def _attach_row_fetch(pool, row: dict | None) -> None:
    """Wire the mock pool so conn.fetchrow returns ``row`` and conn.fetch returns [row]."""
    pool._test_conn.fetchrow = AsyncMock(return_value=row)
    pool._test_conn.fetch = AsyncMock(return_value=[row] if row else [])


@pytest.mark.asyncio
async def test_get_approvals_returns_filtered_list(client, app_with_mocks) -> None:
    pool = app_with_mocks.state.pool
    row = _canned_row()
    pool._test_conn.fetch = AsyncMock(return_value=[row])
    pool._test_conn.fetchval = AsyncMock(return_value=1)

    response = await client.get("/v1/approvals?tier=operator&status=pending&limit=50&offset=0")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(_APPROVAL_ID)
    assert body["items"][0]["tier"] == "operator"


@pytest.mark.asyncio
async def test_decide_happy_path(client, app_with_mocks) -> None:
    pool = app_with_mocks.state.pool
    # Two fetchrow calls: 1) initial SELECT, 2) refetched after UPDATE.
    decided_row = {**_canned_row(), "status": "approved", "decided_by": "op-001",
                   "decided_at": _NOW, "decision_json": '{"decision":"approve","motivation":"ok","decided_by":"op-001"}'}
    pool._test_conn.fetchrow = AsyncMock(side_effect=[_canned_row(), decided_row])

    queue_writer = app_with_mocks.state.queue_writer
    queue_writer.update_decision = AsyncMock(return_value=None)

    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"messages": [], "proposed_actions": []})

    response = await client.post(
        f"/v1/approvals/{_APPROVAL_ID}/decide",
        json={"decision": "approve", "motivation": "ok", "decided_by": "op-001"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["approval"]["status"] == "approved"
    assert body["resumed"] is True
    assert queue_writer.update_decision.await_count == 1
    assert graph.ainvoke.await_count == 1


@pytest.mark.asyncio
async def test_decide_missing_motivation_for_supervisor_tier_returns_400(
    client, app_with_mocks
) -> None:
    pool = app_with_mocks.state.pool
    _attach_row_fetch(pool, _canned_row(tier="supervisor"))

    response = await client.post(
        f"/v1/approvals/{_APPROVAL_ID}/decide",
        json={"decision": "approve", "motivation": "", "decided_by": "sup-001"},
    )
    assert response.status_code == 400, response.text
    body = response.json()
    assert "motivation" in body["detail"].lower()


@pytest.mark.asyncio
async def test_decide_id_not_found_returns_404(client, app_with_mocks) -> None:
    pool = app_with_mocks.state.pool
    _attach_row_fetch(pool, None)

    response = await client.post(
        f"/v1/approvals/{_APPROVAL_ID}/decide",
        json={"decision": "approve", "motivation": "ok", "decided_by": "op"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_decide_already_decided_returns_404(client, app_with_mocks) -> None:
    pool = app_with_mocks.state.pool
    _attach_row_fetch(pool, _canned_row(status="approved"))

    response = await client.post(
        f"/v1/approvals/{_APPROVAL_ID}/decide",
        json={"decision": "approve", "motivation": "ok", "decided_by": "op"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_decide_raises_approval_not_found_returns_404(client, app_with_mocks) -> None:
    """Race-condition path: SELECT finds row, but UPDATE returns 0 (race)."""
    from sft_agents.hitl.approval_queue import ApprovalNotFoundError

    pool = app_with_mocks.state.pool
    pool._test_conn.fetchrow = AsyncMock(return_value=_canned_row())

    queue_writer = app_with_mocks.state.queue_writer
    queue_writer.update_decision = AsyncMock(
        side_effect=ApprovalNotFoundError("race")
    )

    response = await client.post(
        f"/v1/approvals/{_APPROVAL_ID}/decide",
        json={"decision": "approve", "motivation": "ok", "decided_by": "op"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_idempotency_replay_returns_cached_response(client, app_with_mocks) -> None:
    pool = app_with_mocks.state.pool
    decided_row = {**_canned_row(), "status": "approved", "decided_by": "op",
                   "decided_at": _NOW,
                   "decision_json": '{"decision":"approve","motivation":"ok","decided_by":"op"}'}
    pool._test_conn.fetchrow = AsyncMock(side_effect=[_canned_row(), decided_row,
                                                       _canned_row(), decided_row])

    queue_writer = app_with_mocks.state.queue_writer
    queue_writer.update_decision = AsyncMock(return_value=None)

    body = {"decision": "approve", "motivation": "ok", "decided_by": "op"}
    headers = {"Idempotency-Key": "replay-key-1"}

    r1 = await client.post(
        f"/v1/approvals/{_APPROVAL_ID}/decide", json=body, headers=headers
    )
    assert r1.status_code == 200, r1.text

    r2 = await client.post(
        f"/v1/approvals/{_APPROVAL_ID}/decide", json=body, headers=headers
    )
    assert r2.status_code == 200, r2.text
    assert r1.json() == r2.json()
    # Idempotent — UPDATE called exactly once across both requests.
    assert queue_writer.update_decision.await_count == 1


@pytest.mark.asyncio
async def test_idempotency_conflict_on_different_body_returns_409(
    client, app_with_mocks
) -> None:
    pool = app_with_mocks.state.pool
    decided_row = {**_canned_row(), "status": "approved", "decided_by": "op",
                   "decided_at": _NOW,
                   "decision_json": '{"decision":"approve","motivation":"ok","decided_by":"op"}'}
    pool._test_conn.fetchrow = AsyncMock(side_effect=[_canned_row(), decided_row])

    queue_writer = app_with_mocks.state.queue_writer
    queue_writer.update_decision = AsyncMock(return_value=None)

    headers = {"Idempotency-Key": "replay-key-2"}
    r1 = await client.post(
        f"/v1/approvals/{_APPROVAL_ID}/decide",
        json={"decision": "approve", "motivation": "ok", "decided_by": "op"},
        headers=headers,
    )
    assert r1.status_code == 200, r1.text

    r2 = await client.post(
        f"/v1/approvals/{_APPROVAL_ID}/decide",
        json={"decision": "reject", "motivation": "no", "decided_by": "op"},
        headers=headers,
    )
    assert r2.status_code == 409, r2.text
    assert "idempotency" in r2.json()["detail"].lower()
