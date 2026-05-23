"""Test dei modelli OPS Pydantic (D-QI-01..04, D-PP-03, D-AD-02).

Copre:
- Anomaly + AnomalyBaseline (D-AD-02)
- QualityEvent + QualityVerdict + DefectType + Severity (D-QI-01..04)
- OrderSpec + AssetCapacity + ScheduleDraft + ScheduleDraftItem (D-PP-03)
- OpsState TypedDict (LangGraph subgraph)

Tutti i modelli sono frozen=True, extra='forbid', e rifiutano datetime naive (Pitfall 7).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import get_type_hints

import pytest
from pydantic import ValidationError

from sft_domain.ops import (
    Anomaly,
    AnomalyBaseline,
    AssetCapacity,
    DefectType,
    OpsState,
    OrderSpec,
    QualityEvent,
    QualityVerdict,
    RagCitation,
    ScheduleDraft,
    ScheduleDraftItem,
    Severity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year: int = 2026, month: int = 5, day: int = 23, hour: int = 8) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def _citation(score: float = 0.9) -> RagCitation:
    return RagCitation(
        source_uri="sop://SOP-QLT-001",
        snippet="ASTM D5430 four-point rule excerpt.",
        score=score,
        retrieved_at=_utc(),
    )


# ===========================================================================
# Anomaly
# ===========================================================================


class TestAnomaly:
    def test_minimal_valid_anomaly(self) -> None:
        a = Anomaly(
            asset_id="LOOM-01",
            sensor_id="warp_tension",
            value=1.2,
            baseline_low=0.0,
            baseline_high=0.8,
            timestamp=_utc(),
            severity="major",
        )
        assert a.asset_id == "LOOM-01"
        assert a.severity == "major"
        # UUID factory assigned a default id
        assert a.id is not None

    def test_anomaly_is_frozen(self) -> None:
        a = Anomaly(
            asset_id="LOOM-01",
            sensor_id="warp_tension",
            value=1.0,
            baseline_low=0.0,
            baseline_high=0.8,
            timestamp=_utc(),
            severity="minor",
        )
        with pytest.raises(ValidationError):
            a.asset_id = "LOOM-02"  # type: ignore[misc]

    def test_anomaly_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Anomaly(
                asset_id="LOOM-01",
                sensor_id="warp_tension",
                value=1.0,
                baseline_low=0.0,
                baseline_high=0.8,
                timestamp=_utc(),
                severity="minor",
                bogus="x",  # type: ignore[call-arg]
            )

    def test_anomaly_rejects_naive_datetime(self) -> None:
        with pytest.raises(ValidationError):
            Anomaly(
                asset_id="LOOM-01",
                sensor_id="warp_tension",
                value=1.0,
                baseline_low=0.0,
                baseline_high=0.8,
                timestamp=datetime(2026, 5, 23, 8),  # naive
                severity="minor",
            )

    def test_anomaly_severity_literal_enforced(self) -> None:
        with pytest.raises(ValidationError):
            Anomaly(
                asset_id="LOOM-01",
                sensor_id="warp_tension",
                value=1.0,
                baseline_low=0.0,
                baseline_high=0.8,
                timestamp=_utc(),
                severity="catastrophic",  # type: ignore[arg-type]
            )


# ===========================================================================
# AnomalyBaseline
# ===========================================================================


class TestAnomalyBaseline:
    def _baseline(self) -> AnomalyBaseline:
        return AnomalyBaseline(
            asset_family="loom",
            sensor_id="warp_tension",
            low=0.0,
            high=0.8,
            unit="g",
            severity_mapping={"minor": 0.1, "major": 0.3, "critical": 0.6},
        )

    def test_is_within_band(self) -> None:
        b = self._baseline()
        assert b.is_within_band(0.5) is True
        assert b.is_within_band(-0.1) is False
        assert b.is_within_band(0.9) is False

    def test_severity_for_minor(self) -> None:
        b = self._baseline()
        # deviation = 0.05 above high band edge -> minor
        assert b.severity_for(0.85) == "minor"

    def test_severity_for_major(self) -> None:
        b = self._baseline()
        # deviation = 0.32 -> major
        assert b.severity_for(1.12) == "major"

    def test_severity_for_critical(self) -> None:
        b = self._baseline()
        # deviation = 0.7 -> critical
        assert b.severity_for(1.5) == "critical"

    def test_yaml_roundtrip(self) -> None:
        payload = {
            "asset_family": "loom",
            "sensor_id": "warp_tension",
            "low": 0.0,
            "high": 0.8,
            "unit": "g",
            "severity_mapping": {"minor": 0.1, "major": 0.3, "critical": 0.6},
        }
        b = AnomalyBaseline.model_validate(payload)
        assert b.high == 0.8


# ===========================================================================
# QualityEvent
# ===========================================================================


class TestQualityEvent:
    def _kwargs(self) -> dict:
        return dict(
            asset_id="LOOM-01",
            dye_lot_id="DL-LOOM-01-20260523-a3",
            defect_type="broken_end",
            defect_length_inches=3.5,
            full_width=False,
            position_meters=12.5,
            timestamp=_utc(),
            source="simulator",
        )

    def test_minimal_valid_event(self) -> None:
        e = QualityEvent(**self._kwargs())
        assert e.dye_lot_id == "DL-LOOM-01-20260523-a3"
        assert e.event_id is not None

    def test_dye_lot_id_pattern_accepts_canonical(self) -> None:
        kwargs = self._kwargs()
        kwargs["dye_lot_id"] = "DL-SPIN-04-20260523-fe9a"
        e = QualityEvent(**kwargs)
        assert "SPIN" in e.dye_lot_id

    def test_dye_lot_id_pattern_rejects_invalid(self) -> None:
        kwargs = self._kwargs()
        kwargs["dye_lot_id"] = "BAD-LOT-1"
        with pytest.raises(ValidationError):
            QualityEvent(**kwargs)

    def test_defect_type_literal_enforced(self) -> None:
        kwargs = self._kwargs()
        kwargs["defect_type"] = "scratch"  # not in 7-defect taxonomy
        with pytest.raises(ValidationError):
            QualityEvent(**kwargs)

    def test_rejects_naive_timestamp(self) -> None:
        kwargs = self._kwargs()
        kwargs["timestamp"] = datetime(2026, 5, 23)
        with pytest.raises(ValidationError):
            QualityEvent(**kwargs)

    def test_defect_length_must_be_non_negative(self) -> None:
        kwargs = self._kwargs()
        kwargs["defect_length_inches"] = -1.0
        with pytest.raises(ValidationError):
            QualityEvent(**kwargs)

    def test_source_literal_enforced(self) -> None:
        kwargs = self._kwargs()
        kwargs["source"] = "telegram"
        with pytest.raises(ValidationError):
            QualityEvent(**kwargs)

    def test_frozen(self) -> None:
        e = QualityEvent(**self._kwargs())
        with pytest.raises(ValidationError):
            e.asset_id = "LOOM-02"  # type: ignore[misc]


# ===========================================================================
# QualityVerdict
# ===========================================================================


class TestQualityVerdict:
    def _kwargs(self) -> dict:
        return dict(
            score=2,
            severity="major",
            rationale_md="Defect length 5 inches → 2 points (ASTM D5430).",
            citations=[_citation()],
        )

    def test_minimal_valid_verdict(self) -> None:
        v = QualityVerdict(**self._kwargs())
        assert v.score == 2

    def test_score_above_max_rejected(self) -> None:
        kwargs = self._kwargs()
        kwargs["score"] = 5
        with pytest.raises(ValidationError):
            QualityVerdict(**kwargs)

    def test_score_below_zero_rejected(self) -> None:
        kwargs = self._kwargs()
        kwargs["score"] = -1
        with pytest.raises(ValidationError):
            QualityVerdict(**kwargs)

    def test_severity_literal_enforced(self) -> None:
        kwargs = self._kwargs()
        kwargs["severity"] = "fatal"
        with pytest.raises(ValidationError):
            QualityVerdict(**kwargs)

    def test_citations_typed(self) -> None:
        v = QualityVerdict(**self._kwargs())
        assert isinstance(v.citations[0], RagCitation)

    def test_frozen(self) -> None:
        v = QualityVerdict(**self._kwargs())
        with pytest.raises(ValidationError):
            v.score = 4  # type: ignore[misc]


# ===========================================================================
# OrderSpec
# ===========================================================================


class TestOrderSpec:
    def _kwargs(self) -> dict:
        return dict(
            order_id="ORD-0001",
            sku="COTTON-SHIRTING-160",
            quantity_meters=1200.0,
            due_at=_utc(2026, 5, 25, 18),
            processing_minutes=240,
            priority=1,
            compatible_families=["loom"],
        )

    def test_minimal_valid_order(self) -> None:
        o = OrderSpec(**self._kwargs())
        assert o.order_id == "ORD-0001"
        assert o.dye_lot_id is None

    def test_due_at_must_be_tz_aware(self) -> None:
        kwargs = self._kwargs()
        kwargs["due_at"] = datetime(2026, 5, 25)
        with pytest.raises(ValidationError):
            OrderSpec(**kwargs)

    def test_quantity_meters_non_negative(self) -> None:
        kwargs = self._kwargs()
        kwargs["quantity_meters"] = -1.0
        with pytest.raises(ValidationError):
            OrderSpec(**kwargs)

    def test_processing_minutes_positive(self) -> None:
        kwargs = self._kwargs()
        kwargs["processing_minutes"] = 0
        with pytest.raises(ValidationError):
            OrderSpec(**kwargs)

    def test_compatible_families_non_empty(self) -> None:
        kwargs = self._kwargs()
        kwargs["compatible_families"] = []
        with pytest.raises(ValidationError):
            OrderSpec(**kwargs)

    def test_optional_dye_lot_id_accepted(self) -> None:
        kwargs = self._kwargs()
        kwargs["dye_lot_id"] = "DL-LOOM-01-20260523-a3"
        o = OrderSpec(**kwargs)
        assert o.dye_lot_id is not None

    def test_frozen(self) -> None:
        o = OrderSpec(**self._kwargs())
        with pytest.raises(ValidationError):
            o.priority = 99  # type: ignore[misc]


# ===========================================================================
# AssetCapacity
# ===========================================================================


class TestAssetCapacity:
    def _kwargs(self) -> dict:
        return dict(
            asset_id="LOOM-01",
            asset_family="loom",
            max_meters_per_hour=300.0,
        )

    def test_minimal_valid_capacity(self) -> None:
        c = AssetCapacity(**self._kwargs())
        assert c.max_concurrent_dye_lots == 1
        assert c.dye_lot_changeover_minutes == 30
        assert c.downtime_windows == []

    def test_max_meters_per_hour_must_be_positive(self) -> None:
        kwargs = self._kwargs()
        kwargs["max_meters_per_hour"] = 0.0
        with pytest.raises(ValidationError):
            AssetCapacity(**kwargs)

    def test_max_concurrent_dye_lots_min_one(self) -> None:
        kwargs = self._kwargs()
        kwargs["max_concurrent_dye_lots"] = 0
        with pytest.raises(ValidationError):
            AssetCapacity(**kwargs)

    def test_frozen(self) -> None:
        c = AssetCapacity(**self._kwargs())
        with pytest.raises(ValidationError):
            c.asset_id = "X"  # type: ignore[misc]


# ===========================================================================
# ScheduleDraftItem
# ===========================================================================


class TestScheduleDraftItem:
    def _kwargs(self) -> dict:
        start = _utc()
        return dict(
            order_id="ORD-0001",
            asset_id="LOOM-01",
            start_at=start,
            end_at=start + timedelta(minutes=120),
            sequence=0,
        )

    def test_minimal_valid_item(self) -> None:
        item = ScheduleDraftItem(**self._kwargs())
        assert item.sequence == 0
        assert item.dye_lot_id is None

    def test_end_at_must_be_after_start_at(self) -> None:
        kwargs = self._kwargs()
        kwargs["end_at"] = kwargs["start_at"]
        with pytest.raises(ValidationError):
            ScheduleDraftItem(**kwargs)

    def test_sequence_non_negative(self) -> None:
        kwargs = self._kwargs()
        kwargs["sequence"] = -1
        with pytest.raises(ValidationError):
            ScheduleDraftItem(**kwargs)

    def test_start_at_must_be_tz_aware(self) -> None:
        kwargs = self._kwargs()
        kwargs["start_at"] = datetime(2026, 5, 23, 8)
        with pytest.raises(ValidationError):
            ScheduleDraftItem(**kwargs)

    def test_end_at_must_be_tz_aware(self) -> None:
        kwargs = self._kwargs()
        kwargs["end_at"] = datetime(2026, 5, 23, 12)
        with pytest.raises(ValidationError):
            ScheduleDraftItem(**kwargs)


# ===========================================================================
# ScheduleDraft
# ===========================================================================


class TestScheduleDraft:
    def _kwargs(self) -> dict:
        return dict(
            strategy="spt",
            horizon_start=_utc(2026, 5, 23, 6),
            horizon_end=_utc(2026, 5, 24, 6),
            items=[],
        )

    def test_minimal_valid_draft(self) -> None:
        d = ScheduleDraft(**self._kwargs())
        assert d.strategy == "spt"
        assert d.items == []
        assert d.unscheduled_orders == []
        assert d.rationale_md == ""

    def test_strategy_literal_enforced(self) -> None:
        kwargs = self._kwargs()
        kwargs["strategy"] = "fcfs"
        with pytest.raises(ValidationError):
            ScheduleDraft(**kwargs)

    def test_unscheduled_orders_default_empty(self) -> None:
        d = ScheduleDraft(**self._kwargs())
        assert d.unscheduled_orders == []


# ===========================================================================
# OpsState (TypedDict)
# ===========================================================================


class TestOpsState:
    def test_opsstate_importable(self) -> None:
        assert OpsState is not None

    def test_opsstate_keys(self) -> None:
        hints = get_type_hints(OpsState)
        expected_keys = {
            "target_agent",
            "window_minutes",
            "strategy",
            "query",
            "user_roles",
            "thread_id",
            "messages",
            "tool_results",
            "iteration_count",
            "evidence_citations",
            "anomalies",
            "quality_event",
            "verdict",
            "schedule_draft",
            "escalation_payload",
        }
        missing = expected_keys - set(hints.keys())
        assert not missing, f"OpsState missing keys: {missing}"


# ===========================================================================
# Type sanity
# ===========================================================================


def test_severity_literal_values() -> None:
    # DefectType and Severity are runtime-importable Literal aliases.
    assert "minor" in str(Severity)
    assert "broken_end" in str(DefectType)
