---
lang: it
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

## Panoramica

`DowntimeAnalyzer` ingerisce gli eventi di downtime dal simulatore
sim-textile (subject NATS `maintenance.downtime.<asset_id>`), li persiste in
PostgreSQL/TimescaleDB (hypertable `maintenance.downtime_events`, migration
008), e fornisce on-demand i report OEE (Overall Equipment Effectiveness)
con decomposizione **Availability × Performance × Quality** più analisi
Pareto top-N `reason_code`.

La componente Quality è calcolata cross-cluster leggendo le decisioni
`QualityInspector` (cluster ops, Phase 6) con fallback automatico ai metrics
del simulatore in caso di gap (D-DA-02).

`DowntimeAnalyzer` è un **agente deterministico** — non invoca LLM, non ha
percorsi HITL. I report vengono revisionati dai responsabili tramite
dashboard, non tramite approvazione transazionale inline.

## Strumenti Utilizzati

| Tool | Origine | Funzione |
|------|---------|----------|
| `query_timescale` | Phase 3 (`sft_tools.timescale.query`) | Recupera gli eventi da `maintenance.downtime_events` (hypertable) per la finestra temporale richiesta; usato sia per ingest che per query OEE. |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Scrive ogni evento ingerito (`DOWNTIME_VERDICT`) e ogni report OEE generato (`OEE_REPORT`) in `audit.actions`. |

Nota: nessun LLM viene invocato; il modello dichiarato sulle righe di audit
è il sentinel `deterministic@downtime-analyzer` con `prompt_hash = "0"*64`.

## Fonti Dati

- **NATS `maintenance.downtime.>`** — stream eventi downtime dal simulatore
  sim-textile (input primario per ingest in real-time).
- **PostgreSQL `maintenance.downtime_events` (migration 08)** — hypertable
  TimescaleDB; store persistente per query OEE e Pareto storici.
- **PostgreSQL `audit.actions` cross-cluster `QUALITY_VERDICT`** — lettura
  delle decisioni `QualityInspector` (Phase 6 06-01) per componente Quality
  dell'OEE; fallback D-DA-02 se gap temporale.
- **sim-textile `production_state.py` (06-09)** — fonte di fallback per la
  componente Quality in assenza di dati QualityInspector.
- **sft-assets registry** — mappa `asset_id` → `asset_family` per aggregazione
  Pareto per linea / famiglia macchina.

## HITL Tier

| Decisione / Caso | Tier | Approvatore |
|---|---|---|
| Tutti i report OEE e ingest downtime | none (Decision.AUTO) | n/a — revisione via dashboard |

Nessun percorso HITL: l'agente è puramente analitico. Le azioni correttive
derivate dai report sono responsabilità del processo operativo.

## KPI Impattati

- **oee_availability** — (Planned Production Time − Downtime) / Planned
  Production Time; impattato direttamente dall'ingest degli eventi.
- **oee_performance** — (Actual Output / Theoretical Output) calcolato dai
  cicli produttivi registrati dal simulatore.
- **oee_quality** — (Good Units / Total Units) cross-cluster con QualityInspector.
- **mtbf** — Mean Time Between Failures calcolato sulle sequenze di eventi
  per asset; comparato con la stima RUL di `PredictiveMaintenance`.
- **top_5_downtime_reason_codes** — Pareto dei `reason_code` più frequenti
  per finestra temporale; guida la priorità degli interventi preventivi.

## Invocazione

- **Endpoint API**: `POST /v1/agents/downtime-analyzer/report`
  con body `{"window_start": "<ISO8601>", "window_end": "<ISO8601>", "by_asset": false, "top_n_pareto": 5}`
- **Trigger**: on-demand da caposquadra o scheduler dashboard; ingest NATS
  è continuo (consumer JetStream persistente).
- **Thread ID**: convenzione `maintenance.downtime-analyzer.<uuid4>`.
- **Risposta**: `200 OK` con `OEEReport` (availability, performance, quality,
  pareto_top_n); operazione sincrona.

## Audit Footprint

- Riga `audit.actions` per ogni evento downtime ingerito con
  `agent_id = "downtime-analyzer"`, `cluster = "maintenance"`,
  `action_type = DOWNTIME_VERDICT`.
- Riga `audit.actions` per ogni report OEE generato con
  `action_type = OEE_REPORT`; include la finestra temporale e il payload
  aggregato nel campo `evidence_panel`.
- `decision`: sempre `AUTO` (agente deterministico).
- Dichiarazione MNT-05 (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) esposta dal modulo `metadata.py` dell'agente.
