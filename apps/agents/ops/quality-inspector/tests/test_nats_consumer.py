"""Tests for the NATS JetStream qi-consumer (D-QI-01).

Uses AsyncMock to stub out the JetStream client and asyncpg pool so the
suite runs without docker. Coverage:

    1. Happy path: valid event -> handler called once, ack().
    2. Idempotency: replay -> handler skipped, ack() (no double-process).
    3. ValidationError (missing dye_lot_id) -> msg.term() (no redelivery).
    4. Transient error (asyncpg failure raised inside handler) -> msg.nak().
    5. Bootstrap config: QUALITY_STREAM appears in nats-bootstrap-streams.py
       with subjects=['quality.events.>'] and a 7-day max_age.

The consumer is built as a fetch-loop that exits when the shutdown event
is set; in tests we configure the mock JetStream to deliver exactly the
queued messages in one fetch, then raise TimeoutError, then set shutdown.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sft_domain.ops.quality import QualityEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_event_payload(
    *,
    event_id: UUID | None = None,
    dye_lot_id: str = "DL-LOOM-01-20260523-a3",
    defect_type: str = "slub",
) -> bytes:
    event = QualityEvent(
        event_id=event_id or uuid4(),
        asset_id="LOOM-01",
        dye_lot_id=dye_lot_id,
        defect_type=defect_type,  # type: ignore[arg-type]
        defect_length_inches=1.5,
        full_width=False,
        position_meters=12.5,
        timestamp=datetime.now(timezone.utc),
        source="simulator",
    )
    return event.model_dump_json().encode("utf-8")


def _invalid_event_payload_missing_dye_lot() -> bytes:
    """Build a payload missing dye_lot_id field (operator forgot)."""
    raw = {
        "event_id": str(uuid4()),
        "asset_id": "LOOM-01",
        # dye_lot_id missing
        "defect_type": "slub",
        "defect_length_inches": 1.5,
        "full_width": False,
        "position_meters": 12.5,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "operator",
    }
    return json.dumps(raw).encode("utf-8")


def _make_msg(payload: bytes) -> Any:
    """Build a Mock NATS msg with ack/nak/term coroutines."""
    msg = MagicMock()
    msg.data = payload
    msg.ack = AsyncMock(return_value=None)
    msg.nak = AsyncMock(return_value=None)
    msg.term = AsyncMock(return_value=None)
    return msg


class _FetchSequence:
    """Programmable fetch() that returns each batch in turn, then signals shutdown."""

    def __init__(self, batches: list[list[Any]], shutdown: asyncio.Event) -> None:
        self._batches = list(batches)
        self._shutdown = shutdown

    async def fetch(self, batch: int = 10, timeout: float = 5) -> list[Any]:
        if not self._batches:
            # Drain complete: tell the consumer to stop and raise TimeoutError so
            # the loop continues -> sees shutdown -> exits cleanly.
            self._shutdown.set()
            import nats.errors  # noqa: PLC0415

            raise nats.errors.TimeoutError()
        return self._batches.pop(0)


def _make_js(batches: list[list[Any]], shutdown: asyncio.Event) -> Any:
    """Build a Mock JetStream client whose pull_subscribe returns a FetchSequence."""
    js = MagicMock()
    psub = _FetchSequence(batches, shutdown)
    # pull_subscribe is async; returns the psub object.
    js.pull_subscribe = AsyncMock(return_value=psub)
    return js


def _make_pool(*, already_processed_returns: int | None = None) -> Any:
    """Build a Mock asyncpg pool whose acquired conn.fetchval returns the value."""
    pool = MagicMock()
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=already_processed_returns)
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return pool


# ---------------------------------------------------------------------------
# Tests — qi-consumer behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consumer_starts_and_subscribes_to_quality_events() -> None:
    """run_qi_consumer subscribes with durable=qi-consumer / stream=QUALITY_STREAM
    and routes one valid event into the handler."""
    from ops_quality_inspector.nats_consumer import run_qi_consumer

    payload = _valid_event_payload()
    msg = _make_msg(payload)
    shutdown = asyncio.Event()
    js = _make_js([[msg]], shutdown)
    handler = AsyncMock(return_value=None)
    pool = _make_pool(already_processed_returns=None)

    await run_qi_consumer(
        js=js, qi_handler=handler, pool=pool, shutdown=shutdown
    )

    js.pull_subscribe.assert_awaited_once()
    sub_kwargs = js.pull_subscribe.await_args.kwargs
    assert sub_kwargs["durable"] == "qi-consumer"
    assert sub_kwargs["stream"] == "QUALITY_STREAM"
    assert sub_kwargs["subject"] == "quality.events.>"
    handler.assert_awaited_once()
    msg.ack.assert_awaited_once()
    msg.term.assert_not_called()
    msg.nak.assert_not_called()


@pytest.mark.asyncio
async def test_consumer_idempotency_skips_replayed_event() -> None:
    """already_processed=True -> handler NOT called, msg ack'd."""
    from ops_quality_inspector.nats_consumer import run_qi_consumer

    payload = _valid_event_payload()
    msg = _make_msg(payload)
    shutdown = asyncio.Event()
    js = _make_js([[msg]], shutdown)
    handler = AsyncMock(return_value=None)
    pool = _make_pool(already_processed_returns=1)

    await run_qi_consumer(
        js=js, qi_handler=handler, pool=pool, shutdown=shutdown
    )

    handler.assert_not_called()
    msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_consumer_terminates_on_validation_error() -> None:
    """Payload missing dye_lot_id -> ValidationError -> msg.term() (poison)."""
    from ops_quality_inspector.nats_consumer import run_qi_consumer

    msg = _make_msg(_invalid_event_payload_missing_dye_lot())
    shutdown = asyncio.Event()
    js = _make_js([[msg]], shutdown)
    handler = AsyncMock(return_value=None)
    pool = _make_pool(already_processed_returns=None)

    await run_qi_consumer(
        js=js, qi_handler=handler, pool=pool, shutdown=shutdown
    )

    handler.assert_not_called()
    msg.term.assert_awaited_once()
    msg.ack.assert_not_called()
    msg.nak.assert_not_called()


