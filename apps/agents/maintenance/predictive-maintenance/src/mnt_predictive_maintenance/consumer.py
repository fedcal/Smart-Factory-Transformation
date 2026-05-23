"""NATS JetStream durable pm-consumer for maintenance.predict.* (D-PM-04).

Subscribes to ``maintenance.predict.*`` on the ``MAINTENANCE_STREAM`` stream
with durable name ``pm-consumer``. Each fetched message is:

    1. JSON-decoded and validated as a ``PredictRequest`` (frozen+extra=forbid).
       Malformed messages are ack-dropped as poison-pill (T-V7-pm-payload-injection).
    2. Subject vs payload consistency check: ``msg.subject`` must match
       ``maintenance.predict.{payload.asset_id}`` — mismatches are logged + ack-dropped.
    3. Routed to ``agent(state={...})`` with the parsed fields.
    4. ACK/NAK-ed per outcome:
        - ack()  on success
        - ack()  on ValidationError (poison-pill — no redelivery of malformed messages)
        - nak(delay=5s) on agent exception (transient — let redelivery retry; max_deliver=5)

The loop runs until the ``stop_event`` is set; on each fetch timeout the loop
checks ``stop_event.is_set()`` and exits cleanly.

Security notes:
    T-V7-pm-payload-injection: PredictRequest frozen+extra=forbid; poison-pill ack-drop.
    T-V7-pm-consumer-poison: ack() on ValidationError prevents infinite redelivery loop.
    T-V7-pm-stream-drift: add_stream idempotent (existing-stream error caught + logged).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog
from pydantic import ValidationError

from mnt_predictive_maintenance.agent import PredictiveMaintenance
from mnt_predictive_maintenance.models import PredictRequest

logger = structlog.get_logger("agent.predictive-maintenance.consumer")

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: JetStream subject wildcard for all maintenance.predict messages.
PM_SUBJECT_PATTERN: str = "maintenance.predict.*"

#: JetStream stream name for the maintenance cluster.
PM_STREAM: str = "MAINTENANCE_STREAM"

#: Durable consumer name for the PM pull subscriber.
PM_CONSUMER_NAME: str = "pm-consumer"

#: Explicit ack wait in seconds (JetStream redelivers after this timeout if not acked).
_ACK_WAIT_SECONDS: int = 30

#: Max redelivery attempts before NATS marks the message as MaxDeliver and moves on.
_MAX_DELIVER: int = 5

#: NAK delay in seconds for transient agent failures (avoid hot-retry loops).
_NAK_DELAY_SECONDS: int = 5

#: Fetch batch size per JetStream pull iteration.
_FETCH_BATCH: int = 10

#: Fetch timeout per JetStream pull iteration.
_FETCH_TIMEOUT_SECONDS: float = 2.0


# ---------------------------------------------------------------------------
# Consumer entrypoint
# ---------------------------------------------------------------------------


async def run_pm_consumer(
    *,
    nats_client: Any,
    agent: PredictiveMaintenance,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Run the pm-consumer pull-subscribe loop until ``stop_event`` is set.

    Args:
        nats_client:
            Live NATS client (``nats.aio.client.Client``-like).
        agent:
            Instantiated ``PredictiveMaintenance`` node to invoke per message.
        stop_event:
            Optional ``asyncio.Event``. When set, the loop exits after the
            current fetch batch completes. When None, the loop runs indefinitely
            (useful for production; tests should inject a stop_event).

    The stream bootstrap is idempotent: if ``MAINTENANCE_STREAM`` already exists,
    the ``add_stream`` call is silently skipped (T-V7-pm-stream-drift mitigation).

    Graceful shutdown: ``asyncio.CancelledError`` is caught, logged, and re-raised
    cleanly so the caller's task group can detect the cancellation.
    """
    import nats.errors  # local import — nats may not be available in some test environments  # noqa: PLC0415
    from nats.js.api import (  # noqa: PLC0415
        AckPolicy,
        ConsumerConfig,
        DeliverPolicy,
        RetentionPolicy,
        StreamConfig,
    )

    try:
        js = nats_client.jetstream()

        # Idempotent stream bootstrap (T-V7-pm-stream-drift mitigation).
        await _bootstrap_stream(js, RetentionPolicy, StreamConfig)

        # Create / bind the durable pull consumer.
        psub = await js.pull_subscribe(
            subject=PM_SUBJECT_PATTERN,
            durable=PM_CONSUMER_NAME,
            config=ConsumerConfig(
                deliver_policy=DeliverPolicy.ALL,
                ack_policy=AckPolicy.EXPLICIT,
                max_deliver=_MAX_DELIVER,
                ack_wait=_ACK_WAIT_SECONDS,
            ),
        )
        logger.info(
            "pm_consumer_subscribed",
            stream=PM_STREAM,
            durable=PM_CONSUMER_NAME,
            subject=PM_SUBJECT_PATTERN,
        )

        # Main loop
        while not (stop_event and stop_event.is_set()):
            try:
                msgs = await psub.fetch(
                    batch=_FETCH_BATCH,
                    timeout=_FETCH_TIMEOUT_SECONDS,
                )
            except (nats.errors.TimeoutError, asyncio.TimeoutError):
                continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("pm_consumer_fetch_error", error=str(exc))
                await asyncio.sleep(1)
                continue

            for msg in msgs:
                await _process_one(msg, agent)

        logger.info("pm_consumer_shutdown_complete")

    except asyncio.CancelledError:
        logger.info("pm_consumer_cancelled")
        raise


