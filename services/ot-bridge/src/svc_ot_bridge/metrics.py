"""Prometheus metrics per svc-ot-bridge.

Espone:
    nats_pending_acks_gauge         — pending JetStream acks in flight
    ingest_latency_histogram        — latency event→db ingest (Phase 11 alerting target)
    events_published_total          — Counter per subject
    asyncpg_pool_size_used_gauge    — connessioni asyncpg in uso (T-03-04-pool-dos monitoring)

Endpoint Prometheus su porta configurable (default 8080) via start_metrics(port).
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Gauge: NATS pending acks in flight — alta = publisher lag
nats_pending_acks_gauge = Gauge(
    "nats_pending_acks",
    "Pending JetStream acks in flight — monitoraggio lag publisher",
)

# Histogram: latency event→db ingest (D-48 target: p99 < 200ms)
ingest_latency_histogram = Histogram(
    "ingest_latency_seconds",
    "Latency event→db ingest in secondi",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5],
)

# Counter: eventi pubblicati per subject (drill-down per family/asset)
events_published_total = Counter(
    "events_published_total",
    "Totale eventi pubblicati su NATS JetStream",
    ["subject"],
)

# Gauge: connessioni asyncpg in uso (T-03-04-pool-dos)
asyncpg_pool_size_used_gauge = Gauge(
    "asyncpg_pool_size_used",
    "Connessioni asyncpg in uso — monitoraggio pool exhaustion (max_size=20)",
)


def start_metrics(port: int = 8080) -> None:
    """Avvia l'endpoint Prometheus HTTP su porta specificata.

    Args:
        port: Porta HTTP per /metrics (default 8080, env METRICS_PORT).
    """
    start_http_server(port)
