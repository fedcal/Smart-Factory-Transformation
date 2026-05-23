---
lang: it
agent: production-planner
requirements:
  - OPS-05
tags:
  - agents
  - operations
  - OPS-03
  - OPS-05
---

# ProductionPlanner

## Panoramica

`ProductionPlanner` è l'agente di pianificazione produzione di **Mantis
Textile Group**. Riceve l'elenco degli ordini aperti, la capacità degli asset
(telai, orditoi, finissaggio) e la lista delle modalità di guasto note,
e produce una bozza di schedule deterministica utilizzando un'euristica
scelta dal chiamante (`spt` — Shortest Processing Time, oppure `edd` —
Earliest Due Date).

L'LLM **non altera mai** la lista degli items pianificati: viene invocato
soltanto per generare il `rationale_md` (T-V6-llm-hallucination). La bozza
finale è instradata sempre verso il caposquadra (`Tier.SUPERVISOR`) tramite
`human_approval_node`.

## Strumenti Utilizzati

| Tool | Origine | Funzione |
|------|---------|----------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Recupera 5 SOP rilevanti per la strategia (`spt`/`edd`); usato solo per citazioni nel rationale. |

Nota: l'algoritmo di scheduling è una funzione pura
(`sft_domain.scheduling.heuristic.schedule_spt` / `schedule_edd`,
Plan 06-04) e **non** è esposto come tool — è invocato direttamente
dall'orchestratore agentico.

## Fonti Dati

- **YAML domain** — `orders.yaml`, `asset_capacity.yaml`,
  `failure_modes.yaml` caricati via i loader di `sft_domain.ops.schedule`.
- **Qdrant** — collezione `sop_chunks` (per le citazioni del rationale).
- **PostgreSQL** — tabella `audit.actions` (output: bozza schedule + decisione HITL).
- **NATS JetStream** — subject `hitl.approvals.new.ops.production-planner.>`.

## HITL Tier

`ProductionPlanner` non ha mai diritto di auto-applicazione: ogni schedule
draft richiede sempre approvazione umana, indipendentemente dalla strategia
o dall'orizzonte temporale.

| Decisione / Caso | Tier | Approvatore |
|------------------|------|-------------|
| Bozza schedule (qualsiasi strategia / orizzonte) | SUPERVISOR | Caposquadra di turno. |
| Override esplicito su SafetyInterlock | n/a — schedule non scrive PLC | n/a |

T-V6-hitl-bypass è mitigato dal fatto che l'agente non possiede alcun
ramo `Decision.AUTO`.

## KPI Impattati

- **On-Time Delivery Rate** — l'algoritmo EDD massimizza la probabilità
  di consegnare entro `due_at`; SPT minimizza la makespan.
- **OEE Availability** — riempire le finestre asset in modo deterministico
  riduce i tempi morti tra ordini.
- **Schedule Stability** — ricalcoli deterministici (stesso input ⇒ stesso
  `schedule_id`) consentono al caposquadra di confrontare bozze.

## Invocazione

- **Endpoint API**: `POST /v1/agents/production-planner/plan` (Plan 06-12)
  con body `{strategy, horizon_days, user_roles, thread_id}`.
- **Trigger**: Manuale (caposquadra/pianificatore via UI) — non scheduler
  automatico (la pianificazione è un atto di management, non un loop).
- **Thread ID**: convenzione `ops.production-planner.<session-uuid>`.

## Footprint Audit

- `audit.actions` row con `agent_id = "production-planner"`,
  `action_type = SCHEDULE_DRAFT`, `decision = PENDING_APPROVAL`.
- `evidence_panel`: `tool_calls=[]` (algoritmo deterministico),
  `rag_citations` popolato con le 5 SOP recuperate,
  `model = "schedule-heuristic@sft-domain"` per la riga deterministica.
- `approval_id` collegato al record in `approval_actions`.
- Dichiarazione OPS-05 (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) esposta dal modulo `metadata.py` dell'agente.
