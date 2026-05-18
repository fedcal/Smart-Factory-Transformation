"""Test per subject derivation D-52 — sensor.events / sensor.alarms / audit.ot.bridge.

Test 6: event_subject    — derive_event_subject → "sensor.events.loom.LOOM-01.warp_tension"
Test 7: alarm_subject    — derive_alarm_subject → "sensor.alarms.loom.LOOM-01"
Test 8: audit_subject    — derive_audit_subject → "audit.ot.bridge"
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

UTC = timezone.utc


def _make_event(quality_code: int = 0):
    """Helper: crea un SensorEvent LOOM-01 warp_tension con il quality_code dato."""
    from svc_ot_bridge.models import SensorEvent
    from sft_assets._models import AssetFamily

    return SensorEvent(
        asset_id="LOOM-01",
        asset_family=AssetFamily.LOOM,
        tag_id="warp_tension",
        timestamp_utc=datetime(2026, 5, 18, tzinfo=UTC),
        value=25.3,
        unit="N",
        quality_code=quality_code,
        source="live",
        server_received_ts=datetime(2026, 5, 18, tzinfo=UTC),
    )


class TestEventSubject:
    """Test 6 — derive_event_subject ritorna subject nel formato D-52."""

    def test_event_subject(self) -> None:
        """derive_event_subject deve ritornare 'sensor.events.loom.LOOM-01.warp_tension'."""
        from svc_ot_bridge.nats_publisher import derive_event_subject

        event = _make_event()
        subject = derive_event_subject(event)

        assert subject == "sensor.events.loom.LOOM-01.warp_tension"


class TestAlarmSubject:
    """Test 7 — derive_alarm_subject ritorna subject alarm nel formato D-52."""

    def test_alarm_subject(self) -> None:
        """Per evento con quality_code != 0 → derive_alarm_subject == 'sensor.alarms.loom.LOOM-01'."""
        from svc_ot_bridge.nats_publisher import derive_alarm_subject

        event = _make_event(quality_code=0x80AF0000)
        subject = derive_alarm_subject(event)

        assert subject == "sensor.alarms.loom.LOOM-01"


class TestAuditSubject:
    """Test 8 — derive_audit_subject ritorna costante 'audit.ot.bridge'."""

    def test_audit_subject(self) -> None:
        """derive_audit_subject deve ritornare 'audit.ot.bridge' (costante)."""
        from svc_ot_bridge.nats_publisher import derive_audit_subject

        assert derive_audit_subject() == "audit.ot.bridge"