async def _bootstrap_stream(
    js: Any,
    RetentionPolicy: Any,
    StreamConfig: Any,
) -> None:
    """Create MAINTENANCE_STREAM if it does not exist (idempotent).

    Any ``already exists`` / ``stream name already in use`` error from NATS
    is caught and logged at DEBUG level — the consumer continues normally.
    """
    try:
        await js.add_stream(
            StreamConfig(
                name=PM_STREAM,
                subjects=[PM_SUBJECT_PATTERN, "maintenance.downtime.>"],
                retention=RetentionPolicy.LIMITS,
                max_age=30 * 24 * 60 * 60,  # 30 days
            )
        )
        logger.debug("pm_stream_created", stream=PM_STREAM)
    except Exception as exc:  # noqa: BLE001
        # NATS raises a generic exception (or nats.errors.*) if stream already exists.
        error_msg = str(exc).lower()
        if "already" in error_msg or "exists" in error_msg or "stream name" in error_msg:
            logger.debug("pm_stream_already_exists", stream=PM_STREAM)
        else:
            logger.warning(
                "pm_stream_bootstrap_error",
                stream=PM_STREAM,
                error=str(exc),
            )


async def _process_one(msg: Any, agent: PredictiveMaintenance) -> None:
    """Validate + dispatch + ack/nak a single JetStream message.

    Protocol:
        - ValidationError → ack (poison-pill: no redelivery)
        - Subject/payload mismatch → ack (contract violation)
        - Agent exception → nak(delay=5s) (transient: let redelivery retry)
        - Success → ack
    """
    # Step 1: JSON decode
    try:
        raw = json.loads(msg.data)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "pm_consumer_json_decode_error",
            error=str(exc),
            payload_excerpt=(msg.data or b"")[:200].decode("utf-8", errors="replace"),
        )
        await msg.ack()
        return

    # Step 2: Schema validation (T-V7-pm-payload-injection)
    try:
        req = PredictRequest.model_validate(raw)
    except ValidationError as exc:
        logger.warning(
            "pm_consumer_validation_error",
            error=str(exc),
            payload_excerpt=str(raw)[:200],
        )
        await msg.ack()  # poison-pill: don't redeliver malformed messages
        return

    # Step 3: Subject vs payload consistency check
    # Subject is maintenance.predict.<asset_id>; payload.asset_id must match.
    subject = getattr(msg, "subject", "")
    expected_subject = f"maintenance.predict.{req.asset_id}"
    if subject and subject != expected_subject:
        logger.warning(
            "pm_consumer_subject_mismatch",
            msg_subject=subject,
            payload_asset_id=req.asset_id,
            expected_subject=expected_subject,
        )
        await msg.ack()  # contract violation: ack-drop as poison-pill
        return

    # Step 4: Invoke agent
    try:
        await agent({
            "asset_id": req.asset_id,
            "triggered_by_action_id": req.triggered_by_action_id,
            "severity": req.severity,
        })
        await msg.ack()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "pm_consumer_agent_error",
            asset_id=req.asset_id,
            error=str(exc),
        )
        await msg.nak(delay=_NAK_DELAY_SECONDS)


__all__ = [
    "PM_SUBJECT_PATTERN",
    "PM_STREAM",
    "PM_CONSUMER_NAME",
    "run_pm_consumer",
]
