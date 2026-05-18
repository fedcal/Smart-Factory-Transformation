"""OT Bridge: unidirectional data-diode from OPC-UA/PLC simulator to NATS JetStream.

Barrel export — espone i componenti principali del bridge.

D-51 Layer 3: subscribe-only OPC-UA client, zero write API calls in questo package.
D-52: Subject hierarchy sensor.events.*/sensor.alarms.*/audit.ot.bridge.
OQ3: Solo ot-bridge pubblica su audit.ot.bridge.
"""

__version__ = "0.1.0"

from svc_ot_bridge.models import AuditEvent, SensorEvent
from svc_ot_bridge.normalizer import normalize_datachange
from svc_ot_bridge.nats_publisher import (
    NatsPublisher,
    derive_alarm_subject,
    derive_audit_subject,
    derive_event_subject,
)
from svc_ot_bridge.timescale_writer import TimescaleWriter

__all__ = [
    "AuditEvent",
    "NatsPublisher",
    "SensorEvent",
    "TimescaleWriter",
    "derive_alarm_subject",
    "derive_audit_subject",
    "derive_event_subject",
    "normalize_datachange",
]
