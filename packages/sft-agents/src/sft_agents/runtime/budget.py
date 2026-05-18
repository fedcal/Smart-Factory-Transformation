"""BudgetTracker — per-(thread_id, agent_id) UPSERT with soft/hard thresholds (CORE-09, D-60).

Hot-path semantics:
    Called once per LangGraph node step (or LLM call via the BudgetingChatModel
    decorator from Plan 04-03). Each call UPSERTs a delta into ``budget.executions``
    and reads back the new totals to evaluate the soft/hard threshold gates.

Threshold policy (D-60):
    - tokens_total / limit_tokens > 0.80  → Operator-tier approval (soft alert)
    - cost_usd > limit_cost_usd            → Supervisor-tier approval (hard, blocking)
    - duration_ms > limit_duration_s*1000  → Operator-tier approval (soft alert)

Limit resolution precedence:
    1. ``agents[<agent_id>]`` override in budgets.yaml
    2. ``<cluster>`` default
    3. Hard-coded safe defaults (tokens=10_000, cost=0.50, duration=60)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog
import yaml

from sft_agents.hitl.approval_queue import ApprovalQueueWriter
from sft_agents.models.approval import ApprovalRequest
from sft_agents.models.budget import BudgetLimits, BudgetSnapshot
from sft_agents.models.enums import ApprovalStatus, Tier

logger = structlog.get_logger(__name__)

_DEFAULT_YAML_PATH = Path(__file__).parent.parent / "policies" / "budgets.yaml"

# Hard-coded safe fallback when neither agent override nor cluster default is set.
_FALLBACK_LIMITS = BudgetLimits(tokens=10_000, cost_usd=0.5, duration_s=60)

# T-V5-sql: constant + parameterized. RETURNING gives us post-UPSERT totals.
_UPSERT_SQL: str = (
    "INSERT INTO budget.executions "
    "(thread_id, agent_id, tokens_total, cost_usd, duration_ms, step_count, "
    "started_at, last_step_at) "
    "VALUES ($1, $2, $3, $4, $5, 1, NOW(), NOW()) "
    "ON CONFLICT (thread_id, agent_id) DO UPDATE SET "
    "tokens_total = budget.executions.tokens_total + EXCLUDED.tokens_total, "
    "cost_usd = budget.executions.cost_usd + EXCLUDED.cost_usd, "
    "duration_ms = budget.executions.duration_ms + EXCLUDED.duration_ms, "
    "step_count = budget.executions.step_count + 1, "
    "last_step_at = NOW() "
    "RETURNING tokens_total, cost_usd, duration_ms, step_count, started_at"
)


class BudgetTracker:
    """Tracks cumulative budget per (thread_id, agent_id); emits ApprovalRequest on threshold."""

    def __init__(
        self,
        *,
        pool: Any,
        queue_writer: ApprovalQueueWriter,
        budgets_yaml_path: Path | None = None,
    ) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool
        self._queue = queue_writer
        path = budgets_yaml_path or _DEFAULT_YAML_PATH
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        # Parse out the `agents:` block separately.
        self._agent_overrides: dict[str, BudgetLimits] = {}
        agents_block = data.pop("agents", None) or {}
        for agent_id, limits in agents_block.items():
            if isinstance(limits, dict):
                self._agent_overrides[str(agent_id)] = _coerce_limits(limits)
        # Remaining keys are cluster defaults.
        self._cluster_defaults: dict[str, BudgetLimits] = {}
        for cluster, limits in data.items():
            if isinstance(limits, dict):
                self._cluster_defaults[str(cluster)] = _coerce_limits(limits)
        logger.info(
            "budget_tracker_loaded",
            cluster_count=len(self._cluster_defaults),
            agent_overrides=len(self._agent_overrides),
        )

    def resolve_limits(self, *, cluster: str, agent_id: str) -> BudgetLimits:
        """Precedence: agent_overrides → cluster_defaults → fallback."""
        if agent_id in self._agent_overrides:
            return self._agent_overrides[agent_id]
        if cluster in self._cluster_defaults:
            return self._cluster_defaults[cluster]
        return _FALLBACK_LIMITS

    async def track(
        self,
        *,
        thread_id: str,
        agent_id: str,
        cluster: str,
        step_input_tokens: int,
        step_output_tokens: int,
        step_cost_usd: float,
        step_duration_ms: int,
    ) -> BudgetSnapshot:
        """UPSERT a delta + return the new BudgetSnapshot.

        Emits approval requests on threshold crossings.
        """
        if step_input_tokens < 0 or step_output_tokens < 0:
            raise ValueError("step token deltas must be non-negative")
        if step_cost_usd < 0:
            raise ValueError("step_cost_usd must be non-negative")
        if step_duration_ms < 0:
            raise ValueError("step_duration_ms must be non-negative")

        delta_tokens = step_input_tokens + step_output_tokens

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                _UPSERT_SQL,
                thread_id,
                agent_id,
                delta_tokens,
                float(step_cost_usd),
                step_duration_ms,
            )
        if row is None:
            raise RuntimeError(
                "budget.executions UPSERT returned no row — RETURNING failed"
            )

        limits = self.resolve_limits(cluster=cluster, agent_id=agent_id)
        tokens_total = int(row["tokens_total"])
        cost_usd = float(row["cost_usd"])
        duration_ms = int(row["duration_ms"])

        snapshot = BudgetSnapshot(
            tokens_input=step_input_tokens,
            tokens_output=step_output_tokens,
            tokens_total=tokens_total,
            cost_usd_simulated=cost_usd,
            duration_ms=duration_ms,
            limit_tokens=limits.tokens,
            limit_cost_usd=limits.cost_usd,
            limit_duration_s=limits.duration_s,
        )

        # Threshold evaluation. We emit approval rows but do NOT pause the agent
        # here — the calling node decides whether to interrupt based on tier.
        if limits.tokens > 0 and tokens_total > 0.80 * limits.tokens:
            await self._emit_approval(
                tier=Tier.OPERATOR,
                thread_id=thread_id,
                agent_id=agent_id,
                kind="budget_soft_tokens",
                snapshot=snapshot,
            )
        if limits.cost_usd > 0 and cost_usd > limits.cost_usd:
            await self._emit_approval(
                tier=Tier.SUPERVISOR,
                thread_id=thread_id,
                agent_id=agent_id,
                kind="budget_hard_cost",
                snapshot=snapshot,
            )
        if (
            limits.duration_s > 0
            and duration_ms > limits.duration_s * 1000
        ):
            await self._emit_approval(
                tier=Tier.OPERATOR,
                thread_id=thread_id,
                agent_id=agent_id,
                kind="budget_soft_duration",
                snapshot=snapshot,
            )

        return snapshot

    async def _emit_approval(
        self,
        *,
        tier: Tier,
        thread_id: str,
        agent_id: str,
        kind: str,
        snapshot: BudgetSnapshot,
    ) -> None:
        """Build + INSERT a budget-threshold ApprovalRequest."""
        now_ts = datetime.now(timezone.utc)
        sla_minutes = 2 if tier == Tier.OPERATOR else 15
        approval = ApprovalRequest(
            id=uuid4(),
            agent_id=agent_id,
            thread_id=thread_id,
            tier=tier,
            action_type="BUDGET_EXHAUSTED" if "hard" in kind else "BUDGET_SOFT_LIMIT",
            payload_json={
                "kind": kind,
                "tokens_total": snapshot.tokens_total,
                "cost_usd": snapshot.cost_usd_simulated,
                "duration_ms": snapshot.duration_ms,
                "limit_tokens": snapshot.limit_tokens,
                "limit_cost_usd": snapshot.limit_cost_usd,
                "limit_duration_s": snapshot.limit_duration_s,
            },
            status=ApprovalStatus.PENDING,
            created_at=now_ts,
            sla_deadline=now_ts + timedelta(minutes=sla_minutes),
        )
        try:
            await self._queue.insert(approval)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "budget_approval_insert_failed",
                kind=kind,
                error=str(exc),
            )


def _coerce_limits(block: dict[str, Any]) -> BudgetLimits:
    return BudgetLimits(
        tokens=int(block.get("tokens", 0) or 0),
        cost_usd=float(block.get("cost_usd", 0.0) or 0.0),
        duration_s=int(block.get("duration_s", 0) or 0),
    )
