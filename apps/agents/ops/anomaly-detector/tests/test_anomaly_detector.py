"""End-to-end tests for ``ops_anomaly_detector.agent.AnomalyDetector`` (Plan 06-06 Task 1 RED).

Covers the 7 behaviors documented in 06-06-PLAN.md <behavior> for
test_anomaly_detector.py — happy path, in-band suppression, per-machine
override, missing baseline graceful, multi-asset, window_minutes propagation,
state-delta only (no mutation).

Uses pure-Python mocks (mock_pool, mock_query_tool, mock_audit_writer fixtures
from local conftest.py) — no Docker / testcontainers required.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from sft_assets.models import Asset, AssetFamily, SemanticType, Tag
from sft_domain.ops.anomaly import AnomalyBaseline

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers — build deterministic baseline + asset fixtures inline so each test
# states its own contract without sharing global state.
# ---------------------------------------------------------------------------


def _loom_baseline(low: float = 0.2, high: float = 0.8) -> AnomalyBaseline:
    return AnomalyBaseline(
        asset_family="loom",
        sensor_id="warp_tension",
        low=low,
        high=high,
        unit="g",
        severity_mapping={"minor": 0.05, "major": 0.2, "critical": 0.5},
    )


def _loom_asset(asset_id: str = "LOOM-01", line_id: str = "weaving-line-1") -> Asset:
    return Asset(
        asset_id=asset_id,
        asset_family=AssetFamily.LOOM,
        line_id=line_id,
        opcua_namespace=f"urn:mantis:loom:{asset_id}",
        tags=(
            Tag(
                tag_id="warp_tension",
                unit="N",
                sample_rate_hz=10.0,
                semantic_type=SemanticType.TENSION,
            ),
        ),
        status="active",
    )


def _sensor_df(asset_id: str, sensor_id: str, value: float, ts: datetime | None = None) -> pd.DataFrame:
    """Build a single-row sensor_events DataFrame matching QueryTimescaleTool output."""
    ts = ts or datetime.now(UTC)
    return pd.DataFrame(
        [{
            "asset_id": asset_id,
            "sensor_id": sensor_id,
            "timestamp": ts,
            "value": value,
            "unit": "N",
        }]
    )


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["asset_id", "sensor_id", "timestamp", "value", "unit"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_happy_path_emits_anomaly(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """Seed value=1.2 outside band [0.2, 0.8] → 1 Anomaly + 1 audit row (Decision.AUTO + ANOMALY_ALERT)."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415
    from sft_agents.models.enums import ActionType, Decision  # noqa: PLC0415

    asset = _loom_asset()
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=1.2)

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    result = await detector({"window_minutes": 15})

    assert "anomalies" in result
    assert len(result["anomalies"]) == 1
    anomaly = result["anomalies"][0]
    assert anomaly.asset_id == "LOOM-01"
    assert anomaly.sensor_id == "warp_tension"
    assert anomaly.value == pytest.approx(1.2)
    assert anomaly.severity == "major"  # deviation 0.4 → major (>=0.2, <0.5)

    # Exactly one audit row written, decision=AUTO + action_type=ANOMALY_ALERT.
    assert mock_audit_writer.write.await_count == 1
    record = mock_audit_writer.write.await_args.args[0]
    assert record.decision is Decision.AUTO
    assert record.action_type == ActionType.ANOMALY_ALERT.value


async def test_no_false_positive_on_normal_loom_vibration(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """In-band value=0.5 → no anomaly, no audit row (success criterion #3)."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset()
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=0.5)

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    result = await detector({"window_minutes": 15})

    assert result == {"anomalies": []}
    assert mock_audit_writer.write.await_count == 0


async def test_per_machine_override_applied(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """Per-machine override band [0.3, 0.6] flags value=0.7 even though family band [0.2, 0.8] would accept it."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset()
    family_baseline = _loom_baseline(low=0.2, high=0.8)
    machine_baseline = AnomalyBaseline(
        asset_family="LOOM-01",  # machine_id reused as key
        sensor_id="warp_tension",
        low=0.3,
        high=0.6,
        unit="N",
        severity_mapping={"minor": 0.05, "major": 0.2, "critical": 0.5},
    )
    baselines = {
        ("loom", "warp_tension"): family_baseline,
        ("LOOM-01", "warp_tension"): machine_baseline,
    }
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=0.7)

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    result = await detector({"window_minutes": 15})
    assert len(result["anomalies"]) == 1
    anomaly = result["anomalies"][0]
    # Machine baseline upper edge is 0.6 → emit, with the override band.
    assert anomaly.baseline_low == pytest.approx(0.3)
    assert anomaly.baseline_high == pytest.approx(0.6)


