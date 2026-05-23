"""Regression tests for WR-04: compute_pareto cumulative_percent uses grand total of ALL rows,
not just the trimmed top-N subset.

Plan 07-16 — Task 1 RED phase.
All tests must FAIL before Task 2 fixes oee.py.

Bug: oee.py line 320 computes grand_total = sum(r[1] for r in trimmed) where
trimmed = sorted_rows[:top_n]. This means cumulative_percent is computed relative
to only the top-N entries, not total downtime across all reason codes.

The last entry will always show cumulative_percent=100.0, misrepresenting Pareto coverage.

Fix (Task 2): grand_total = sum(r[1] for r in sorted_rows)  # ALL rows, before trimming.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# WR-04 regression: grand_total must use all rows, not trimmed rows
# ---------------------------------------------------------------------------


def test_cumulative_percent_uses_all_rows_total() -> None:
    """The last returned entry's cumulative_percent must reflect all rows, not just top-N.

    Setup: 4 rows totaling 100 min; top_n=2 selects rows covering 70 min.
    Expected last cumulative_percent: 70.0 (70/100 × 100).
    Bug (current code): grand_total = sum of trimmed rows = 70, so last entry = 100.0.
    After fix: grand_total = sum of all rows = 100, so last entry = 70.0.
    """
    from mnt_downtime_analyzer.oee import compute_pareto

    # 4 rows: top 2 = 50+20=70 min; remaining = 20+10=30 min; total = 100 min
    rows = [
        ("CODE-A", 50, 5),   # 50 min
        ("CODE-B", 20, 3),   # 20 min
        ("CODE-C", 20, 2),   # 20 min
        ("CODE-D", 10, 1),   # 10 min
    ]
    # top_n=2: trimmed = [CODE-A(50), CODE-B(20)] = 70 min out of 100 total
    result = compute_pareto(rows, top_n=2)

    assert len(result) == 2, f"Expected 2 entries, got {len(result)}"

    last_entry = result[-1]
    # The last (CODE-B) cumulative_percent should be 70/100 × 100 = 70.0
    # Bug: current code uses grand_total=70 → 70/70*100 = 100.0 (WRONG)
    # Fix: uses grand_total=100 → 70/100*100 = 70.0 (CORRECT)
    assert abs(last_entry.cumulative_percent - 70.0) < 0.1, (
        f"cumulative_percent of last Pareto entry (top_n=2 out of 4 rows totaling 100 min) "
        f"must be 70.0 (reflecting 70/100 total coverage), "
        f"got {last_entry.cumulative_percent}. "
        "WR-04: grand_total must use ALL sorted rows, not just the trimmed top-N."
    )


def test_cumulative_percent_last_entry_not_always_100() -> None:
    """When top-N entries do not cover all downtime, last entry must NOT be 100.0.

    If the Pareto top-3 of 5 rows covers 60% of total downtime, the last entry
    should show 60.0, not 100.0.
    """
    from mnt_downtime_analyzer.oee import compute_pareto

    # 5 rows: top 3 = 30+20+10=60 min; total = 30+20+10+7+3=70 min
    rows = [
        ("CODE-A", 30, 10),
        ("CODE-B", 20, 8),
        ("CODE-C", 10, 5),
        ("CODE-D", 7, 3),
        ("CODE-E", 3, 1),
    ]
    result = compute_pareto(rows, top_n=3)

    assert len(result) == 3
    last_pct = result[-1].cumulative_percent

    # top 3 cover 60/70 = 85.7%; bug would show 100.0
    expected_pct = 60.0 / 70.0 * 100.0  # ≈ 85.71

    assert abs(last_pct - expected_pct) < 0.5, (
        f"Expected last cumulative_percent ≈ {expected_pct:.2f} (60/70 total), "
        f"got {last_pct}. "
        "WR-04: grand_total must be computed from ALL rows before trimming."
    )
    # Crucially: it must NOT be 100.0
    assert abs(last_pct - 100.0) > 5.0, (
        f"last cumulative_percent must not be 100.0 when top-N doesn't cover all rows, "
        f"got {last_pct}. WR-04 regression."
    )


def test_cumulative_percent_monotonically_increasing_with_all_rows_total() -> None:
    """cumulative_percent must be monotonically non-decreasing, using all-rows total.

    With grand_total from all rows, each step adds proportional coverage.
    """
    from mnt_downtime_analyzer.oee import compute_pareto

    rows = [
        ("CODE-A", 40, 5),
        ("CODE-B", 30, 4),
        ("CODE-C", 20, 3),
        ("CODE-D", 10, 2),  # not in top_n=3
    ]
    result = compute_pareto(rows, top_n=3)

    assert len(result) == 3
    pcts = [e.cumulative_percent for e in result]

    # Must be monotonically non-decreasing
    for i in range(len(pcts) - 1):
        assert pcts[i] <= pcts[i + 1], (
            f"cumulative_percent not monotonic at index {i}: {pcts[i]} > {pcts[i+1]}"
        )

    # All values must be < 100.0 (since top-3 = 90 min out of 100 total)
    # Bug: with trimmed grand_total (=90), last entry would be 100.0
    # Fix: with all-rows grand_total (=100), last entry = 90/100*100 = 90.0
    last_pct = pcts[-1]
    assert abs(last_pct - 90.0) < 0.5, (
        f"Expected last cumulative_percent ≈ 90.0 (90/100 total), got {last_pct}. "
        "WR-04: grand_total from all rows makes top-3 show 90%, not 100%."
    )


def test_first_entry_cumulative_percent_correct_with_all_rows_total() -> None:
    """First Pareto entry cumulative_percent must also use all-rows grand_total.

    If the top entry has 50 min out of 200 total, its cumulative_percent = 25.0.
    With trimmed grand_total (top_n=5 sum), this would be different.
    """
    from mnt_downtime_analyzer.oee import compute_pareto

    # top_n=2, total_all = 50+30+20+20+80 = 200 min
    rows = [
        ("CODE-A", 50, 5),   # top-1
        ("CODE-B", 30, 4),   # top-2
        ("CODE-C", 20, 3),   # not in top-2
        ("CODE-D", 20, 2),   # not in top-2
        ("CODE-E", 80, 8),   # Wait, this would sort to first — adjust
    ]
    # After sort by total DESC: CODE-E(80), CODE-A(50), CODE-B(30), CODE-C(20), CODE-D(20)
    # top_n=2: CODE-E(80), CODE-A(50) = 130 min out of 200 total
    result = compute_pareto(rows, top_n=2)

    assert len(result) == 2
    assert result[0].reason_code == "CODE-E"

    # First entry: 80/200 × 100 = 40.0
    # Bug: grand_total from trimmed = 80+50 = 130 → 80/130*100 ≈ 61.5 (WRONG)
    # Fix: grand_total = 200 → 80/200*100 = 40.0 (CORRECT)
    first_pct = result[0].cumulative_percent
    assert abs(first_pct - 40.0) < 0.5, (
        f"Expected first entry cumulative_percent ≈ 40.0 (80/200 total), got {first_pct}. "
        "WR-04: grand_total must use all rows."
    )

    # Last entry: (80+50)/200 × 100 = 65.0
    last_pct = result[1].cumulative_percent
    assert abs(last_pct - 65.0) < 0.5, (
        f"Expected last entry cumulative_percent ≈ 65.0 (130/200 total), got {last_pct}. "
        "WR-04: grand_total must use all rows."
    )


def test_cumulative_percent_100_when_top_n_equals_all_rows() -> None:
    """When top_n >= total rows, last cumulative_percent must still be 100.0.

    This verifies the fix does not break the edge case where top-N covers everything.
    """
    from mnt_downtime_analyzer.oee import compute_pareto

    rows = [("CODE-A", 100, 5), ("CODE-B", 50, 3)]
    result = compute_pareto(rows, top_n=10)  # top_n > len(rows)

    assert len(result) == 2
    # grand_total from all rows = 150; top-2 = 150; last pct = 100.0
    last_pct = result[-1].cumulative_percent
    assert abs(last_pct - 100.0) < 0.01, (
        f"When top_n >= all rows, last cumulative_percent must be 100.0, got {last_pct}"
    )
