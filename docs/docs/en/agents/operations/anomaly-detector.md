---
lang: en
agent: anomaly-detector
requirements:
  - OPS-05
tags:
  - agents
  - operations
  - OPS-02
  - OPS-05
---

# AnomalyDetector

## Overview

`AnomalyDetector` is the first fully **deterministic** OPS agent — it does
not invoke any LLM, does not subscribe to NATS queues, and does not run on
an internal scheduler. On demand (typically driven by an external scheduler
loop or an operator command) it runs a scan: for every asset in the
registry, it fetches a `window_minutes`-wide slice of `sensor_events`,
compares every sample against the matching baseline band
(`anomaly_baselines.yaml`, with optional per-machine override), and emits
one `Anomaly` per out-of-band sample.

A rate limiter (`12 alerts/hour`/agent, D-AD-03) shields the system from
alert storms: anomalies above the cap are still written to `audit.actions`
with `Decision.SUPPRESSED` (forensic retention, never silently dropped).

## Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `query_timescale` | Phase 3 (`sft_tools.timescale.query`) | Retrieves the `(time_range, asset_id)` slice of `sensor_events`. |

Note: no LLM is invoked; the model declared on the audit row is the sentinel
`deterministic@anomaly-detector` with `prompt_hash = "0"*64`.

## Data Sources

- **TimescaleDB / PostgreSQL** — `sensor_events` hypertable (input);
  `audit.actions` (output) and `rate_limit_state` (12/h cap state).
- **YAML domain** — `anomaly_baselines.yaml` (per-asset-family bands with
  optional `(machine_id, sensor_id)` overrides).
- **Asset registry** — `sft_assets` (list of assets to scan).

## HITL Tier

`AnomalyDetector` is a **fully autonomous** agent — it emits `Decision.AUTO`
for every alert under the cap. Alerts are published for downstream consumers
(e.g. `OperatorAssistant`, `PredictiveMaintenance`) which decide whether to
escalate.

| Decision / Case | Tier | Approver |
|------------------|------|----------|
| Anomaly alert within rate limit | none (Decision.AUTO) | n/a |
| Alert beyond rate limit (12/h) | none (Decision.SUPPRESSED) | n/a — suppressed but logged. |
| Derived corrective action | n/a (delegated to consumer) | depends on the consumer. |

## KPIs Impacted

- **MTBF (Mean Time Between Failures)** — early out-of-band detection
  enables intervention before machine downtime.
- **Alert Fatigue Rate** — the 12/h rate limiter prevents alert floods
  that would desensitise operators; the `suppressed_count` counter is
  exposed as a tuning KPI.
- **Sensor Coverage** — share of sensors with a configured baseline vs
  monitored sensors (grows with each iteration on `anomaly_baselines.yaml`).

## Invocation

- **API endpoint**: `POST /v1/agents/anomaly-detector/scan` (Plan 06-12)
  with body `{window_minutes, triggered_by}`.
- **Trigger**: External scheduler loop (`services/agents-scheduler`,
  Plan 06-09) every `window_minutes` minutes, or one-shot from operator.
- **Thread ID**: convention `ops.anomaly-detector.<scan-uuid>`.
- **Rate limit**: 12 emissions/hour/agent (D-AD-03) — overflow ⇒
  `Decision.SUPPRESSED`.

## Audit Footprint

- One `audit.actions` row per anomaly (emitted or suppressed) with
  `agent_id = "anomaly-detector"`, `cluster = "ops"`,
  `action_type = ANOMALY_ALERT`.
- `evidence_panel`: synthetic `tool_calls=[anomaly_detect]` capturing
  `asset_id, sensor_id, value, baseline_low, baseline_high, severity,
  rate_count`. `confidence = 1.0` (deterministic algorithm).
- `decision`: `AUTO` or `SUPPRESSED`.
- OPS-05 declaration (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) exposed by the agent's `metadata.py` module.
