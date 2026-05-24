"""agent_runner — extract del traceparent NATS + child span CONSUMER (OBS-02).

Fornisce handle_agent_command(), che:
    1. Estrae il contesto W3C traceparent dagli header del messaggio NATS.
    2. Attacca il contesto al thread corrente (propagazione cross-NATS).
    3. Apre uno span figlio CONSUMER sotto la stessa trace del publisher.
    4. Invoca process_fn(payload) all'interno dello span.
    5. Detach in finally (sicuro contro eccezioni).

Pattern (RESEARCH Pattern 1 — NATS Consumer extract):
    carrier = NatsHeaderCarrier(dict(msg.headers or {}))
    ctx = propagate.extract(carrier)
    token = otel_context.attach(ctx)
    try:
        with tracer.start_as_current_span("agent.command", kind=SpanKind.CONSUMER):
            process_fn(msg.data)
    finally:
        otel_context.detach(token)

NON aggiunge auto-instrumentation NATS (non esiste su PyPI — RESEARCH Pitfall 1).
Lo span CONSUMER è il punto di aggancio della trace cross-NATS; evita doppio span
se già esiste uno span attivo nel contesto (non ne crea uno annidato inutile).

Utilizzo:
    from sft_agents.runtime.agent_runner import handle_agent_command
    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)

    # All'interno del loop consumer:
    for msg in msgs:
        handle_agent_command(
            msg=msg,
            tracer=tracer,
            process_fn=lambda payload: asyncio.create_task(invoke_agent(payload)),
        )
"""

from __future__ import annotations

from typing import Any, Callable

import structlog
from opentelemetry import context as otel_context
from opentelemetry import propagate, trace
from opentelemetry.trace import SpanKind

from sft_agents.otel import NatsHeaderCarrier

logger = structlog.get_logger(__name__)


def handle_agent_command(
    msg: Any,
    tracer: Any,
    process_fn: Callable[[bytes], Any],
) -> Any:
    """Estrae il traceparent dal msg NATS e invoca process_fn dentro uno span CONSUMER.

    Il trace_id dello span CONSUMER è identico al trace_id dello span del publisher
    (gateway) perché il contesto viene propagato via W3C traceparent negli header NATS.

    Args:
        msg: Messaggio NATS-like con attributi:
            - ``headers``: dict[str, str] o None — header del messaggio NATS.
            - ``data``: bytes — payload del messaggio.
        tracer: ``opentelemetry.trace.Tracer`` da usare per lo span CONSUMER.
            Tipicamente ``trace.get_tracer(__name__)``.
        process_fn: Callable(payload: bytes) -> Any invocata all'interno dello
            span CONSUMER. Può essere sync o restituire una coroutine (il caller
            è responsabile dell'await in quel caso).

    Returns:
        Il valore di ritorno di process_fn (utile per test e per awaiting).

    Raises:
        Qualsiasi eccezione sollevata da process_fn — non viene swallowed.
    """
    # Estrai il contesto W3C traceparent dagli header NATS.
    raw_headers: dict[str, str] = dict(getattr(msg, "headers", None) or {})
    carrier = NatsHeaderCarrier(raw_headers)
    ctx = propagate.extract(carrier)

    # Attacca il contesto estratto al thread corrente.
    # detach() in finally è OBBLIGATORIO (RESEARCH Pattern 1).
    token = otel_context.attach(ctx)
    result: Any = None
    try:
        with tracer.start_as_current_span(
            "agent.command",
            kind=SpanKind.CONSUMER,
        ) as span:
            # Log diagnostico (non espone dati sensibili).
            span_ctx = span.get_span_context()
            logger.debug(
                "agent_command_consumer_span_started",
                trace_id=f"{span_ctx.trace_id:x}",
                span_id=f"{span_ctx.span_id:x}",
                has_traceparent="traceparent" in raw_headers,
            )

            payload: bytes = getattr(msg, "data", b"")
            result = process_fn(payload)
    finally:
        otel_context.detach(token)

    return result


__all__ = ["handle_agent_command"]
