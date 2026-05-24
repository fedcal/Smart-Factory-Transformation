"""setup_tracer_provider — configura il TracerProvider OTEL con esportatore OTLP.

Implementa un singleton idempotente: la prima chiamata configura il provider
globale; le chiamate successive restituiscono lo stesso oggetto senza override.

Anti-pattern evitato: doppio set_tracer_provider() che causa ProviderOverride
warning (RESEARCH Pattern 2 — singleton-guarded).

Utilizzo:
    from sft_agents.otel.provider import setup_tracer_provider

    tp = setup_tracer_provider("sft-inventory-manager")
    tracer = tp.get_tracer(__name__)
    with tracer.start_as_current_span("operation"):
        ...

Variabili d'ambiente:
    OTEL_EXPORTER_OTLP_ENDPOINT: Endpoint OTLP (default http://tempo:4317).
        Se termina con /v1/traces usa l'exporter HTTP, altrimenti gRPC.
    OTEL_SERVICE_NAME: Sovrascrive service_name se presente.
"""

from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Modulo-level singleton guard — evita double-init e ProviderOverride warning.
_initialized: bool = False
_provider_instance: TracerProvider | None = None

_DEFAULT_ENDPOINT = "http://tempo:4317"


def setup_tracer_provider(service_name: str) -> TracerProvider:
    """Configura (o restituisce) il TracerProvider OTEL globale per questo processo.

    Idempotente: la seconda chiamata restituisce lo stesso oggetto senza
    sovrascrivere il provider globale.

    Args:
        service_name: Nome del servizio per il resource attribute ``service.name``.
            Viene sovrascrito da ``OTEL_SERVICE_NAME`` se presente.

    Returns:
        Il TracerProvider configurato (nuovo o esistente se già inizializzato).
    """
    global _initialized, _provider_instance  # noqa: PLW0603

    if _initialized and _provider_instance is not None:
        return _provider_instance

    resolved_name = os.environ.get("OTEL_SERVICE_NAME", service_name)
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", _DEFAULT_ENDPOINT)

    resource = Resource.create({"service.name": resolved_name})
    provider = TracerProvider(resource=resource)

    # Sceglie il protocollo in base all'endpoint: HTTP se path /v1/traces, gRPC altrimenti.
    if endpoint.endswith("/v1/traces"):
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter as OTLPHttpExporter,
        )

        exporter = OTLPHttpExporter(endpoint=endpoint)
    else:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter as OTLPGrpcExporter,
        )

        exporter = OTLPGrpcExporter(endpoint=endpoint, insecure=True)

    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Registra il provider globale solo alla prima inizializzazione.
    trace.set_tracer_provider(provider)

    _initialized = True
    _provider_instance = provider
    return provider
