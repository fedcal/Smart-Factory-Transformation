"""NATS JetStream durable pull consumer for DowntimeAnalyzer (plan 07-09, D-DA-01).

Subscribes to ``maintenance.downtime.>`` on the ``MAINTENANCE_STREAM`` JetStream
stream with durable name ``da-consumer``.

Lifecycle per message (PG-first dual-write convention):
    1. JSON-validated as DowntimeEvent (Pydantic frozen+extra=forbid).
       Malformed JSON or schema-invalid → ack() poison-pill drop (no retry).
    2. Subject/payload asset_id consistency check:
       If subject says LOOM-01 but payload says LOOM-02, log WARN and proceed
       with payload value. **Payload is the source of truth; subject is routing.**
       Rationale: NATS subjects are infrastructure-level routing labels; the
       actual business entity identity lives in the Pydantic-validated payload.
    3. PG-first: await repository.insert_event(event)  ← operational truth
    4. await audit_writer.write(record)                ← observability (best-effort)
    5. await msg.ack()
    On insert failure: msg.nak(delay=5) — let JetStream retry (max_deliver=5).
    On audit failure: log + ack (audit failure must not cause infinite redelivery;
    PG insert is the operational truth per T-V7-da-audit-write-failure policy).

Constants:
    DA_SUBJECT_PATTERN = "maintenance.downtime.>"   # multi-level wildcard
    DA_STREAM          = "MAINTENANCE_STREAM"        # shared with pm-consumer
    DA_CONSUMER_NAME   = "da-consumer"
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from pydantic import ValidationError
from sim_textile.downtime_event_generator import DowntimeEvent

logger = structlog.get_logger("agent.downtime-analyzer.consumer")


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: NATS JetStream filter subject (multi-level wildcard — catches all sub-subjects).
DA_SUBJECT_PATTERN: str = "maintenance.downtime.>"

#: JetStream stream name (MAINTENANCE_STREAM is shared with 07-06 pm-consumer).
DA_STREAM: str = "MAINTENANCE_STREAM"

#: Durable consumer name (D-DA-01).
DA_CONSUMER_NAME: str = "da-consumer"

# Fetch batch parameters (mirror quality-inspector nats_consumer.py).
_FETCH_BATCH: int = 10
_FETCH_TIMEOUT: float = 5.0

# NAK delay on transient errors (seconds).
_NAK_DELAY_S: float = 5.0


# ---------------------------------------------------------------------------
# Main consumer coroutine
# ---------------------------------------------------------------------------


async def run_da_consumer(
    *,
    nats_client: Any,
    repository: Any,
    audit_writer: Any,
    write_event_audit: Callable[[DowntimeEvent], Awaitable[None]] | None = None,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Run the da-consumer pull-subscribe loop until ``stop_event`` is set.

    Args:
        nats_client: NATS JetStream context (``nats.JetStream``-like).
            Pull subscribe is called as ``js.pull_subscribe(subject=..., durable=...)``.
        repository: DowntimeEventRepository instance (insert_event method).
        audit_writer: AuditWriter instance (write method, accepts AuditRecord).
        write_event_audit: Optional async callback for per-event DOWNTIME_VERDICT
            audit row construction. When None, a minimal inline audit row is written.
            In production wiring (07-10 api-gateway), pass ``analyzer._write_event_audit``.
        stop_event: asyncio.Event — the loop exits cleanly when this is set.
            If None, the loop runs until CancelledError.

    Raises:
        asyncio.CancelledError: propagates cleanly (caller should cancel tasks on shutdown).
    """
    import nats.errors  # local import — nats may not be available in all envs

    psub = await nats_client.pull_subscribe(
        subject=DA_SUBJECT_PATTERN,
        durable=DA_CONSUMER_NAME,
        stream=DA_STREAM,
    )
    logger.info(
        "da_consumer_subscribed",
        stream=DA_STREAM,
        durable=DA_CONSUMER_NAME,
        subject=DA_SUBJECT_PATTERN,
    )

    while stop_event is None or not stop_event.is_set():
        try:
            msgs = await psub.fetch(batch=_FETCH_BATCH, timeout=_FETCH_TIMEOUT)
        except nats.errors.TimeoutError:
            continue
        except asyncio.CancelledError:
            logger.info("da_consumer_cancelled")
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("da_consumer_fetch_error", error=str(exc))
            await asyncio.sleep(0.5)
            continue

        for msg in msgs:
            await _process_one(msg, repository, audit_writer, write_event_audit)

    logger.info("da_consumer_shutdown_complete")


