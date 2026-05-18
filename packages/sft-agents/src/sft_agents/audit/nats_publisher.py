"""AuditNatsPublisher — NATS JetStream publisher for audit + HITL events (Plan 04-04).

Mirrors `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py` for the audit
dual-write substrate (D-56):
    PG = source of truth (synchronous, 7y retention).
    NATS AUDIT_STREAM = telemetry replica (asynchronous, 90d retention).

Failure semantics (T-04-Outbox-Drop contract):
    publish_* methods re-raise on any NATS error. The caller (Plan 04-06
    AuditWriter) is responsible for enqueuing a row in `audit.outbox` so the
    record can be replayed once NATS is healthy again. This module deliberately
    does NOT swallow exceptions — silent drops would break the dual-write
    invariant.

Security (T-04-NATS-Spoofed):
    Every subject is derived via the helpers in `sft_agents.audit.subjects`,
    which validate cluster / tier / agent_id tokens. No method on this class
    accepts a user-controlled subject string.
"""

from __future__ import annotations

import json
from typing import Any

import nats
import structlog

from sft_agents.audit.subjects import (
    subject_for_approval_new,
    subject_for_approval_resolved,
    subject_for_audit,
    subject_for_governor_alert,
)
from sft_agents.models.approval import ApprovalRequest
from sft_agents.models.audit import AuditRecord

logger = structlog.get_logger(__name__)


class AuditNatsPublisher:
    """JetStream publisher for `AUDIT_STREAM` subjects.

    Lifecycle:
        publisher = AuditNatsPublisher("nats://nats:4222")
        await publisher.connect()
        await publisher.publish_audit(record)
        await publisher.drain()

    Subjects published:
        audit.actions.<cluster>.<agent_id>      — publish_audit
        hitl.approvals.new.<tier>               — publish_approval_new
        hitl.approvals.resolved.<tier>          — publish_approval_resolved
        hitl.governor.alert                     — publish_governor_alert
    """

    def __init__(self, nats_url: str) -> None:
        """Store the NATS URL — does not connect (lazy via `connect()`).

        Args:
            nats_url: e.g. "nats://nats:4222" (read from NATS_URL env in callers).
        """
        if not isinstance(nats_url, str) or not nats_url:
            raise ValueError(f"nats_url must be a non-empty string; got {nats_url!r}")
        self._url: str = nats_url
        self._nc: Any = None  # nats.NATS connection
        self._js: Any = None  # JetStreamContext

    async def connect(self) -> None:
        """Open the NATS connection and bind a JetStream context."""
        self._nc = await nats.connect(self._url)
        self._js = self._nc.jetstream()
        logger.info("audit_publisher_connected", url=self._url)

    async def publish_audit(self, record: AuditRecord) -> None:
        """Publish an AuditRecord to `audit.actions.<cluster>.<agent_id>`.

        Args:
            record: Validated AuditRecord (Pydantic model; subject derivation
                reads `record.cluster` + `record.agent_id`).

        Raises:
            Re-raises any underlying NATS error so the caller can enqueue an
            outbox row (T-04-Outbox-Drop contract).
        """
        subject = subject_for_audit(
            cluster=record.cluster, agent_id=record.agent_id
        )
        payload = record.model_dump_json().encode("utf-8")
        await self._js.publish(subject, payload)
        logger.debug(
            "audit_record_published",
            subject=subject,
            agent_id=record.agent_id,
            decision=record.decision.value,
        )

    async def publish_approval_new(self, approval: ApprovalRequest) -> None:
        """Publish a newly-created ApprovalRequest to `hitl.approvals.new.<tier>`.

        D-55: UI subscribes to this subject for real-time push notification of
        new approval requests.
        """
        subject = subject_for_approval_new(tier=approval.tier)
        payload = approval.model_dump_json().encode("utf-8")
        await self._js.publish(subject, payload)
        logger.info(
            "approval_new_published",
            subject=subject,
            approval_id=str(approval.id),
            tier=approval.tier.value,
        )

    async def publish_approval_resolved(self, approval: ApprovalRequest) -> None:
        """Publish a decided ApprovalRequest to `hitl.approvals.resolved.<tier>`.

        D-55: UI subscribes to this subject to clear pending-approval banners.
        """
        subject = subject_for_approval_resolved(tier=approval.tier)
        payload = approval.model_dump_json().encode("utf-8")
        await self._js.publish(subject, payload)
        logger.info(
            "approval_resolved_published",
            subject=subject,
            approval_id=str(approval.id),
            tier=approval.tier.value,
            status=approval.status.value,
        )

    async def publish_governor_alert(self, payload: dict[str, Any]) -> None:
        """Publish a governor-rate alert to `hitl.governor.alert` (D-58).

        Args:
            payload: dict shape {auto_rate, sample_size, window_start,
                window_end, top_agents} — JSON-serializable.
        """
        subject = subject_for_governor_alert()
        payload_bytes = json.dumps(payload, default=str).encode("utf-8")
        await self._js.publish(subject, payload_bytes)
        logger.info(
            "governor_alert_published",
            subject=subject,
            auto_rate=payload.get("auto_rate"),
            sample_size=payload.get("sample_size"),
        )

    async def drain(self) -> None:
        """Drain the connection gracefully — safe to call when not connected."""
        if self._nc is not None:
            await self._nc.drain()
            logger.info("audit_publisher_drained")
            self._nc = None
            self._js = None
