"""Asyncio entry point orchestrator per svc-ot-bridge.

Wire publisher + writer + subscriber via asyncio.Queue handoff.
Gestisce graceful shutdown (SIGINT/SIGTERM) con final flush e audit events.

Env vars:
    OPCUA_URL:       OPC-UA endpoint (default: opc.tcp://sim-textile:4840)
    NATS_URL:        NATS server URL (default: nats://nats:4222)
    TIMESCALE_DSN:   PostgreSQL DSN — REQUIRED (no default — fail fast se mancante)
    METRICS_PORT:    Prometheus port (default: 8080)
    LOG_LEVEL:       structlog level (default: INFO)
    WORKER_COUNT:    Numero worker task asyncio (default: 4)

D-51: bridge e' subscribe-only verso OPC-UA. Nessun write API call in questo file.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from datetime import datetime, timezone

import structlog

UTC = timezone.utc

# Configura structlog JSON output prima di qualsiasi log
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)

logger = structlog.get_logger(__name__)


async def run() -> None:
    """Asyncio main loop del bridge OT.

    1. Legge env vars (OPCUA_URL, NATS_URL, TIMESCALE_DSN obbligatorio)
    2. Avvia Prometheus metrics endpoint
    3. Connette NatsPublisher e TimescaleWriter
    4. Emette AuditEvent bridge_start
    5. Avvia OpcUaSubscriber e worker tasks
    6. Attende shutdown (SIGINT/SIGTERM)
    7. Graceful shutdown: cancel workers, close components, emette bridge_stop
    """
    from svc_ot_bridge.metrics import start_metrics
    from svc_ot_bridge.models import AuditEvent
    from svc_ot_bridge.nats_publisher import NatsPublisher
    from svc_ot_bridge.normalizer import normalize_datachange
    from svc_ot_bridge.opcua_client import OpcUaSubscriber
    from svc_ot_bridge.timescale_writer import TimescaleWriter

    # Env vars — TIMESCALE_DSN e' required (fail fast su None)
    opcua_url = os.environ.get("OPCUA_URL", "opc.tcp://sim-textile:4840")
    nats_url = os.environ.get("NATS_URL", "nats://nats:4222")
    timescale_dsn = os.environ.get("TIMESCALE_DSN")
    if timescale_dsn is None:
        raise RuntimeError(
            "TIMESCALE_DSN env var e' richiesto. "
            "Usa: postgresql://user:pass@timescaledb:5432/sft"
        )
    metrics_port = int(os.environ.get("METRICS_PORT", "8080"))
    worker_count = int(os.environ.get("WORKER_COUNT", "4"))

    log = structlog.get_logger("ot-bridge").bind(service="ot-bridge")
    log.info("bridge_starting", opcua_url=opcua_url, nats_url=nats_url, workers=worker_count)

    # Avvia Prometheus metrics endpoint
    start_metrics(metrics_port)

    # Inizializza componenti
    publisher = NatsPublisher()
    await publisher.start(nats_url)

    writer = TimescaleWriter(timescale_dsn)
    await writer.start()

    # Audit: bridge_start (OQ3)
    await publisher.publish_audit(
        AuditEvent(
            ts=datetime.now(UTC),
            level="INFO",
            event_type="bridge_start",
            details={"opcua_url": opcua_url, "nats_url": nats_url, "workers": worker_count},
        )
    )

    # Queue per handoff OPC-UA → worker (backpressure: maxsize=10000)
    event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)

    # Subscriber OPC-UA (subscribe-only, D-51 Layer 3)
    subscriber = OpcUaSubscriber(opcua_url, event_queue)
    await subscriber.start()

    # Shutdown event
    shutdown_event = asyncio.Event()

    def _handle_signal(sig: int) -> None:
        log.info("shutdown_signal_received", signal=sig)
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal, sig)

    async def worker() -> None:
        """Worker task: drain queue, normalizza, publish + write."""
        while not shutdown_event.is_set():
            try:
                node, val, data = await asyncio.wait_for(event_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                # Risolvi asset_id e tag_id dalla nodeid_map del subscriber
                identity = await subscriber.get_node_identity(node)
                if identity is None:
                    log.warning("unknown_node", node_id=str(node.nodeid))
                    event_queue.task_done()
                    continue

                asset_id, tag_id = identity

                # Estrai timestamp sorgente e status code
                try:
                    source_ts = data.monitored_item.Value.SourceTimestamp
                    if source_ts is None or source_ts.tzinfo is None:
                        source_ts = datetime.now(UTC)
                    opcua_status = data.monitored_item.Value.StatusCode.value
                except AttributeError:
                    source_ts = datetime.now(UTC)
                    opcua_status = 0

                # Valore float dal nodo (gestisce None → NaN)
                opcua_value = float(val) if val is not None else float("nan")

                # Normalizza in SensorEvent
                event = normalize_datachange(
                    asset_id=asset_id,
                    tag_id=tag_id,
                    opcua_value=opcua_value,
                    opcua_status=opcua_status,
                    source_ts=source_ts,
                    server_received=datetime.now(UTC),
                )

                # Fan-out: NATS publish + TimescaleDB write
                await publisher.publish_event(event)
                await writer.push(event)

            except Exception as exc:
                log.error(
                    "worker_event_error",
                    error=str(exc),
                    node_id=str(node.nodeid) if node else "unknown",
                )
            finally:
                event_queue.task_done()

    # Lancia worker tasks
    worker_tasks = [asyncio.create_task(worker()) for _ in range(worker_count)]
    log.info("bridge_running", worker_count=worker_count)

    # Attende shutdown
    await shutdown_event.wait()
    log.info("bridge_shutting_down")

    # Graceful shutdown
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)

    await subscriber.close()
    await writer.close()

    # Audit: bridge_stop (OQ3)
    try:
        await publisher.publish_audit(
            AuditEvent(
                ts=datetime.now(UTC),
                level="INFO",
                event_type="bridge_stop",
                details={"reason": "graceful_shutdown"},
            )
        )
    except Exception as exc:
        log.warning("bridge_stop_audit_failed", error=str(exc))

    await publisher.close()
    log.info("bridge_stopped")


def main() -> None:
    """Entry point per il container ot-bridge.

    Lancia l'asyncio loop con run().
    """
    asyncio.run(run())


if __name__ == "__main__":
    main()
