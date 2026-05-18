"""Unit tests for POST /v1/threads/{thread_id}/resume — Plan 04-07 Task 2."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest


UTC = timezone.utc

_APPROVAL_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_THREAD_ID = "ops.operator-assistant.00000000-1111-2222-3333-444444444444"


@pytest.mark.asyncio
async def test_resume_endpoint_happy_path(client, app_with_mocks) -> None:
    # Checkpoint exists — aget_tuple returns a non-None object.
    checkpointer = app_with_mocks.state.checkpointer
    checkpointer.aget_tuple = AsyncMock(return_value=object())

    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"messages": [], "proposed_actions": []})

    response = await client.post(
        f"/v1/threads/{_THREAD_ID}/resume",
        json={
            "approval_id": str(_APPROVAL_ID),
            "decision": "approve",
            "motivation": "ok",
            "decided_by": "op-1",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["thread_id"] == _THREAD_ID
    assert body["completed"] is True
    assert isinstance(body["state_after"], dict)


@pytest.mark.asyncio
async def test_resume_endpoint_thread_not_found_returns_404(client, app_with_mocks) -> None:
    checkpointer = app_with_mocks.state.checkpointer
    checkpointer.aget_tuple = AsyncMock(return_value=None)

    response = await client.post(
        f"/v1/threads/{_THREAD_ID}/resume",
        json={
            "approval_id": str(_APPROVAL_ID),
            "decision": "approve",
            "motivation": "ok",
            "decided_by": "op-1",
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resume_endpoint_idempotency_replay_cached(client, app_with_mocks) -> None:
    checkpointer = app_with_mocks.state.checkpointer
    checkpointer.aget_tuple = AsyncMock(return_value=object())

    graph = app_with_mocks.state.supervisor_graph
    graph.ainvoke = AsyncMock(return_value={"messages": [], "proposed_actions": []})

    headers = {"Idempotency-Key": "thread-replay-1"}
    body = {
        "approval_id": str(_APPROVAL_ID),
        "decision": "approve",
        "motivation": "ok",
        "decided_by": "op-1",
    }

    r1 = await client.post(f"/v1/threads/{_THREAD_ID}/resume", json=body, headers=headers)
    assert r1.status_code == 200, r1.text

    r2 = await client.post(f"/v1/threads/{_THREAD_ID}/resume", json=body, headers=headers)
    assert r2.status_code == 200, r2.text
    assert r1.json() == r2.json()
    assert graph.ainvoke.await_count == 1
