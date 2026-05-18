"""Governor — sliding-window approval-rate alert (HITL-09, D-58).

Every ``scan_interval_s`` seconds, scans ``audit.actions`` for the last 1h. If

    auto_count / total > 0.80   AND   total >= 20

then emit a ``governor_alert`` audit row + ``hitl.governor.alert`` NATS event +
Manager-tier ApprovalRequest with action_type='GOVERNOR_ALERT'.

Cooldown (anti-thrash, T-04-LLM-Inject defense):
    If any ``governor_alert`` audit row exists in the last 5 minutes, the next
    scan returns False — alerts are de-duplicated.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

from sft_agents.hitl.approval_queue import ApprovalQueueWriter
from sft_agents.models.approval import ApprovalRequest
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, ApprovalStatus, Decision, Tier
from sft_agents.models.evidence import EvidencePanel, TokenUsage

if TYPE_CHECKING:
    from sft_agents.audit.writer import AuditWriter

logger = structlog.get_logger(__name__)

# T-V5-sql: constants only. Window + cooldown intervals are server-side literals.
_GOVERNOR_SCAN_SQL: str = (
    "SELECT count(*) FILTER (WHERE decision='auto') AS auto_count, "
    "count(*) AS total "
    "FROM audit.actions "
    "WHERE ts > NOW() - INTERVAL '1 hour' "
    "AND decision NOT IN ('escalated','governor_alert','timed_out')"
)

_TOP_AGENTS_SQL: str = (
    "SELECT agent_id, count(*) AS cnt "
    "FROM audit.actions "
    "WHERE ts > NOW() - INTERVAL '1 hour' AND decision='auto' "
    "GROUP BY agent_id ORDER BY cnt DESC LIMIT 5"
)

_COOLDOWN_SQL: str = (
    "SELECT 1 FROM audit.actions "
    "WHERE decision='governor_alert' AND ts > NOW() - INTERVAL '5 minutes' "
    "LIMIT 1"
)


class Governor:
    """Background asyncio task — emits ``governor_alert`` when auto-rate spikes."""

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: "AuditWriter",
        nats_publisher: Any,
        queue_writer: ApprovalQueueWriter,
        scan_interval_s: float = 60.0,
        threshold: float = 0.80,
        min_sample: int = 20,
    ) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool
        self._audit = audit_writer
        self._nats = nats_publisher
        self._queue = queue_writer
        self._scan_interval_s = float(scan_interval_s)
        self._threshold = float(threshold)
        self._min_sample = int(min_sample)
        self._shutdown = asyncio.Event()

    async def _scan_once(self) -> bool:
        """One scan iteration; return True if an alert was emitted."""
        async with self._pool.acquire() as conn:
            # Cooldown gate first — if any governor_alert in last 5m, skip.
            cooldown = await conn.fetchrow(_COOLDOWN_SQL)
            if cooldown is not None:
                logger.debug("governor_cooldown_active")
                return False

            row = await conn.fetchrow(_GOVERNOR_SCAN_SQL)
            if row is None:
                return False
            auto_count = int(row["auto_count"] or 0)
            total = int(row["total"] or 0)

            if total < self._min_sample:
                return False
            auto_rate = auto_count / total if total > 0 else 0.0
            if auto_rate <= self._threshold:
                return False

            top_rows = await conn.fetch(_TOP_AGENTS_SQL)
            top_agents = [
                {"agent_id": r["agent_id"], "count": int(r["cnt"])}
                for r in top_rows
            ]

        # Emit audit + NATS + Manager-tier approval (outside the connection ctx
        # so we don't hold the pool slot while the audit writer dual-writes).
        now_ts = datetime.now(timezone.utc)
        window_start = now_ts - timedelta(hours=1)
        audit_record = self._build_alert_audit(
            now_ts=now_ts, auto_rate=auto_rate, sample_size=total
        )
        await self._audit.write(audit_record)

        try:
            await self._nats.publish_governor_alert(
                {
                    "auto_rate": auto_rate,
                    "sample_size": total,
                    "window_start": window_start.isoformat(),
                    "window_end": now_ts.isoformat(),
                    "top_agents": top_agents,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("governor_alert_publish_failed", error=str(exc))

        # Create a Manager-tier approval row so the UI surfaces the alert.
        approval = ApprovalRequest(
            id=uuid4(),
            agent_id="__system_governor__",
            thread_id="__system__.governor",
            tier=Tier.MANAGER,
            action_type=ActionType.GOVERNOR_ALERT.value,
            payload_json={
                "auto_rate": auto_rate,
                "sample_size": total,
                "top_agents": top_agents,
            },
            status=ApprovalStatus.PENDING,
            created_at=now_ts,
            sla_deadline=now_ts + timedelta(minutes=60),
        )
        try:
            await self._queue.insert(approval)
        except Exception as exc:  # noqa: BLE001
            logger.warning("governor_approval_insert_failed", error=str(exc))

        logger.info(
            "governor_alert_emitted",
            auto_rate=auto_rate,
            sample_size=total,
            top_agent_count=len(top_agents),
        )
        return True

    def _build_alert_audit(
        self, *, now_ts: datetime, auto_rate: float, sample_size: int
    ):
        from sft_agents.models.audit import AuditRecord  # noqa: PLC0415

        evidence = EvidencePanel(
            input_summary=(
                f"governor alert auto_rate={auto_rate:.3f} "
                f"sample_size={sample_size}"
            ),
            tool_calls=[],
            rag_citations=[],
            confidence=1.0,
            model="system-governor@plan-04-06",
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
            ts=now_ts,
            action_id=uuid4(),
            agent_id="__system_governor__",
            thread_id="__system__.governor",
            cluster="ops",  # system marker — Plan 04-01 enum does not include 'system'
            action_type=ActionType.GOVERNOR_ALERT.value,
            evidence_panel=evidence,
            decision=Decision.GOVERNOR_ALERT,
            decision_actor=None,
            motivation=None,
            budget_snapshot=budget,
            approval_id=None,
        )

    async def run(self) -> None:
        try:
            while not self._shutdown.is_set():
                try:
                    await asyncio.wait_for(
                        self._shutdown.wait(), timeout=self._scan_interval_s
                    )
                    break
                except asyncio.TimeoutError:
                    pass
                try:
                    await self._scan_once()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.error("governor_scan_error", error=str(exc))
        except asyncio.CancelledError:
            logger.info("governor_cancelled")
            raise

    async def stop(self) -> None:
        self._shutdown.set()
