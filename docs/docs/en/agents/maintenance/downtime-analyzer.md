---
lang: en
agent: downtime-analyzer
requirements:
  - MNT-04
  - MNT-05
tags:
  - agents
  - maintenance
  - MNT-04
  - MNT-05
---

# DowntimeAnalyzer

## Overview

`DowntimeAnalyzer` ingests downtime events from the sim-textile simulator
(NATS subject `maintenance.downtime.<asset_id>`), persists them in
PostgreSQL/TimescaleDB (hypertable `maintenance.downtime_events`, migration
008), and provides on-demand OEE (Overall Equipment Effectiveness) reports
with **Availability × Performance × Quality** decomposition plus Pareto
analysis of the top-N `reason_code`.

The Quality component is computed cross-cluster by reading `QualityInspector`
decisions (ops cluster, Phase 6) with automatic fallback to simulator metrics
when data gaps occur (D-DA-02).

`DowntimeAnalyzer` is a **deterministic agent** — it does not invoke any LLM
and has no HITL paths. Reports are reviewed by managers via dashboard, not via
inline transactional approval.

## Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `query_timescale` | Phase 3 (`sft_tools.timescale.query`) | Retrieves events from `maintenance.downtime_events` (hypertable) for the requested time window; used both for ingest and OEE queries. |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Writes every ingested event (`DOWNTIME_VERDICT`) and every generated OEE report (`OEE_REPORT`) to `audit.actions`. |

Note: no LLM is invoked; the model declared on audit rows is the sentinel
`deterministic@downtime-analyzer` with `prompt_hash = "0"*64`.

## Data Sources

- **NATS `maintenance.downtime.>`** — downtime event stream from the
  sim-textile simulator (primary real-time ingest input).
- **PostgreSQL `maintenance.downtime_events` (migration 08)** — TimescaleDB
  hypertable; persistent store for historical OEE queries and Pareto analysis.
- **PostgreSQL `audit.actions` cross-cluster `QUALITY_VERDICT`** — reads
  `QualityInspector` decisions (Phase 6 06-01) for the OEE Quality component;
  D-DA-02 fallback when time gap exists.
- **sim-textile `production_state.py` (06-09)** — fallback source for the
  Quality component when QualityInspector data is unavailable.
- **sft-assets registry** — maps `asset_id` to `asset_family` for Pareto
  aggregation by line or machine family.

## HITL Tier

| Decision / Case | Tier | Approver |
|---|---|---|
| All OEE reports and downtime ingest | none (Decision.AUTO) | n/a — reviewed via dashboard |

No HITL path: the agent is purely analytical. Corrective actions derived from
reports are the responsibility of the operational process.

## KPIs Impacted

- **oee_availability** — (Planned Production Time − Downtime) / Planned
  Production Time; directly impacted by event ingest.
- **oee_performance** — (Actual Output / Theoretical Output) computed from
  production cycles recorded by the simulator.
- **oee_quality** — (Good Units / Total Units) cross-cluster with
  QualityInspector.
- **mtbf** — Mean Time Between Failures computed from per-asset event
  sequences; compared against `PredictiveMaintenance` RUL estimates.
- **top_5_downtime_reason_codes** — Pareto of most frequent `reason_code`
  values for the time window; guides preventive maintenance priorities.

## Invocation

- **API endpoint**: `POST /v1/agents/downtime-analyzer/report`
  with body `{"window_start": "<ISO8601>", "window_end": "<ISO8601>", "by_asset": false, "top_n_pareto": 5}`
- **Trigger**: on-demand from shift supervisor or dashboard scheduler; NATS
  ingest is continuous (persistent JetStream consumer).
- **Thread ID**: convention `maintenance.downtime-analyzer.<uuid4>`.
- **Response**: `200 OK` with `OEEReport` (availability, performance, quality,
  pareto_top_n); synchronous operation.

## Audit Footprint

- One `audit.actions` row per ingested downtime event with
  `agent_id = "downtime-analyzer"`, `cluster = "maintenance"`,
  `action_type = DOWNTIME_VERDICT`.
- One `audit.actions` row per generated OEE report with
  `action_type = OEE_REPORT`; includes the time window and aggregated payload
  in the `evidence_panel` field.
- `decision`: always `AUTO` (deterministic agent).
- MNT-05 declaration (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) exposed by the agent's `metadata.py` module.
