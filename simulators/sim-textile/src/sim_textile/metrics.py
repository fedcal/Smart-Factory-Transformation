"""Prometheus metrics per sim-textile (D-50, IOT-01).

Espone endpoint /metrics su porta 8080 (default).
Counters: sim_events_emitted_total, sim_fault_injected_total.
Gauge: sim_message_rate_per_second.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, start_http_server

# Counter: eventi emessi per asset_family, asset_id, tag_id
sim_events_emitted_total = Counter(
    "sim_events_emitted_total",
    "Numero totale di eventi sensore emessi dal simulatore",
    ["asset_family", "asset_id", "tag_id"],
)

# Counter: fault injection applicati per tipo e family
sim_fault_injected_total = Counter(
    "sim_fault_injected_total",
    "Numero totale di fault injection applicati",
    ["type", "asset_family"],
)

# Gauge: rate eventi al secondo (aggiornato periodicamente)
sim_message_rate_gauge = Gauge(
    "sim_message_rate_per_second",
    "Rate eventi emessi al secondo (media mobile)",
)


def start_metrics(port: int = 8080) -> None:
    """Avvia il server HTTP Prometheus su porta port.

    Args:
        port: Porta di ascolto per il server /metrics (default 8080).
    """
    start_http_server(port)
