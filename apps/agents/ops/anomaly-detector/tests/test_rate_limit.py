"""Rate-limit suppression tests for AnomalyDetector (Plan 06-06 Task 1 RED).

Covers the 3 behaviors from 06-06-PLAN.md <behavior> for test_rate_limit.py:

* ``test_12h_window_caps_emission`` — seed COUNT=12 → 5 new candidates all
  suppressed; audit rows decision=SUPPRESSED, return ``{"anomalies": []}``.
* ``test_11_existing_plus_1_new_emits`` — seed COUNT=11 → exactly 1 emission
  (12th allowed; further would be suppressed).
* ``test_suppressed_audit_row_includes_original_payload`` — assert the
  SUPPRESSED audit row's evidence_panel includes the original anomaly's
  asset_id / sensor_id / value.

Uses pure-Python mocks — the RateLimiter calls ``conn.fetchval(SQL, ...)`` and
we control its return value to simulate "N rows in audit.actions".
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from sft_assets.models import Asset, AssetFamily, SemanticType, Tag
from sft_domain.ops.anomaly import AnomalyBaseline

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers (duplicated from test_anomaly_detector for test-file independence)
# ---------------------------------------------------------------------------


def _baseline() -> AnomalyBaseline:
    return AnomalyBaseline(
        asset_family="loom",
        sensor_id="warp_tension",
        low=0.2,
        high=0.8,
        unit="g",
        severity_mapping={"minor": 0.05, "major": 0.2, "critical": 0.5},
    )


def _asset(asset_id: str = "LOOM-01") -> Asset:
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


def _df_with_n_rows(asset_id: str, n: int, value: float = 1.5) -> pd.DataFrame:
    """Return a DataFrame with ``n`` out-of-band rows for ``asset_id``."""
    now = datetime.now(UTC)
    return pd.DataFrame(
        [
            {
                "asset_id": asset_id,
                "sensor_id": "warp_tension",
                "timestamp": now,
                "value": value,
                "unit": "N",
            }
            for _ in range(n)
        ]
    )


def _set_fetchval(pool: AsyncMock, count: int) -> None:
    """Pre-program the pool's ``fetchval`` to return ``count`` (existing audit rows)."""
    pool.acquire.return_value.__aenter__.return_value.fetchval.return_value = count


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_12h_window_caps_emission(
    mock_pool: AsyncMock,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """12 existing audit rows → next 5 candidates all suppressed (cap = 12)."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415
    from sft_agents.models.enums import ActionType, Decision  # noqa: PLC0415

    _set_fetchval(mock_pool, 12)

    asset = _asset()
    mock_query_tool._arun.return_value = _df_with_n_rows(asset.asset_id, n=5, value=1.5)

    detector = AnomalyDetector(
        pool=mock_pool,
        baselines={("loom", "warp_tension"): _baseline()},
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    result = await detector({"window_minutes": 15})

    assert result == {"anomalies": []}
    # 5 audit rows, ALL Decision.SUPPRESSED with ActionType.ANOMALY_ALERT.
    assert mock_audit_writer.write.await_count == 5
    for call in mock_audit_writer.write.await_args_list:
        record = call.args[0]
        assert record.decision is Decision.SUPPRESSED
        assert record.action_type == ActionType.ANOMALY_ALERT.value


async def test_11_existing_plus_1_new_emits(
    mock_pool: AsyncMock,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """11 existing → 1 new candidate emits with Decision.AUTO + ANOMALY_ALERT."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415
    from sft_agents.models.enums import ActionType, Decision  # noqa: PLC0415

    _set_fetchval(mock_pool, 11)

    asset = _asset()
    mock_query_tool._arun.return_value = _df_with_n_rows(asset.asset_id, n=1, value=1.5)

    detector = AnomalyDetector(
        pool=mock_pool,
        baselines={("loom", "warp_tension"): _baseline()},
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    result = await detector({"window_minutes": 15})

    assert len(result["anomalies"]) == 1
    assert mock_audit_writer.write.await_count == 1
    record = mock_audit_writer.write.await_args.args[0]
    assert record.decision is Decision.AUTO
    assert record.action_type == ActionType.ANOMALY_ALERT.value


async def test_suppressed_audit_row_includes_original_payload(
    mock_pool: AsyncMock,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """SUPPRESSED audit row's evidence_panel.tool_calls carries the original anomaly fields."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415
    from sft_agents.models.enums import Decision  # noqa: PLC0415

    _set_fetchval(mock_pool, 12)  # already at limit
    asset = _asset()
    mock_query_tool._arun.return_value = _df_with_n_rows(asset.asset_id, n=1, value=1.5)

    detector = AnomalyDetector(
        pool=mock_pool,
        baselines={("loom", "warp_tension"): _baseline()},
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    await detector({"window_minutes": 15})

    assert mock_audit_writer.write.await_count == 1
    record = mock_audit_writer.write.await_args.args[0]
    assert record.decision is Decision.SUPPRESSED

    # Original anomaly payload must be discoverable inside evidence_panel.
    panel = record.evidence_panel
    # The agent persists the suppressed anomaly as a synthetic ToolCall (same
    # convention as LogEventTool — keeps audit rows queryable without JSONB scan).
    assert len(panel.tool_calls) >= 1
    tc_args: dict[str, Any] = panel.tool_calls[0].args
    assert tc_args.get("asset_id") == "LOOM-01"
    assert tc_args.get("sensor_id") == "warp_tension"
    assert tc_args.get("value") == pytest.approx(1.5)


async def test_below_limit_emits_normally(
    mock_pool: AsyncMock,
    mock_query_tool: AsyncMock,
    mock_audit_writer: AsyncMock,
) -> None:
    """0 existing rows → 3 candidates all emit (sanity check around the cap)."""
    from ops_anomaly_detector.agent import AnomalyDetector  # noqa: PLC0415

    _set_fetchval(mock_pool, 0)
    asset = _asset()
    mock_query_tool._arun.return_value = _df_with_n_rows(asset.asset_id, n=3, value=1.2)

    detector = AnomalyDetector(
        pool=mock_pool,
        baselines={("loom", "warp_tension"): _baseline()},
        asset_registry=(asset,),
        query_tool=mock_query_tool,
        audit_writer=mock_audit_writer,
    )

    result = await detector({"window_minutes": 15})

    assert len(result["anomalies"]) == 3
    assert mock_audit_writer.write.await_count == 3
