"""KPI aggregation layer — Plan 10-02 (SRV-02).

Computes the 6 real KPIs (OEE, MTTR, MTBF, scrap_rate, throughput, downtime)
from TimescaleDB tables:
  - maintenance.downtime_events  → OEE / MTTR / MTBF / downtime
  - scm.historical_orders        → throughput
  - audit.actions                → scrap_rate (QUALITY_VERDICT proxy)

OEE approximation (documented per RESEARCH note):
  OEE = Availability-only (P=1.0, Q=1.0 approximation);
  Availability = (planned_min - SUM(duration_min)) / planned_min * 100
  clamped to [0, 100].  Phase 11 can wire real P/Q sources.
"""

from svc_api_gateway.kpi.queries import compute_kpi_snapshot

__all__ = ["compute_kpi_snapshot"]
