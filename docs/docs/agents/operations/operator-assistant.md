---
lang: it
agent: operator-assistant
requirements:
  - OPS-05
tags:
  - agents
  - operations
  - OPS-01
  - OPS-05
---

# OperatorAssistant

## Panoramica

`OperatorAssistant` è l'agente conversazionale di front-line per gli operatori
di stabilimento di **Mantis Textile Group**. Risponde in italiano e in inglese
a domande operative (es. "Il telaio LOOM-01 si è fermato, cosa devo fare?"),
recupera procedure (SOP) e dati sensoriali pertinenti, e — quando l'azione
proposta richiede una decisione critica — escala al caposquadra tramite la
pipeline HITL (Human-in-the-Loop).

L'agente è realizzato come ciclo ReAct (LangGraph
`create_react_agent`, ricursione limitata a 5 iterazioni) con un toolbelt di
5 strumenti. Ogni richiesta istanzia gli strumenti ex-novo: i `user_roles`
fluiscono nelle ACL del RAG senza poter trapelare da una sessione all'altra
(mitigazione T-V6-injection).

## Strumenti Utilizzati

| Tool | Origine | Funzione |
|------|---------|----------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Ricerca ibrida su Qdrant `sop_chunks` con pre-filtro ACL su `user_roles`. |
| `traverse_graph` | Phase 5 (`sft_knowledge.tools.graph`) | Navigazione del grafo Neo4j Machine→Part→FailureMode→SOP. |
| `query_timescale` | Phase 3 (`sft_tools.timescale.query`) | Estrae slice di `sensor_events` (hypertable TimescaleDB) per asset/finestra. |
| `escalate_to_supervisor` | Plan 06-05 (`sft_agents.tools.hitl`) | Crea un'`approval_action` tier=SUPERVISOR e la pubblica su NATS. |
| `log_event` | Plan 06-05 (`sft_agents.tools.audit`) | Scrive una riga in `audit.actions` con `EvidencePanel` per ogni interazione. |

## Fonti Dati

- **Qdrant** — collezione `sop_chunks` (procedure, runbook, manuali tessili).
- **Neo4j** — grafo entità tessili (telai, orditoi, parti, modalità di guasto, SOP).
- **TimescaleDB / PostgreSQL** — hypertable `sensor_events`; tabella `audit.actions` per log.
- **NATS JetStream** — subject `hitl.approvals.new.>` per escalation HITL.

## HITL Tier

`OperatorAssistant` non decide autonomamente azioni critiche: ogni
escalation transita per `escalate_to_supervisor`, che inserisce un
record in coda approvazioni.

| Decisione / Caso | Tier | Approvatore |
|------------------|------|-------------|
| Risposta informativa (read-only) | none | n/a — solo `log_event` su audit. |
| Suggerimento procedura (link a SOP) | none | n/a — risposta con citazioni inline. |
| Azione operativa proposta (ferma macchina, reset) | SUPERVISOR | Caposquadra di turno. |
| Azione safety-critical (intervento PLC) | MANAGER + SAFETY_INTERLOCK | Manager di produzione + responsabile sicurezza. |

## KPI Impattati

- **MTTR** (Mean Time To Recovery) — risposte rapide riducono il tempo di
  diagnosi prima dell'intervento del tecnico.
- **First-Time-Fix Rate** — le SOP citate inline migliorano la probabilità
  che il primo tentativo risolva il problema.
- **Knowledge Reuse Rate** — ogni interazione di successo viene loggata
  e diventa potenziale dataset per training/curation futura.

## Invocazione

- **Endpoint API**: `POST /v1/agents/operator-assistant/chat` (Plan 06-12)
  con body `{query, user_roles, thread_id, target_agent?}`.
- **Trigger**: Manuale (operatore via UI), oppure routing da HybridRouter
  del supervisor.
- **Thread ID**: convenzione `ops.operator-assistant.<uuid4>`.
- **Recursion limit**: 5 iterazioni (D-OA-01) — vincolo difensivo contro
  loop ReAct degenerati.

## Footprint Audit

Per ogni interazione, l'agente scrive una riga in `audit.actions` con:

- `agent_id = "operator-assistant"`, `cluster = "ops"`.
- `action_type = ESCALATION` (quando `escalate_to_supervisor` viene chiamato)
  oppure logging-only via `log_event`.
- `evidence_panel`: contiene `input_summary` (max 500 char), `tool_calls`,
  `rag_citations`, `confidence`, `model`, `prompt_hash`, `tokens`,
  `duration_ms`.
- `thread_id` propagato per consentire ricostruzione end-to-end della sessione.
- Dichiarazione OPS-05 (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) esposta dal modulo `metadata.py` dell'agente — single
  source of truth condivisa con questa pagina di documentazione.
