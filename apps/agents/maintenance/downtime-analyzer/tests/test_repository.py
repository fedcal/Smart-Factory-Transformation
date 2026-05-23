"""Tests for DowntimeEventRepository and QualityVerdictReader (plan 07-09).

TDD RED phase: all tests fail on ImportError until Task 2 implements the modules.

T-V5-sql gate: meta-test asserts no f-string / %s-style interpolation in SQL
ClassVar constants (Shared Pattern H).

Integration tests (``pytestmark integration+testcontainers``) are skipped
automatically when Docker is unavailable; unit-level SQL inspection tests run
always (no containers required).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

pytestmark = [pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# T-V5-sql meta-test (no Docker required — runs always)
# ---------------------------------------------------------------------------


def test_sql_uses_parameterization() -> None:
    """T-V5-sql gate: none of the SQL ClassVar constants use f-strings or %s.

    This is the formal parameterization guard described in Shared Pattern H.
    All SQL must use $1..$N asyncpg placeholders only.
    """
    from mnt_downtime_analyzer.repository import (
        DowntimeEventRepository,
        QualityVerdictReader,
    )

    sql_constants = [
        DowntimeEventRepository._SQL_INSERT,
        DowntimeEventRepository._SQL_FETCH_WINDOW,
        DowntimeEventRepository._SQL_PARETO,
        DowntimeEventRepository._SQL_VALIDATE_ASSET,
        QualityVerdictReader._SQL_QUALITY,
    ]
    forbidden_patterns = [
        r"%s",          # old-style string interpolation
        r"%\(",         # named old-style
        r"\{[^}]*\}",   # f-string or .format() placeholders (allows empty {} from format)
    ]
    for sql in sql_constants:
        for pat in forbidden_patterns:
            assert not re.search(pat, sql), (
                f"SQL contains forbidden interpolation pattern '{pat}':\n{sql}"
            )
        # Must contain at least one asyncpg placeholder
        assert re.search(r"\$\d+", sql), (
            f"SQL contains no asyncpg $N placeholder — suspicious:\n{sql}"
        )


def test_sql_constants_are_strings() -> None:
    """SQL ClassVar constants must be plain str (not None / callable)."""
    from mnt_downtime_analyzer.repository import (
        DowntimeEventRepository,
        QualityVerdictReader,
    )

    assert isinstance(DowntimeEventRepository._SQL_INSERT, str)
    assert isinstance(DowntimeEventRepository._SQL_FETCH_WINDOW, str)
    assert isinstance(DowntimeEventRepository._SQL_PARETO, str)
    assert isinstance(DowntimeEventRepository._SQL_VALIDATE_ASSET, str)
    assert isinstance(QualityVerdictReader._SQL_QUALITY, str)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    asset_id: str = "LOOM-01",
    reason_code: str = "WEAVING-BE-001",
    duration_min: int = 30,
    severity: str = "minor",
    event_id: str | None = None,
) -> "DowntimeEvent":  # type: ignore[name-defined]  # noqa: F821
    from sim_textile.downtime_event_generator import DowntimeEvent

    return DowntimeEvent(
        event_id=event_id or str(uuid4()),
        asset_id=asset_id,
        reason_code=reason_code,
        duration_min=duration_min,
        severity=severity,  # type: ignore[arg-type]
        work_order_id=None,
        dye_lot_id=None,
        source="simulator",
        timestamp=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Integration tests (testcontainers PG — skipped when Docker unavailable)
# ---------------------------------------------------------------------------

pytestmark_integration = [
    pytest.mark.integration,
    pytest.mark.testcontainers,
    pytest.mark.asyncio,
]


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_insert_event_and_select_confirms_row(fresh_pg) -> None:
    """insert_event persists a DowntimeEvent; SELECT confirms row presence."""
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    event = _make_event()
    await repo.insert_event(event)

    async with fresh_pg.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM maintenance.downtime_events WHERE event_id = $1",
            event.event_id,
        )
    assert row is not None
    assert row["asset_id"] == event.asset_id
    assert row["reason_code"] == event.reason_code
    assert row["duration_min"] == event.duration_min
    assert row["severity"] == event.severity
    assert row["source"] == event.source


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_insert_event_idempotent(fresh_pg) -> None:
    """Inserting same event twice results in exactly 1 row (ON CONFLICT DO NOTHING)."""
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    event = _make_event()
    await repo.insert_event(event)
    await repo.insert_event(event)  # second insert must be idempotent

    async with fresh_pg.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM maintenance.downtime_events WHERE event_id = $1",
            event.event_id,
        )
    assert count == 1


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_fetch_window_returns_events_in_range(fresh_pg) -> None:
    """fetch_window returns DowntimeEvent list for the given time window."""
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    now = datetime.now(UTC)
    event = _make_event()
    await repo.insert_event(event)

    results = await repo.fetch_window(now - timedelta(minutes=5), now + timedelta(minutes=5))
    assert len(results) >= 1
    event_ids = [e.event_id for e in results]
    assert event.event_id in event_ids


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_fetch_window_empty_returns_empty_list(fresh_pg) -> None:
    """fetch_window with no rows in range returns empty list."""
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    past = datetime.now(UTC) - timedelta(days=365)
    results = await repo.fetch_window(past - timedelta(hours=1), past)
    assert results == []


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_fetch_window_asset_id_filter(fresh_pg) -> None:
    """fetch_window with asset_id returns only events for that asset."""
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    now = datetime.now(UTC)
    event_a = _make_event(asset_id="LOOM-01")
    event_b = _make_event(asset_id="LOOM-02")
    await repo.insert_event(event_a)
    await repo.insert_event(event_b)

    results = await repo.fetch_window(
        now - timedelta(minutes=5), now + timedelta(minutes=5), asset_id="LOOM-01"
    )
    returned_asset_ids = {e.asset_id for e in results}
    assert "LOOM-01" in returned_asset_ids
    assert "LOOM-02" not in returned_asset_ids


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_validate_asset_exists_true(fresh_pg) -> None:
    """validate_asset_exists returns True for a known asset (LOOM-01)."""
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    result = await repo.validate_asset_exists("LOOM-01")
    assert result is True


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_validate_asset_exists_false_for_unknown(fresh_pg) -> None:
    """validate_asset_exists returns False for an unknown asset id."""
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    result = await repo.validate_asset_exists("GHOST-99")
    assert result is False


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_pareto_returns_sorted_by_total_downtime(fresh_pg) -> None:
    """pareto() returns tuples sorted DESC by total_min; ordering matches expected."""
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    now = datetime.now(UTC)

    # Seed 3 reason_codes with different totals
    events = [
        _make_event(reason_code="WEAVING-BE-001", duration_min=60),
        _make_event(reason_code="WEAVING-BE-001", duration_min=40),   # total=100
        _make_event(reason_code="SPINNING-BE-001", duration_min=50),  # total=50
        _make_event(reason_code="DYEING-DL-001", duration_min=20),    # total=20
    ]
    for ev in events:
        await repo.insert_event(ev)

    rows = await repo.pareto(
        now - timedelta(minutes=5), now + timedelta(minutes=5), top_n=10
    )
    assert len(rows) == 3
    assert rows[0][0] == "WEAVING-BE-001"
    assert rows[0][1] == 100  # total_min
    assert rows[1][0] == "SPINNING-BE-001"
    assert rows[2][0] == "DYEING-DL-001"
    # Verify descending order
    totals = [r[1] for r in rows]
    assert totals == sorted(totals, reverse=True)


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_pareto_respects_top_n(fresh_pg) -> None:
    """pareto() with top_n=2 returns at most 2 entries."""
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    now = datetime.now(UTC)

    for i in range(5):
        await repo.insert_event(_make_event(reason_code=f"CODE-{i:02d}", duration_min=10 * (5 - i)))

    rows = await repo.pareto(now - timedelta(minutes=5), now + timedelta(minutes=5), top_n=2)
    assert len(rows) <= 2


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_quality_verdict_reader_returns_parsed_values(fresh_pg) -> None:
    """QualityVerdictReader returns (good_sum, total_sum) from seeded audit rows."""
    from mnt_downtime_analyzer.repository import QualityVerdictReader

    reader = QualityVerdictReader(pool=fresh_pg)
    now = datetime.now(UTC)

    # Seed an audit.actions row with QUALITY_VERDICT evidence_panel
    evidence = {
        "tool_calls": [
            {
                "name": "grade_quality_event",
                "args": {"asset_id": "LOOM-01"},
                "result": {"good_parts": 950, "total_parts": 1000},
                "duration_ms": 0,
                "ts": now.isoformat(),
            }
        ],
        "asset_id": "LOOM-01",
        "input_summary": "test",
        "input_truncated": False,
        "rag_citations": [],
        "confidence": 1.0,
        "model": "log-only@quality-inspector",
        "prompt_hash": "0" * 64,
        "tokens": {"input": 0, "output": 0, "total": 0},
        "duration_ms": 0,
    }

    import json

    async with fresh_pg.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit.actions
              (id, ts, action_id, agent_id, thread_id, cluster,
               action_type, evidence_panel, decision, decision_actor,
               motivation, budget_snapshot, approval_id)
            VALUES
              ($1, $2, $3, $4, $5, $6,
               'QUALITY_VERDICT', $7::jsonb, 'auto', NULL,
               NULL, '{}'::jsonb, NULL)
            """,
            str(uuid4()),
            now,
            str(uuid4()),
            "quality-inspector",
            "ops.quality-inspector.test",
            "ops",
            json.dumps(evidence),
        )

    good_sum, total_sum = await reader.fetch_quality_metrics(
        "LOOM-01", now - timedelta(minutes=5), now + timedelta(minutes=5)
    )
    assert good_sum == 950
    assert total_sum == 1000


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_quality_verdict_reader_empty_window_returns_zero_tuple(fresh_pg) -> None:
    """QualityVerdictReader returns (0, 0) when no audit rows in window."""
    from mnt_downtime_analyzer.repository import QualityVerdictReader

    reader = QualityVerdictReader(pool=fresh_pg)
    past = datetime.now(UTC) - timedelta(days=365)
    good_sum, total_sum = await reader.fetch_quality_metrics(
        "LOOM-01", past - timedelta(hours=1), past
    )
    assert good_sum == 0
    assert total_sum == 0


@pytest.mark.integration
@pytest.mark.testcontainers
async def test_sql_injection_probe_fetch_window(fresh_pg) -> None:
    """SQL injection probe: malicious asset_id is neutralized by asyncpg parameterization.

    Passes a value containing SQL-injection syntax as asset_id; asyncpg parameter
    substitution neutralizes it. The query returns empty (no exception, no drop).
    This is a defense-in-depth test and must not be removed.
    """
    from mnt_downtime_analyzer.repository import DowntimeEventRepository

    repo = DowntimeEventRepository(pool=fresh_pg)
    now = datetime.now(UTC)
    malicious_asset_id = "'; DROP TABLE maintenance.downtime_events; --"

    # Should not raise, should return empty list
    results = await repo.fetch_window(
        now - timedelta(minutes=5), now + timedelta(minutes=5),
        asset_id=malicious_asset_id,
    )
    assert isinstance(results, list)
    assert len(results) == 0

    # Table must still exist
    async with fresh_pg.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM maintenance.downtime_events"
        )
    assert count is not None  # table still exists
