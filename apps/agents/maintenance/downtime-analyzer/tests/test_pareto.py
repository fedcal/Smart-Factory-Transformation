"""Tests for Pareto computation (plan 07-09, D-DA-03).

TDD RED phase: tests fail until Task 3 implements compute_pareto in oee.py.
All tests are pure unit (no Docker / testcontainers required).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# compute_pareto unit tests
# ---------------------------------------------------------------------------


def test_pareto_empty_input_returns_empty_list() -> None:
    """compute_pareto([]) returns []."""
    from mnt_downtime_analyzer.oee import compute_pareto

    result = compute_pareto([])
    assert result == []


def test_pareto_two_entries_correct_ordering_and_cumulative() -> None:
    """compute_pareto with 2 entries: A=100,5 / B=50,3 -> A first, cumulative correct."""
    from mnt_downtime_analyzer.oee import compute_pareto

    rows = [("WEAVING-A", 100, 5), ("SPINNING-B", 50, 3)]
    result = compute_pareto(rows, top_n=10)

    assert len(result) == 2
    assert result[0].reason_code == "WEAVING-A"
    assert result[0].total_downtime_min == 100
    assert result[0].occurrence_count == 5
    # cumulative_percent for first entry: 100/150 * 100 = 66.666...
    expected_first = 100.0 / 150.0 * 100.0
    assert abs(result[0].cumulative_percent - expected_first) < 0.01

    assert result[1].reason_code == "SPINNING-B"
    assert result[1].cumulative_percent == pytest.approx(100.0, abs=0.01)


def test_pareto_cumulative_monotonically_increasing() -> None:
    """cumulative_percent is monotonically non-decreasing across entries."""
    from mnt_downtime_analyzer.oee import compute_pareto

    rows = [
        ("CODE-A", 200, 10),
        ("CODE-B", 150, 8),
        ("CODE-C", 100, 5),
        ("CODE-D", 50, 3),
    ]
    result = compute_pareto(rows, top_n=10)
    assert len(result) == 4
    for i in range(len(result) - 1):
        assert result[i].cumulative_percent <= result[i + 1].cumulative_percent, (
            f"Not monotonic at index {i}: {result[i].cumulative_percent} > {result[i+1].cumulative_percent}"
        )


def test_pareto_top_n_trim() -> None:
    """compute_pareto with 3 rows + top_n=2 returns only top 2 entries."""
    from mnt_downtime_analyzer.oee import compute_pareto

    rows = [("CODE-A", 300, 5), ("CODE-B", 200, 4), ("CODE-C", 100, 3)]
    result = compute_pareto(rows, top_n=2)
    assert len(result) == 2
    assert result[0].reason_code == "CODE-A"
    assert result[1].reason_code == "CODE-B"


def test_pareto_top_n_zero_returns_empty_list() -> None:
    """compute_pareto with top_n=0 returns empty list defensively."""
    from mnt_downtime_analyzer.oee import compute_pareto

    rows = [("CODE-A", 100, 5)]
    result = compute_pareto(rows, top_n=0)
    assert result == []


def test_pareto_report_request_top_n_zero_raises_validation_error() -> None:
    """ReportRequest with top_n_pareto=0 raises ValidationError (Field ge=1 constraint)."""
    from pydantic import ValidationError

    from mnt_downtime_analyzer.models import ReportRequest
    from datetime import UTC, datetime

    with pytest.raises(ValidationError):
        ReportRequest(
            window_start=datetime(2026, 1, 1, tzinfo=UTC),
            window_end=datetime(2026, 1, 1, 1, tzinfo=UTC),
            top_n_pareto=0,  # invalid — ge=1 required
        )


def test_pareto_ordered_by_total_downtime_desc() -> None:
    """Order is total_downtime_min DESC; occurrence_count breaks ties."""
    from mnt_downtime_analyzer.oee import compute_pareto

    rows = [
        ("CODE-LOW", 50, 10),
        ("CODE-HIGH", 200, 2),
        ("CODE-MED", 100, 5),
    ]
    result = compute_pareto(rows, top_n=10)
    totals = [e.total_downtime_min for e in result]
    assert totals == sorted(totals, reverse=True)


def test_pareto_entries_pass_pydantic_validation() -> None:
    """All ParetoEntry fields pass Pydantic validation (reason_code regex, etc.)."""
    from mnt_downtime_analyzer.oee import compute_pareto

    rows = [("WEAVING-BE-001", 100, 5), ("SPINNING-SA-002", 50, 3)]
    result = compute_pareto(rows)
    for entry in result:
        assert entry.reason_code  # non-empty
        assert entry.total_downtime_min >= 0
        assert entry.occurrence_count >= 0
        assert 0.0 <= entry.cumulative_percent <= 100.0


def test_pareto_bad_reason_code_raises_validation_error() -> None:
    """ParetoEntry with lowercase reason_code raises ValidationError."""
    from pydantic import ValidationError

    from mnt_downtime_analyzer.models import ParetoEntry

    with pytest.raises(ValidationError):
        ParetoEntry(
            reason_code="lowercase-code",  # fails ^[A-Z][A-Z0-9-]+$
            total_downtime_min=100,
            occurrence_count=5,
            cumulative_percent=50.0,
        )


def test_pareto_round_trip_json() -> None:
    """ParetoEntry.model_dump_json() is parseable back to ParetoEntry."""
    from mnt_downtime_analyzer.oee import compute_pareto
    from mnt_downtime_analyzer.models import ParetoEntry

    rows = [("WEAVING-BE-001", 100, 5)]
    result = compute_pareto(rows)

    for entry in result:
        json_str = entry.model_dump_json()
        parsed = ParetoEntry.model_validate_json(json_str)
        assert parsed.reason_code == entry.reason_code
        assert parsed.total_downtime_min == entry.total_downtime_min
