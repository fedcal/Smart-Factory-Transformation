"""Tests for PredictiveMaintenance inference path + model/audit contracts (Plan 07-06 TDD).

RED phase: all tests fail until Task 2/3 implementations land.

Covers:
- RULEstimate Pydantic D-PM-04 contract (frozen, extra=forbid, field validators)
- compute_health_index + RUL_MAX_CYCLES
- load_pretrained_model (sft-ml Ridge joblib)
- PredictRequest round-trip + validation
- PredictiveMaintenance.__call__ smoke + HITL gate + audit row content
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pandas as pd
import pytest
from pydantic import ValidationError
from sft_agents.models.enums import Decision
from sft_assets.models import Asset, AssetFamily, SemanticType, Tag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _sensor_window_df(asset_id: str = "LOOM-01", rows: int = 60) -> pd.DataFrame:
    """Build a synthetic 60-sample sensor window matching QueryTimescaleTool output."""
    now = datetime.now(UTC)
    records = [
        {
            "asset_id": asset_id,
            "sensor_id": "warp_tension",
            "timestamp": now,
            "value": 0.5,
            "unit": "N",
        }
        for _ in range(rows)
    ]
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# RULEstimate tests
# ---------------------------------------------------------------------------


def test_rul_estimate_frozen_extra_forbid() -> None:
    """RULEstimate is frozen and rejects extra fields."""
    from mnt_predictive_maintenance.models import RULEstimate  # noqa: PLC0415

    now = datetime.now(UTC)
    estimate = RULEstimate(
        estimate_id="abc123",
        asset_id="LOOM-01",
        rul_cycles=80,
        confidence_band_lower=72,
        confidence_band_upper=88,
        health_index=0.64,
        model_version="ridge-fd001-fd003-v1.0",
        created_at=now,
    )
    # Frozen: mutation raises
    with pytest.raises(Exception):
        object.__setattr__(estimate, "rul_cycles", 90)

    # Extra field: validation error
    with pytest.raises(ValidationError):
        RULEstimate(
            estimate_id="abc123",
            asset_id="LOOM-01",
            rul_cycles=80,
            confidence_band_lower=72,
            confidence_band_upper=88,
            health_index=0.64,
            model_version="ridge-fd001-fd003-v1.0",
            created_at=now,
            unknown_extra_field="banned",
        )


def test_rul_estimate_health_index_bounds() -> None:
    """health_index must be in [0.0, 1.0]."""
    from mnt_predictive_maintenance.models import RULEstimate  # noqa: PLC0415

    now = datetime.now(UTC)
    base = dict(
        estimate_id="abc",
        asset_id="LOOM-01",
        rul_cycles=50,
        confidence_band_lower=45,
        confidence_band_upper=55,
        model_version="ridge-fd001-fd003-v1.0",
        created_at=now,
    )
    with pytest.raises(ValidationError):
        RULEstimate(**base, health_index=-0.1)
    with pytest.raises(ValidationError):
        RULEstimate(**base, health_index=1.1)
    # valid boundary
    ok = RULEstimate(**base, health_index=0.0)
    assert ok.health_index == 0.0
    ok2 = RULEstimate(**base, health_index=1.0)
    assert ok2.health_index == 1.0


def test_rul_estimate_rul_cycles_ge_zero() -> None:
    """rul_cycles must be >= 0."""
    from mnt_predictive_maintenance.models import RULEstimate  # noqa: PLC0415

    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        RULEstimate(
            estimate_id="abc",
            asset_id="LOOM-01",
            rul_cycles=-1,
            confidence_band_lower=0,
            confidence_band_upper=10,
            health_index=0.5,
            model_version="ridge-fd001-fd003-v1.0",
            created_at=now,
        )


def test_rul_estimate_naive_datetime_rejected() -> None:
    """created_at must be tz-aware UTC; naive datetime raises ValidationError."""
    from mnt_predictive_maintenance.models import RULEstimate  # noqa: PLC0415

    naive_now = datetime.now()  # no tzinfo
    with pytest.raises(ValidationError):
        RULEstimate(
            estimate_id="abc",
            asset_id="LOOM-01",
            rul_cycles=50,
            confidence_band_lower=45,
            confidence_band_upper=55,
            health_index=0.5,
            model_version="ridge-fd001-fd003-v1.0",
            created_at=naive_now,
        )


def test_rul_estimate_all_dpm04_fields() -> None:
    """All D-PM-04 fields are present and round-trip correctly."""
    from mnt_predictive_maintenance.models import RULEstimate  # noqa: PLC0415

    now = datetime.now(UTC)
    estimate = RULEstimate(
        estimate_id="estimate-uuid-1",
        asset_id="LOOM-01",
        rul_cycles=80,
        confidence_band_lower=72,
        confidence_band_upper=88,
        health_index=0.64,
        recommended_action="Scheduled preventive maintenance",
        triggered_by_action_id="ad-action-uuid-1",
        model_version="ridge-fd001-fd003-v1.0",
        created_at=now,
    )
    assert estimate.estimate_id == "estimate-uuid-1"
    assert estimate.asset_id == "LOOM-01"
    assert estimate.rul_cycles == 80
    assert estimate.confidence_band_lower == 72
    assert estimate.confidence_band_upper == 88
    assert estimate.health_index == pytest.approx(0.64)
    assert estimate.recommended_action == "Scheduled preventive maintenance"
    assert estimate.triggered_by_action_id == "ad-action-uuid-1"
    assert estimate.model_version == "ridge-fd001-fd003-v1.0"
    assert estimate.created_at == now


# ---------------------------------------------------------------------------
# compute_health_index + RUL_MAX_CYCLES
# ---------------------------------------------------------------------------


def test_rul_max_cycles_constant() -> None:
    """RUL_MAX_CYCLES == 125 (C-MAPSS piecewise-linear cap convention, 07-03)."""
    from mnt_predictive_maintenance.inference import RUL_MAX_CYCLES  # noqa: PLC0415

    assert RUL_MAX_CYCLES == 125


def test_compute_health_index_boundary_values() -> None:
    """compute_health_index: clamp to [0.0, 1.0]; 125 -> 1.0, 0 -> 0.0."""
    from mnt_predictive_maintenance.inference import compute_health_index  # noqa: PLC0415

    assert compute_health_index(125) == pytest.approx(1.0)
    assert compute_health_index(0) == pytest.approx(0.0)
    assert compute_health_index(60) == pytest.approx(60 / 125)
    # Clamp above 125
    assert compute_health_index(200) == pytest.approx(1.0)
    # Clamp below 0
    assert compute_health_index(-5) == pytest.approx(0.0)


def test_load_pretrained_model_returns_sklearn_pipeline() -> None:
    """load_pretrained_model() returns a sklearn Pipeline and is deterministic."""
    import sklearn  # noqa: PLC0415

    from mnt_predictive_maintenance.inference import load_pretrained_model  # noqa: PLC0415

    pipeline = load_pretrained_model()
    assert pipeline is not None
    # Should be a sklearn Pipeline
    assert hasattr(pipeline, "predict"), "Expected sklearn Pipeline with predict method"

    # Deterministic: same input -> same output across 2 calls on same loaded pipeline
    import pandas as pd  # noqa: PLC0415

    features = pd.DataFrame(
        [{col: 0.0 for col in
          ["op_setting_1", "op_setting_2", "op_setting_3"] + [f"s{i}" for i in range(1, 22)]}]
    )
    r1 = pipeline.predict(features)
    r2 = pipeline.predict(features)
    assert r1[0] == r2[0], "Pipeline must be deterministic"


# ---------------------------------------------------------------------------
# PredictRequest round-trip + validation
# ---------------------------------------------------------------------------


def test_predict_request_round_trip() -> None:
    """PredictRequest round-trip: model_dump_json -> json.loads -> model_validate yields equal instance."""
    from mnt_predictive_maintenance.models import PredictRequest  # noqa: PLC0415

    now = datetime.now(UTC)
    req = PredictRequest(
        asset_id="LOOM-01",
        triggered_by_action_id="ad-action-uuid-1",
        severity="major",
        emitted_at=now,
    )
    serialized = req.model_dump_json()
    data = json.loads(serialized)
    req2 = PredictRequest.model_validate(data)
    assert req2.asset_id == req.asset_id
    assert req2.severity == req.severity
    assert req2.triggered_by_action_id == req.triggered_by_action_id


def test_predict_request_invalid_severity() -> None:
    """PredictRequest rejects invalid severity literals."""
    from mnt_predictive_maintenance.models import PredictRequest  # noqa: PLC0415

    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        PredictRequest(
            asset_id="LOOM-01",
            severity="invalid",
            emitted_at=now,
        )

    # 'low' and 'medium' are not valid per PredictRequest Literal
    with pytest.raises(ValidationError):
        PredictRequest(
            asset_id="LOOM-01",
            severity="low",
            emitted_at=now,
        )


# ---------------------------------------------------------------------------
# PredictiveMaintenance.__call__ smoke test
# ---------------------------------------------------------------------------


async def test_agent_call_smoke_returns_rul_estimate(
    mock_audit_writer: AsyncMock,
    mock_query_tool: AsyncMock,
) -> None:
    """__call__ with valid asset returns RULEstimate with expected fields."""
    from mnt_predictive_maintenance.agent import PredictiveMaintenance  # noqa: PLC0415
    from mnt_predictive_maintenance.models import RULEstimate  # noqa: PLC0415

    asset = _loom_asset("LOOM-01")
    mock_query_tool._arun.return_value = _sensor_window_df("LOOM-01", rows=60)

    agent = PredictiveMaintenance(
        pool=MagicMock(),
        audit_writer=mock_audit_writer,
        asset_registry=[asset],
        query_tool=mock_query_tool,
        escalate_tool=AsyncMock(),
    )

    result = await agent({
        "asset_id": "LOOM-01",
        "triggered_by_action_id": "ad-action-uuid-1",
    })

    assert "rul_estimate" in result
    estimate = result["rul_estimate"]
    assert isinstance(estimate, RULEstimate)
    assert estimate.asset_id == "LOOM-01"
    assert estimate.triggered_by_action_id == "ad-action-uuid-1"
    assert estimate.model_version == "ridge-fd001-fd003-v1.0"


# ---------------------------------------------------------------------------
# PredictiveMaintenance HITL gate test
# ---------------------------------------------------------------------------


async def test_agent_hitl_gate_called_before_audit(
    mock_audit_writer: AsyncMock,
    mock_query_tool: AsyncMock,
) -> None:
    """HITL gate: escalate_to_supervisor called BEFORE audit_writer.write (Pitfall §3)."""
    from mnt_predictive_maintenance.agent import PredictiveMaintenance  # noqa: PLC0415
    from mnt_predictive_maintenance.inference import load_pretrained_model  # noqa: PLC0415
    from sklearn.pipeline import Pipeline  # noqa: PLC0415

    # Build a mock model that always returns 0 cycles (health_index = 0.0 < 0.3)
    mock_model = MagicMock(spec=Pipeline)
    mock_model.predict.return_value = [0.0]

    asset = _loom_asset("LOOM-01")
    mock_query_tool._arun.return_value = _sensor_window_df("LOOM-01", rows=60)

    mock_escalate = AsyncMock()
    mock_escalate._arun = AsyncMock(return_value={"decision": "approved"})

    call_order: list[str] = []

    async def track_escalate(**kwargs: object) -> dict:
        call_order.append("escalate")
        return {"decision": "approved"}

    async def track_write(record: object) -> None:
        call_order.append("write")

    mock_escalate._arun.side_effect = track_escalate
    mock_audit_writer.write.side_effect = track_write

    agent = PredictiveMaintenance(
        pool=MagicMock(),
        audit_writer=mock_audit_writer,
        asset_registry=[asset],
        model=mock_model,
        query_tool=mock_query_tool,
        escalate_tool=mock_escalate,
    )

    result = await agent({
        "asset_id": "LOOM-01",
        "triggered_by_action_id": "ad-action-uuid-1",
    })

    # escalate must come before write
    assert "escalate" in call_order, "escalate_to_supervisor must be called when health_index < 0.3"
    assert "write" in call_order, "audit_writer.write must be called after escalate"
    escalate_idx = call_order.index("escalate")
    write_idx = call_order.index("write")
    assert escalate_idx < write_idx, f"Pitfall §3: escalate ({escalate_idx}) must precede write ({write_idx})"

    # recommended_action must be non-empty IT string mentioning asset_id
    estimate = result["rul_estimate"]
    assert estimate.recommended_action is not None and "LOOM-01" in estimate.recommended_action


# ---------------------------------------------------------------------------
# PredictiveMaintenance audit row content test
# ---------------------------------------------------------------------------


async def test_agent_audit_row_content(
    mock_audit_writer: AsyncMock,
    mock_query_tool: AsyncMock,
) -> None:
    """Audit row content: action_type=RUL_ESTIMATE, thread_id format, triggered_by_action_id chain."""
    from mnt_predictive_maintenance.agent import PredictiveMaintenance  # noqa: PLC0415
    from sft_agents.models.enums import ActionType  # noqa: PLC0415

    asset = _loom_asset("LOOM-01")
    mock_query_tool._arun.return_value = _sensor_window_df("LOOM-01", rows=60)

    # Use a model that returns health_index >= 0.3 (rul_cycles=80 -> health=0.64)
    from sklearn.pipeline import Pipeline  # noqa: PLC0415
    mock_model = MagicMock(spec=Pipeline)
    mock_model.predict.return_value = [80.0]  # health_index = 80/125 = 0.64

    agent = PredictiveMaintenance(
        pool=MagicMock(),
        audit_writer=mock_audit_writer,
        asset_registry=[asset],
        model=mock_model,
        query_tool=mock_query_tool,
        escalate_tool=AsyncMock(),
    )

    result = await agent({
        "asset_id": "LOOM-01",
        "triggered_by_action_id": "ad-action-uuid-1",
    })

    estimate = result["rul_estimate"]
    assert mock_audit_writer.write.await_count == 1
    record = mock_audit_writer.write.await_args.args[0]

    assert record.action_type == ActionType.RUL_ESTIMATE.value
    assert record.decision in (Decision.AUTO, Decision.HITL_SUPERVISOR)
    assert record.thread_id == f"maintenance.predictive-maintenance.{estimate.estimate_id}"
    assert len(record.evidence_panel.tool_calls) >= 1
    tc = record.evidence_panel.tool_calls[0]
    assert tc.name == "rul_predict"
    assert tc.args["triggered_by_action_id"] == "ad-action-uuid-1"
