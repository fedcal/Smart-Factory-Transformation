"""EpisodicReplay — read-only projection of audit.actions (CORE-08, D-59).

Implements the :class:`Memory` ABC by SELECTing from ``audit.actions`` ordered
by ``ts`` ASC. The write side (``store()``) raises NotImplementedError because
episodic memory is a *projection* of the immutable audit log — agents do not
write to episodic memory directly; new episodes are created via AuditWriter.

Per D-59, queries are bounded:
    LIMIT 1000 per call (audit hypertable is partitioned by ts; 1000 rows fits
    in a single 30-day chunk for most agents).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import Decision
from sft_agents.models.evidence import EvidencePanel
from sft_agents.models.memory_record import MemoryRecord
from sft_agents.sdk.memory import Memory

logger = structlog.get_logger(__name__)

# T-V5-sql: SQL constants only. The two queries share a column projection so
# AuditRecord hydration is straightforward.
_REPLAY_SQL: str = (
    "SELECT id, ts, action_id, agent_id, thread_id, cluster, action_type, "
    "evidence_panel::text AS evidence_panel, decision, decision_actor, "
    "motivation, budget_snapshot::text AS budget_snapshot, approval_id "
    "FROM audit.actions "
    "WHERE thread_id = $1 AND ($2::timestamptz IS NULL OR ts >= $2) "
    "ORDER BY ts ASC LIMIT 1000"
)

_RECENT_BY_AGENT_SQL: str = (
    "SELECT id, ts, action_id, agent_id, thread_id, cluster, action_type, "
    "evidence_panel::text AS evidence_panel, decision, decision_actor, "
    "motivation, budget_snapshot::text AS budget_snapshot, approval_id "
    "FROM audit.actions "
    "WHERE agent_id = $1 "
    "ORDER BY ts DESC LIMIT $2"
)


class EpisodicReplay(Memory):
    """Read-only audit-log projection (CORE-08, D-59)."""

    def __init__(self, *, pool: Any) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool

    async def replay_thread(
        self,
        thread_id: str,
        since: datetime | None = None,
    ) -> list[AuditRecord]:
        """Return all audit rows for ``thread_id`` ordered by ts ASC (LIMIT 1000)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_REPLAY_SQL, thread_id, since)
        return [_row_to_audit_record(row) for row in rows]

    async def query(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        """Convert audit rows → MemoryRecord. Filters supported: thread_id, agent_id."""
        filters = filters or {}
        records: list[AuditRecord] = []
        if "thread_id" in filters:
            records = await self.replay_thread(str(filters["thread_id"]))
        elif "agent_id" in filters:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    _RECENT_BY_AGENT_SQL, str(filters["agent_id"]), int(k)
                )
            records = [_row_to_audit_record(row) for row in rows]
        else:
            return []

        out: list[MemoryRecord] = []
        for rec in records[:k]:
            content = rec.evidence_panel.input_summary or rec.action_type
            out.append(
                MemoryRecord(
                    source_uri=f"audit://{rec.cluster}/{rec.agent_id}/{rec.action_id}",
                    content=content,
                    score=1.0,
                    ts=rec.ts,
                    metadata={
                        "kind": "episodic",
                        "decision": rec.decision.value,
                        "thread_id": rec.thread_id,
                        "agent_id": rec.agent_id,
                    },
                )
            )
        return out

    async def store(self, record: MemoryRecord) -> str:
        """Raise — episodic memory is a read-only projection of the audit log."""
        raise NotImplementedError(
            "EpisodicReplay is read-only; episodes are created via AuditWriter"
        )


def _row_to_audit_record(row: Any) -> AuditRecord:
    """Materialise an asyncpg row dict → AuditRecord.

    Both ``evidence_panel`` and ``budget_snapshot`` are JSONB columns selected
    as ``::text`` so we round-trip through ``json.loads`` for robust handling
    across asyncpg versions (some return dicts, others strings).
    """
    evidence_value = row["evidence_panel"]
    budget_value = row["budget_snapshot"]
    if isinstance(evidence_value, (bytes, bytearray)):
        evidence_value = evidence_value.decode("utf-8")
    if isinstance(budget_value, (bytes, bytearray)):
        budget_value = budget_value.decode("utf-8")
    if isinstance(evidence_value, str):
        evidence = EvidencePanel.model_validate_json(evidence_value)
    else:
        evidence = EvidencePanel.model_validate(evidence_value)
    if isinstance(budget_value, str):
        budget = BudgetSnapshot.model_validate_json(budget_value)
    else:
        budget = BudgetSnapshot.model_validate(budget_value)

    approval_id = row["approval_id"]
    if isinstance(approval_id, str):
        approval_id = UUID(approval_id)

    return AuditRecord(
        id=row["id"] if isinstance(row["id"], UUID) else UUID(str(row["id"])),
        ts=row["ts"],
        action_id=row["action_id"]
        if isinstance(row["action_id"], UUID)
        else UUID(str(row["action_id"])),
        agent_id=row["agent_id"],
        thread_id=row["thread_id"],
        cluster=row["cluster"],
        action_type=row["action_type"],
        evidence_panel=evidence,
        decision=Decision(row["decision"]),
        decision_actor=row["decision_actor"],
        motivation=row["motivation"],
        budget_snapshot=budget,
        approval_id=approval_id,
    )
