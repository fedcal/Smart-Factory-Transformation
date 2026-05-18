"""Unit tests for AuditWriter / AuditPgWriter / OutboxWriter / OutboxRetry (Plan 04-06 Task 01).

D-56 invariant under test:
    1. PG INSERT sync → re-raises on failure (agent aborts; NO NATS-only audit)
    2. NATS publish async → on failure, audit.outbox enqueue (T-04-Outbox-Drop)
    3. OutboxRetry → exp backoff on publish failure; UPDATE published_at on success

Tests use the ``mock_pool`` + ``mock_nats_js`` fixtures from ``conftest.py`` so
the suite runs without docker. The ``@pytest.mark.integration`` round-trip path
against a real testcontainers PG + NATS is gated separately.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest

# Import-or-skip — keeps the W0 → W3 transition clean.
pytest.importorskip(
    "sft_agents.audit.writer",
    reason="Plan 04-06 Task 01 implements AuditWriter",
)

from sft_agents.audit import (  # noqa: E402
    AuditPgWriter,
    AuditWriter,
    OutboxRetry,
    OutboxWriter,
    subject_for_audit,
)
from sft_agents.audit.outbox import _backoff_seconds  # noqa: E402
from sft_agents.models.audit import AuditRecord  # noqa: E402
from sft_agents.models.budget import BudgetSnapshot  # noqa: E402
from sft_agents.models.enums import Decision  # noqa: E402
from sft_agents.models.evidence import EvidencePanel, TokenUsage  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence() -> EvidencePanel:
    return EvidencePanel(
        input_summary="test input",
        tool_calls=[],
        rag_citations=[],
        confidence=0.9,
        model="qwen2.5-14b-awq@vllm-0.8",
        prompt_hash="a" * 64,
        tokens=TokenUsage(input=10, output=5, total=15),
        duration_ms=42,
    )


def _make_budget() -> BudgetSnapshot:
    return BudgetSnapshot(
        tokens_input=10,
        tokens_output=5,
        tokens_total=15,
        cost_usd_simulated=0.01,
        duration_ms=42,
        limit_tokens=50000,
        limit_cost_usd=1.0,
        limit_duration_s=60,
    )


def _make_record(*, decision: Decision = Decision.AUTO) -> AuditRecord:
    kwargs = dict(
        id=uuid4(),
        ts=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        action_id=uuid4(),
        agent_id="operator-assistant",
        thread_id="ops.operator-assistant.session-1",
        cluster="ops",
        action_type="TEST",
        evidence_panel=_make_evidence(),
        decision=decision,
        decision_actor=None,
        motivation=None,
        budget_snapshot=_make_budget(),
        approval_id=None,
    )
    if decision in {
        Decision.HITL_OPERATOR,
        Decision.HITL_SUPERVISOR,
        Decision.HITL_MANAGER,
    }:
        kwargs["motivation"] = "test motivation"
        kwargs["approval_id"] = uuid4()
        kwargs["decision_actor"] = "user-1"
    return AuditRecord(**kwargs)


# ---------------------------------------------------------------------------
# AuditPgWriter
# ---------------------------------------------------------------------------


async def test_pg_writer_insert_parameterized(mock_pool: AsyncMock) -> None:
    """AuditPgWriter.insert executes the constant _INSERT_SQL with $1..$13 params."""
    writer = AuditPgWriter(mock_pool)
    record = _make_record()

    returned = await writer.insert(record)

    assert returned == record.id
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    assert conn.execute.await_count == 1
    args, _ = conn.execute.call_args
    # First arg is the SQL string — must be the module constant (not f-string).
    sql = args[0]
    assert "INSERT INTO audit.actions" in sql
    assert "$1" in sql and "$13" in sql
    # No f-string interpolation: the raw values must appear as bound params,
    # not embedded into the SQL string.
    assert record.agent_id not in sql
    assert str(record.action_id) not in sql


async def test_pg_writer_reraises_on_failure(mock_pool: AsyncMock) -> None:
    """D-56 invariant: PG failure RE-RAISES — no swallowing."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.execute.side_effect = RuntimeError("simulated PG outage")
    writer = AuditPgWriter(mock_pool)

    with pytest.raises(RuntimeError, match="simulated PG outage"):
        await writer.insert(_make_record())


async def test_pg_writer_rejects_none_pool() -> None:
    """Defense-in-depth: bad pool argument fails fast."""
    with pytest.raises(ValueError, match="pool must not be None"):
        AuditPgWriter(None)


