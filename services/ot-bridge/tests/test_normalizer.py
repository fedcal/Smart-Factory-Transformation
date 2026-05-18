"""Test per svc_ot_bridge.normalizer — pure transform DataChangeNotification → SensorEvent.

Test 1: normalize_basic         — ritorna SensorEvent con asset_family=LOOM, unit=N
Test 2: nan_value               — NaN opcua_value → SensorEvent.value is None
Test 3: immutability            — event.asset_id = "X" solleva ValidationError (frozen)
Test 4: timestamp_tz_required  — naive datetime source_ts solleva ValidationError
Test 5: quality_code_alarm      — OPC-UA error status passato invariato
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

UTC = timezone.utc


class TestNormalizeBasic:
    """Test 1 — normalize_datachange ritorna SensorEvent valido con metadati risolti."""

    def test_normalize_basic(self) -> None:
        """normalize_datachange con valori validi ritorna SensorEvent con asset_family=LOOM, unit=N."""
        from svc_ot_bridge.normalizer import normalize_datachange
        from sft_assets._models import AssetFamily

        source_ts = datetime(2026, 5, 18, tzinfo=UTC)
        server_ts = datetime(2026, 5, 18, 0, 0, 1, tzinfo=UTC)

        event = normalize_datachange(
            asset_id="LOOM-01",
            tag_id="warp_tension",
            opcua_value=25.3,
            opcua_status=0,
            source_ts=source_ts,
            server_received=server_ts,
        )

        assert event.asset_id == "LOOM-01"
        assert event.asset_family == AssetFamily.LOOM
        assert event.tag_id == "warp_tension"
        assert event.unit == "N"
        assert event.value == pytest.approx(25.3)
        assert event.quality_code == 0
        assert event.source == "live"
        assert event.timestamp_utc == source_ts
        assert event.server_received_ts == server_ts


class TestNanValue:
    """Test 2 — NaN opcua_value viene mappato a None per JSON-safety."""

    def test_nan_value(self) -> None:
        """Se opcua_value e' NaN, SensorEvent.value deve essere None."""
        from svc_ot_bridge.normalizer import normalize_datachange

        source_ts = datetime(2026, 5, 18, tzinfo=UTC)
        server_ts = datetime(2026, 5, 18, 0, 0, 1, tzinfo=UTC)

        event = normalize_datachange(
            asset_id="LOOM-01",
            tag_id="warp_tension",
            opcua_value=float("nan"),
            opcua_status=0,
            source_ts=source_ts,
            server_received=server_ts,
        )

        assert event.value is None


class TestImmutability:
    """Test 3 — SensorEvent e' frozen: assignment solleva ValidationError."""

    def test_immutability(self) -> None:
        """event.asset_id = 'X' deve sollevare ValidationError (Pydantic frozen)."""
        from svc_ot_bridge.normalizer import normalize_datachange

        source_ts = datetime(2026, 5, 18, tzinfo=UTC)
        server_ts = datetime(2026, 5, 18, 0, 0, 1, tzinfo=UTC)

        event = normalize_datachange(
            asset_id="LOOM-01",
            tag_id="warp_tension",
            opcua_value=25.3,
            opcua_status=0,
            source_ts=source_ts,
            server_received=server_ts,
        )

        with pytest.raises(ValidationError):
            event.asset_id = "X"  # type: ignore[misc]


class TestTimestampTzRequired:
    """Test 4 — timestamp_utc naive solleva ValidationError (validator tzinfo is not None)."""

    def test_timestamp_tz_required(self) -> None:
        """Passare source_ts naive (no tzinfo) deve sollevare ValidationError."""
        from svc_ot_bridge.models import SensorEvent
        from sft_assets._models import AssetFamily

        naive_ts = datetime(2026, 5, 18)  # no tzinfo — deve fallire

        with pytest.raises(ValidationError):
            SensorEvent(
                asset_id="LOOM-01",
                asset_family=AssetFamily.LOOM,
                tag_id="warp_tension",
                timestamp_utc=naive_ts,  # naive!
                value=25.3,
                unit="N",
                quality_code=0,
                source="live",
                server_received_ts=datetime(2026, 5, 18, tzinfo=UTC),
            )


class TestQualityCodeAlarmPassthrough:
    """Test 5 — quality_code non-zero passato invariato (alarm passthrough)."""

    def test_quality_code_alarm_passthrough(self) -> None:
        """opcua_status=0x80AF0000 deve essere preservato in event.quality_code."""
        from svc_ot_bridge.normalizer import normalize_datachange

        source_ts = datetime(2026, 5, 18, tzinfo=UTC)
        server_ts = datetime(2026, 5, 18, 0, 0, 1, tzinfo=UTC)
        alarm_status = 0x80AF0000

        event = normalize_datachange(
            asset_id="LOOM-01",
            tag_id="warp_tension",
            opcua_value=0.0,
            opcua_status=alarm_status,
            source_ts=source_ts,
            server_received=server_ts,
        )

        assert event.quality_code == alarm_status
