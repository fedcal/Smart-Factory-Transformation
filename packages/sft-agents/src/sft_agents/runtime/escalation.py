"""EscalationSupervisor — D-57 background task that advances stale approvals.

Loop pattern (mirrors ``services/ot-bridge/src/svc_ot_bridge/main.py:114-168``):
    while not shutdown.is_set():
        wait(shutdown, timeout=scan_interval) — break if signalled
        _scan_once() — process up to 100 stale rows

For each stale row:
    - tier=operator → escalate to supervisor (insert new row, mark old escalated)
    - tier=supervisor → escalate to manager
    - tier=manager (next_tier=null) → mark timed_out + emit hitl.governor.alert
    - tier=safety_interlock → SKIPPED by query filter (never auto-escalate)

The audit trail is the source of truth for each transition (decision='escalated'
for the chain hops; decision='timed_out' for the manager-terminal case).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog
import yaml

from sft_agents.hitl.approval_queue import ApprovalQueueWriter
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import Decision, Tier
from sft_agents.models.evidence import EvidencePanel, TokenUsage

if TYPE_CHECKING:
    from sft_agents.audit.writer import AuditWriter

logger = structlog.get_logger(__name__)

_DEFAULT_SLA_YAML = (
    Path(__file__).parent.parent / "policies" / "escalation-sla.yaml"
)

# T-V5-sql: constant + parameterized.
_SCAN_SQL: str = (
    "SELECT id, agent_id, thread_id, tier, action_type, payload_json::text AS payload_json "
    "FROM hitl.approvals "
    "WHERE status = 'pending' AND sla_deadline < NOW() AND tier <> 'safety_interlock' "
    "ORDER BY sla_deadline ASC "
    "LIMIT 100"
)


class EscalationSupervisor:
    """Background asyncio task driving the D-57 escalation chain."""

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: "AuditWriter",
        nats_publisher: Any,
        queue_writer: ApprovalQueueWriter,
        sla_yaml_path: Path | None = None,
        scan_interval_s: float = 30.0,
    ) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool
        self._audit = audit_writer
        self._nats = nats_publisher
        self._queue = queue_writer
        self._scan_interval_s = float(scan_interval_s)
        self._shutdown = asyncio.Event()
        with (sla_yaml_path or _DEFAULT_SLA_YAML).open(
            "r", encoding="utf-8"
        ) as fh:
            sla_data = yaml.safe_load(fh) or {}
        # Build {tier_value: (minutes_or_None, next_tier_or_None)}.
        self._sla: dict[str, tuple[int | None, Tier | None]] = {}
        for tier_key, block in sla_data.items():
            if not isinstance(block, dict):
                continue
            minutes = block.get("sla_minutes")
            nxt = block.get("next_tier")
            next_tier = Tier(nxt) if isinstance(nxt, str) and nxt else None
            self._sla[str(tier_key)] = (
                int(minutes) if minutes is not None else None,
                next_tier,
            )

    async def _scan_once(self) -> int:
        """Process up to 100 stale pending rows; return rows processed."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_SCAN_SQL)

        if not rows:
            return 0

        processed = 0
        for row in rows:
            processed += 1
            await self._handle_row(row)
        return processed

    async def _handle_row(self, row: Any) -> None:
        tier_value: str = row["tier"]
        original_id = row["id"]
        agent_id: str = row["agent_id"]
        thread_id: str = row["thread_id"]
        action_type: str = row["action_type"]

        sla_entry = self._sla.get(tier_value)
        if sla_entry is None:
            logger.warning(
                "escalation_unknown_tier",
                tier=tier_value,
                approval_id=str(original_id),
            )
            return

        minutes, next_tier = sla_entry
        if next_tier is None:
            # Manager-terminal: mark timed_out + emit governor.alert.
            await self._queue.mark_timed_out(original_id)
            audit_record = self._build_audit(
                Decision.TIMED_OUT,
                agent_id=agent_id,
                thread_id=thread_id,
                action_type=action_type,
                original_id=original_id,
            )
            await self._audit.write(audit_record)
            try:
                await self._nats.publish_governor_alert(
                    {
                        "kind": "manager_timeout",
                        "tier": tier_value,
                        "approval_id": str(original_id),
                        "thread_id": thread_id,
                        "agent_id": agent_id,
                        "action_type": action_type,
                        "sla_breach_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "escalation_governor_alert_failed",
                    error=str(exc),
                    approval_id=str(original_id),
                )
            logger.info(
                "escalation_manager_timeout",
                approval_id=str(original_id),
                tier=tier_value,
            )
            return

        # Tier escalation: insert next-tier row + mark original escalated.
        next_minutes, _ = self._sla.get(next_tier.value, (None, None))
        next_deadline = datetime.now(timezone.utc) + timedelta(
            minutes=int(next_minutes or 0)
        )
        new_id = await self._queue.insert_escalation(
            original_id,
            new_tier=next_tier,
            new_sla_deadline=next_deadline,
        )
        audit_record = self._build_audit(
            Decision.ESCALATED,
            agent_id=agent_id,
            thread_id=thread_id,
            action_type=action_type,
            original_id=original_id,
            escalated_to_id=new_id,
        )
        await self._audit.write(audit_record)
        logger.info(
            "escalation_tier_advanced",
            from_tier=tier_value,
            to_tier=next_tier.value,
            approval_id=str(original_id),
            new_id=str(new_id),
        )

    def _build_audit(
        self,
        decision: Decision,
        *,
        agent_id: str,
        thread_id: str,
        action_type: str,
        original_id: Any,
        escalated_to_id: Any | None = None,
    ):
        """Build a minimal AuditRecord for the escalation transition."""
        from sft_agents.models.audit import AuditRecord  # noqa: PLC0415

        evidence = EvidencePanel(
            input_summary=f"escalation_event original_id={original_id}",
            tool_calls=[],
            rag_citations=[],
            confidence=1.0,
            model="system-escalation@plan-04-06",
            prompt_hash="0" * 64,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=0,
        )
        budget = BudgetSnapshot(
            tokens_input=0,
            tokens_output=0,
            tokens_total=0,
            cost_usd_simulated=0.0,
            duration_ms=0,
            limit_tokens=0,
            limit_cost_usd=0.0,
            limit_duration_s=0,
        )
        return AuditRecord(
            id=uuid4(),
            ts=datetime.now(timezone.utc),
            action_id=uuid4(),
            agent_id=agent_id,
            thread_id=thread_id,
            cluster="ops",  # system-marker; escalation is cluster-agnostic
            action_type=action_type,
            evidence_panel=evidence,
            decision=decision,
            decision_actor=None,
            motivation=None,
            budget_snapshot=budget,
            approval_id=None,
        )

    async def run(self) -> None:
        """Main loop — sleep + scan until stop() is signalled."""
        try:
            while not self._shutdown.is_set():
                try:
                    await asyncio.wait_for(
                        self._shutdown.wait(), timeout=self._scan_interval_s
                    )
                    break  # signalled during sleep
                except asyncio.TimeoutError:
                    pass
                try:
                    await self._scan_once()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.error("escalation_scan_error", error=str(exc))
        except asyncio.CancelledError:
            logger.info("escalation_supervisor_cancelled")
            raise

    async def stop(self) -> None:
        self._shutdown.set()