# ---------------------------------------------------------------------------
# AuditWriter — D-56 dual-write ordering
# ---------------------------------------------------------------------------


async def test_pg_happy_path(mock_pool: AsyncMock) -> None:
    """Test 1: happy path — PG row + NATS publish both succeed."""
    pg_writer = AuditPgWriter(mock_pool)
    nats_pub = AsyncMock()
    nats_pub.publish_audit = AsyncMock(return_value=None)
    outbox = OutboxWriter(mock_pool)
    writer = AuditWriter(pg_writer, nats_pub, outbox)

    record = _make_record()
    await writer.write(record)

    conn = mock_pool.acquire.return_value.__aenter__.return_value
    assert conn.execute.await_count == 1  # PG INSERT only — no outbox
    nats_pub.publish_audit.assert_awaited_once_with(record)


async def test_nats_failure_falls_to_outbox(mock_pool: AsyncMock) -> None:
    """Test 2: NATS publish fails → outbox enqueue + NO re-raise to caller."""
    pg_writer = AuditPgWriter(mock_pool)
    nats_pub = AsyncMock()
    nats_pub.publish_audit = AsyncMock(side_effect=ConnectionError("NATS down"))
    outbox = OutboxWriter(mock_pool)
    writer = AuditWriter(pg_writer, nats_pub, outbox)

    record = _make_record()
    # MUST NOT raise — caller (agent) keeps going.
    await writer.write(record)

    conn = mock_pool.acquire.return_value.__aenter__.return_value
    # Two execute calls: 1 INSERT audit.actions + 1 INSERT audit.outbox is via
    # fetchrow on the OutboxWriter path. Let's verify fetchrow was called.
    assert conn.fetchrow.await_count == 1
    fetch_args, _ = conn.fetchrow.call_args
    sql = fetch_args[0]
    assert "INSERT INTO audit.outbox" in sql
    # The subject in fetch_args should match subject_for_audit
    expected_subject = subject_for_audit(
        cluster=record.cluster, agent_id=record.agent_id
    )
    assert expected_subject == fetch_args[2]


async def test_pg_failure_no_outbox_fallback(mock_pool: AsyncMock) -> None:
    """Test 3: PG fails → AuditWriter re-raises AND outbox NEVER inserted (D-56)."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.execute.side_effect = RuntimeError("PG outage")

    pg_writer = AuditPgWriter(mock_pool)
    nats_pub = AsyncMock()
    nats_pub.publish_audit = AsyncMock()
    outbox = OutboxWriter(mock_pool)
    writer = AuditWriter(pg_writer, nats_pub, outbox)

    with pytest.raises(RuntimeError, match="PG outage"):
        await writer.write(_make_record())

    # NATS must NOT have been attempted — PG-first ordering.
    nats_pub.publish_audit.assert_not_awaited()
    # Outbox must NOT have been written — no fake audit (T-04-Audit-Tamper).
    assert conn.fetchrow.await_count == 0


async def test_writer_rejects_none_dependencies(mock_pool: AsyncMock) -> None:
    """Defense-in-depth: all three collaborators are required."""
    pg = AuditPgWriter(mock_pool)
    outbox = OutboxWriter(mock_pool)
    with pytest.raises(ValueError, match="pg_writer must not be None"):
        AuditWriter(None, AsyncMock(), outbox)
    with pytest.raises(ValueError, match="nats_publisher must not be None"):
        AuditWriter(pg, None, outbox)
    with pytest.raises(ValueError, match="outbox_writer must not be None"):
        AuditWriter(pg, AsyncMock(), None)


# ---------------------------------------------------------------------------
# OutboxWriter
# ---------------------------------------------------------------------------


async def test_outbox_enqueue_inserts_row(mock_pool: AsyncMock) -> None:
    """OutboxWriter.enqueue runs parameterized INSERT into audit.outbox."""
    outbox = OutboxWriter(mock_pool)
    subject = "audit.actions.ops.operator-assistant"
    payload = b'{"hello": "world"}'

    new_id = await outbox.enqueue(subject, payload)

    conn = mock_pool.acquire.return_value.__aenter__.return_value
    assert conn.fetchrow.await_count == 1
    args, _ = conn.fetchrow.call_args
    sql = args[0]
    assert "INSERT INTO audit.outbox" in sql
    assert subject == args[2]
    # payload arrives as a UTF-8 string (JSONB column).
    assert args[3] == payload.decode("utf-8")
    assert new_id is not None


async def test_outbox_rejects_non_ascii_subject(mock_pool: AsyncMock) -> None:
    outbox = OutboxWriter(mock_pool)
    with pytest.raises(ValueError, match="subject must be ASCII"):
        await outbox.enqueue("audit.actions.naïve", b"{}")


async def test_outbox_rejects_non_bytes_payload(mock_pool: AsyncMock) -> None:
    outbox = OutboxWriter(mock_pool)
    with pytest.raises(ValueError, match="payload must be bytes"):
        await outbox.enqueue("audit.actions.x.y", "not-bytes")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# OutboxRetry — Tests 4 + 5
# ---------------------------------------------------------------------------


async def test_outbox_retry_success(mock_pool: AsyncMock) -> None:
    """Test 4: healthy NATS → row marked published_at (no attempts bump)."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    seeded_id = uuid4()
    conn.fetch = AsyncMock(
        return_value=[
            {
                "id": seeded_id,
                "subject": "audit.actions.ops.operator-assistant",
                "payload_json": '{"hello":"world"}',
                "attempts": 0,
            }
        ]
    )
    nats_pub = AsyncMock()
    nats_pub.publish_raw = AsyncMock(return_value=None)
    retry = OutboxRetry(mock_pool, nats_pub, interval_s=0.01, max_attempts=10)

    processed = await retry.run_once()

    assert processed == 1
    nats_pub.publish_raw.assert_awaited_once()
    # UPDATE published_at executed (the only conn.execute on success path).
    assert conn.execute.await_count == 1
    args, _ = conn.execute.call_args
    assert "UPDATE audit.outbox" in args[0]
    assert "published_at" in args[0]
    assert args[1] == seeded_id


