"""AuditWriter — dual-write orchestrator enforcing D-56 ordering invariant.

Invariant (D-56 + T-04-Audit-Tamper):
    1. PG INSERT (audit.actions) is SYNCHRONOUS and BLOCKING.
       Any failure RE-RAISES — the agent aborts. There is no NATS-only audit
       (T-04-Audit-Tamper mitigation — never write a fake audit).
    2. After PG success, NATS publish (audit.actions.<cluster>.<agent_id>) is
       attempted. On failure, the record is enqueued into ``audit.outbox`` and
       the retry loop ships it later (T-04-Outbox-Drop mitigation).

Ordering invariant matters for two reasons:
    - PG is the source of truth (7y retention). NATS is the telemetry replica
      (90d retention).
    - If NATS were written first and PG then failed, downstream subscribers would
      see a record that does not exist in the forensic record — a tampering
      vector.

Single responsibility:
    This class composes ``AuditPgWriter`` + ``AuditNatsPublisher`` + ``OutboxWriter``.
    Each collaborator has its own narrow contract; ``write()`` enforces the
    ordering and the failure-mode policy.
"""

from __future__ import annotations

from typing import Any

import structlog

from sft_agents.audit.outbox import OutboxWriter
from sft_agents.audit.pg_writer import AuditPgWriter
from sft_agents.audit.subjects import subject_for_audit
from sft_agents.models.audit import AuditRecord

logger = structlog.get_logger(__name__)


class AuditWriter:
    """Compose PG-first + NATS-async + outbox-on-failure (D-56 invariant)."""

    def __init__(
        self,
        pg_writer: AuditPgWriter,
        nats_publisher: Any,
        outbox_writer: OutboxWriter,
    ) -> None:
        """Bind the three collaborators.

        Args:
            pg_writer: ``AuditPgWriter`` instance (sync PG INSERT).
            nats_publisher: ``AuditNatsPublisher`` (or any object exposing
                async ``publish_audit(record)``). The outbox retry path
                uses ``publish_raw(subject, payload)``.
            outbox_writer: ``OutboxWriter`` instance (enqueue on NATS failure).
        """
        if pg_writer is None:
            raise ValueError("pg_writer must not be None")
        if nats_publisher is None:
            raise ValueError("nats_publisher must not be None")
        if outbox_writer is None:
            raise ValueError("outbox_writer must not be None")
        self._pg = pg_writer
        self._nats = nats_publisher
        self._outbox = outbox_writer

    async def write(self, record: AuditRecord) -> None:
        """Persist + publish a single AuditRecord (D-56 dual-write).

        Args:
            record: Pydantic-validated AuditRecord. Motivation/approval_id
                consistency is already enforced by
                ``AuditRecord._check_decision_consistency``.

        Raises:
            Re-raises any PG error (D-56 invariant — abort the agent rather
            than silently swallow). NATS errors are caught + outbox-enqueued.
        """
        # Step 1: PG sync write. Re-raises on failure — no outbox fallback.
        await self._pg.insert(record)

        # Step 2: NATS publish. On failure, enqueue into the outbox.
        try:
            await self._nats.publish_audit(record)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "audit_nats_publish_failed",
                error=str(exc),
                action_id=str(record.action_id),
                agent_id=record.agent_id,
                decision=record.decision.value,
            )
            subject = subject_for_audit(
                cluster=record.cluster, agent_id=record.agent_id
            )
            payload = record.model_dump_json().encode("utf-8")
            try:
                await self._outbox.enqueue(subject, payload)
            except Exception as outbox_exc:  # noqa: BLE001
                # D-56 invariant: we already have a PG row (source of truth) so
                # we MUST NOT re-raise from outbox failure — the audit is durable.
                # Surface the loss via structlog so Phase 11 alerting can catch it.
                logger.error(
                    "audit_outbox_enqueue_failed",
                    error=str(outbox_exc),
                    subject=subject,
                    action_id=str(record.action_id),
                )
