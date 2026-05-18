"""EpisodicReplay query primitive tests (CORE-08, HITL-10) — Plan 04-06 Task 02.

Verifies:
    - replay_thread uses LIMIT 1000 + parameterized $1 thread_id $2 since
    - hydrates AuditRecord (with motivation/approval_id consistency intact)
    - store() raises NotImplementedError (read-only projection)

Integration round-trip (seed audit.actions, replay, assert ts-ordering) is gated
by ``@pytest.mark.integration`` since it requires a real PG hypertable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

pytest.importorskip(
    "sft_agents.memory.episodic",
    reason="Plan 04-06 Task 02 implements EpisodicReplay",
)

from sft_agents.memory.episodic import EpisodicReplay  # noqa: E402
from sft_agents.models.budget import BudgetSnapshot  # noqa: E402
from sft_agents.models.enums import Decision  # noqa: E402
from sft_agents.models.evidence import EvidencePanel, TokenUsage  # noqa: E402
from sft_agents.models.memory_record import MemoryRecord  # noqa: E402


def _evidence_json(summary: str = "ev1") -> str:
    return EvidencePanel(
        input_summary=summary,
        tool_calls=[],
        rag_citations=[],
        confidence=0.9,
        model="qwen2.5-14b-awq@vllm-0.8",
        prompt_hash="a" * 64,
        tokens=TokenUsage(input=1, output=2, total=3),
        duration_ms=10,
    ).model_dump_json()


def _budget_json() -> str:
    return BudgetSnapshot(
        tokens_input=1,
        tokens_output=2,
        tokens_total=3,
        cost_usd_simulated=0.01,
        duration_ms=10,
        limit_tokens=50000,
        limit_cost_usd=1.0,
        limit_duration_s=60,
    ).model_dump_json()


def _seed_row(*, thread_id: str, ts: datetime, agent_id: str = "operator-assistant") -> dict:
    return {
        "id": uuid4(),
        "ts": ts,
        "action_id": uuid4(),
        "agent_id": agent_id,
        "thread_id": thread_id,
        "cluster": "ops",
        "action_type": "TEST",
        "evidence_panel": _evidence_json(thread_id),
        "decision": Decision.AUTO.value,
        "decision_actor": None,
        "motivation": None,
        "budget_snapshot": _budget_json(),
        "approval_id": None,
    }


async def test_replay_thread_uses_limit_1000_and_parameterized_sql(
    mock_pool: AsyncMock,
) -> None:
    """SQL contains LIMIT 1000 and $1/$2 placeholders; no f-string interpolation."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetch = AsyncMock(return_value=[])
    ep = EpisodicReplay(pool=mock_pool)

    await ep.replay_thread("ops.operator-assistant.session-1", since=None)

    args, _ = conn.fetch.call_args
    sql = args[0]
    assert "LIMIT 1000" in sql
    assert "$1" in sql and "$2" in sql
    assert "ops.operator-assistant.session-1" not in sql  # NOT interpolated


async def test_replay_thread_hydrates_audit_records(mock_pool: AsyncMock) -> None:
    """Replay yields AuditRecord instances with EvidencePanel parsed back from JSONB."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    rows = [
        _seed_row(thread_id="t-rate-1", ts=datetime(2026, 5, 18, 12, 0, tzinfo=UTC)),
        _seed_row(thread_id="t-rate-1", ts=datetime(2026, 5, 18, 12, 1, tzinfo=UTC)),
        _seed_row(thread_id="t-rate-1", ts=datetime(2026, 5, 18, 12, 2, tzinfo=UTC)),
    ]
    conn.fetch = AsyncMock(return_value=rows)
    ep = EpisodicReplay(pool=mock_pool)

    records = await ep.replay_thread("t-rate-1")

    assert len(records) == 3
    assert all(r.thread_id == "t-rate-1" for r in records)
    assert records[0].evidence_panel.input_summary == "t-rate-1"
    assert records[0].decision == Decision.AUTO


async def test_replay_thread_filters_passed_to_sql(mock_pool: AsyncMock) -> None:
    """`since` value is the second SQL parameter (not interpolated)."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetch = AsyncMock(return_value=[])
    ep = EpisodicReplay(pool=mock_pool)

    since = datetime(2026, 5, 18, 12, 30, tzinfo=UTC)
    await ep.replay_thread("t-rate-1", since=since)

    args, _ = conn.fetch.call_args
    assert args[1] == "t-rate-1"
    assert args[2] == since


async def test_query_filter_by_thread_id_limits_k(mock_pool: AsyncMock) -> None:
    """query(filters={'thread_id': ...}) → first k AuditRecord rows as MemoryRecord."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    rows = [
        _seed_row(thread_id="t1", ts=datetime(2026, 5, 18, 12, i, tzinfo=UTC))
        for i in range(10)
    ]
    conn.fetch = AsyncMock(return_value=rows)
    ep = EpisodicReplay(pool=mock_pool)

    out = await ep.query("ignored", k=3, filters={"thread_id": "t1"})

    assert len(out) == 3
    assert all(isinstance(r, MemoryRecord) for r in out)
    assert all(r.metadata["kind"] == "episodic" for r in out)


async def test_query_without_filters_returns_empty(mock_pool: AsyncMock) -> None:
    ep = EpisodicReplay(pool=mock_pool)
    out = await ep.query("anything", k=5, filters=None)
    assert out == []


async def test_store_raises_notimplemented(mock_pool: AsyncMock) -> None:
    ep = EpisodicReplay(pool=mock_pool)
    rec = MemoryRecord(
        source_uri="mem://x",
        content="hello",
        score=0.5,
        ts=datetime(2026, 5, 18, tzinfo=UTC),
    )
    with pytest.raises(NotImplementedError, match="read-only"):
        await ep.store(rec)


async def test_episodic_rejects_none_pool() -> None:
    with pytest.raises(ValueError, match="pool must not be None"):
        EpisodicReplay(pool=None)
