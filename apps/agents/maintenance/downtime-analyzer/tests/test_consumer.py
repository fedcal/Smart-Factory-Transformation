"""Tests for the DowntimeAnalyzer NATS da-consumer (plan 07-09).

TDD RED phase — all tests fail on ImportError until Task 2 implements consumer.py.

Pattern: AsyncMock NATS — mirrors 07-06 PM consumer test pattern.
Consumer behavior: PG-first dual-write convention (insert_event BEFORE audit).
Subject/payload consistency: payload asset_id is source of truth, subject is routing.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_downtime_payload(
    *,
    asset_id: str = "LOOM-01",
    reason_code: str = "WEAVING-BE-001",
    duration_min: int = 30,
    severity: str = "minor",
    event_id: str | None = None,
) -> bytes:
    """Return JSON-encoded DowntimeEvent payload bytes."""
    data = {
        "event_id": event_id or str(uuid4()),
        "asset_id": asset_id,
        "reason_code": reason_code,
        "duration_min": duration_min,
        "severity": severity,
        "work_order_id": None,
        "dye_lot_id": None,
        "source": "simulator",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return json.dumps(data).encode("utf-8")


def _make_nats_msg(
    *,
    subject: str = "maintenance.downtime.LOOM-01",
    asset_id: str = "LOOM-01",
    event_id: str | None = None,
) -> MagicMock:
    """Return a mock NATS message."""
    msg = MagicMock()
    msg.subject = subject
    msg.data = _make_downtime_payload(asset_id=asset_id, event_id=event_id)
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.term = AsyncMock()
    return msg


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


def test_da_subject_pattern_constant() -> None:
    """DA_SUBJECT_PATTERN must be exactly 'maintenance.downtime.>'."""
    from mnt_downtime_analyzer.consumer import DA_SUBJECT_PATTERN

    assert DA_SUBJECT_PATTERN == "maintenance.downtime.>"


def test_da_consumer_name_constant() -> None:
    """DA_CONSUMER_NAME must be exactly 'da-consumer'."""
    from mnt_downtime_analyzer.consumer import DA_CONSUMER_NAME

    assert DA_CONSUMER_NAME == "da-consumer"


# ---------------------------------------------------------------------------
# Consumer happy-path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_ack_after_insert_and_audit() -> None:
    """Happy path: valid DowntimeEvent -> insert_event called -> audit written -> msg.ack()."""
    from mnt_downtime_analyzer.consumer import run_da_consumer

    repo = AsyncMock()
    audit_writer = AsyncMock()
    stop_event = asyncio.Event()

    msg = _make_nats_msg()

    # js.pull_subscribe returns a mock psub that yields exactly 1 message then times out
    import nats.errors  # type: ignore[import-not-found]

    psub = AsyncMock()
    psub.fetch = AsyncMock(side_effect=[[msg], nats.errors.TimeoutError()])
    js = AsyncMock()
    js.pull_subscribe = AsyncMock(return_value=psub)

    # After second fetch (TimeoutError), set stop_event to end the loop
    original_fetch = psub.fetch.side_effect

    fetch_count = 0

    async def fetch_side_effect(*args, **kwargs):
        nonlocal fetch_count
        fetch_count += 1
        if fetch_count == 1:
            return [msg]
        stop_event.set()
        raise nats.errors.TimeoutError()

    psub.fetch = AsyncMock(side_effect=fetch_side_effect)

    await run_da_consumer(
        nats_client=js,
        repository=repo,
        audit_writer=audit_writer,
        stop_event=stop_event,
    )

    repo.insert_event.assert_called_once()
    audit_writer.write.assert_called_once()
    msg.ack.assert_called_once()
    msg.nak.assert_not_called()


@pytest.mark.asyncio
async def test_pg_first_dual_write_ordering() -> None:
    """insert_event is called BEFORE audit_writer.write (PG-first convention)."""
    from mnt_downtime_analyzer.consumer import run_da_consumer

    call_order = []
    repo = AsyncMock()
    audit_writer = AsyncMock()

    async def mock_insert(event):
        call_order.append("insert_event")

    async def mock_write(record):
        call_order.append("audit_write")

    repo.insert_event = AsyncMock(side_effect=mock_insert)
    audit_writer.write = AsyncMock(side_effect=mock_write)

    stop_event = asyncio.Event()
    msg = _make_nats_msg()

    import nats.errors  # type: ignore[import-not-found]

    fetch_count = 0

    psub = AsyncMock()

    async def fetch_side_effect(*args, **kwargs):
        nonlocal fetch_count
        fetch_count += 1
        if fetch_count == 1:
            return [msg]
        stop_event.set()
        raise nats.errors.TimeoutError()

    psub.fetch = AsyncMock(side_effect=fetch_side_effect)
    js = AsyncMock()
    js.pull_subscribe = AsyncMock(return_value=psub)

    await run_da_consumer(
        nats_client=js,
        repository=repo,
        audit_writer=audit_writer,
        stop_event=stop_event,
    )

    assert call_order == ["insert_event", "audit_write"], (
        f"Expected PG-first (insert_event then audit_write), got: {call_order}"
    )


@pytest.mark.asyncio
async def test_malformed_json_acks_without_insert() -> None:
    """Malformed JSON payload: log + ack (poison-pill drop); insert NOT called."""
    from mnt_downtime_analyzer.consumer import run_da_consumer

    repo = AsyncMock()
    audit_writer = AsyncMock()
    stop_event = asyncio.Event()

    msg = MagicMock()
    msg.subject = "maintenance.downtime.LOOM-01"
    msg.data = b"not-valid-json{"
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    import nats.errors  # type: ignore[import-not-found]

    fetch_count = 0
    psub = AsyncMock()

    async def fetch_side_effect(*args, **kwargs):
        nonlocal fetch_count
        fetch_count += 1
        if fetch_count == 1:
            return [msg]
        stop_event.set()
        raise nats.errors.TimeoutError()

    psub.fetch = AsyncMock(side_effect=fetch_side_effect)
    js = AsyncMock()
    js.pull_subscribe = AsyncMock(return_value=psub)

    await run_da_consumer(
        nats_client=js,
        repository=repo,
        audit_writer=audit_writer,
        stop_event=stop_event,
    )

    repo.insert_event.assert_not_called()
    msg.ack.assert_called_once()  # poison-pill drop, ack to move on


@pytest.mark.asyncio
async def test_schema_invalid_acks_without_insert() -> None:
    """Schema-invalid DowntimeEvent (severity='unknown'): log + ack; insert NOT called."""
    from mnt_downtime_analyzer.consumer import run_da_consumer

    repo = AsyncMock()
    audit_writer = AsyncMock()
    stop_event = asyncio.Event()

    invalid_payload = json.dumps({
        "event_id": str(uuid4()),
        "asset_id": "LOOM-01",
        "reason_code": "WEAVING-BE-001",
        "duration_min": 30,
        "severity": "unknown",  # invalid
        "work_order_id": None,
        "dye_lot_id": None,
        "source": "simulator",
        "timestamp": datetime.now(UTC).isoformat(),
    }).encode("utf-8")

    msg = MagicMock()
    msg.subject = "maintenance.downtime.LOOM-01"
    msg.data = invalid_payload
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    import nats.errors  # type: ignore[import-not-found]

    fetch_count = 0
    psub = AsyncMock()

    async def fetch_side_effect(*args, **kwargs):
        nonlocal fetch_count
        fetch_count += 1
        if fetch_count == 1:
            return [msg]
        stop_event.set()
        raise nats.errors.TimeoutError()

    psub.fetch = AsyncMock(side_effect=fetch_side_effect)
    js = AsyncMock()
    js.pull_subscribe = AsyncMock(return_value=psub)

    await run_da_consumer(
        nats_client=js,
        repository=repo,
        audit_writer=audit_writer,
        stop_event=stop_event,
    )

    repo.insert_event.assert_not_called()
    msg.ack.assert_called_once()


@pytest.mark.asyncio
async def test_repository_raises_triggers_nak() -> None:
    """Repository raises (e.g. PG connection lost) -> msg.nak(delay=5); retry expected."""
    from mnt_downtime_analyzer.consumer import run_da_consumer

    repo = AsyncMock()
    repo.insert_event = AsyncMock(side_effect=Exception("PG connection lost"))
    audit_writer = AsyncMock()
    stop_event = asyncio.Event()

    msg = _make_nats_msg()

    import nats.errors  # type: ignore[import-not-found]

    fetch_count = 0
    psub = AsyncMock()

    async def fetch_side_effect(*args, **kwargs):
        nonlocal fetch_count
        fetch_count += 1
        if fetch_count == 1:
            return [msg]
        stop_event.set()
        raise nats.errors.TimeoutError()

    psub.fetch = AsyncMock(side_effect=fetch_side_effect)
    js = AsyncMock()
    js.pull_subscribe = AsyncMock(return_value=psub)

    await run_da_consumer(
        nats_client=js,
        repository=repo,
        audit_writer=audit_writer,
        stop_event=stop_event,
    )

    msg.nak.assert_called_once()
    msg.ack.assert_not_called()


@pytest.mark.asyncio
async def test_stop_event_exits_loop_cleanly() -> None:
    """stop_event.set() exits the consumer loop cleanly."""
    from mnt_downtime_analyzer.consumer import run_da_consumer

    repo = AsyncMock()
    audit_writer = AsyncMock()
    stop_event = asyncio.Event()

    import nats.errors  # type: ignore[import-not-found]

    fetch_count = 0
    psub = AsyncMock()

    async def fetch_side_effect(*args, **kwargs):
        nonlocal fetch_count
        fetch_count += 1
        stop_event.set()  # signal stop on first fetch
        raise nats.errors.TimeoutError()

    psub.fetch = AsyncMock(side_effect=fetch_side_effect)
    js = AsyncMock()
    js.pull_subscribe = AsyncMock(return_value=psub)

    await run_da_consumer(
        nats_client=js,
        repository=repo,
        audit_writer=audit_writer,
        stop_event=stop_event,
    )
    # No exception — loop exited cleanly


@pytest.mark.asyncio
async def test_cancelled_error_propagates() -> None:
    """asyncio.CancelledError propagates cleanly out of run_da_consumer."""
    from mnt_downtime_analyzer.consumer import run_da_consumer

    repo = AsyncMock()
    audit_writer = AsyncMock()
    stop_event = asyncio.Event()

    psub = AsyncMock()
    psub.fetch = AsyncMock(side_effect=asyncio.CancelledError())
    js = AsyncMock()
    js.pull_subscribe = AsyncMock(return_value=psub)

    with pytest.raises(asyncio.CancelledError):
        await run_da_consumer(
            nats_client=js,
            repository=repo,
            audit_writer=audit_writer,
            stop_event=stop_event,
        )


@pytest.mark.asyncio
async def test_subject_payload_mismatch_still_inserts_payload_asset_id() -> None:
    """Subject asset_id LOOM-01 but payload asset_id LOOM-02 -> insert with payload value.

    The payload is the source of truth; the subject is routing only.
    Consumer must log mismatch but proceed with payload asset_id.
    """
    from mnt_downtime_analyzer.consumer import run_da_consumer

    repo = AsyncMock()
    audit_writer = AsyncMock()
    stop_event = asyncio.Event()

    # Subject says LOOM-01, payload says LOOM-02
    msg = MagicMock()
    msg.subject = "maintenance.downtime.LOOM-01"
    msg.data = _make_downtime_payload(asset_id="LOOM-02")
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()

    import nats.errors  # type: ignore[import-not-found]

    fetch_count = 0
    psub = AsyncMock()

    async def fetch_side_effect(*args, **kwargs):
        nonlocal fetch_count
        fetch_count += 1
        if fetch_count == 1:
            return [msg]
        stop_event.set()
        raise nats.errors.TimeoutError()

    psub.fetch = AsyncMock(side_effect=fetch_side_effect)
    js = AsyncMock()
    js.pull_subscribe = AsyncMock(return_value=psub)

    await run_da_consumer(
        nats_client=js,
        repository=repo,
        audit_writer=audit_writer,
        stop_event=stop_event,
    )

    # insert_event must have been called with the payload's asset_id (LOOM-02)
    repo.insert_event.assert_called_once()
    inserted_event = repo.insert_event.call_args[0][0]
    assert inserted_event.asset_id == "LOOM-02"
    msg.ack.assert_called_once()


@pytest.mark.asyncio
async def test_pull_subscribe_uses_correct_subject_and_durable() -> None:
    """Consumer subscribes with subject='maintenance.downtime.>' and durable='da-consumer'."""
    from mnt_downtime_analyzer.consumer import DA_CONSUMER_NAME, DA_SUBJECT_PATTERN, run_da_consumer

    repo = AsyncMock()
    audit_writer = AsyncMock()
    stop_event = asyncio.Event()

    import nats.errors  # type: ignore[import-not-found]

    psub = AsyncMock()
    psub.fetch = AsyncMock(side_effect=[nats.errors.TimeoutError()])
    js = AsyncMock()
    js.pull_subscribe = AsyncMock(return_value=psub)

    stop_event.set()  # exit immediately

    await run_da_consumer(
        nats_client=js,
        repository=repo,
        audit_writer=audit_writer,
        stop_event=stop_event,
    )

    js.pull_subscribe.assert_called_once()
    call_kwargs = js.pull_subscribe.call_args
    # subject and durable must match constants
    subject_used = (
        call_kwargs.kwargs.get("subject")
        or (call_kwargs.args[0] if call_kwargs.args else None)
    )
    durable_used = call_kwargs.kwargs.get("durable")
    assert subject_used == DA_SUBJECT_PATTERN
    assert durable_used == DA_CONSUMER_NAME
