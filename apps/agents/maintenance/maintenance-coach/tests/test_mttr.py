"""Unit tests for MTTR computation helpers (mnt_maintenance_coach.mttr).

All tests in this module are pure unit tests — no I/O, no network, no DB.
They verify:
  - compute_mttr_minutes(state) -> int | None
  - compute_active_work_minutes(state) -> int
  - CoachThreadState + StepReport Pydantic validation edge cases

RED phase: all tests fail via ImportError until Task 2 implements the modules.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers for building test fixtures
# ---------------------------------------------------------------------------


def _make_step_report(**overrides: Any) -> dict[str, Any]:
    """Return a minimal valid StepReport dict."""
    base: dict[str, Any] = {
        "step_no": 0,
        "instruction": "Disconnect power supply",
        "technician_input": "Done, power is off",
        "duration_minutes": 10,
        "completed_at": datetime(2026, 5, 23, 8, 10, tzinfo=UTC),
        "citations": [],
    }
    base.update(overrides)
    return base


def _make_state(
    *,
    mttr_start: datetime | None = None,
    mttr_end: datetime | None = None,
    completed_steps: list[dict[str, Any]] | None = None,
    as_dict: bool = False,
) -> Any:
    """Return either a CoachThreadState instance or a plain dict."""
    from mnt_maintenance_coach.models import CoachThreadState, StepReport

    if mttr_start is None:
        mttr_start = datetime(2026, 5, 23, 8, 0, tzinfo=UTC)

    steps_raw = completed_steps if completed_steps is not None else []
    steps = [StepReport(**s) for s in steps_raw]

    if as_dict:
        return {
            "intervention_id": "test-001",
            "asset_id": "LOOM-01",
            "sop_id": "SOP-LOOM-001",
            "technician_id": "TECH-42",
            "current_step": len(steps),
            "completed_steps": [s.model_dump() for s in steps],
            "messages": [],
            "mttr_start": mttr_start,
            "mttr_end": mttr_end,
        }

    return CoachThreadState(
        intervention_id="test-001",
        asset_id="LOOM-01",
        sop_id="SOP-LOOM-001",
        technician_id="TECH-42",
        current_step=len(steps),
        completed_steps=steps,
        messages=[],
        mttr_start=mttr_start,
        mttr_end=mttr_end,
    )


# ---------------------------------------------------------------------------
# compute_mttr_minutes — basic cases
# ---------------------------------------------------------------------------


class TestComputeMttrMinutes:
    def test_returns_int_when_end_set(self) -> None:
        """compute_mttr_minutes returns int = (end - start).total_seconds() // 60."""
        from mnt_maintenance_coach.mttr import compute_mttr_minutes

        start = datetime(2026, 5, 23, 8, 0, tzinfo=UTC)
        end = datetime(2026, 5, 23, 9, 30, tzinfo=UTC)  # 90 min
        state = _make_state(mttr_start=start, mttr_end=end)
        result = compute_mttr_minutes(state)
        assert result == 90

    def test_returns_none_when_end_not_set(self) -> None:
        """compute_mttr_minutes returns None if mttr_end is None (intervention open)."""
        from mnt_maintenance_coach.mttr import compute_mttr_minutes

        state = _make_state(mttr_end=None)
        assert compute_mttr_minutes(state) is None

    def test_raises_on_negative_mttr(self) -> None:
        """compute_mttr_minutes raises ValueError if mttr_end < mttr_start (clock skew)."""
        from mnt_maintenance_coach.mttr import compute_mttr_minutes

        start = datetime(2026, 5, 23, 9, 0, tzinfo=UTC)
        end = datetime(2026, 5, 23, 8, 0, tzinfo=UTC)  # 1 hour before start
        state = _make_state(mttr_start=start, mttr_end=end)
        with pytest.raises(ValueError, match="mttr_end"):
            compute_mttr_minutes(state)

    def test_cross_shift_simulation(self) -> None:
        """Cross-shift: 2026-05-23 08:00 -> 2026-05-24 14:00 = 30h = 1800 min."""
        from mnt_maintenance_coach.mttr import compute_mttr_minutes

        start = datetime(2026, 5, 23, 8, 0, tzinfo=UTC)
        end = datetime(2026, 5, 24, 14, 0, tzinfo=UTC)
        state = _make_state(mttr_start=start, mttr_end=end)
        assert compute_mttr_minutes(state) == 1800

    def test_accepts_dict_shape(self) -> None:
        """compute_mttr_minutes accepts dict (checkpoint replay may yield dict)."""
        from mnt_maintenance_coach.mttr import compute_mttr_minutes

        start = datetime(2026, 5, 23, 8, 0, tzinfo=UTC)
        end = datetime(2026, 5, 23, 10, 0, tzinfo=UTC)  # 120 min
        state_dict = _make_state(mttr_start=start, mttr_end=end, as_dict=True)
        assert compute_mttr_minutes(state_dict) == 120

    def test_exact_minute_boundary(self) -> None:
        """Exactly 45 minutes returns 45 (not 44 due to floor)."""
        from mnt_maintenance_coach.mttr import compute_mttr_minutes

        start = datetime(2026, 5, 23, 8, 0, tzinfo=UTC)
        end = start + timedelta(minutes=45)
        state = _make_state(mttr_start=start, mttr_end=end)
        assert compute_mttr_minutes(state) == 45


