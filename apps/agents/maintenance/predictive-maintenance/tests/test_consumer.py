"""Tests for NATS JetStream durable pm-consumer (Plan 07-06 Task 4 TDD).

Tests the run_pm_consumer contract:
- Happy path: valid PredictRequest → agent invoked → msg.ack()
- Malformed JSON → log + msg.ack() (poison-pill); agent NOT invoked
- Schema-invalid payload (bad severity) → log + msg.ack(); agent NOT invoked
- Agent raises exception → msg.nak(delay=5); agent CAN be re-invoked
- stop_event.set() causes loop to exit cleanly
- asyncio.CancelledError propagates cleanly
- Stream bootstrap idempotent (add_stream twice does not crash consumer)
- Subject extraction: subject maintenance.predict.LOOM-01 → asset_id=LOOM-01
- PM_SUBJECT_PATTERN matches maintenance.predict.LOOM-01, not maintenance.downtime.LOOM-01
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from mnt_predictive_maintenance.consumer import (
    PM_CONSUMER_NAME,
    PM_SUBJECT_PATTERN,
    run_pm_consumer,
)


# ---------------------------------------------------------------------------
# Helpers + fake infrastructure
# ---------------------------------------------------------------------------


@dataclass
class _FakeMsg:
    """Simulates nats.aio.msg.Msg interface used by the consumer."""

    data: bytes
    subject: str = "maintenance.predict.LOOM-01"
    ack: AsyncMock = field(default_factory=AsyncMock)
    nak: AsyncMock = field(default_factory=lambda: AsyncMock())


def _make_valid_payload(asset_id: str = "LOOM-01", severity: str = "major") -> bytes:
    return json.dumps({
        "asset_id": asset_id,
        "severity": severity,
        "emitted_at": datetime.now(UTC).isoformat(),
        "triggered_by_action_id": "ad-action-uuid-1",
    }).encode()


class _FakePsub:
    """Fake pull-subscribe that returns pre-defined batches then raises TimeoutError."""

    def __init__(self, batches: list[list[_FakeMsg]], stop_after: int = -1) -> None:
        self._batches = list(batches)
        self._fetch_count = 0

    async def fetch(self, batch: int = 10, timeout: float = 2.0) -> list[_FakeMsg]:
        # Yield to event loop so cancellation can be delivered
        await asyncio.sleep(0)
        if self._batches:
            msgs = self._batches.pop(0)
            self._fetch_count += 1
            return msgs
        # Simulate fetch timeout with a small real sleep so cancellation can interrupt
        await asyncio.sleep(0.01)
        raise asyncio.TimeoutError()


def _make_js(psub: _FakePsub, *, stream_error: Exception | None = None) -> MagicMock:
    """Build a fake JetStream context."""
    js = MagicMock()
    js.add_stream = AsyncMock(side_effect=stream_error)
    js.pull_subscribe = AsyncMock(return_value=psub)
    return js


def _make_nc(js: MagicMock) -> MagicMock:
    """Build a fake NATS client."""
    nc = MagicMock()
    nc.jetstream = MagicMock(return_value=js)
    return nc


def _make_agent(return_value: dict | None = None) -> AsyncMock:
    """Build a fake PredictiveMaintenance agent."""
    agent = AsyncMock()
    agent.__call__ = AsyncMock(return_value=return_value or {"rul_estimate": MagicMock()})
    # Make agent callable directly
    agent.side_effect = None
    agent.return_value = return_value or {"rul_estimate": MagicMock()}
    return agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_happy_path_valid_message_ack() -> None:
    """1 valid PredictRequest → agent invoked once → msg.ack() called."""
    msg = _FakeMsg(data=_make_valid_payload("LOOM-01", "major"))
    psub = _FakePsub(batches=[[msg]])
    stop_event = asyncio.Event()
    agent = _make_agent()

    # After first batch consumed, let fetch raise TimeoutError then check stop_event
    # We set stop_event after agent is called
    original_call = agent.__call__

    async def _side_effect(state: dict) -> dict:
        stop_event.set()
        return {"rul_estimate": MagicMock()}

    agent.side_effect = _side_effect

    js = _make_js(psub)
    nc = _make_nc(js)

    await asyncio.wait_for(
        run_pm_consumer(nats_client=nc, agent=agent, stop_event=stop_event),
        timeout=3.0,
    )

    # Agent was called with correct state
    agent.assert_called_once()
    call_args = agent.call_args[0][0]
    assert call_args["asset_id"] == "LOOM-01"
    assert call_args["triggered_by_action_id"] == "ad-action-uuid-1"

    # Message was acked
    msg.ack.assert_called_once()
    msg.nak.assert_not_called()


async def test_malformed_json_poison_pill_ack() -> None:
    """Malformed JSON payload → msg.ack() (poison-pill); agent NOT invoked."""
    msg = _FakeMsg(data=b"not valid json", subject="maintenance.predict.LOOM-01")
    psub = _FakePsub(batches=[[msg]])
    stop_event = asyncio.Event()
    agent = _make_agent()

    # Set stop after psub drains
    original_fetch = psub.fetch

    async def _patched_fetch(**kwargs: Any) -> list:
        result = await original_fetch(**kwargs)
        stop_event.set()  # stop after first batch
        return result

    psub.fetch = _patched_fetch  # type: ignore[assignment]

    js = _make_js(psub)
    nc = _make_nc(js)

    await asyncio.wait_for(
        run_pm_consumer(nats_client=nc, agent=agent, stop_event=stop_event),
        timeout=3.0,
    )

    msg.ack.assert_called_once()
    msg.nak.assert_not_called()
    agent.assert_not_called()


async def test_schema_invalid_payload_poison_pill_ack() -> None:
    """Schema-invalid payload (bad severity literal) → ack (poison-pill); agent NOT invoked."""
    bad_payload = json.dumps({
        "asset_id": "LOOM-01",
        "severity": "invalid_severity",
        "emitted_at": datetime.now(UTC).isoformat(),
    }).encode()
    msg = _FakeMsg(data=bad_payload, subject="maintenance.predict.LOOM-01")
    psub = _FakePsub(batches=[[msg]])
    stop_event = asyncio.Event()
    agent = _make_agent()

    original_fetch = psub.fetch

    async def _patched_fetch(**kwargs: Any) -> list:
        result = await original_fetch(**kwargs)
        stop_event.set()
        return result

    psub.fetch = _patched_fetch  # type: ignore[assignment]

    js = _make_js(psub)
    nc = _make_nc(js)

    await asyncio.wait_for(
        run_pm_consumer(nats_client=nc, agent=agent, stop_event=stop_event),
        timeout=3.0,
    )

    msg.ack.assert_called_once()
    msg.nak.assert_not_called()
    agent.assert_not_called()


async def test_agent_exception_causes_nak() -> None:
    """Agent raises RuntimeError → msg.nak(delay=5) called; agent was invoked."""
    msg = _FakeMsg(data=_make_valid_payload("LOOM-01", "critical"))
    psub = _FakePsub(batches=[[msg]])
    stop_event = asyncio.Event()
    agent = _make_agent()

    async def _failing_agent(state: dict) -> dict:
        stop_event.set()
        raise RuntimeError("Simulated agent failure")

    agent.side_effect = _failing_agent

    js = _make_js(psub)
    nc = _make_nc(js)

    await asyncio.wait_for(
        run_pm_consumer(nats_client=nc, agent=agent, stop_event=stop_event),
        timeout=3.0,
    )

    agent.assert_called_once()
    msg.ack.assert_not_called()
    msg.nak.assert_called_once_with(delay=5)


async def test_stop_event_exits_loop() -> None:
    """stop_event.set() causes loop to exit cleanly within 1 tick."""
    psub = _FakePsub(batches=[])  # No messages
    stop_event = asyncio.Event()
    agent = _make_agent()

    js = _make_js(psub)
    nc = _make_nc(js)

    # Set stop_event immediately — loop should exit on first check
    stop_event.set()

    await asyncio.wait_for(
        run_pm_consumer(nats_client=nc, agent=agent, stop_event=stop_event),
        timeout=3.0,
    )

    agent.assert_not_called()


async def test_cancelled_error_propagates_cleanly() -> None:
    """asyncio.CancelledError propagates cleanly; no exception leak."""
    psub = _FakePsub(batches=[])
    agent = _make_agent()

    js = _make_js(psub)
    nc = _make_nc(js)

    task = asyncio.create_task(run_pm_consumer(nats_client=nc, agent=agent))
    await asyncio.sleep(0.05)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


async def test_stream_bootstrap_idempotent() -> None:
    """Calling add_stream twice (stream already exists) does not crash the consumer."""
    msg = _FakeMsg(data=_make_valid_payload())
    psub = _FakePsub(batches=[[msg]])
    stop_event = asyncio.Event()
    agent = _make_agent()

    async def _side_effect(state: dict) -> dict:
        stop_event.set()
        return {"rul_estimate": MagicMock()}

    agent.side_effect = _side_effect

    # Simulate stream-already-exists error
    stream_exists_error = Exception("stream name already in use")
    js = _make_js(psub, stream_error=stream_exists_error)
    nc = _make_nc(js)

    # Should NOT raise — idempotent bootstrap
    await asyncio.wait_for(
        run_pm_consumer(nats_client=nc, agent=agent, stop_event=stop_event),
        timeout=3.0,
    )

    # Consumer still processed the message
    agent.assert_called_once()
    msg.ack.assert_called_once()


async def test_subject_extraction_asset_id_consistency() -> None:
    """Subject maintenance.predict.LOOM-01 → payload asset_id must equal LOOM-01."""
    # subject=LOOM-01 but payload has asset_id=LOOM-02 → mismatch → ack (poison)
    mismatch_payload = json.dumps({
        "asset_id": "LOOM-02",  # mismatch with subject
        "severity": "major",
        "emitted_at": datetime.now(UTC).isoformat(),
    }).encode()
    msg = _FakeMsg(data=mismatch_payload, subject="maintenance.predict.LOOM-01")
    psub = _FakePsub(batches=[[msg]])
    stop_event = asyncio.Event()
    agent = _make_agent()

    original_fetch = psub.fetch

    async def _patched_fetch(**kwargs: Any) -> list:
        result = await original_fetch(**kwargs)
        stop_event.set()
        return result

    psub.fetch = _patched_fetch  # type: ignore[assignment]

    js = _make_js(psub)
    nc = _make_nc(js)

    await asyncio.wait_for(
        run_pm_consumer(nats_client=nc, agent=agent, stop_event=stop_event),
        timeout=3.0,
    )

    # Mismatch → ack-drop; agent NOT invoked
    msg.ack.assert_called_once()
    msg.nak.assert_not_called()
    agent.assert_not_called()


async def test_consistent_subject_and_payload_accepted() -> None:
    """Subject LOOM-01 + payload asset_id=LOOM-01 → agent invoked (positive case)."""
    msg = _FakeMsg(
        data=_make_valid_payload("LOOM-01", "critical"),
        subject="maintenance.predict.LOOM-01",
    )
    psub = _FakePsub(batches=[[msg]])
    stop_event = asyncio.Event()
    agent = _make_agent()

    async def _side_effect(state: dict) -> dict:
        stop_event.set()
        return {"rul_estimate": MagicMock()}

    agent.side_effect = _side_effect

    js = _make_js(psub)
    nc = _make_nc(js)

    await asyncio.wait_for(
        run_pm_consumer(nats_client=nc, agent=agent, stop_event=stop_event),
        timeout=3.0,
    )

    agent.assert_called_once()
    msg.ack.assert_called_once()


def test_pm_subject_pattern_constant() -> None:
    """PM_SUBJECT_PATTERN matches maintenance.predict.LOOM-01 but not maintenance.downtime.LOOM-01."""
    import fnmatch  # noqa: PLC0415

    assert fnmatch.fnmatch("maintenance.predict.LOOM-01", PM_SUBJECT_PATTERN)
    assert not fnmatch.fnmatch("maintenance.downtime.LOOM-01", PM_SUBJECT_PATTERN)
    assert PM_CONSUMER_NAME == "pm-consumer"


async def test_consumer_pull_subscription_constants() -> None:
    """Consumer creates pull subscription with correct subject + durable name."""
    msg = _FakeMsg(data=_make_valid_payload())
    psub = _FakePsub(batches=[[msg]])
    stop_event = asyncio.Event()
    agent = _make_agent()

    async def _side_effect(state: dict) -> dict:
        stop_event.set()
        return {"rul_estimate": MagicMock()}

    agent.side_effect = _side_effect

    js = _make_js(psub)
    nc = _make_nc(js)

    await asyncio.wait_for(
        run_pm_consumer(nats_client=nc, agent=agent, stop_event=stop_event),
        timeout=3.0,
    )

    # Verify pull_subscribe called with correct subject + durable
    js.pull_subscribe.assert_called_once()
    call_kwargs = js.pull_subscribe.call_args
    subject = call_kwargs.kwargs.get("subject") or (call_kwargs.args[0] if call_kwargs.args else None)
    durable = call_kwargs.kwargs.get("durable") or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
    assert subject == PM_SUBJECT_PATTERN
    assert durable == PM_CONSUMER_NAME
