"""Unit tests for ``ops_anomaly_detector.baseline`` (Plan 06-06 Task 1 RED).

Covers the three baseline helpers documented in 06-06-PLAN.md <behavior>:

* ``test_is_within_band_inclusive`` — band edges are inclusive.
* ``test_severity_for_uses_mapping`` — severity mapping picks the highest
  threshold the deviation crosses.
* ``test_select_baseline_machine_override_wins`` — per-machine override
  shadows the per-asset-family baseline.

No DB / no async — pure dict / Pydantic model construction.
"""

from __future__ import annotations

import pytest

from sft_domain.ops.anomaly import AnomalyBaseline


def _baseline(low: float, high: float, *, asset_family: str = "loom", sensor_id: str = "warp_tension") -> AnomalyBaseline:
    return AnomalyBaseline(
        asset_family=asset_family,
        sensor_id=sensor_id,
        low=low,
        high=high,
        unit="g",
        severity_mapping={"minor": 0.1, "major": 0.3, "critical": 0.6},
    )


def test_is_within_band_inclusive() -> None:
    """Band edges are inclusive (Plan 06-06 must_haves truth: in-band → no anomaly)."""
    b = _baseline(0.0, 0.8)
    assert b.is_within_band(0.0) is True  # left edge
    assert b.is_within_band(0.8) is True  # right edge
    assert b.is_within_band(0.5) is True  # interior
    assert b.is_within_band(-0.01) is False
    assert b.is_within_band(0.81) is False


def test_severity_for_uses_mapping() -> None:
    """Severity mapping picks the highest threshold the deviation crosses.

    Band [0.0, 0.8] with mapping {minor:0.1, major:0.3, critical:0.6}:

      * value=0.9 → deviation=0.1 → minor (>=0.1, <0.3)
      * value=1.2 → deviation=0.4 → major (>=0.3, <0.6)
      * value=1.5 → deviation=0.7 → critical (>=0.6)
    """
    b = _baseline(0.0, 0.8)
    assert b.severity_for(0.9) == "minor"
    assert b.severity_for(1.2) == "major"
    assert b.severity_for(1.5) == "critical"


def test_select_baseline_machine_override_wins() -> None:
    """Per-machine override (keyed by (machine_id, sensor_id)) wins over per-family."""
    from ops_anomaly_detector.baseline import select_baseline  # noqa: PLC0415

    family = _baseline(0.2, 0.8, asset_family="loom", sensor_id="warp_tension")
    machine = _baseline(0.3, 0.6, asset_family="LOOM-01", sensor_id="warp_tension")
    baselines = {
        ("loom", "warp_tension"): family,
        ("LOOM-01", "warp_tension"): machine,
    }

    # When machine_id matches an override key, override wins.
    chosen = select_baseline(baselines, asset_family="loom", sensor_id="warp_tension", machine_id="LOOM-01")
    assert chosen is machine

    # Without a matching override (LOOM-02), the family baseline wins.
    chosen2 = select_baseline(baselines, asset_family="loom", sensor_id="warp_tension", machine_id="LOOM-02")
    assert chosen2 is family

    # Without machine_id, falls back to family baseline.
    chosen3 = select_baseline(baselines, asset_family="loom", sensor_id="warp_tension", machine_id=None)
    assert chosen3 is family


def test_select_baseline_returns_none_when_missing() -> None:
    """Missing baseline (no family + no machine) returns None — caller logs warning."""
    from ops_anomaly_detector.baseline import select_baseline  # noqa: PLC0415

    chosen = select_baseline({}, asset_family="loom", sensor_id="unknown_sensor", machine_id="LOOM-01")
    assert chosen is None


def test_select_baseline_rejects_invalid_inputs() -> None:
    """Empty asset_family / sensor_id raises ValueError (defensive boundary)."""
    from ops_anomaly_detector.baseline import select_baseline  # noqa: PLC0415

    with pytest.raises(ValueError):
        select_baseline({}, asset_family="", sensor_id="warp_tension", machine_id=None)
    with pytest.raises(ValueError):
        select_baseline({}, asset_family="loom", sensor_id="", machine_id=None)