# ---------------------------------------------------------------------------
# compute_active_work_minutes — basic cases
# ---------------------------------------------------------------------------


class TestComputeActiveWorkMinutes:
    def test_empty_steps_returns_zero(self) -> None:
        """No completed steps -> 0 active work minutes."""
        from mnt_maintenance_coach.mttr import compute_active_work_minutes

        state = _make_state(completed_steps=[])
        assert compute_active_work_minutes(state) == 0

    def test_sums_duration_minutes(self) -> None:
        """Active work = sum of completed_steps[*].duration_minutes."""
        from mnt_maintenance_coach.mttr import compute_active_work_minutes

        steps = [
            _make_step_report(step_no=0, duration_minutes=15),
            _make_step_report(step_no=1, duration_minutes=20),
            _make_step_report(step_no=2, duration_minutes=5),
        ]
        state = _make_state(completed_steps=steps)
        assert compute_active_work_minutes(state) == 40

    def test_zero_duration_steps(self) -> None:
        """Steps with duration_minutes=0 contribute 0 to active work."""
        from mnt_maintenance_coach.mttr import compute_active_work_minutes

        steps = [_make_step_report(step_no=i, duration_minutes=0) for i in range(5)]
        state = _make_state(completed_steps=steps)
        assert compute_active_work_minutes(state) == 0

    def test_cross_shift_mttr_vs_active_work(self) -> None:
        """MTTR (1800) >> active_work (120) demonstrates pause-inclusive vs active-only."""
        from mnt_maintenance_coach.mttr import (
            compute_active_work_minutes,
            compute_mttr_minutes,
        )

        start = datetime(2026, 5, 23, 8, 0, tzinfo=UTC)
        end = datetime(2026, 5, 24, 14, 0, tzinfo=UTC)  # 1800 min
        steps = [_make_step_report(step_no=i, duration_minutes=15) for i in range(8)]  # 120 min
        state = _make_state(mttr_start=start, mttr_end=end, completed_steps=steps)
        assert compute_mttr_minutes(state) == 1800
        assert compute_active_work_minutes(state) == 120
        assert compute_mttr_minutes(state) > compute_active_work_minutes(state)  # type: ignore[operator]


# ---------------------------------------------------------------------------
# CoachThreadState Pydantic validation
# ---------------------------------------------------------------------------


class TestCoachThreadStateValidation:
    def test_requires_tz_aware_mttr_start(self) -> None:
        """Naive datetime for mttr_start raises ValidationError."""
        from mnt_maintenance_coach.models import CoachThreadState

        with pytest.raises(ValidationError, match="tz-aware|timezone"):
            CoachThreadState(
                intervention_id="test-001",
                asset_id="LOOM-01",
                sop_id="SOP-001",
                technician_id="TECH-1",
                current_step=0,
                completed_steps=[],
                messages=[],
                mttr_start=datetime(2026, 5, 23, 8, 0),  # naive — no tzinfo
                mttr_end=None,
            )

    def test_step_report_duration_cap(self) -> None:
        """StepReport.duration_minutes > 10080 (1 week) raises ValidationError."""
        from mnt_maintenance_coach.models import StepReport

        with pytest.raises(ValidationError):
            StepReport(
                step_no=0,
                instruction="Some instruction",
                technician_input="Input from tech",
                duration_minutes=10081,  # exceeds le=10080
                completed_at=datetime(2026, 5, 23, 8, 0, tzinfo=UTC),
                citations=[],
            )

    def test_step_report_valid_at_cap(self) -> None:
        """StepReport.duration_minutes = 10080 (exactly 1 week) is valid."""
        from mnt_maintenance_coach.models import StepReport

        report = StepReport(
            step_no=0,
            instruction="Some instruction",
            technician_input="Done",
            duration_minutes=10080,
            completed_at=datetime(2026, 5, 23, 8, 0, tzinfo=UTC),
            citations=[],
        )
        assert report.duration_minutes == 10080
