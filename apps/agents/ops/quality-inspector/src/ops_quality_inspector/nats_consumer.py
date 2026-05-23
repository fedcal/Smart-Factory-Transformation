"""NATS JetStream durable consumer for quality.events.* (D-QI-01).

Subscribes to ``quality.events.>`` on the ``QUALITY_STREAM`` JetStream stream
with durable name ``qi-consumer``. Each fetched message is:

    1. JSON-validated as a ``QualityEvent`` (rejects naive datetime + bad
       dye_lot_id regex + unknown defect_type — T-V6-injection).
    2. Idempotency-checked via SQL ``SELECT 1 FROM audit.actions WHERE
       action_id = $1 LIMIT 1`` (audit.actions.action_id is the same UUID
       as ``QualityEvent.event_id`` — guarantees one audit row per event
       across JetStream redeliveries).
    3. Routed to ``qi_handler(event, msg)`` on first-time delivery.
    4. ACK/NAK/TERM-ed per outcome:
        - ack()  on success and on idempotent skip
        - term() on permanent ValidationError (poison message)
        - nak()  on any other exception (transient — let redelivery retry)

The loop runs until the ``shutdown`` event is set; on each fetch timeout
the loop checks ``shutdown.is_set()`` and exits cleanly. ``max_deliver=5``
and ``ack_wait=30s`` are configured at consumer-creation time (in
``scripts/nats-bootstrap-streams.py``).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
from pydantic import ValidationError
from sft_domain.ops.quality import QualityEvent

if TYPE_CHECKING:
    pass

logger = structlog.get_logger("agent.quality-inspector.consumer")


# T-V5-sql: constants only (no f-string SQL with user data).
_DEDUP_SQL: str = "SELECT 1 FROM audit.actions WHERE action_id = $1 LIMIT 1"

# Subscription parameters (mirror scripts/nats-bootstrap-streams.py).
_STREAM_NAME: str = "QUALITY_STREAM"
_DURABLE_NAME: str = "qi-consumer"
_FILTER_SUBJECT: str = "quality.events.>"

# Fetch batch parameters.
_FETCH_BATCH: int = 10
_FETCH_TIMEOUT: float = 5.0


async def already_processed(pool: Any, event_id: UUID) -> bool:
    """Return True iff an audit row with ``action_id=event_id`` already exists.

    Used by the consumer loop to skip JetStream redeliveries that have
    already been processed (Pitfall §3 + §4 audit double-write mitigation).
    """
    async with pool.acquire() as conn:
        row = await conn.fetchval(_DEDUP_SQL, event_id)
    return row is not None


async def run_qi_consumer(
    *,
    js: Any,
    qi_handler: Any,
    pool: Any,
    shutdown: asyncio.Event,
) -> None:
    """Run the qi-consumer pull-subscribe loop until ``shutdown`` is set.

    Args:
        js: NATS JetStream context (``nats.JetStream``-like).
        qi_handler: Async callable ``async def handler(event, msg)`` invoked
            for each new (non-replayed) QualityEvent.
        pool: asyncpg pool used by ``already_processed`` for idempotency.
        shutdown: asyncio.Event - the loop exits cleanly when this is set.

    The consumer is created with durable=qi-consumer and filter_subject=
    quality.events.>; on first call the JetStream server side binds the
    durable to QUALITY_STREAM and remembers the ack position.
    """
    import nats.errors  # local import - nats may not be available in some envs

    psub = await js.pull_subscribe(
        subject=_FILTER_SUBJECT,
        durable=_DURABLE_NAME,
        stream=_STREAM_NAME,
    )
    logger.info(
        "qi_consumer_subscribed",
        stream=_STREAM_NAME,
        durable=_DURABLE_NAME,
        subject=_FILTER_SUBJECT,
    )

    while not shutdown.is_set():
        try:
            msgs = await psub.fetch(batch=_FETCH_BATCH, timeout=_FETCH_TIMEOUT)
        except nats.errors.TimeoutError:
            continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("qi_consumer_fetch_error", error=str(exc))
            # Brief pause to avoid tight error loops; respect shutdown promptly.
            await asyncio.sleep(0.5)
            continue

        for msg in msgs:
            await _process_one(msg, qi_handler, pool)

    logger.info("qi_consumer_shutdown_complete")


async def _process_one(msg: Any, qi_handler: Any, pool: Any) -> None:
    """Validate + idempotency-check + dispatch + ack/term/nak a single msg."""
    # Step 1: parse + validate (T-V6-injection).
    try:
        event = QualityEvent.model_validate_json(msg.data)
    except ValidationError as exc:
        # Poison: permanent invalid payload. terminate (no redelivery).
        logger.warning(
            "qi_consumer_validation_error_term",
            error=str(exc),
            payload_excerpt=(msg.data or b"")[:200].decode("utf-8", errors="replace"),
        )
        await msg.term()
        return
    except Exception as exc:  # noqa: BLE001
        # Unexpected deserialization issue - treat as transient and let
        # redelivery retry rather than dropping the message.
        logger.warning("qi_consumer_decode_error_nak", error=str(exc))
        await msg.nak()
        return

    # Step 2: idempotency check (Pitfall §3 + §4).
    try:
        if await already_processed(pool, event.event_id):
            logger.info(
                "qi_consumer_idempotent_skip",
                event_id=str(event.event_id),
                asset_id=event.asset_id,
            )
            await msg.ack()
            return
    except Exception as exc:  # noqa: BLE001
        # PG transient failure -> nak so we retry rather than skip.
        logger.warning(
            "qi_consumer_dedup_query_failed_nak",
            error=str(exc),
            event_id=str(event.event_id),
        )
        await msg.nak()
        return

    # Step 3: dispatch + ack/nak.
    try:
        await qi_handler(event, msg)
    except ValidationError as exc:
        # Downstream Pydantic validation failed on a derived structure -
        # still treat as poison for this event.
        logger.warning(
            "qi_consumer_handler_validation_error_term",
            error=str(exc),
            event_id=str(event.event_id),
        )
        await msg.term()
        return
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "qi_consumer_handler_transient_error_nak",
            error=str(exc),
            event_id=str(event.event_id),
        )
        await msg.nak()
        return

    await msg.ack()


__all__ = ["already_processed", "run_qi_consumer"]
