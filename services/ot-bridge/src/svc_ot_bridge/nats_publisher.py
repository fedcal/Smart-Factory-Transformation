"""NATS JetStream publisher per svc-ot-bridge.

Pubblica SensorEvent su subject D-52 e AuditEvent su audit.ot.bridge (OQ3).

Subject derivation (D-52):
    sensor.events.<asset_family>.<asset_id>.<tag_id>  — main event stream
    sensor.alarms.<asset_family>.<asset_id>            — alarm storm aggregate
    audit.ot.bridge                                    — connection/failure events (OQ3)

Sicurezza:
    - D-51 Layer 3: questo modulo NON usa OPC-UA, solo NATS publish
    - No f-string SQL (nessun SQL qui)
    - Subject derivation da enum AssetFamily.value — no user-controlled string injection (T-03-04-nats-subj)
"""

from __future__ import annotations

from typing import Any

import nats
import structlog

from svc_ot_bridge.models import AuditEvent, SensorEvent

logger = structlog.get_logger(__name__)

# Costante soggetto audit — OQ3: solo ot-bridge pubblica su questo subject
_AUDIT_SUBJECT = "audit.ot.bridge"


def derive_event_subject(event: SensorEvent) -> str:
    """Deriva il NATS subject per un evento sensore (D-52).

    Format: sensor.events.<asset_family>.<asset_id>.<tag_id>

    Esempio: sensor.events.loom.LOOM-01.warp_tension
    """
    return f"sensor.events.{event.asset_family.value}.{event.asset_id}.{event.tag_id}"


def derive_alarm_subject(event: SensorEvent) -> str:
    """Deriva il NATS subject alarm per un evento con quality_code != 0 (D-52).

    Format: sensor.alarms.<asset_family>.<asset_id>

    Esempio: sensor.alarms.loom.LOOM-01
    """
    return f"sensor.alarms.{event.asset_family.value}.{event.asset_id}"


def derive_audit_subject() -> str:
    """Ritorna il NATS subject per eventi audit (D-52 + OQ3 — costante).

    Returns:
        "audit.ot.bridge" — subject esclusivo di ot-bridge (OQ3 resolution).
    """
    return _AUDIT_SUBJECT


class NatsPublisher:
    """Publisher JetStream per SensorEvent e AuditEvent.

    Pubblica su subjects D-52 tramite JetStream per delivery garantito.
    Gli eventi alarm (quality_code != 0) vengono pubblicati anche sul subject alarm.

    Usage:
        publisher = NatsPublisher()
        await publisher.start("nats://nats:4222")
        await publisher.publish_event(event)
        await publisher.close()
    """

    def __init__(self) -> None:
        self._nc: Any = None  # nats.NATS connection
        self._js: Any = None  # JetStreamContext

    async def start(self, url: str) -> None:
        """Connette a NATS e inizializza il JetStream context.

        Args:
            url: URL NATS (es. "nats://nats:4222", env NATS_URL).
        """
        self._nc = await nats.connect(url)
        self._js = self._nc.jetstream()
        logger.info("nats_publisher_started", url=url)

    async def publish_event(self, event: SensorEvent) -> None:
        """Pubblica un SensorEvent su JetStream.

        Subject: sensor.events.<family>.<asset_id>.<tag_id> (D-52)
        Se quality_code != 0: pubblica anche su sensor.alarms.<family>.<asset_id>

        Args:
            event: SensorEvent da pubblicare.
        """
        subject = derive_event_subject(event)
        payload = event.model_dump_json().encode("utf-8")
        await self._js.publish(subject, payload)

        logger.debug(
            "sensor_event_published",
            subject=subject,
            asset_id=event.asset_id,
            tag_id=event.tag_id,
            quality_code=event.quality_code,
        )

        # Alarm passthrough — quality_code != 0 → anche subject alarm (D-52)
        if event.quality_code != 0:
            alarm_subject = derive_alarm_subject(event)
            alarm_payload = event.model_dump_json().encode("utf-8")
            await self._js.publish(alarm_subject, alarm_payload)
            logger.info(
                "alarm_event_published",
                alarm_subject=alarm_subject,
                asset_id=event.asset_id,
                quality_code=event.quality_code,
            )

    async def publish_audit(self, audit: AuditEvent) -> None:
        """Pubblica un AuditEvent su audit.ot.bridge (OQ3).

        Args:
            audit: AuditEvent da pubblicare. Solo ot-bridge pubblica su questo subject.
        """
        payload = audit.model_dump_json().encode("utf-8")
        await self._js.publish(_AUDIT_SUBJECT, payload)
        logger.info(
            "audit_event_published",
            event_type=audit.event_type,
            level=audit.level,
        )

    async def close(self) -> None:
        """Drena la connessione NATS e chiude gracefully."""
        if self._nc is not None:
            await self._nc.drain()
            logger.info("nats_publisher_closed")
