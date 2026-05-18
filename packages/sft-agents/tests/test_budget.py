"""BudgetTracker UPSERT + soft/hard threshold tests (CORE-09, D-60).

The UPSERT is mocked at the asyncpg layer; threshold gating is asserted via
ApprovalQueueWriter.insert call counts. The real PG round-trip lives in
tests/integration/ (Plan 04-07 owns the api-gateway e2e).
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytest.importorskip(
    "sft_agents.runtime.budget",
    reason="Plan 04-06 Task 04 implements BudgetTracker",
)

from sft_agents.hitl.approval_queue import ApprovalQueueWriter  # noqa: E402
from sft_agents.models.budget import BudgetLimits  # noqa: E402
from sft_agents.models.enums import Tier  # noqa: E402
from sft_agents.runtime.budget import BudgetTracker, _UPSERT_SQL  # noqa: E402


def _build_tracker(
    mock_pool: AsyncMock, *, budgets_yaml_path: Path | None = None
) -> tuple[BudgetTracker, AsyncMock]:
    queue = ApprovalQueueWriter(mock_pool)
    # Spy on insert so we can assert tier-specific approval emission.
    queue.insert = AsyncMock(return_value=uuid4())  # type: ignore[method-assign]
    tracker = BudgetTracker(
        pool=mock_pool,
        queue_writer=queue,
        budgets_yaml_path=budgets_yaml_path,
    )
    return tracker, queue.insert  # type: ignore[return-value]


def _stub_upsert(conn, *, tokens_total, cost_usd, duration_ms, step_count=1) -> None:
    """Wire conn.fetchrow to return the UPSERT RETURNING row."""
    from datetime import datetime, timezone

    conn.fetchrow = AsyncMock(
        return_value={
            "tokens_total": tokens_total,
            "cost_usd": cost_usd,
            "duration_ms": duration_ms,
            "step_count": step_count,
            "started_at": datetime.now(timezone.utc),
        }
    )


async def test_upsert_uses_parameterized_sql(mock_pool: AsyncMock) -> None:
    """SQL constant has $1..$5 placeholders + ON CONFLICT … DO UPDATE."""
    assert "ON CONFLICT (thread_id, agent_id) DO UPDATE" in _UPSERT_SQL
    assert "$1" in _UPSERT_SQL and "$5" in _UPSERT_SQL
    assert "RETURNING tokens_total" in _UPSERT_SQL


async def test_upsert_accumulates_within_limit(mock_pool: AsyncMock) -> None:
    """Below all thresholds: no approval emitted."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    _stub_upsert(conn, tokens_total=100, cost_usd=0.01, duration_ms=50)
    tracker, insert_spy = _build_tracker(mock_pool)

    snap = await tracker.track(
        thread_id="t1",
        agent_id="operator-assistant",
        cluster="ops",
        step_input_tokens=50,
        step_output_tokens=50,
        step_cost_usd=0.01,
        step_duration_ms=50,
    )
    assert snap.tokens_total == 100
    assert snap.limit_tokens == 50_000  # ops cluster default
    insert_spy.assert_not_called()


async def test_soft_token_threshold(mock_pool: AsyncMock) -> None:
    """tokens_total > 80% of limit_tokens → Operator-tier approval."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    # ops limit = 50000, 80% = 40000. Stage above that.
    _stub_upsert(conn, tokens_total=45_000, cost_usd=0.01, duration_ms=10)
    tracker, insert_spy = _build_tracker(mock_pool)

    await tracker.track(
        thread_id="t1",
        agent_id="operator-assistant",
        cluster="ops",
        step_input_tokens=100,
        step_output_tokens=100,
        step_cost_usd=0.01,
        step_duration_ms=10,
    )
    assert insert_spy.await_count == 1
    approval = insert_spy.await_args.args[0]
    assert approval.tier == Tier.OPERATOR
    assert approval.action_type == "BUDGET_SOFT_LIMIT"


async def test_hard_cost_threshold(mock_pool: AsyncMock) -> None:
    """cost_usd > limit_cost_usd → Supervisor-tier approval."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    _stub_upsert(conn, tokens_total=100, cost_usd=2.0, duration_ms=10)  # ops cost limit = 1.0
    tracker, insert_spy = _build_tracker(mock_pool)

    await tracker.track(
        thread_id="t1",
        agent_id="operator-assistant",
        cluster="ops",
        step_input_tokens=10,
        step_output_tokens=10,
        step_cost_usd=2.0,
        step_duration_ms=10,
    )
    assert insert_spy.await_count == 1
    approval = insert_spy.await_args.args[0]
    assert approval.tier == Tier.SUPERVISOR
    assert approval.action_type == "BUDGET_EXHAUSTED"


