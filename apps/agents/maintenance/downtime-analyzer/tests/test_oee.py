"""Tests for OEE computation (plan 07-09, D-DA-02/03).

TDD: tests written before implementation (RED) → Task 3 implementation makes them GREEN.

Tests cover:
- compute_availability: basic math, clamp to [0,1], custom planned_time
- compute_performance: stub reader, fallback to 1.0 + WARN
- compute_quality_cross_cluster: audit source, sim fallback, no-data fallback
- compute_oee: integration A*P*Q product
- quality_source marker: returned as part of compute_quality_cross_cluster tuple
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# compute_availability tests
# ---------------------------------------------------------------------------


def test_availability_basic_calculation() -> None:
    """compute_availability(window=60min, downtime=15min) returns 0.75."""
    from mnt_downtime_analyzer.oee import compute_availability

    start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)  # 60 min window

    result = compute_availability(
        window_start=start,
        window_end=end,
        downtime_minutes=15,
    )
    assert abs(result - 0.75) < 1e-9


def test_availability_clamped_to_zero_when_downtime_exceeds_planned() -> None:
    """compute_availability with downtime=120min and 60min window clamps to 0.0."""
    from mnt_downtime_analyzer.oee import compute_availability

    start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)  # 60 min window

    result = compute_availability(
        window_start=start,
        window_end=end,
        downtime_minutes=120,
    )
    assert result == 0.0


def test_availability_custom_planned_production_time() -> None:
    """compute_availability with planned=45min, downtime=15min returns 30/45."""
    from mnt_downtime_analyzer.oee import compute_availability

    start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)  # 60 min window

    result = compute_availability(
        window_start=start,
        window_end=end,
        downtime_minutes=15,
        planned_production_minutes=45,
    )
    expected = 30.0 / 45.0
    assert abs(result - expected) < 1e-9


def test_availability_zero_downtime_returns_one() -> None:
    """compute_availability with 0 downtime returns 1.0."""
    from mnt_downtime_analyzer.oee import compute_availability

    start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)

    result = compute_availability(
        window_start=start,
        window_end=end,
        downtime_minutes=0,
    )
    assert result == 1.0


# ---------------------------------------------------------------------------
# compute_performance tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_performance_with_reader_returning_good_target() -> None:
    """compute_performance with stub reader (good=900, target=1000) -> 0.9."""
    from mnt_downtime_analyzer.oee import compute_performance

    async def reader(asset_id, window_start, window_end):
        return (900, 1000)  # (good_meters, target_meters)

    result = await compute_performance(
        asset_id="LOOM-01",
        window_start=datetime(2026, 1, 1, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        production_state_reader=reader,
    )
    assert abs(result - 0.9) < 1e-9


@pytest.mark.asyncio
async def test_performance_reader_none_returns_one_with_warn(caplog) -> None:
    """compute_performance with reader=None returns 1.0 + structlog WARN."""
    import structlog.testing

    from mnt_downtime_analyzer.oee import compute_performance

    with structlog.testing.capture_logs() as cap:
        result = await compute_performance(
            asset_id="LOOM-01",
            window_start=datetime(2026, 1, 1, tzinfo=UTC),
            window_end=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
            production_state_reader=None,
        )

    assert result == 1.0
    warn_events = [e for e in cap if e.get("log_level") == "warning"]
    assert any("oee_performance_fallback_unavailable_source" in str(e) for e in warn_events)


@pytest.mark.asyncio
async def test_performance_with_zero_target_returns_one_with_warn() -> None:
    """compute_performance with target=0 returns 1.0 + WARN."""
    import structlog.testing

    from mnt_downtime_analyzer.oee import compute_performance

    async def reader(asset_id, window_start, window_end):
        return (0, 0)  # zero target

    with structlog.testing.capture_logs() as cap:
        result = await compute_performance(
            asset_id="LOOM-01",
            window_start=datetime(2026, 1, 1, tzinfo=UTC),
            window_end=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
            production_state_reader=reader,
        )

    assert result == 1.0
    warn_events = [e for e in cap if e.get("log_level") == "warning"]
    assert any("oee_performance_fallback_unavailable_source" in str(e) for e in warn_events)


# ---------------------------------------------------------------------------
# compute_quality_cross_cluster tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quality_cross_cluster_happy_path_returns_ratio_and_audit_marker() -> None:
    """compute_quality_cross_cluster happy: reader returns (950,1000) -> 0.95 + source='audit'."""
    import structlog.testing

    from mnt_downtime_analyzer.oee import compute_quality_cross_cluster
    from mnt_downtime_analyzer.repository import QualityVerdictReader

    quality_reader = AsyncMock(spec=QualityVerdictReader)
    quality_reader.fetch_quality_metrics = AsyncMock(return_value=(950, 1000))

    with structlog.testing.capture_logs() as cap:
        quality, source = await compute_quality_cross_cluster(
            asset_id="LOOM-01",
            window_start=datetime(2026, 1, 1, tzinfo=UTC),
            window_end=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
            quality_reader=quality_reader,
        )

    assert abs(quality - 0.95) < 1e-9
    assert source == "audit"
    info_events = [e for e in cap if e.get("log_level") == "info"]
    assert any("oee_quality_source_audit" in str(e) for e in info_events)


@pytest.mark.asyncio
async def test_quality_cross_cluster_audit_empty_uses_sim_fallback() -> None:
    """Audit empty + sim fallback: reader returns (0,0) -> sim returns (980,1000) -> 0.98."""
    import structlog.testing

    from mnt_downtime_analyzer.oee import compute_quality_cross_cluster
    from mnt_downtime_analyzer.repository import QualityVerdictReader

    quality_reader = AsyncMock(spec=QualityVerdictReader)
    quality_reader.fetch_quality_metrics = AsyncMock(return_value=(0, 0))

    async def sim_fallback(asset_id, window_start, window_end):
        return (980, 1000)

    with structlog.testing.capture_logs() as cap:
        quality, source = await compute_quality_cross_cluster(
            asset_id="LOOM-01",
            window_start=datetime(2026, 1, 1, tzinfo=UTC),
            window_end=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
            quality_reader=quality_reader,
            sim_fallback_reader=sim_fallback,
        )

    assert abs(quality - 0.98) < 1e-9
    assert source == "simfallback"
    info_events = [e for e in cap if e.get("log_level") == "info"]
    assert any("oee_quality_source_simfallback" in str(e) for e in info_events)


@pytest.mark.asyncio
async def test_quality_cross_cluster_no_fallback_audit_empty_returns_one() -> None:
    """No fallback + audit empty -> 1.0 + WARN (no-data assumption)."""
    import structlog.testing

    from mnt_downtime_analyzer.oee import compute_quality_cross_cluster
    from mnt_downtime_analyzer.repository import QualityVerdictReader

    quality_reader = AsyncMock(spec=QualityVerdictReader)
    quality_reader.fetch_quality_metrics = AsyncMock(return_value=(0, 0))

    with structlog.testing.capture_logs() as cap:
        quality, source = await compute_quality_cross_cluster(
            asset_id="LOOM-01",
            window_start=datetime(2026, 1, 1, tzinfo=UTC),
            window_end=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
            quality_reader=quality_reader,
            sim_fallback_reader=None,
        )

    assert quality == 1.0
    assert source == "no-data"


@pytest.mark.asyncio
async def test_quality_cross_cluster_fires_exactly_once() -> None:
    """Cross-cluster SQL fired exactly once per compute call."""
    from mnt_downtime_analyzer.oee import compute_quality_cross_cluster
    from mnt_downtime_analyzer.repository import QualityVerdictReader

    quality_reader = AsyncMock(spec=QualityVerdictReader)
    quality_reader.fetch_quality_metrics = AsyncMock(return_value=(800, 1000))

    await compute_quality_cross_cluster(
        asset_id="LOOM-01",
        window_start=datetime(2026, 1, 1, tzinfo=UTC),
        window_end=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        quality_reader=quality_reader,
    )

    quality_reader.fetch_quality_metrics.assert_called_once()


# ---------------------------------------------------------------------------
# compute_oee integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_oee_integration_abc_product() -> None:
    """compute_oee: A=0.9, P=0.95, Q=0.98 -> 0.9*0.95*0.98 = 0.8379 (±1e-6)."""
    from mnt_downtime_analyzer.oee import compute_oee
    from mnt_downtime_analyzer.repository import DowntimeEventRepository, QualityVerdictReader

    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)

    repo = AsyncMock(spec=DowntimeEventRepository)
    # fetch_window returns a list of events with total 6min downtime in a 60min window -> A=0.9
    from sim_textile.downtime_event_generator import DowntimeEvent
    from uuid import uuid4

    mock_event = DowntimeEvent(
        event_id=str(uuid4()),
        asset_id="LOOM-01",
        reason_code="WEAVING-BE-001",
        duration_min=6,
        severity="minor",
        work_order_id=None,
        dye_lot_id=None,
        source="simulator",
        timestamp=now,
    )
    repo.fetch_window = AsyncMock(return_value=[mock_event])
    repo.pareto = AsyncMock(return_value=[])

    quality_reader = AsyncMock(spec=QualityVerdictReader)
    quality_reader.fetch_quality_metrics = AsyncMock(return_value=(980, 1000))  # Q=0.98

    async def production_reader(asset_id, window_start, window_end):
        return (950, 1000)  # P=0.95

    availability, performance, quality, oee, total_downtime, event_count = await compute_oee(
        asset_id="LOOM-01",
        window_start=now,
        window_end=end,
        repository=repo,
        quality_reader=quality_reader,
        production_state_reader=production_reader,
        sim_fallback_reader=production_reader,
        planned_production_minutes=60,
    )

    assert abs(availability - 0.9) < 1e-6, f"A={availability}"
    assert abs(performance - 0.95) < 1e-6, f"P={performance}"
    assert abs(quality - 0.98) < 1e-6, f"Q={quality}"
    expected_oee = 0.9 * 0.95 * 0.98
    assert abs(oee - expected_oee) < 1e-6, f"OEE={oee}, expected={expected_oee}"
    assert total_downtime == 6
    assert event_count == 1


@pytest.mark.asyncio
async def test_compute_oee_zero_events_returns_ones() -> None:
    """compute_oee zero-event window: availability=1.0, performance=1.0, quality=1.0."""
    from mnt_downtime_analyzer.oee import compute_oee
    from mnt_downtime_analyzer.repository import DowntimeEventRepository, QualityVerdictReader

    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 1, 0, 0, tzinfo=UTC)

    repo = AsyncMock(spec=DowntimeEventRepository)
    repo.fetch_window = AsyncMock(return_value=[])  # no events

    quality_reader = AsyncMock(spec=QualityVerdictReader)
    quality_reader.fetch_quality_metrics = AsyncMock(return_value=(1000, 1000))  # Q=1.0

    async def production_reader(asset_id, window_start, window_end):
        return (1000, 1000)  # P=1.0

    availability, performance, quality, oee, total_downtime, event_count = await compute_oee(
        asset_id="LOOM-01",
        window_start=now,
        window_end=end,
        repository=repo,
        quality_reader=quality_reader,
        production_state_reader=production_reader,
    )

    assert availability == 1.0
    assert performance == 1.0
    assert quality == 1.0
    assert oee == 1.0
    assert total_downtime == 0
    assert event_count == 0
