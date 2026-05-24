"""nats_publisher — publish di comandi agent su NATS con inject del traceparent (OBS-02).

Fornisce publish_agent_command(), che inietta il W3C traceparent nel dict di
header NATS prima di invocare la funzione di publish sottostante.

Pattern (da RESEARCH Pattern 1):
    headers: dict[str, str] = {}
    propagate.inject(NatsHeaderCarrier(headers))   # inietta traceparent
    await nats_js.publish(subject, payload, headers=headers)

Nessun esporter OTLP verso Langfuse — solo il CallbackHandler LangChain già
wired in langfuse_callback.py (RESEARCH Pitfall 3: evita trace duplicate).

Utilizzo tipico:
    from svc_api_gateway.nats_publisher import publish_agent_command

    def nats_publish(subject, payload, headers):
        asyncio.get_event_loop().run_until_complete(
            nats_js.publish(subject, payload, headers=headers)
        )

    publish_agent_command(
        publish_fn=nats_publish,
        subject="sft.agents.cmd.quality",
        payload=event_bytes,
    )

Per codice asincrono, avvolgi la chiamata async al di fuori — questa funzione
è synchronous per essere testabile con un fake_publish senza event loop.
La variante async è publish_agent_command_async() qui sotto.
"""

from __future__ import annotations

from typing import Callable

import structlog
from opentelemetry import propagate

from sft_agents.otel import NatsHeaderCarrier

logger = structlog.get_logger(__name__)


def publish_agent_command(
    publish_fn: Callable[[str, bytes, dict[str, str]], None],
    subject: str,
    payload: bytes,
) -> None:
    """Inietta il traceparent W3C e invoca publish_fn con gli header arricchiti.

    Questa funzione è synchronous per facilitare il testing con fake callables.
    Per il publish async su NATS JetStream, usa publish_agent_command_async().

    Args:
        publish_fn: Callable(subject, payload, headers) — ad es. un wrapper
            che chiama ``await nats_js.publish(subject, payload, headers=headers)``.
        subject: Soggetto NATS (es. "sft.agents.cmd.quality").
        payload: Payload bytes del comando (tipicamente JSON UTF-8).
    """
    headers: dict[str, str] = {}
    propagate.inject(NatsHeaderCarrier(headers))

    logger.debug(
        "nats_publish_agent_command",
        subject=subject,
        has_traceparent="traceparent" in headers,
        payload_bytes=len(payload),
    )

    publish_fn(subject, payload, headers)


async def publish_agent_command_async(
    nats_js: object,
    subject: str,
    payload: bytes,
) -> None:
    """Inietta il traceparent W3C e pubblica su NATS JetStream (async).

    Variante async di publish_agent_command per l'uso diretto con nats-py.

    Args:
        nats_js: NATS JetStream context (``nats.JetStream``-like) con metodo
            ``publish(subject, payload, headers=...) coroutine``.
        subject: Soggetto NATS (es. "sft.agents.cmd.quality").
        payload: Payload bytes del comando (tipicamente JSON UTF-8).
    """
    headers: dict[str, str] = {}
    propagate.inject(NatsHeaderCarrier(headers))

    logger.debug(
        "nats_publish_agent_command_async",
        subject=subject,
        has_traceparent="traceparent" in headers,
        payload_bytes=len(payload),
    )

    await nats_js.publish(subject, payload, headers=headers)  # type: ignore[union-attr]


__all__ = ["publish_agent_command", "publish_agent_command_async"]