async def test_soft_duration_threshold(mock_pool: AsyncMock) -> None:
    """duration_ms > limit_duration_s * 1000 → Operator-tier approval."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    # ops duration_s = 60 → 60000ms. Set above.
    _stub_upsert(conn, tokens_total=100, cost_usd=0.01, duration_ms=70_000)
    tracker, insert_spy = _build_tracker(mock_pool)

    await tracker.track(
        thread_id="t1",
        agent_id="operator-assistant",
        cluster="ops",
        step_input_tokens=10,
        step_output_tokens=10,
        step_cost_usd=0.01,
        step_duration_ms=70_000,
    )
    assert insert_spy.await_count == 1
    approval = insert_spy.await_args.args[0]
    assert approval.tier == Tier.OPERATOR


async def test_resolve_limits_agent_override(
    tmp_path: Path, mock_pool: AsyncMock
) -> None:
    """agents:<id> override beats cluster default."""
    yaml_content = textwrap.dedent(
        """
        ops:
          tokens: 50000
          cost_usd: 1.0
          duration_s: 60
        agents:
          operator-assistant:
            tokens: 100
            cost_usd: 0.01
            duration_s: 5
        """
    )
    yaml_path = tmp_path / "budgets.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")
    tracker, _ = _build_tracker(mock_pool, budgets_yaml_path=yaml_path)

    limits = tracker.resolve_limits(cluster="ops", agent_id="operator-assistant")
    assert limits.tokens == 100  # override wins
    # Different agent falls through to cluster default.
    limits2 = tracker.resolve_limits(cluster="ops", agent_id="other-agent")
    assert limits2.tokens == 50_000


async def test_resolve_limits_fallback() -> None:
    """Unknown cluster + unknown agent → fallback safe defaults."""
    # Use a yaml with no clusters at all.
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        fh.write("agents: {}\n")
        path = Path(fh.name)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock()
    queue = ApprovalQueueWriter(MagicMock())
    queue.insert = AsyncMock()  # type: ignore[method-assign]
    tracker = BudgetTracker(
        pool=MagicMock(), queue_writer=queue, budgets_yaml_path=path
    )
    limits = tracker.resolve_limits(cluster="unknown", agent_id="unknown")
    assert isinstance(limits, BudgetLimits)
    assert limits.tokens == 10_000  # fallback
    assert limits.cost_usd == 0.5
    assert limits.duration_s == 60


async def test_track_rejects_negative_deltas(mock_pool: AsyncMock) -> None:
    tracker, _ = _build_tracker(mock_pool)
    with pytest.raises(ValueError, match="non-negative"):
        await tracker.track(
            thread_id="t1",
            agent_id="x",
            cluster="ops",
            step_input_tokens=-1,
            step_output_tokens=0,
            step_cost_usd=0.0,
            step_duration_ms=0,
        )


async def test_track_uses_yaml_safe_load(mock_pool: AsyncMock) -> None:
    """BudgetTracker.__init__ does not blow up on the on-disk budgets.yaml."""
    tracker, _ = _build_tracker(mock_pool)
    # Smoke: at least one cluster default loaded.
    assert "ops" in tracker._cluster_defaults  # type: ignore[attr-defined]


async def test_budget_rejects_none_pool() -> None:
    with pytest.raises(ValueError, match="pool must not be None"):
        BudgetTracker(
            pool=None,
            queue_writer=MagicMock(),
        )
