---
lang: en
agent: predictive-maintenance
requirements:
  - MNT-01
  - MNT-05
tags:
  - agents
  - maintenance
  - MNT-01
  - MNT-05
---

# PredictiveMaintenance

## Overview

`PredictiveMaintenance` estimates the Remaining Useful Life (RUL) of a
textile asset (looms, spinning frames) using a lightweight ML model (Ridge
regression) trained on the NASA C-MAPSS FD001+FD003 dataset. It is
event-driven: it is triggered automatically when `AnomalyDetector` (Phase 6
ops cluster) detects a `major` or `critical` anomaly and publishes to the
NATS subject `maintenance.predict.<asset_id>`.

The model returns a `health_index` in `[0.0, 1.0]` (1.0 = perfect). Values
`< 0.3` trigger the HITL `supervisor` tier — the system automatically escalates
to the shift supervisor to schedule maintenance. Values `≥ 0.3` result in an
`AUTO` decision with write-only to `audit.actions`.

## Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `query_timescale` | Phase 3 (`sft_tools.timescale.query`) | Retrieves the `sensor_events` window for the requested asset to compute the RUL feature vector. |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Sends the approval request to the shift supervisor when `health_index < 0.3`. |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Writes the RUL estimate to `audit.actions` with `action_type=RUL_ESTIMATE`. |

Note: the ML model (`ridge-fd001-fd003-v1.0.joblib`) is loaded in-process at
startup; inference is deterministic given the same input window.

## Data Sources

- **TimescaleDB `sensor_events`** — Phase 3 hypertable; provides the
  temporal window of sensor samples used to compute the feature vector.
- **sft-ml `ridge-fd001-fd003-v1.0.joblib`** — ML model artefact trained on
  NASA C-MAPSS FD001+FD003; loaded at agent process startup.
- **sft-assets registry** — provides `asset_family` to select the correct
  normalisation profile before inference.

## HITL Tier

| Decision / Case | Tier | Approver |
|---|---|---|
| `health_index ≥ 0.3` — normal RUL estimate | none (Decision.AUTO) | n/a |
| `health_index < 0.3` — critical deterioration | supervisor (Decision.HITL_SUPERVISOR) | Shift supervisor |

## KPIs Impacted

- **MTBF (Mean Time Between Failures)** — early identification of at-risk
  assets enables preventive intervention before unplanned downtime, increasing
  mean time between failures.
- **planned_vs_unplanned_downtime** — RUL estimates shift unplanned downtime
  to planned downtime; the ratio is the cluster's primary operational KPI.
- **rul_accuracy_mae** — Mean Absolute Error of the RUL estimate measured on
  the C-MAPSS test set; monitored via Langfuse to detect model drift in
  production.

## Invocation

- **API endpoint**: `POST /v1/agents/predictive-maintenance/score`
  with body `{"asset_id": "<uuid>", "triggered_by_action_id": "<uuid>", "user_roles": ["operator"]}`
- **Trigger**: NATS event `maintenance.predict.<asset_id>` published by
  `AnomalyDetector` on `major`/`critical` anomaly (cross-cluster wiring via
  NATS JetStream).
- **Thread ID**: convention `maintenance.predictive-maintenance.<uuid4>`.
- **Response**: `202 Accepted` when HITL; `200 OK` with `RULEstimate` when AUTO.

## Audit Footprint

- One `audit.actions` row per estimate with `agent_id = "predictive-maintenance"`,
  `cluster = "maintenance"`, `action_type = RUL_ESTIMATE` (migration 009, 07-01).
- `evidence_panel.tool_calls[0].args.triggered_by_action_id` links the estimate
  to `AnomalyDetector`'s `action_id` (MNT-06 audit chain).
- `decision`: `AUTO` (`health_index ≥ 0.3`) or `HITL_SUPERVISOR` (`health_index < 0.3`).
- MNT-05 declaration (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) exposed by the agent's `metadata.py` module.
