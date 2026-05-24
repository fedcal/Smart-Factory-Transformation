"""Test OTEL NatsHeaderCarrier round-trip e provider idempotency.

Phase 11 — Plan 11-00, Task 2 (TDD RED → GREEN).

Tre comportamenti verificati:
  1. inject di un traceparent in un dict vuoto via NatsHeaderCarrier popola la
     chiave `traceparent`; extract dello stesso dict riproduce un SpanContext
     con lo stesso trace_id.
  2. NatsHeaderCarrier soddisfa il protocollo MutableMapping (get/set/del/iter/len).
  3. setup_tracer_provider("svc-x") chiamato due volte NON sovrascrive il
     provider globale la seconda volta (flag _initialized singleton).
"""
from __future__ import annotations

import importlib


def test_nats_carrier_round_trip_traceparent() -> None:
    """inject + extract via NatsHeaderCarrier riproduce lo stesso trace_id."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.propagate import inject, extract

    from sft_agents.otel.nats_carrier import NatsHeaderCarrier

    # Crea un tracer provider locale (non il globale) con un tracer che produce span reali
    provider = TracerProvider()
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("test-span") as span:
        trace_id_before = span.get_span_context().trace_id
        assert trace_id_before != 0, "trace_id deve essere non-zero"

        # inject nel carrier
        headers: dict[str, str] = {}
        carrier = NatsHeaderCarrier(headers)
        inject(carrier)

        assert "traceparent" in headers, (
            f"inject deve popolare 'traceparent' in headers, got: {headers}"
        )

    # extract dallo stesso carrier fuori dallo span (propagazione simulata)
    carrier_out = NatsHeaderCarrier(headers)
    ctx = extract(carrier_out)
    span_ctx = trace.get_current_span(ctx).get_span_context()
    extracted_trace_id = span_ctx.trace_id

    assert extracted_trace_id == trace_id_before, (
        f"trace_id estratto {extracted_trace_id:#x} != originale {trace_id_before:#x}"
    )


def test_nats_carrier_mutable_mapping_protocol() -> None:
    """NatsHeaderCarrier soddisfa il protocollo MutableMapping."""
    from sft_agents.otel.nats_carrier import NatsHeaderCarrier

    h: dict[str, str] = {"existing": "value"}
    c = NatsHeaderCarrier(h)

    # __getitem__
    assert c["existing"] == "value"

    # __setitem__
    c["traceparent"] = "00-abc-def-01"
    assert h["traceparent"] == "00-abc-def-01"

    # __delitem__
    del c["existing"]
    assert "existing" not in h

    # __iter__
    keys = list(c)
    assert "traceparent" in keys

    # __len__
    assert len(c) == 1

    # get (ereditato da MutableMapping)
    assert c.get("traceparent") == "00-abc-def-01"
    assert c.get("missing", "default") == "default"


def test_setup_tracer_provider_idempotent() -> None:
    """setup_tracer_provider chiamato due volte NON sovrascrive il provider globale."""
    # Reset del modulo provider per un test isolato
    import sft_agents.otel.provider as prov_mod

    # Salva lo stato originale
    original_initialized = prov_mod._initialized
    original_provider = prov_mod._provider_instance

    try:
        # Resetta per test pulito
        prov_mod._initialized = False
        prov_mod._provider_instance = None

        import os
        # Usa un endpoint fittizio per evitare connessioni reali
        os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:14317")

        tp1 = prov_mod.setup_tracer_provider("svc-test-idempotent")
        assert tp1 is not None

        tp2 = prov_mod.setup_tracer_provider("svc-test-idempotent")

        # Devono essere lo stesso oggetto (singleton)
        assert tp1 is tp2, (
            "setup_tracer_provider chiamato due volte deve restituire lo stesso provider"
        )
        assert prov_mod._initialized is True
    finally:
        # Ripristina lo stato originale del modulo
        prov_mod._initialized = original_initialized
        prov_mod._provider_instance = original_provider
