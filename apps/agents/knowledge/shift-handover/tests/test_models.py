"""Unit tests for ShiftWindow + HandoverReport Pydantic models (TDD - plan 08-02, Task 1).

Contracts:
- ShiftWindow rejects naive datetime (tz-aware validator, Pattern S-6).
- ShiftWindow rejects shift_end <= shift_start (model_validator).
- HandoverReport carries citations: list[RagCitation] (TRN-05).
- All models are frozen (ConfigDict frozen=True, extra="forbid").
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# ShiftWindow tests
# ---------------------------------------------------------------------------


def test_shiftwindow_rejects_naive_shift_start() -> None:
    """ShiftWindow raises ValidationError when shift_start is naive (no tzinfo)."""
    from trn_shift_handover.models import ShiftWindow

    naive_start = datetime(2024, 1, 15, 6, 0, 0)
    aware_end = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError):
        ShiftWindow(
            shift_start=naive_start,
            shift_end=aware_end,
            boundary_label="06:00-14:00",
        )


def test_shiftwindow_rejects_naive_shift_end() -> None:
    """ShiftWindow raises ValidationError when shift_end is naive (no tzinfo)."""
    from trn_shift_handover.models import ShiftWindow

    aware_start = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
    naive_end = datetime(2024, 1, 15, 14, 0, 0)

    with pytest.raises(ValidationError):
        ShiftWindow(
            shift_start=aware_start,
            shift_end=naive_end,
            boundary_label="06:00-14:00",
        )


def test_shiftwindow_rejects_end_before_start() -> None:
    """ShiftWindow raises ValidationError when shift_end <= shift_start."""
    from trn_shift_handover.models import ShiftWindow

    start = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError):
        ShiftWindow(
            shift_start=start,
            shift_end=end,
            boundary_label="14:00-06:00",
        )


def test_shiftwindow_rejects_equal_start_end() -> None:
    """ShiftWindow raises ValidationError when shift_end == shift_start."""
    from trn_shift_handover.models import ShiftWindow

    ts = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError):
        ShiftWindow(
            shift_start=ts,
            shift_end=ts,
            boundary_label="06:00-06:00",
        )


def test_shiftwindow_accepts_valid_tz_aware_window() -> None:
    """ShiftWindow accepts valid tz-aware shift window."""
    from trn_shift_handover.models import ShiftWindow

    start = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
    window = ShiftWindow(
        shift_start=start,
        shift_end=end,
        boundary_label="06:00-14:00",
    )
    assert window.shift_start == start
    assert window.shift_end == end
    assert window.boundary_label == "06:00-14:00"


def test_shiftwindow_is_frozen() -> None:
    """ShiftWindow is immutable (frozen=True)."""
    from trn_shift_handover.models import ShiftWindow

    start = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
    window = ShiftWindow(
        shift_start=start,
        shift_end=end,
        boundary_label="06:00-14:00",
    )
    with pytest.raises((ValidationError, TypeError)):
        window.boundary_label = "mutated"  # type: ignore[misc]


def test_shiftwindow_rejects_extra_fields() -> None:
    """ShiftWindow raises ValidationError for extra fields (extra='forbid')."""
    from trn_shift_handover.models import ShiftWindow

    start = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError):
        ShiftWindow(
            shift_start=start,
            shift_end=end,
            boundary_label="06:00-14:00",
            unexpected_field="boom",  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# HandoverReport tests
# ---------------------------------------------------------------------------


def _make_rag_citation() -> "RagCitation":
    from sft_agents.models.evidence import RagCitation

    return RagCitation(
        source_uri="urn:sft:sop:loom-startup-v2",
        snippet="Procedura di avvio telaio: verificare tensione ordito prima di avviare.",
        score=0.92,
        retrieved_at=datetime(2024, 1, 15, 7, 30, 0, tzinfo=timezone.utc),
    )


def _make_valid_handover_report() -> dict:
    return {
        "shift_start": datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc),
        "shift_end": datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
        "boundary_label": "06:00-14:00",
        "open_alerts": 2,
        "completed_work_orders": 5,
        "downtime_events": 1,
        "quality_events": 3,
        "equipment_status": {"loom-01": "running", "loom-02": "maintenance"},
        "narrative_summary": "Turno mattina regolare con 1 fermo non programmato.",
        "source_events": [],
        "citations": [],
    }


def test_handover_report_has_citations_field() -> None:
    """HandoverReport has a citations field typed list[RagCitation]."""
    from trn_shift_handover.models import HandoverReport
    from sft_agents.models.evidence import RagCitation

    data = _make_valid_handover_report()
    citation = _make_rag_citation()
    data["citations"] = [citation]

    report = HandoverReport(**data)
    assert len(report.citations) == 1
    assert isinstance(report.citations[0], RagCitation)
    assert report.citations[0].source_uri == "urn:sft:sop:loom-startup-v2"


def test_handover_report_citations_empty_by_default() -> None:
    """HandoverReport.citations defaults to empty list (no citations required)."""
    from trn_shift_handover.models import HandoverReport

    data = _make_valid_handover_report()
    report = HandoverReport(**data)
    assert report.citations == []


def test_handover_report_has_count_fields() -> None:
    """HandoverReport carries open_alerts, completed_work_orders, downtime_events, quality_events."""
    from trn_shift_handover.models import HandoverReport

    data = _make_valid_handover_report()
    report = HandoverReport(**data)
    assert report.open_alerts == 2
    assert report.completed_work_orders == 5
    assert report.downtime_events == 1
    assert report.quality_events == 3


def test_handover_report_equipment_status_is_dict() -> None:
    """HandoverReport.equipment_status is a dict[str, str]."""
    from trn_shift_handover.models import HandoverReport

    data = _make_valid_handover_report()
    report = HandoverReport(**data)
    assert isinstance(report.equipment_status, dict)
    assert report.equipment_status["loom-01"] == "running"


def test_handover_report_is_frozen() -> None:
    """HandoverReport is immutable (frozen=True)."""
    from trn_shift_handover.models import HandoverReport

    data = _make_valid_handover_report()
    report = HandoverReport(**data)
    with pytest.raises((ValidationError, TypeError)):
        report.open_alerts = 99  # type: ignore[misc]


def test_handover_report_rejects_extra_fields() -> None:
    """HandoverReport raises ValidationError for extra fields (extra='forbid')."""
    from trn_shift_handover.models import HandoverReport

    data = _make_valid_handover_report()
    data["unknown_field"] = "surprise"

    with pytest.raises(ValidationError):
        HandoverReport(**data)


def test_handover_report_multiple_citations() -> None:
    """HandoverReport accepts multiple RagCitation entries (TRN-05 multi-source)."""
    from trn_shift_handover.models import HandoverReport
    from sft_agents.models.evidence import RagCitation

    citation1 = _make_rag_citation()
    citation2 = RagCitation(
        source_uri="urn:sft:sop:dyeing-bath-v1",
        snippet="Bagno di tintura: verificare pH prima dell'avvio.",
        score=0.88,
        retrieved_at=datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc),
    )

    data = _make_valid_handover_report()
    data["citations"] = [citation1, citation2]

    report = HandoverReport(**data)
    assert len(report.citations) == 2
    assert all(isinstance(c, RagCitation) for c in report.citations)
