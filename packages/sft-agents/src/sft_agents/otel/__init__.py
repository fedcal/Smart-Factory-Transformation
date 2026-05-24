"""sft_agents.otel — OpenTelemetry utilities per Smart Factory Transformation.

Exports:
    setup_tracer_provider: Configura il TracerProvider OTEL con exporter OTLP.
    NatsHeaderCarrier: Adattatore MutableMapping per inject/extract su messaggi NATS.
"""

from sft_agents.otel.nats_carrier import NatsHeaderCarrier
from sft_agents.otel.provider import setup_tracer_provider

__all__ = ["NatsHeaderCarrier", "setup_tracer_provider"]