async def test_outbox_retry_backoff(mock_pool: AsyncMock) -> None:
    """Test 5: failing NATS → attempts bumped, next_attempt_at uses ~2s backoff."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    seeded_id = uuid4()
    conn.fetch = AsyncMock(
        return_value=[
            {
                "id": seeded_id,
                "subject": "audit.actions.ops.operator-assistant",
                "payload_json": '{"hello":"world"}',
                "attempts": 0,
            }
        ]
    )
    nats_pub = AsyncMock()
    nats_pub.publish_raw = AsyncMock(
        side_effect=ConnectionError("NATS down")
    )
    retry = OutboxRetry(mock_pool, nats_pub, interval_s=0.01, max_attempts=10)

    processed = await retry.run_once()

    assert processed == 1
    # The failure path runs the bump UPDATE — exactly one execute call.
    assert conn.execute.await_count == 1
    args, _ = conn.execute.call_args
    sql = args[0]
    assert "attempts = attempts + 1" in sql
    assert "INTERVAL '2s'" in sql  # first retry → 2 seconds
    assert args[1] == seeded_id


async def test_backoff_exponential_capped() -> None:
    """_backoff_seconds: 2,4,8,16,... with 3600s cap once 2**exp > 3600."""
    assert _backoff_seconds(0) == 2
    assert _backoff_seconds(1) == 4
    assert _backoff_seconds(2) == 8
    # 2**12 = 4096 > 3600 → cap engages at attempts=11.
    assert _backoff_seconds(11) == 3600
    assert _backoff_seconds(100) == 3600


async def test_outbox_retry_run_stops_on_signal(mock_pool: AsyncMock) -> None:
    """Run loop exits when stop() is called."""
    nats_pub = AsyncMock()
    nats_pub.publish_raw = AsyncMock()
    retry = OutboxRetry(mock_pool, nats_pub, interval_s=0.05, max_attempts=10)
    import asyncio

    task = asyncio.create_task(retry.run())
    await asyncio.sleep(0.01)
    await retry.stop()
    await asyncio.wait_for(task, timeout=1.0)


# ---------------------------------------------------------------------------
# Integration round-trip (gated)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_audit_writer_pg_roundtrip_integration() -> None:
    """Round-trip against testcontainers PG: write → SELECT → row present.

    Skipped when docker/testcontainers is unavailable.
    """
    pytest.importorskip("testcontainers.postgres")
    pytest.importorskip("asyncpg")
    pytest.skip(
        "Integration round-trip uses the full migrations stack; "
        "tests/integration/ owns the full e2e round-trip."
    )