@pytest.mark.asyncio
async def test_consumer_naks_on_transient_handler_error() -> None:
    """Handler raises RuntimeError -> msg.nak() so JetStream redelivers."""
    from ops_quality_inspector.nats_consumer import run_qi_consumer

    msg = _make_msg(_valid_event_payload())
    shutdown = asyncio.Event()
    js = _make_js([[msg]], shutdown)
    handler = AsyncMock(side_effect=RuntimeError("transient db error"))
    pool = _make_pool(already_processed_returns=None)

    await run_qi_consumer(
        js=js, qi_handler=handler, pool=pool, shutdown=shutdown
    )

    handler.assert_awaited_once()
    msg.nak.assert_awaited_once()
    msg.ack.assert_not_called()
    msg.term.assert_not_called()


# ---------------------------------------------------------------------------
# Tests — already_processed helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_already_processed_returns_true_when_row_exists() -> None:
    from ops_quality_inspector.nats_consumer import already_processed

    pool = _make_pool(already_processed_returns=1)
    result = await already_processed(pool, uuid4())
    assert result is True


@pytest.mark.asyncio
async def test_already_processed_returns_false_when_no_row() -> None:
    from ops_quality_inspector.nats_consumer import already_processed

    pool = _make_pool(already_processed_returns=None)
    result = await already_processed(pool, uuid4())
    assert result is False


# ---------------------------------------------------------------------------
# Tests — bootstrap config extension
# ---------------------------------------------------------------------------


def test_bootstrap_script_declares_quality_stream() -> None:
    """nats-bootstrap-streams.py extended to create QUALITY_STREAM."""
    # tests/test_nats_consumer.py -> tests/ -> quality-inspector/ ->
    # ops/ -> agents/ -> apps/ -> repo_root
    repo_root = pathlib.Path(__file__).resolve().parents[5]
    script = repo_root / "scripts" / "nats-bootstrap-streams.py"
    assert script.exists(), f"missing: {script}"
    content = script.read_text(encoding="utf-8")
    assert "QUALITY_STREAM" in content, "QUALITY_STREAM not in bootstrap script"
    assert '"quality.events.>"' in content or "'quality.events.>'" in content, (
        "quality.events.> subject not declared in bootstrap script"
    )
    # 7-day retention (Pitfall §4 - generous catch-up window).
    assert "7 * 24 * 3600" in content, "expected 7-day max_age (Pitfall §4)"
