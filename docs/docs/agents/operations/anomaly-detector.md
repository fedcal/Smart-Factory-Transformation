---
lang: it
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

## Panoramica

`AnomalyDetector` è il primo agente OPS interamente **deterministico** — non
invoca alcun LLM, non sottoscrive code NATS, non gira su scheduler interno.
Su richiesta (tipicamente da un loop di scheduler esterno o da un comando
operatore) esegue una scansione: per ogni asset del registry, recupera una
finestra di `window_minutes` da `sensor_events`, confronta ogni campione
con la banda di baseline corrispondente (`anomaly_baselines.yaml`, con
override per-macchina opzionale), e produce un'`Anomaly` per ogni campione
fuori-banda.

Un rate limiter (`12 alert/ora`/agente, D-AD-03) protegge il sistema da
storm di alert: ogni anomalia oltre la soglia viene comunque scritta su
`audit.actions` con `Decision.SUPPRESSED` (retention forense, mai silent drop).

## Strumenti Utilizzati

| Tool | Origine | Funzione |
|------|---------|----------|
| `query_timescale` | Phase 3 (`sft_tools.timescale.query`) | Recupera lo slice `(time_range, asset_id)` di `sensor_events`. |

Nota: nessun LLM viene invocato; il modello dichiarato sulla riga di audit
è il sentinel `deterministic@anomaly-detector` con `prompt_hash = "0"*64`.

## Fonti Dati

- **TimescaleDB / PostgreSQL** — hypertable `sensor_events` (input);
  tabelle `audit.actions` (output) e `rate_limit_state` (gestione cap 12/h).
- **YAML domain** — `anomaly_baselines.yaml` (bande per famiglia asset
  con override per `(machine_id, sensor_id)`).
- **Asset registry** — `sft_assets` (lista degli asset da scansionare).

## HITL Tier

`AnomalyDetector` è un agente **fully autonomous** — emette `Decision.AUTO`
per ogni alert sotto soglia. Gli alert vengono pubblicati per i consumatori
downstream (es. `OperatorAssistant`, `PredictiveMaintenance`) che decidono
se escalare.

| Decisione / Caso | Tier | Approvatore |
|------------------|------|-------------|
| Alert anomalia entro rate limit | none (Decision.AUTO) | n/a |
| Alert oltre rate limit (12/h) | none (Decision.SUPPRESSED) | n/a — soppresso ma loggato. |
| Azione correttiva derivata | n/a (delegata al consumatore) | dipende dal consumatore. |

## KPI Impattati

- **MTBF (Mean Time Between Failures)** — rilevazione precoce fuori-banda
  consente intervento prima del fermo macchina.
- **Alert Fatigue Rate** — il rate limiter 12/h previene flood di alert
  che disabituerebbero gli operatori; il counter `suppressed_count`
  è esposto come KPI di tuning.
- **Coverage Sensoriale** — proporzione di sensori con baseline configurata
  vs sensori monitorati (incrementi a ogni iterazione su `anomaly_baselines.yaml`).

## Invocazione

- **Endpoint API**: `POST /v1/agents/anomaly-detector/scan` (Plan 06-12)
  con body `{window_minutes, triggered_by}`.
- **Trigger**: Loop di scheduler esterno (`services/agents-scheduler`,
  Plan 06-09) ogni `window_minutes` minuti, oppure one-shot da operatore.
- **Thread ID**: convenzione `ops.anomaly-detector.<scan-uuid>`.
- **Rate limit**: 12 emissioni/ora/agente (D-AD-03) — eccedenze ⇒
  `Decision.SUPPRESSED`.

## Footprint Audit

- Una riga `audit.actions` per ogni anomalia (emessa o soppressa) con
  `agent_id = "anomaly-detector"`, `cluster = "ops"`,
  `action_type = ANOMALY_ALERT`.
- `evidence_panel`: `tool_calls=[anomaly_detect]` sintetico che cattura
  `asset_id, sensor_id, value, baseline_low, baseline_high, severity,
  rate_count`. `confidence = 1.0` (algoritmo deterministico).
- `decision`: `AUTO` o `SUPPRESSED`.
- Dichiarazione OPS-05 (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) esposta dal modulo `metadata.py` dell'agente.
