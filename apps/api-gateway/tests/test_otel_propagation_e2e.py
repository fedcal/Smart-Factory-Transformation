"""E2E test — OTEL trace propagation gateway → NATS → agent (OBS-02, SC-1).

Verifica:
    1. Il TracerProvider è inizializzato con service.name "sft-api-gateway"
       dopo la chiamata a setup_tracer_provider() nel lifespan.
    2. Il publish di un comando agent via publish_agent_command() inietta un
       header NATS ``traceparent`` ben formato (W3C traceparent).
    3. Il consumer estrae il traceparent dal messaggio NATS e il trace_id
       estratto coincide con quello del publisher (propagazione end-to-end).
    4. build_invocation_config() include il tag "phase11" nella lista tags.

Struttura test (TDD):
    - Task 1 (provider + inject):
        test_tracer_provider_service_name
        test_publish_agent_command_injects_traceparent
    - Task 2 (extract + Langfuse tag):
        test_consumer_extract_same_trace_id
        test_langfuse_build_invocation_config_phase11_tag  (in langfuse_callback)

Dipendenze: opentelemetry-sdk (già in pyproject.toml), sft_agents.otel (11-00).
Non richiede NATS reale — usa header dict sintetici.
"""

from __future__ import annotations

import re

import pytest
from opentelemetry import propagate, trace
from opentelemetry.context import attach, detach
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import SpanKind

from sft_agents.otel import NatsHeaderCarrier, setup_tracer_provider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# W3C traceparent format: 00-<32hex>-<16hex>-<2hex>
_TRACEPARENT_RE = re.compile(
    r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$"
)


def _make_test_provider() -> tuple[TracerProvider, InMemorySpanExporter]:
    """Crea un TracerProvider isolato con InMemorySpanExporter per i test.

    Restituisce (provider, exporter) senza toccare il provider globale.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


# ---------------------------------------------------------------------------
# Task 1 — TracerProvider init + publish inject
# ---------------------------------------------------------------------------


def test_tracer_provider_service_name():
    """Il setup_tracer_provider('sft-api-gateway') registra service.name corretto.

    Verifica che dopo la chiamata, il provider globale abbia il resource attribute
    service.name == 'sft-api-gateway'.
    """
    # Nota: setup_tracer_provider è singleton-guarded — se già inizializzato
    # restituisce l'istanza esistente. Testiamo il resource del provider restituito.
    provider = setup_tracer_provider("sft-api-gateway")
    resource = provider.resource
    assert resource.attributes.get("service.name") == "sft-api-gateway", (
        f"Expected service.name='sft-api-gateway', got {resource.attributes!r}"
    )


def test_publish_agent_command_injects_traceparent():
    """publish_agent_command() inietta un header 'traceparent' W3C ben formato.

    Usa un TracerProvider di test (isolato) con InMemorySpanExporter per
    avere uno span attivo senza dipendenze di infrastruttura.
    """
    from svc_api_gateway.nats_publisher import publish_agent_command

    provider, _exporter = _make_test_provider()

    # Apri uno span attivo con il provider di test.
    tracer = provider.get_tracer(__name__)

    captured_headers: dict[str, str] = {}

    # Simula una funzione publish NATS che cattura gli header.
    def fake_publish(subject: str, payload: bytes, headers: dict[str, str]) -> None:
        captured_headers.update(headers)

    with tracer.start_as_current_span("test.publish.parent"):
        publish_agent_command(
            publish_fn=fake_publish,
            subject="sft.agents.cmd.test",
            payload=b'{"action": "test"}',
        )

    assert "traceparent" in captured_headers, (
        f"Header 'traceparent' mancante. Headers: {captured_headers}"
    )
    assert _TRACEPARENT_RE.match(captured_headers["traceparent"]), (
        f"traceparent non valido W3C: {captured_headers['traceparent']!r}"
    )


# ---------------------------------------------------------------------------
# Task 2 — Consumer extract + same trace_id
# ---------------------------------------------------------------------------


def test_consumer_extract_same_trace_id():
    """Il consumer estrae il traceparent e ottiene lo stesso trace_id del publisher.

    Simula il flusso end-to-end:
        1. Publisher apre span e inietta traceparent negli header NATS.
        2. Consumer estrae il contesto e apre span CONSUMER.
        3. Il trace_id del publisher == trace_id del consumer.
    """
    from svc_api_gateway.nats_publisher import publish_agent_command
    from sft_agents.runtime.agent_runner import handle_agent_command

    publisher_provider, publisher_exporter = _make_test_provider()
    consumer_provider, consumer_exporter = _make_test_provider()

    # --- Publisher lato ---
    publisher_tracer = publisher_provider.get_tracer("publisher")
    captured_headers: dict[str, str] = {}

    def fake_publish(subject: str, payload: bytes, headers: dict[str, str]) -> None:
        captured_headers.update(headers)

    with publisher_tracer.start_as_current_span("gateway.request") as publisher_span:
        publisher_trace_id = publisher_span.get_span_context().trace_id
        publish_agent_command(
            publish_fn=fake_publish,
            subject="sft.agents.cmd.test",
            payload=b'{"action": "test"}',
        )

    # --- Consumer lato ---
    consumer_tracer = consumer_provider.get_tracer("consumer")
    consumer_trace_ids: list[int] = []

    def mock_process_fn(payload: bytes) -> None:
        """Callable simulata per il corpo del comando agent."""
        span = trace.get_current_span()
        consumer_trace_ids.append(span.get_span_context().trace_id)

    # Simula msg NATS con gli header iniettati dal publisher.
    class FakeMsg:
        headers = dict(captured_headers)
        data = b'{"action": "test"}'

    handle_agent_command(
        msg=FakeMsg(),
        tracer=consumer_tracer,
        process_fn=mock_process_fn,
    )

    assert len(consumer_trace_ids) == 1, (
        "process_fn non invocata all'interno dello span CONSUMER"
    )
    assert consumer_trace_ids[0] == publisher_trace_id, (
        f"trace_id publisher ({publisher_trace_id:x}) != "
        f"trace_id consumer ({consumer_trace_ids[0]:x})"
    )
