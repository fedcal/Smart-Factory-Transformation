---
lang: it
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

## Panoramica

`PredictiveMaintenance` stima la Remaining Useful Life (RUL) di un asset
tessile (telai, filatoi) usando un modello ML lightweight (Ridge regression)
addestrato sul dataset NASA C-MAPSS FD001+FD003. È event-driven: viene
attivato automaticamente quando `AnomalyDetector` (Phase 6 cluster ops)
rileva un'anomalia con severità `major` o `critical` e pubblica sul subject
NATS `maintenance.predict.<asset_id>`.

Il modello restituisce un `health_index` in `[0.0, 1.0]` (1.0 = perfetto).
Valori `< 0.3` attivano il tier HITL `supervisor` — il sistema escalates
automaticamente a caposquadra per pianificare la manutenzione. Valori `≥ 0.3`
risultano in una decisione `AUTO` con sola scrittura su `audit.actions`.

## Strumenti Utilizzati

| Tool | Origine | Funzione |
|------|---------|----------|
| `query_timescale` | Phase 3 (`sft_tools.timescale.query`) | Recupera la finestra di `sensor_events` per l'asset richiesto ai fini del calcolo RUL. |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Invia la richiesta di approvazione al caposquadra quando `health_index < 0.3`. |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Scrive la stima RUL in `audit.actions` con `action_type=RUL_ESTIMATE`. |

Nota: il modello ML (`ridge-fd001-fd003-v1.0.joblib`) è caricato in-process
all'avvio; la stima è deterministica condizionatamente alla finestra di input.

## Fonti Dati

- **TimescaleDB `sensor_events`** — hypertable Phase 3; fornisce la finestra
  temporale di campioni sensore su cui il modello calcola il feature vector.
- **sft-ml `ridge-fd001-fd003-v1.0.joblib`** — artefatto modello ML addestrato
  su NASA C-MAPSS FD001+FD003; caricato all'avvio del processo agente.
- **sft-assets registry** — fornisce `asset_family` per selezionare il
  corretto profilo di normalizzazione prima dell'inference.

## HITL Tier

| Decisione / Severità | Tier | Approvatore |
|---|---|---|
| `health_index ≥ 0.3` — RUL stima normale | none (Decision.AUTO) | n/a |
| `health_index < 0.3` — deterioramento critico | supervisor (Decision.HITL_SUPERVISOR) | Caposquadra di turno |

## KPI Impattati

- **MTBF (Mean Time Between Failures)** — l'identificazione precoce degli
  asset a rischio consente interventi preventivi prima del fermo non
  pianificato, incrementando il tempo medio tra guasti.
- **planned_vs_unplanned_downtime** — la stima RUL sposta fermi non
  pianificati verso fermi pianificati; il rapporto è il KPI operativo
  primario del cluster maintenance.
- **rul_accuracy_mae** — Mean Absolute Error della stima RUL misurato sul
  dataset di test C-MAPSS; monitorato via Langfuse per rilevare drift del
  modello in produzione.

## Invocazione

- **Endpoint API**: `POST /v1/agents/predictive-maintenance/score`
  con body `{"asset_id": "<uuid>", "triggered_by_action_id": "<uuid>", "user_roles": ["operator"]}`
- **Trigger**: evento NATS `maintenance.predict.<asset_id>` pubblicato da
  `AnomalyDetector` su anomalia `major`/`critical` (cross-cluster wiring
  via NATS JetStream).
- **Thread ID**: convenzione `maintenance.predictive-maintenance.<uuid4>`.
- **Risposta sincrona**: `202 Accepted` quando HITL; `200 OK` con `RULEstimate`
  quando AUTO.

## Audit Footprint

- Una riga `audit.actions` per ogni stima con `agent_id = "predictive-maintenance"`,
  `cluster = "maintenance"`, `action_type = RUL_ESTIMATE` (migration 009, 07-01).
- `evidence_panel.tool_calls[0].args.triggered_by_action_id` collega la stima
  all'`action_id` di `AnomalyDetector` (catena di audit MNT-06).
- `decision`: `AUTO` (`health_index ≥ 0.3`) o `HITL_SUPERVISOR` (`health_index < 0.3`).
- Dichiarazione MNT-05 (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) esposta dal modulo `metadata.py` dell'agente.
