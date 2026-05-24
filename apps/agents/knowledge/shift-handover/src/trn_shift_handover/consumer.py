"""NATS JetStream durable pull consumer for ShiftHandover (plan 08-04, D-SH-01).

Subscribes to ``shift.boundary.>`` on the ``KNOWLEDGE_STREAM`` JetStream stream
with durable name ``sh-consumer``. Each boundary event triggers a shift handover
invocation via the supervisor graph.

Trust boundary (T-08-07):
    The server derives ShiftWindow from configured boundary times; client-supplied
    windows that violate ShiftWindow bounds (inverted range, naive datetimes) are
    rejected by Pydantic validation before the graph is invoked. The NATS payload
    provides shift_start / shift_end datetimes — these are validated by ShiftWindow
    field_validator and model_validator, rejecting any tampered payload.

D-SH-01 (resolved): scheduled trigger arrives via NATS shift.boundary.> subject.
Manual trigger is handled by the api-gateway endpoint (plan 08-08).

Injectable design (testability):
    The ``invoke_fn`` parameter accepts the graph/invoke callable, so the consumer
    is fully unit-testable without a live NATS server or real LangGraph graph.

Pattern mirrors: apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/consumer.py
    - Durable JetStream pull subscription
    - Batch fetch with timeout
    - ack on success, nak(delay=5) on transient failure
    - structlog logging

Constants:
    SH_SUBJECT_PATTERN = "shift.boundary.>"    # multi-level wildcard
    SH_STREAM          = "KNOWLEDGE_STREAM"     # knowledge cluster JetStream stream
    SH_CONSUMER_NAME   = "sh-consumer"          # durable consumer name
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import ValidationError

from trn_shift_handover.models import ShiftWindow

logger = structlog.get_logger("agent.shift-handover.consumer")


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: NATS JetStream filter subject (multi-level wildcard — catches all sub-subjects).
SH_SUBJECT_PATTERN: str = "shift.boundary.>"

#: JetStream stream name (knowledge cluster stream).
SH_STREAM: str = "KNOWLEDGE_STREAM"

#: Durable consumer name (D-SH-01).
SH_CONSUMER_NAME: str = "sh-consumer"

#: Target agent name passed to the supervisor graph (routing key).
_TARGET_AGENT: str = "shift-handover"

# Fetch batch parameters (mirror da-consumer).
_FETCH_BATCH: int = 5
_FETCH_TIMEOUT: float = 5.0

# NAK delay on transient errors (seconds).
_NAK_DELAY_S: float = 5.0


# ---------------------------------------------------------------------------
# Payload schema (internal — validates NATS boundary event body)
# ---------------------------------------------------------------------------

def _parse_boundary_payload(data: bytes) -> ShiftWindow:
    """Parse and validate a NATS shift.boundary.> event payload.

    Expected JSON fields:
        shift_start (str, ISO-8601 tz-aware)
        shift_end   (str, ISO-8601 tz-aware)
        boundary_label (str, optional, e.g. "06:00-14:00")

    Trust boundary (T-08-07):
        ShiftWindow.field_validator rejects naive datetimes.
        ShiftWindow.model_validator rejects inverted / zero-width windows.
        Server-side configured boundary times are the authoritative source;
        this parser converts the NATS payload, and ShiftWindow validates bounds.

    Args:
        data: Raw NATS message bytes (UTF-8 JSON).

    Returns:
        Validated ShiftWindow ready for graph invocation.

    Raises:
        ValueError: on JSON decode error.
        ValidationError: on ShiftWindow constraint violation (invalid window).
    """
    try:
        payload = json.loads(data.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"shift.boundary payload JSON decode error: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(
            f"shift.boundary payload must be a JSON object, got {type(payload).__name__}"
        )

    # Parse shift_start / shift_end — accept ISO-8601 strings or datetime objects.
    shift_start = _parse_datetime(payload.get("shift_start"), field="shift_start")
    shift_end = _parse_datetime(payload.get("shift_end"), field="shift_end")
    boundary_label: str = str(payload.get("boundary_label", ""))

    # ShiftWindow validates tz-awareness + end > start (T-08-07).
    return ShiftWindow(
        shift_start=shift_start,
        shift_end=shift_end,
        boundary_label=boundary_label,
    )


def _parse_datetime(value: Any, *, field: str) -> datetime:
    """Parse a datetime from an ISO-8601 string or return a datetime object.

    Raises:
        ValueError: if value is missing, wrong type, or cannot be parsed.
    """
    if value is None:
        raise ValueError(f"shift.boundary payload missing required field: {field!r}")
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            return dt
        except ValueError as exc:
            raise ValueError(
                f"shift.boundary field {field!r} is not a valid ISO-8601 datetime: {value!r}"
            ) from exc
    raise ValueError(
        f"shift.boundary field {field!r} must be str or datetime, got {type(value).__name__}"
    )


# ---------------------------------------------------------------------------
# Main consumer coroutine
# ---------------------------------------------------------------------------


async def run_sh_consumer(
    *,
    nats_client: Any,
    invoke_fn: Callable[[dict[str, Any]], Awaitable[Any]],
    stop_event: asyncio.Event | None = None,
) -> None:
    """Run the sh-consumer pull-subscribe loop until ``stop_event`` is set.

    On each shift.boundary.> event:
        1. Parse + Pydantic-validate payload as ShiftWindow (T-08-07 boundary guard).
           Malformed JSON or invalid window → ack() poison-pill drop (no retry).
        2. Build the graph invocation state dict with target_agent="shift-handover"
           and the validated ShiftWindow.
        3. await invoke_fn(state) — injectable for testability (pass the real graph
           invoke callable in production, AsyncMock in tests).
        4. ack() on success; nak(delay=5) on invoke failure (JetStream redelivery).

    Args:
        nats_client: NATS JetStream context (``nats.JetStream``-like).
            Pull subscribe is called as ``js.pull_subscribe(subject=..., durable=...)``.
        invoke_fn:   Async callable(state_dict) → Any. In production, pass the
            supervisor graph's ainvoke method. Must accept at minimum:
                {"target_agent": str, "shift_window": ShiftWindow}
            Returns the graph result (ignored by the consumer — fire-and-forget
            trigger pattern; the HITL loop lives inside the graph).
        stop_event:  asyncio.Event — the loop exits cleanly when this is set.
            If None, the loop runs until CancelledError.

    Raises:
        asyncio.CancelledError: propagates cleanly (caller cancels tasks on shutdown).
    """
    import nats.errors  # local import — nats may not be available in all envs

    psub = await nats_client.pull_subscribe(
        subject=SH_SUBJECT_PATTERN,
        durable=SH_CONSUMER_NAME,
        stream=SH_STREAM,
    )
    logger.info(
        "sh_consumer_subscribed",
        stream=SH_STREAM,
        durable=SH_CONSUMER_NAME,
        subject=SH_SUBJECT_PATTERN,
        target_agent=_TARGET_AGENT,
    )

    while stop_event is None or not stop_event.is_set():
        try:
            msgs = await psub.fetch(batch=_FETCH_BATCH, timeout=_FETCH_TIMEOUT)
        except nats.errors.TimeoutError:
            continue
        except asyncio.CancelledError:
            logger.info("sh_consumer_cancelled")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("sh_consumer_fetch_error", error=str(exc))
            await asyncio.sleep(0.5)
            continue

        for msg in msgs:
            await _process_one(msg, invoke_fn)

    logger.info("sh_consumer_shutdown_complete")


async def _process_one(
    msg: Any,
    invoke_fn: Callable[[dict[str, Any]], Awaitable[Any]],
) -> None:
    """Validate + invoke + ack/nak a single NATS shift.boundary message.

    Trust boundary (T-08-07):
        ShiftWindow validates the parsed boundary payload before graph invocation.
        Invalid payload (naive datetime, inverted window, malformed JSON) → ack
        poison-pill (no redelivery of permanently invalid data).

    Lifecycle:
        parse payload as ShiftWindow → build state dict with target_agent →
        await invoke_fn(state) → ack on success, nak(delay=5) on invoke failure.
    """
    # Step 1: parse + Pydantic-validate payload (T-08-07 boundary guard).
    try:
        window = _parse_boundary_payload(msg.data or b"")
    except (ValueError, ValidationError) as exc:
        logger.warning(
            "sh_consumer_payload_invalid_ack",
            error=str(exc),
            payload_excerpt=(msg.data or b"")[:200].decode("utf-8", errors="replace"),
        )
        # Poison-pill: permanently invalid payload — ack to move on (no redelivery).
        await msg.ack()
        return

    subject = getattr(msg, "subject", "")
    logger.debug(
        "sh_consumer_boundary_received",
        subject=subject,
        boundary_label=window.boundary_label,
        shift_start=window.shift_start.isoformat(),
        shift_end=window.shift_end.isoformat(),
    )

    # Step 2 + 3: Build state dict and invoke graph.
    state: dict[str, Any] = {
        "target_agent": _TARGET_AGENT,
        "shift_window": window,
    }

    try:
        await invoke_fn(state)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "sh_consumer_invoke_failed_nak",
            error=str(exc),
            boundary_label=window.boundary_label,
            subject=subject,
        )
        await msg.nak(delay=_NAK_DELAY_S)
        return

    # Step 4: ack after successful invocation.
    await msg.ack()
    logger.debug(
        "sh_consumer_boundary_acked",
        subject=subject,
        boundary_label=window.boundary_label,
    )


__all__ = [
    "SH_CONSUMER_NAME",
    "SH_STREAM",
    "SH_SUBJECT_PATTERN",
    "run_sh_consumer",
]
