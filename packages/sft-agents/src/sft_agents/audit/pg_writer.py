"""AuditPgWriter — synchronous INSERT into audit.actions (D-56 first half).

Replicates the asyncpg-pool + module-constant SQL pattern from
``services/ot-bridge/src/svc_ot_bridge/timescale_writer.py``:

    - ``_INSERT_SQL`` is a module-level constant — NEVER an f-string (T-V5-sql).
    - Placeholders ``$1..$13`` — parameterized query, zero SQL injection path.
    - Pool config uses ``statement_cache_size=0`` (TimescaleDB hypertable requirement,
      Pitfall 6) when the caller creates the pool via :func:`create_audit_pool`.

D-56 invariant (T-04-Audit-Tamper mitigation):
    PG INSERT is synchronous and re-raises on failure. The agent ABORTS — there is
    NO NATS-only fallback. ``AuditWriter`` (writer.py) is the orchestrator that
    enforces this ordering: ``pg.insert`` first, then NATS publish, then outbox.

Notes:
    - ``evidence_panel`` and ``budget_snapshot`` are persisted as JSONB; the writer
      serialises via ``model_dump_json()`` and asyncpg accepts the string as a
      JSONB value when cast via ``$N::jsonb`` placeholders.
    - The composite PRIMARY KEY ``(ts, id)`` enforced by the hypertable migration
      means we MUST pass both ``id`` and ``ts`` explicitly (no DB default).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from sft_agents.models.audit import AuditRecord

logger = structlog.get_logger(__name__)

# SQL parameterized constant — T-V5-sql (zero f-string interpolation).
# Placeholders $1..$13: id, ts, action_id, agent_id, thread_id, cluster,
#                       action_type, evidence_panel, decision, decision_actor,
#                       motivation, budget_snapshot, approval_id
_INSERT_SQL: str = (
    "INSERT INTO audit.actions "
    "(id, ts, action_id, agent_id, thread_id, cluster, action_type, "
    "evidence_panel, decision, decision_actor, motivation, "
    "budget_snapshot, approval_id) "
    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, $11, $12::jsonb, $13)"
)


class AuditPgWriter:
    """Synchronous PG writer for ``audit.actions`` rows (D-56).

    Single responsibility: execute one parameterized INSERT and surface failures
    to the caller. The caller (``AuditWriter``) enforces the dual-write ordering.

    Usage::

        pg_writer = AuditPgWriter(pool)
        await pg_writer.insert(record)  # re-raises on any DB error
    """

    def __init__(self, pool: Any) -> None:
        """Bind to an existing asyncpg pool (or any pool-shaped duck type).

        Args:
            pool: An asyncpg.Pool (or compatible mock) whose ``acquire()`` returns
                an async-context-manager yielding a connection with ``execute()``.
        """
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool

    async def insert(self, record: AuditRecord) -> UUID:
        """INSERT one ``AuditRecord`` into ``audit.actions``.

        Args:
            record: Pydantic-validated AuditRecord (motivation/approval_id
                consistency already enforced by ``AuditRecord._check_decision_consistency``).

        Returns:
            The ``record.id`` for downstream callers that want a confirmed PK.

        Raises:
            Any underlying asyncpg error (re-raised so the agent aborts;
            D-56 invariant — never silently swallow PG failures).
        """
        evidence_json = record.evidence_panel.model_dump_json()
        budget_json = record.budget_snapshot.model_dump_json()
        decision_value = record.decision.value

        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    _INSERT_SQL,
                    record.id,
                    record.ts,
                    record.action_id,
                    record.agent_id,
                    record.thread_id,
                    record.cluster,
                    record.action_type,
                    evidence_json,
                    decision_value,
                    record.decision_actor,
                    record.motivation,
                    budget_json,
                    record.approval_id,
                )
        except Exception as exc:
            logger.error(
                "audit_pg_insert_failed",
                error=str(exc),
                action_id=str(record.action_id),
                agent_id=record.agent_id,
                decision=decision_value,
            )
            raise

        logger.debug(
            "audit_pg_insert_ok",
            audit_id=str(record.id),
            action_id=str(record.action_id),
            agent_id=record.agent_id,
            decision=decision_value,
        )
        return record.id
