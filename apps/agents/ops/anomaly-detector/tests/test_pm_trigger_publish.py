"""Tests for the Open Q1 Option (a) thin extension: AnomalyDetector NATS publish hook.

RED phase until Task 3 implementation of the nats_client kwarg + publish hook.

Verifies:
- nats_client=None (default) → no publish, Phase 6 behavior unchanged
- nats_client=AsyncMock() + AUTO + major/critical → publish once on correct subject
- severity=minor → no publish
- Decision.SUPPRESSED → no publish
- Publish happens AFTER audit write (call-order assertion)
- Payload is JSON-deserializable to a PredictRequest-compatible dict
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call

import pandas as pd
import pytest
from sft_assets.models import Asset, AssetFamily, SemanticType, Tag
from sft_domain.ops.anomaly import AnomalyBaseline


# ---------------------------------------------------------------------------
# Helpers (mirrors test_anomaly_detector.py helpers)
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


def _loom_asset(asset_id: str = "LOOM-01") -> Asset:
    return Asset(
        asset_id=asset_id,
        asset_family=AssetFamily.LOOM,
        line_id="weaving-line-1",
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


def _sensor_df(asset_id: str, sensor_id: str, value: float) -> pd.DataFrame:
    """Build a single-row sensor_events DataFrame."""
    return pd.DataFrame(
        [{
            "asset_id": asset_id,
            "sensor_id": sensor_id,
            "timestamp": datetime.now(UTC),
            "value": value,
            "unit": "N",
        }]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_no_nats_client_default_no_publish(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """nats_client=None (default) → no publish attempt, all Phase 6 behavior unchanged."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset()
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=1.2)

    # Instantiate WITHOUT nats_client
    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    result = await detector({"window_minutes": 15})
    # Phase 6 behavior: anomaly emitted, audit written, NO NATS publish
    assert len(result["anomalies"]) == 1
    assert mock_audit_writer.write.await_count == 1
    # No nats client → no publish possible (assert no publish attribute used)
    # This verifies backward-compat: the detector has no _nats or it is None
    nats = getattr(detector, "_nats", None)
    assert nats is None


async def test_auto_major_triggers_publish(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """AUTO + severity=major → exactly 1 NATS publish on maintenance.predict.LOOM-01."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset("LOOM-01")
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    # value=1.2 → deviation=0.4 → major (>= 0.2, < 0.5 threshold)
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=1.2)

    mock_nats = AsyncMock()
    mock_nats.publish = AsyncMock(return_value=None)

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
        nats_client=mock_nats,
    )

    result = await detector({"window_minutes": 15})
    assert len(result["anomalies"]) == 1

    # Exactly 1 publish
    assert mock_nats.publish.await_count == 1
    publish_call = mock_nats.publish.await_args
    subject = publish_call.args[0] if publish_call.args else publish_call.kwargs.get("subject")
    payload_bytes = publish_call.args[1] if len(publish_call.args) > 1 else publish_call.kwargs.get("payload")

    assert subject == "maintenance.predict.LOOM-01"

    # Payload is JSON-deserializable and has required fields
    payload = json.loads(payload_bytes.decode() if isinstance(payload_bytes, bytes) else payload_bytes)
    assert payload["asset_id"] == "LOOM-01"
    assert payload["severity"] in ("major",)
    assert "triggered_by_action_id" in payload
    assert "emitted_at" in payload


async def test_auto_critical_triggers_publish(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """AUTO + severity=critical → publish triggered."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset("LOOM-01")
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    # value=1.5 → deviation=0.7 → critical (>= 0.5)
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=1.5)

    mock_nats = AsyncMock()
    mock_nats.publish = AsyncMock(return_value=None)

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
        nats_client=mock_nats,
    )

    result = await detector({"window_minutes": 15})
    assert len(result["anomalies"]) == 1
    assert mock_nats.publish.await_count == 1

    payload_bytes = mock_nats.publish.await_args.args[1] if len(mock_nats.publish.await_args.args) > 1 else mock_nats.publish.await_args.kwargs.get("payload")
    payload = json.loads(payload_bytes.decode() if isinstance(payload_bytes, bytes) else payload_bytes)
    assert payload["severity"] == "critical"


