"""Test per svc_ot_bridge.nats_publisher — JetStream publish + audit.ot.bridge.

Test 9:  publish_event   — js.publish chiamato con subject e payload JSON SensorEvent
Test 10: publish_audit   — publisher emette AuditEvent su audit.ot.bridge con campi richiesti
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

UTC = timezone.utc


def _make_event():
    """Helper: crea SensorEvent LOOM-01 warp_tension."""
    from svc_ot_bridge.models import SensorEvent
    from sft_assets._models import AssetFamily

    return SensorEvent(
        asset_id="LOOM-01",
        asset_family=AssetFamily.LOOM,
        tag_id="warp_tension",
        timestamp_utc=datetime(2026, 5, 18, tzinfo=UTC),
        value=25.3,
        unit="N",
        quality_code=0,
        source="live",
        server_received_ts=datetime(2026, 5, 18, tzinfo=UTC),
    )


class TestPublishEvent:
    """Test 9 — publish_event chiama js.publish con subject e payload JSON corretto."""

    async def test_publish_event(self, mock_jetstream_ctx: AsyncMock) -> None:
        """js.publish deve essere chiamato con subject='sensor.events.loom.LOOM-01.warp_tension'
        e payload che e' il model_dump_json() dell'evento."""
        from svc_ot_bridge.nats_publisher import NatsPublisher

        publisher = NatsPublisher()
        publisher._js = mock_jetstream_ctx

        event = _make_event()
        await publisher.publish_event(event)

        mock_jetstream_ctx.publish.assert_called_once()
        call_args = mock_jetstream_ctx.publish.call_args

        subject = call_args[0][0]
        payload_bytes = call_args[0][1]

        assert subject == "sensor.events.loom.LOOM-01.warp_tension"

        # Payload deve essere JSON decodificabile con i campi di SensorEvent
        payload = json.loads(payload_bytes.decode("utf-8"))
        assert payload["asset_id"] == "LOOM-01"
        assert payload["tag_id"] == "warp_tension"
        assert payload["quality_code"] == 0


class TestPublishAudit:
    """Test 10 — publisher emette AuditEvent su audit.ot.bridge."""

    async def test_publish_audit(self, mock_jetstream_ctx: AsyncMock) -> None:
        """publisher.publish_audit deve chiamare js.publish su 'audit.ot.bridge'
        con payload che include ts, level, event_type, details."""
        from svc_ot_bridge.nats_publisher import NatsPublisher
        from svc_ot_bridge.models import AuditEvent

        publisher = NatsPublisher()
        publisher._js = mock_jetstream_ctx

        audit = AuditEvent(
            ts=datetime(2026, 5, 18, tzinfo=UTC),
            level="ERROR",
            event_type="publish_failure",
            details={"error": "connection_timeout", "retries": 3},
        )

        await publisher.publish_audit(audit)

        mock_jetstream_ctx.publish.assert_called_once()
        call_args = mock_jetstream_ctx.publish.call_args

        subject = call_args[0][0]
        payload_bytes = call_args[0][1]

        assert subject == "audit.ot.bridge"

        payload = json.loads(payload_bytes.decode("utf-8"))
        assert "ts" in payload
        assert payload["level"] == "ERROR"
        assert payload["event_type"] == "publish_failure"
        assert "details" in payload
