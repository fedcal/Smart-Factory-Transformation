"""NatsHeaderCarrier — adattatore MutableMapping per propagazione OTEL su NATS.

Implementa il protocollo TextMap carrier di OpenTelemetry per permettere
inject/extract del contesto W3C traceparent negli header dei messaggi NATS.

Non esiste un package `opentelemetry-instrumentation-nats` su PyPI (RESEARCH Pitfall 1).
Questo carrier manuale (~30 righe) è il pattern raccomandato dalla specifica OTEL.

Utilizzo:
    from opentelemetry.propagate import inject, extract
    from sft_agents.otel.nats_carrier import NatsHeaderCarrier

    # Publisher (inject):
    headers: dict[str, str] = {}
    inject(NatsHeaderCarrier(headers))
    await nc.publish("subject", payload, headers=headers)

    # Subscriber (extract):
    ctx = extract(NatsHeaderCarrier(msg.headers or {}))
    with tracer.start_as_current_span("process", context=ctx):
        ...
"""

from __future__ import annotations

from collections.abc import Iterator, MutableMapping


class NatsHeaderCarrier(MutableMapping[str, str]):
    """Adatta un dict di header NATS al protocollo TextMap di OpenTelemetry.

    Wrappa un ``dict[str, str]`` di header in ingresso/uscita per permettere
    a ``opentelemetry.propagate.inject`` e ``extract`` di leggere/scrivere
    il contesto W3C traceparent (e tracestate opzionale).

    Args:
        headers: Il dizionario di header NATS da wrappare.
            Viene modificato in-place da ``inject``.
    """

    def __init__(self, headers: dict[str, str]) -> None:
        self._headers = headers

    def __getitem__(self, key: str) -> str:
        return self._headers[key]

    def __setitem__(self, key: str, value: str) -> None:
        self._headers[key] = value

    def __delitem__(self, key: str) -> None:
        del self._headers[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._headers)

    def __len__(self) -> int:
        return len(self._headers)