async def test_minor_severity_no_publish(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """AUTO + severity=minor → NO publish (only major/critical trigger PM)."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset("LOOM-01")
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    # value=0.82 → deviation=0.02 → minor (< 0.05 threshold, actually minor starts at 0.05)
    # Actually: deviation from high=0.8 is 0.82-0.8=0.02 < 0.05 minor threshold → minor
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=0.82)

    mock_nats = AsyncMock()
    mock_nats.publish = AsyncMock(return_value=None)

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
        nats_client=mock_nats,
    )

    result = await detector({"window_minutes": 15})
    # Anomaly with minor severity → emitted but no publish
    anomalies = result["anomalies"]
    assert len(anomalies) == 1
    assert anomalies[0].severity == "minor"
    assert mock_nats.publish.await_count == 0


async def test_suppressed_decision_no_publish(
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """Decision.SUPPRESSED (rate-limited) → NO publish even for major severity."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset("LOOM-01")
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=1.2)

    # Build a pool that returns count=13 (>12 limit) so RateLimiter suppresses
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=13)  # already at limit
    conn.execute = AsyncMock(return_value="UPDATE 1")
    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)
    from unittest.mock import MagicMock  # noqa: PLC0415
    pool = AsyncMock()
    pool.acquire = MagicMock(return_value=acquire_ctx)

    mock_nats = AsyncMock()
    mock_nats.publish = AsyncMock(return_value=None)

    detector = AnomalyDetector(
        pool=pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
        nats_client=mock_nats,
    )

    result = await detector({"window_minutes": 15})
    # Suppressed → not in emitted list
    assert result["anomalies"] == []
    # No publish for suppressed decisions
    assert mock_nats.publish.await_count == 0


async def test_publish_happens_after_audit_write(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """Publish happens AFTER audit write (call-order assertion)."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset("LOOM-01")
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=1.2)

    call_order: list[str] = []

    async def track_write(record: object) -> None:
        call_order.append("write")

    async def track_publish(subject: str, payload: bytes) -> None:
        call_order.append("publish")

    mock_audit_writer.write.side_effect = track_write
    mock_nats = AsyncMock()
    mock_nats.publish.side_effect = track_publish

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
        nats_client=mock_nats,
    )

    await detector({"window_minutes": 15})

    assert "write" in call_order, "audit write must be called"
    assert "publish" in call_order, "NATS publish must be called"
    write_idx = call_order.index("write")
    publish_idx = call_order.index("publish")
    assert write_idx < publish_idx, f"write ({write_idx}) must precede publish ({publish_idx})"


async def test_payload_contains_triggered_by_action_id(
    fixed_count_pool: Any,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """Publish payload includes triggered_by_action_id equal to the audit row's action_id."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    asset = _loom_asset("LOOM-01")
    baselines = {("loom", "warp_tension"): _loom_baseline()}
    mock_query_tool._arun.return_value = _sensor_df(asset.asset_id, "warp_tension", value=1.2)

    captured_action_id: list[str] = []

    async def capture_write(record: object) -> None:
        captured_action_id.append(str(record.action_id))

    mock_audit_writer.write.side_effect = capture_write

    mock_nats = AsyncMock()
    mock_nats.publish = AsyncMock(return_value=None)

    detector = AnomalyDetector(
        pool=fixed_count_pool,
        baselines=baselines,
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
        nats_client=mock_nats,
    )

    await detector({"window_minutes": 15})

    payload_bytes = mock_nats.publish.await_args.args[1] if len(mock_nats.publish.await_args.args) > 1 else mock_nats.publish.await_args.kwargs.get("payload")
    payload = json.loads(payload_bytes.decode() if isinstance(payload_bytes, bytes) else payload_bytes)

    assert len(captured_action_id) == 1
    assert payload["triggered_by_action_id"] == captured_action_id[0], (
        "PM trigger payload's triggered_by_action_id must match the audit row's action_id "
        "(MNT-06 cross-cluster audit chain)"
    )