async def test_missing_baseline_logs_warning_no_crash(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Sensor with no baseline → no exception, no anomaly emitted."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset()
    # No baselines at all — every row is "missing baseline".
    baselines: dict[tuple[str, str], AnomalyBaseline] = {}
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "unknown_sensor", value=99.0)

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    # Must NOT raise.
    result = await detector({"window_minutes": 15})
    assert result == {"anomalies": []}
    assert mock_audit_writer.write.await_count == 0


async def test_handles_multiple_assets_in_one_scan(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """3 assets in registry, 2 with anomalies → 2 anomalies returned (in scan order)."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    a1 = _loom_asset("LOOM-01")
    a2 = _loom_asset("LOOM-02")
    a3 = _loom_asset("LOOM-03")
    baselines = {("loom", "warp_tension"): _loom_baseline()}

    # a1 anomaly (value=1.2), a2 in-band (value=0.5), a3 anomaly (value=1.5).
    async def _arun_side_effect(asset_id: str, **kwargs: Any) -> pd.DataFrame:
        if asset_id == "LOOM-01":
            return _sensor_df(asset_id, "warp_tension", value=1.2)
        if asset_id == "LOOM-02":
            return _sensor_df(asset_id, "warp_tension", value=0.5)
        if asset_id == "LOOM-03":
            return _sensor_df(asset_id, "warp_tension", value=1.5)
        return _empty_df()

    mock_query_tool._arun.side_effect = _arun_side_effect

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(a1, a2, a3),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    result = await detector({"window_minutes": 15})
    assert len(result["anomalies"]) == 2
    assert [a.asset_id for a in result["anomalies"]] == ["LOOM-01", "LOOM-03"]


async def test_window_minutes_parameter_passed_to_timescale_tool(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """state.window_minutes=30 → QueryTimescaleTool._arun called with (now-30min, now) tuple."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset()
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    mock_query_tool._arun.return_value = _empty_df()

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    before = datetime.now(UTC)
    await detector({"window_minutes": 30})
    after = datetime.now(UTC)

    assert mock_query_tool._arun.await_count == 1
    call_kwargs = mock_query_tool._arun.await_args.kwargs
    assert call_kwargs["asset_id"] == "LOOM-01"
    start, end = call_kwargs["time_range"]
    # tz-aware UTC datetimes (Pitfall 7 / T-V6-naive-datetime)
    assert start.tzinfo is not None
    assert end.tzinfo is not None
    # end is between before/after of this call (give 5s margin for clock drift)
    assert before - timedelta(seconds=5) <= end <= after + timedelta(seconds=5)
    # window = 30 minutes (with 5s tolerance)
    delta = end - start
    assert timedelta(minutes=29, seconds=55) <= delta <= timedelta(minutes=30, seconds=5)


async def test_window_minutes_defaults_to_15(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """Default window when state omits ``window_minutes`` is 15 minutes."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset()
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    mock_query_tool._arun.return_value = _empty_df()

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    await detector({})

    start, end = mock_query_tool._arun.await_args.kwargs["time_range"]
    delta = end - start
    assert timedelta(minutes=14, seconds=55) <= delta <= timedelta(minutes=15, seconds=5)


async def test_state_delta_only_no_mutation(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """__call__ returns a state-delta dict (``anomalies`` key only) — never mutates input state."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset()
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=1.2)

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    state_in = {"window_minutes": 15, "messages": ["sentinel"]}
    state_snapshot = dict(state_in)
    result = await detector(state_in)

    # State was not mutated.
    assert state_in == state_snapshot
    # Returned dict contains only ``anomalies``.
    assert set(result.keys()) == {"anomalies"}


async def test_default_collaborators_when_omitted(
    fixed_count_pool: Any,
) -> None:
    """When query_tool / rate_limiter are omitted, defaults are constructed (no crash on init)."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset()
    baselines = {("loom", "warp_tension"): _loom_baseline()}

    # We pass an audit_writer (mandatory dependency — no sane default).
    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        audit_writer=AsyncMock(),
    )
    # Just verifying the object is constructable with the defaulted collaborators.
    assert detector is not None
