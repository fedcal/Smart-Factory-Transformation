"""AnomalyDetector (OPS-04) — happy / degraded / failure E2E scenarios.

Plan 06-13 / success criterion #5.

Happy:
    1 LOOM-01 sensor sample outside baseline band → 1 Anomaly emitted +
    1 Decision.AUTO audit row.

Degraded:
    No samples in window → 0 anomalies, 0 audit rows. Structlog
    "anomaly_scan_complete" emitted=0.

Failure:
    RateLimiter pre-loaded with 12 alerts in the past hour → next anomaly
    suppressed (Decision.SUPPRESSED audit row).

Mock collaborators — TimescaleDB query tool + RateLimiter are mocked so the
test runs deterministically without docker.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

# RED gate — skip if the agent isn't installed in this env.
pytest.importorskip(
    "ops_anomaly_detector.agent",
    reason="Plan 06-06 implements ops_anomaly_detector.agent",
)

from ops_anomaly_detector.agent import AnomalyDetector  # noqa: E402
from sft_assets.models import Asset, AssetFamily  # noqa: E402
from sft_domain.ops.anomaly import AnomalyBaseline  # noqa: E402


pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


_SCENARIOS = [
    "anomaly-detector/happy",
    "anomaly-detector/degraded",
    "anomaly-detector/failure",
]


def _build_assets() -> tuple[Asset, ...]:
    """Single LOOM-01 asset — minimum surface for the scan tick."""
    return (
        Asset(
            asset_id="LOOM-01",
            asset_family=AssetFamily.LOOM,
            line_id="LINE-A",
            opcua_namespace="urn:mantis:loom:LOOM-01",
            tags=(),
            status="active",
        ),
    )


def _build_baselines() -> dict[tuple[str, str], AnomalyBaseline]:
    """Single (loom, vibration_mm_s) baseline; band [0, 8]."""
    bl = AnomalyBaseline(
        asset_family="loom",
        sensor_id="vibration_mm_s",
        low=0.0,
        high=8.0,
        unit="mm_s",
        severity_mapping={"minor": 1.0, "major": 5.0, "critical": 15.0},
    )
    return {("loom", "vibration_mm_s"): bl}


def _build_dataframe(tsdb_rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Materialize the scenario's tsdb_rows into the DataFrame shape AnomalyDetector expects."""
    if not tsdb_rows:
        return pd.DataFrame(columns=["asset_id", "sensor_id", "timestamp", "value"])
    now = datetime.now(timezone.utc)
    rows = []
    for r in tsdb_rows:
        offset = r.get("timestamp_offset_seconds", 0)
        rows.append(
            {
                "asset_id": r.get("asset_id", "LOOM-01"),
                "sensor_id": r.get("sensor_id", "vibration_mm_s"),
                "timestamp": now + timedelta(seconds=offset),
                "value": float(r.get("value", 0.0)),
            }
        )
    return pd.DataFrame(rows)


def _build_query_tool(df: pd.DataFrame) -> Any:
    """Mock QueryTimescaleTool whose _arun returns the supplied DataFrame."""
    tool = MagicMock(name="query_tool")
    tool._arun = AsyncMock(return_value=df)
    return tool


def _build_rate_limiter(*, allow_all: bool, suppressed_count: int = 12) -> Any:
    """Mock RateLimiter.

    ``allow_all=True``  → check_and_emit returns (True, n) for any call.
    ``allow_all=False`` → returns (False, suppressed_count) (rate cap hit).
    """
    limiter = MagicMock(name="rate_limiter")
    call_count = {"n": 0}

    async def _check(action_type: str) -> tuple[bool, int]:
        call_count["n"] += 1
        if allow_all:
            return True, call_count["n"]
        return False, suppressed_count + call_count["n"]

    limiter.check_and_emit = _check
    return limiter


@pytest.mark.parametrize("ops_scenario", _SCENARIOS, indirect=True)
async def test_anomaly_detector_scenario(
    ops_scenario: dict[str, Any],
    mock_collaborators: dict[str, Any],
) -> None:
    """Drive AnomalyDetector.__call__ end-to-end against the scenario YAML."""
    assert ops_scenario
    expected = ops_scenario["expected"]
    body = ops_scenario["input"]["body"]

    df = _build_dataframe(ops_scenario.get("seed", {}).get("tsdb_rows") or [])
    query_tool = _build_query_tool(df)

    # Failure scenario: pre-existing 12 alerts → rate-limiter rejects.
    audit_seed = ops_scenario.get("seed", {}).get("audit_seed") or {}
    pre_existing = (
        audit_seed.get("pre_existing_anomaly_alerts", 0) if isinstance(audit_seed, dict) else 0
    )
    allow_all = pre_existing < 12
    rate_limiter = _build_rate_limiter(allow_all=allow_all, suppressed_count=pre_existing)

    detector = AnomalyDetector(
        pool=mock_collaborators["pool"],
        baselines=_build_baselines(),
        asset_registry=_build_assets(),
        audit_writer=mock_collaborators["audit_writer"],
        query_tool=query_tool,
        rate_limiter=rate_limiter,
    )

    state = {
        "window_minutes": body.get("window_minutes", 15),
        "triggered_by": body.get("triggered_by", "scheduler"),
    }
    result = await detector(state)

    # Anomalies emitted.
    anomalies = result.get("anomalies", [])
    anomalies_min = expected.get("anomalies_min", 0)
    anomalies_max = expected.get("anomalies_max")
    assert len(anomalies) >= anomalies_min
    if anomalies_max is not None:
        assert len(anomalies) <= anomalies_max

    # Audit row count.
    writes = mock_collaborators["audit_writer"].writes
    audit_min = expected.get("audit_rows_min", 0)
    audit_max = expected.get("audit_rows_max")
    assert len(writes) >= audit_min, f"expected ≥ {audit_min} audit row(s), got {len(writes)}"
    if audit_max is not None:
        assert len(writes) <= audit_max, (
            f"expected ≤ {audit_max} audit row(s), got {len(writes)}"
        )

    # Decision label on the written rows.
    if expected.get("decision") and writes:
        from sft_agents.models.enums import Decision

        target = Decision[expected["decision"].upper()]
        assert all(w.decision == target for w in writes), (
            f"expected all writes to be {target!r}; got {[w.decision for w in writes]!r}"
        )

    # ActionType ANOMALY_ALERT on every audit row.
    if expected.get("action_type") and writes:
        from sft_agents.models.enums import ActionType

        target_at = ActionType[expected["action_type"]].value
        assert all(w.action_type == target_at for w in writes)

    # Suppressed count when failure path triggers.
    if "suppressed_count_min" in expected:
        # AnomalyDetector returns suppressed via a side-channel (the state delta
        # only carries "anomalies"); we proxy by counting SUPPRESSED audit rows.
        from sft_agents.models.enums import Decision

        n_suppressed = sum(1 for w in writes if w.decision == Decision.SUPPRESSED)
        assert n_suppressed >= expected["suppressed_count_min"]