async def _process_one(
    msg: Any,
    repository: Any,
    audit_writer: Any,
    write_event_audit: Callable[[DowntimeEvent], Awaitable[None]] | None,
) -> None:
    """Validate + persist + audit + ack/nak a single NATS message.

    PG-first dual-write convention:
        insert_event(event) → audit_writer.write(record) → msg.ack()
    On insert failure: nak(delay=5).
    On audit failure: log + ack (audit is observability, not operational truth).
    """
    # Step 1: parse + Pydantic validate.
    try:
        event = DowntimeEvent.model_validate_json(msg.data)
    except (ValidationError, ValueError, Exception) as exc:  # noqa: BLE001
        logger.warning(
            "da_consumer_validation_error_ack",
            error=str(exc),
            payload_excerpt=(msg.data or b"")[:200].decode("utf-8", errors="replace"),
        )
        # Poison-pill: permanent invalid payload — ack to move on (no redelivery).
        await msg.ack()
        return

    # Step 2: Subject/payload asset_id consistency check.
    # Subject is routing-only; payload is source of truth.
    subject_parts = getattr(msg, "subject", "").split(".")
    subject_asset_id = subject_parts[-1] if len(subject_parts) >= 3 else None
    if subject_asset_id and subject_asset_id != event.asset_id:
        logger.warning(
            "da_consumer_subject_payload_mismatch",
            subject_asset_id=subject_asset_id,
            payload_asset_id=event.asset_id,
            event_id=event.event_id,
            note="Payload is source of truth; proceeding with payload asset_id.",
        )

    # Step 3: PG-first insert (operational truth).
    try:
        await repository.insert_event(event)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "da_consumer_insert_failed_nak",
            error=str(exc),
            event_id=event.event_id,
            asset_id=event.asset_id,
        )
        await msg.nak(delay=_NAK_DELAY_S)
        return

    # Step 4: Audit write (observability — best-effort after insert).
    try:
        if write_event_audit is not None:
            await write_event_audit(event)
        else:
            await _write_minimal_audit(event, audit_writer)
    except Exception as exc:  # noqa: BLE001
        # T-V7-da-audit-write-failure: PG insert is operational truth.
        # Audit failure must not cause infinite redelivery loop.
        logger.warning(
            "da_consumer_audit_write_failed_ack",
            error=str(exc),
            event_id=event.event_id,
            asset_id=event.asset_id,
            note="PG insert succeeded; audit failure logged but ack proceeds.",
        )

    # Step 5: ack after successful insert (and best-effort audit).
    await msg.ack()
    logger.debug(
        "da_consumer_event_acked",
        event_id=event.event_id,
        asset_id=event.asset_id,
        severity=event.severity,
    )


async def _write_minimal_audit(event: DowntimeEvent, audit_writer: Any) -> None:
    """Write a minimal DOWNTIME_VERDICT audit row when no write_event_audit callback is set.

    This is a fallback for test scenarios or cases where the full DowntimeAnalyzer
    agent is not wired. Production wiring (07-10) uses analyzer._write_event_audit.
    """
    from datetime import timezone
    from uuid import UUID

    from sft_agents.models.audit import AuditRecord
    from sft_agents.models.budget import BudgetSnapshot
    from sft_agents.models.enums import ActionType, Decision
    from sft_agents.models.evidence import EvidencePanel, TokenUsage, ToolCall

    _AGENT_ID = "downtime-analyzer"
    _CLUSTER = "maintenance"
    _NO_LLM_MODEL = "deterministic@downtime-analyzer"
    _NO_PROMPT_HASH = "0" * 64
    _EMPTY_BUDGET = BudgetSnapshot(
        tokens_input=0,
        tokens_output=0,
        tokens_total=0,
        cost_usd_simulated=0.0,
        duration_ms=0,
        limit_tokens=0,
        limit_cost_usd=0.0,
        limit_duration_s=0,
    )

    now = datetime.now(timezone.utc)
    synthetic_call = ToolCall(
        name="downtime_event_ingest",
        args={
            "asset_id": event.asset_id,
            "reason_code": event.reason_code,
            "severity": event.severity,
            "duration_min": event.duration_min,
            "source": event.source,
        },
        result={
            "event_id": event.event_id,
            "persisted_at": now.isoformat(),
        },
        duration_ms=0,
        ts=now,
    )
    evidence_panel = EvidencePanel(
        input_summary=f"downtime event={event.event_id} asset={event.asset_id}",
        input_truncated=False,
        tool_calls=[synthetic_call],
        rag_citations=[],
        confidence=1.0,
        model=_NO_LLM_MODEL,
        prompt_hash=_NO_PROMPT_HASH,
        tokens=TokenUsage(input=0, output=0, total=0),
        duration_ms=0,
    )
    record = AuditRecord(
        id=uuid4(),
        ts=now,
        action_id=UUID(event.event_id),
        agent_id=_AGENT_ID,
        thread_id=f"{_CLUSTER}.{_AGENT_ID}.{event.event_id}",
        cluster=_CLUSTER,
        action_type=ActionType.DOWNTIME_VERDICT.value,
        evidence_panel=evidence_panel,
        decision=Decision.AUTO,
        decision_actor=None,
        motivation=None,
        budget_snapshot=_EMPTY_BUDGET,
        approval_id=None,
    )
    await audit_writer.write(record)


__all__ = [
    "DA_CONSUMER_NAME",
    "DA_STREAM",
    "DA_SUBJECT_PATTERN",
    "run_da_consumer",
]
