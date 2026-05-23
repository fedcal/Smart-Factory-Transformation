# mnt-downtime-analyzer

**Cluster:** maintenance | **Tier:** AUTO (deterministic — no LLM)

## Role

DowntimeAnalyzer is the fourth agent of the Maintenance & Reliability cluster (Phase 7,
plan 07-09). It operates in two modes:

1. **Reactive (NATS consumer):** Durable JetStream consumer `da-consumer` subscribed to
   `maintenance.downtime.>` — receives `DowntimeEvent` payloads from the sim-textile
   downtime generator (07-05), persists each event to the `maintenance.downtime_events`
   TimescaleDB hypertable (migration 008), and writes a `DOWNTIME_VERDICT` audit row.

2. **On-demand (REST endpoint):** `POST /v1/agents/downtime-analyzer/report` accepts a
   `ReportRequest` (window_start, window_end, by_asset, top_n_pareto) and returns an
   `OEEReport` with full OEE A×P×Q decomposition + Pareto top-N reason_codes.

## OEE Decomposition

- **Availability (A):** `(planned_time - downtime) / planned_time` computed from
  `maintenance.downtime_events` hypertable. For hour-aligned windows, reads from
  `maintenance.oee_hourly` CAGG (O(1)); otherwise raw hypertable scan.
- **Performance (P):** `output_meters / target_meters` from sim-textile `production_state`
  fallback to 1.0 with WARN when source unavailable.
- **Quality (Q):** Cross-cluster audit query on `audit.actions WHERE action_type='QUALITY_VERDICT'`
  (Phase 6 QualityInspector). Falls back to sim-textile production metrics when ops cluster
  has no data for the window (D-DA-02). Source observable via structlog INFO.

## Key Data Sources

- `NATS maintenance.downtime.>` — DowntimeEvent stream
- `PG maintenance.downtime_events` — hypertable (migration 008)
- `PG maintenance.oee_hourly` — CAGG (1h buckets, 5min refresh)
- `PG audit.actions` — QUALITY_VERDICT cross-cluster read (Phase 6)
- `sim-textile production_state` — OEE.P source + OEE.Q fallback
- `sft-assets registry` — asset validation in DowntimeEventRepository

## Audit Trail

- Per-event: `DOWNTIME_VERDICT` + `Decision.AUTO` (thread_id = `maintenance.downtime-analyzer.<event_id>`)
- Per-report: `OEE_REPORT` + `Decision.AUTO` (thread_id = `maintenance.downtime-analyzer.<report_id>`)

## Requirements

- MNT-04: Downtime categorization + OEE/MTTR/MTBF + Pareto recurring
- MNT-06: Audit chain + asset registry integration
