---
lang: it
agent: maintenance-coach
requirements:
  - MNT-03
  - MNT-05
tags:
  - agents
  - maintenance
  - MNT-03
  - MNT-05
---

# MaintenanceCoach

## Panoramica

`MaintenanceCoach` guida un tecnico passo-passo nell'esecuzione di una SOP
per la riparazione di un asset di **Mantis Textile Group**. Ogni intervento è
un thread LangGraph asincrono persistito in PostgreSQL
(`langgraph_checkpoints`, migration 005), così il tecnico può pausare e
riprendere anche dopo turni successivi senza perdere lo stato dell'intervento.

Il MTTR (Mean Time To Repair) è calcolato dall'inizio (`mttr_start`) alla
chiusura (`mttr_end`) dell'intervento e registrato in `audit.actions`.

Quando il tecnico usa parole-chiave di richiesta aiuto (`aiuto`, `sono
bloccato`, `help`, `stuck`), il tool `request_help` escalates al supervisore
con il marker `escalation_trigger='technician_request'` nel payload di audit.
Il tecnico riceve una risposta quando il supervisore approva il passo
successivo o modifica l'istruzione SOP.

## Strumenti Utilizzati

| Tool | Origine | Funzione |
|------|---------|----------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Recupera il passo SOP corrente e le istruzioni di sicurezza correlate dall'asset_family e dal `reason_code`. |
| `request_help` | Phase 7 07-04 (`sft_agents.tools.hitl`) | Segnala che il tecnico è bloccato e richiede assistenza supervisore; imposta `escalation_trigger='technician_request'`. |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Alternativa programmatica per escalation diretta (es. condizioni di sicurezza). |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Scrive ogni passo SOP in `audit.actions` con `action_type=COACH_STEP`. |

## Fonti Dati

- **Qdrant `sop_chunks`** — collezione vettoriale Phase 5; fornisce i passi
  SOP per l'asset e il tipo di intervento richiesti.
- **Phase 5 SOP corpus** — documenti sorgente usati per popolare Qdrant;
  incluono SOP-LOOM-001..005, SOP-SPN-001..005, SOP-DYE-001..005.
- **`langgraph_checkpoints` PostgreSQL (migration 005)** — persiste lo stato
  del thread LangGraph per ripresa cross-turno.

## HITL Tier

| Decisione / Caso | Tier | Approvatore |
|---|---|---|
| Passo SOP normale | none (Decision.AUTO) | n/a |
| `request_help` invocato — tecnico bloccato | supervisor (Decision.HITL_SUPERVISOR) | Caposquadra di turno — marker `escalation_trigger='technician_request'` |

## KPI Impattati

- **mttr** — Mean Time To Repair calcolato come differenza `mttr_end -
  mttr_start`; ridotto dalla guida passo-passo che evita errori di procedura.
- **first_time_fix_rate** — proporzione di interventi completati senza
  secondo apertura; indicatore di efficacia della coaching procedurale.
- **intervention_completion_rate** — percentuale di thread Coach giunti a
  completamento vs abbandonati; misura l'usabilità del sistema.
- **technician_help_request_rate** — frequenza di `request_help` per
  intervento; alta frequenza segnala SOP da rivedere o tecnico da formare.

## Invocazione

- **Avvio intervento**: `POST /v1/agents/maintenance-coach/start`
  con body `{"asset_id": "<uuid>", "reason_code": "WEAVING-BE-001", "technician_id": "<uuid>", "user_roles": ["technician"]}`
- **Passo successivo**: `POST /v1/agents/maintenance-coach/step`
  con body `{"thread_id": "coach-<intervention_id>", "technician_input": "<str>"}`
- **Ripresa cross-turno**: `POST /v1/agents/maintenance-coach/resume`
  con body `{"thread_id": "coach-<intervention_id>", "technician_id": "<uuid>"}`
- **Thread ID**: convenzione `coach-<intervention_id>` (Open Q6).
- **Trigger**: on-demand da tecnico da UI factory-floor.

## Audit Footprint

- Una riga `audit.actions` per passo SOP con `agent_id = "maintenance-coach"`,
  `cluster = "maintenance"`, `action_type = COACH_STEP`.
- Le righe `request_help` portano il marker `escalation_trigger='technician_request'`
  nel campo `action_meta` del payload.
- `decision`: `AUTO` (passo normale) / `HITL_SUPERVISOR` (request_help).
- Dichiarazione MNT-05 (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) esposta dal modulo `metadata.py` dell'agente.
