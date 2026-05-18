"""ApprovalQueueWriter — hitl.approvals INSERT/UPDATE/escalation (D-55).

Implements the three CRUD shapes consumed by:
    - human_approval_node (Task 02): INSERT pending row before interrupt(); UPDATE on resume
    - EscalationSupervisor (Task 03): atomic insert_escalation transaction

T-04-Resume-Replay mitigation:
    - INSERT uses ON CONFLICT (id) DO NOTHING with a sha256-deterministic id
      (derived from ProposedAction.id) — so re-execution of human_approval_node
      after interrupt() does not create duplicate rows.
    - UPDATE returns ApprovalNotFoundError when 0 rows match (stale/forged id).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from sft_agents.models.approval import ApprovalRequest
from sft_agents.models.enums import ApprovalStatus, Tier

logger = structlog.get_logger(__name__)


# T-V5-sql: all SQL is constant + parameterized.
_INSERT_SQL: str = (
    "INSERT INTO hitl.approvals "
    "(id, agent_id, thread_id, tier, action_type, payload_json, status, "
    "created_at, sla_deadline) "
    "VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9) "
    "ON CONFLICT (id) DO NOTHING "
    "RETURNING id"
)

_UPDATE_DECISION_SQL: str = (
    "UPDATE hitl.approvals "
    "SET status = $2, decided_at = $3, decided_by = $4, decision_json = $5::jsonb "
    "WHERE id = $1 AND status = 'pending' "
    "RETURNING id"
)

# Two-step escalation in a single transaction:
#   1. INSERT a new row at the next tier (copy payload from original)
#   2. UPDATE original row → status='escalated', escalated_to_id=<new id>
# We expose this as a single method (`insert_escalation`) that wraps both
# operations in a connection-level transaction so partial failures do not
# leave the queue in an inconsistent state.
_ESCALATION_INSERT_SQL: str = (
    "INSERT INTO hitl.approvals "
    "(id, agent_id, thread_id, tier, action_type, payload_json, status, "
    "created_at, sla_deadline) "
    "SELECT $1, agent_id, thread_id, $2, action_type, payload_json, "
    "'pending', NOW(), $3 "
    "FROM hitl.approvals WHERE id = $4 "
    "RETURNING id"
)

_ESCALATION_UPDATE_SQL: str = (
    "UPDATE hitl.approvals "
    "SET status = 'escalated', escalated_to_id = $2 "
    "WHERE id = $1 AND status = 'pending' "
    "RETURNING id"
)


class ApprovalNotFoundError(LookupError):
    """Raised when an UPDATE affects 0 rows (stale/forged approval id).

    T-04-Resume-Replay defense: an attacker who replays an old ``Command(resume=)``
    payload should not be able to flip the audit log — the row has already moved
    to ``status='approved'`` (or 'rejected'/'escalated'/'timed_out') so the
    WHERE clause filters it out and we raise here.
    """


class ApprovalQueueWriter:
    """Persistence layer for ``hitl.approvals`` (D-55)."""

    def __init__(self, pool: Any) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool

    async def insert(self, approval: ApprovalRequest) -> UUID:
        """INSERT a new ``hitl.approvals`` row (idempotent on id).

        Args:
            approval: Pydantic-validated ApprovalRequest. The ``id`` field
                is the idempotency anchor — same id on re-run yields a no-op.

        Returns:
            ``approval.id`` regardless of whether the row was newly inserted
            or already existed (idempotency contract).
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                _INSERT_SQL,
                approval.id,
                approval.agent_id,
                approval.thread_id,
                approval.tier.value,
                approval.action_type,
                _payload_json_str(approval.payload_json),
                approval.status.value,
                approval.created_at,
                approval.sla_deadline,
            )
        # When ON CONFLICT fires, RETURNING yields no row — but the id IS in PG.
        # Either way the caller's id is the canonical identifier.
        was_inserted = row is not None
        logger.info(
            "approval_queue_insert",
            approval_id=str(approval.id),
            tier=approval.tier.value,
            inserted=was_inserted,
        )
        return approval.id

    async def update_decision(
        self,
        approval_id: UUID,
        *,
        decision: str,
        decided_by: str,
        motivation: str,
        decided_at: datetime,
    ) -> ApprovalStatus:
        """Mark an approval as approved/rejected/escalated (D-55).

        Args:
            approval_id: PK of the pending row.
            decision: ``"approve" | "reject" | "escalate"`` (from
                ApprovalDecision.decision Literal).
            decided_by: User id of the human decision-maker.
            motivation: HITL-07 required free-text motivation.
            decided_at: UTC tz-aware decision timestamp.

        Returns:
            The final ApprovalStatus written to the row.

        Raises:
            ApprovalNotFoundError: If 0 rows match (stale/forged id) —
                T-04-Resume-Replay defense.
        """
        if decision == "approve":
            status = ApprovalStatus.APPROVED
        elif decision == "reject":
            status = ApprovalStatus.REJECTED
        elif decision == "escalate":
            status = ApprovalStatus.ESCALATED
        else:
            raise ValueError(
                f"decision must be approve/reject/escalate; got {decision!r}"
            )

        decision_json = _payload_json_str(
            {
                "decision": decision,
                "motivation": motivation,
                "decided_by": decided_by,
            }
        )

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                _UPDATE_DECISION_SQL,
                approval_id,
                status.value,
                decided_at,
                decided_by,
                decision_json,
            )
        if row is None:
            raise ApprovalNotFoundError(
                f"hitl.approvals row {approval_id} not found or not pending "
                "(T-04-Resume-Replay defense — stale/forged resume id)"
            )
        logger.info(
            "approval_queue_decision",
            approval_id=str(approval_id),
            status=status.value,
            decided_by=decided_by,
        )
        return status

    async def insert_escalation(
        self,
        original_id: UUID,
        *,
        new_tier: Tier,
        new_sla_deadline: datetime,
    ) -> UUID:
        """Atomically escalate an approval to the next tier (D-57).

        Inserts a fresh row at ``new_tier`` (copying agent_id/thread_id/action_type/
        payload_json from the original) and flips the original's status to
        'escalated', wiring ``escalated_to_id`` to the new row.

        Args:
            original_id: PK of the expired/pending row.
            new_tier: Tier value to set on the new row.
            new_sla_deadline: Fresh SLA cutoff for the next tier.

        Returns:
            UUID of the new row.

        Raises:
            ApprovalNotFoundError: If the original row no longer exists OR
                is already non-pending (race condition with another supervisor).
        """
        from uuid import uuid4

        new_id = uuid4()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                inserted = await conn.fetchrow(
                    _ESCALATION_INSERT_SQL,
                    new_id,
                    new_tier.value,
                    new_sla_deadline,
                    original_id,
                )
                if inserted is None:
                    raise ApprovalNotFoundError(
                        f"escalation source row {original_id} not found"
                    )
                updated = await conn.fetchrow(
                    _ESCALATION_UPDATE_SQL,
                    original_id,
                    inserted["id"],
                )
                if updated is None:
                    raise ApprovalNotFoundError(
                        f"escalation source row {original_id} no longer pending"
                    )
        logger.info(
            "approval_queue_escalated",
            original_id=str(original_id),
            new_id=str(inserted["id"]),
            new_tier=new_tier.value,
        )
        return inserted["id"]

    async def mark_timed_out(self, approval_id: UUID) -> None:
        """Mark a manager-tier expired approval as timed_out (D-57 terminal)."""
        sql = (
            "UPDATE hitl.approvals SET status = 'timed_out' "
            "WHERE id = $1 AND status = 'pending'"
        )
        async with self._pool.acquire() as conn:
            await conn.execute(sql, approval_id)
        logger.info("approval_queue_timed_out", approval_id=str(approval_id))


def _payload_json_str(payload: dict[str, Any] | None) -> str:
    """Serialise a Python dict to a JSONB-compatible string.

    Uses ``json.dumps`` with ``default=str`` so UUIDs / datetimes round-trip
    through the JSONB column as their string forms.
    """
    import json

    return json.dumps(payload or {}, default=str)
