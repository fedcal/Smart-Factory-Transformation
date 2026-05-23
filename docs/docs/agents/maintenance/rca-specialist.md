---
lang: it
agent: rca-specialist
requirements:
  - MNT-02
  - MNT-05
tags:
  - agents
  - maintenance
  - MNT-02
  - MNT-05
---

# RCASpecialist

## Panoramica

`RCASpecialist` conduce l'analisi delle cause radici (Root Cause Analysis)
usando la metodologia 5-Why iterativa. Ogni passo è obbligatoriamente
supportato da almeno una citazione recuperata dal knowledge base tessile
(SOP, manuali) tramite `rag_search`; la validazione post-LLM verifica che
ogni `source_uri` esista in PostgreSQL (Open Q5 — full lookup).

La raccomandazione correttiva passa **sempre** per approvazione supervisor
(D-RCA-02 letterale): non esiste percorso AUTO per questo agente. Questo
vincolo è hardcoded in `metadata.py` — qualsiasi override del tier da parte
del chiamante viene ignorato silenziosamente per prevenire de-escalation
accidentale.

Opzionalmente, `traverse_graph` interroga il knowledge graph Neo4j (Phase 5)
per esplorare relazioni causa-effetto tra componenti tessili, arricchendo la
catena 5-Why con evidenza strutturata oltre le SOP.

## Strumenti Utilizzati

| Tool | Origine | Funzione |
|------|---------|----------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Recupera SOP e manuali pertinenti al `problem_statement`; ogni `WhyStep` deve contenere almeno una citazione. |
| `traverse_graph` | Phase 5 (`sft_knowledge.tools.graph`) | Naviga il knowledge graph Neo4j per relazioni causa-effetto tra componenti dell'impianto tessile. |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Invia la RCA completa (5 WhyStep + `corrective_action`) al caposquadra per approvazione obbligatoria (D-RCA-02). |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Scrive ciascun passo della catena 5-Why in `audit.actions` con `action_type=RCA_CHAIN`. |

## Fonti Dati

- **Qdrant `sop_chunks`** — collezione vettoriale delle SOP tessili (Phase 5);
  fornisce le citazioni obbligatorie per ogni WhyStep.
- **Neo4j textile graph** — knowledge graph Phase 5; usato da `traverse_graph`
  per relazioni causa-effetto strutturate.
- **PostgreSQL `documents`** — tabella di riferimento per validare i
  `source_uri` post-retrieval (full lookup, Open Q5).
- **`maintenance.downtime_events` (migration 08)** — fornisce il contesto
  dell'evento di downtime collegato alla richiesta RCA.

## HITL Tier

| Decisione / Caso | Tier | Approvatore |
|---|---|---|
| Tutte le RCA — `corrective_action_recommendation` | supervisor (Decision.HITL_SUPERVISOR) | Caposquadra di turno |

Nessun percorso AUTO: D-RCA-02 è un requisito letterale e non configurabile.

## KPI Impattati

- **rca_completeness_5why** — percentuale di RCA con catena completa di 5
  livelli Why, ciascuno con almeno una citazione; indica la qualità del
  processo di analisi.
- **citation_grounding_rate** — proporzione di WhyStep con `source_uri`
  validato; misura l'allucinazione residua del modello LLM.
- **mttr_root_cause_to_fix** — tempo tra l'apertura della RCA e
  l'applicazione della correzione approvata; riduce il MTTR complessivo.

## Invocazione

- **Endpoint API**: `POST /v1/agents/rca-specialist/analyze`
  con body `{"problem_statement": "<str>", "downtime_event_id": "<uuid>", "asset_id": "<uuid>", "user_roles": ["technician"], "lang": "it"}`
- **Risposta**: `202 Accepted` (async HITL); la RCA completa è disponibile
  via `GET /v1/agents/rca-specialist/result/<thread_id>` dopo approvazione.
- **Trigger**: on-demand da tecnico o caposquadra post-evento downtime.
- **Thread ID**: convenzione `maintenance.rca-specialist.<uuid4>`.

## Audit Footprint

- Una riga `audit.actions` per passo 5-Why con `agent_id = "rca-specialist"`,
  `cluster = "maintenance"`, `action_type = RCA_CHAIN`.
- `evidence_panel` include la catena completa di `WhyStep` + `rag_citations`
  per ogni passo; campo `decision = "hitl_supervisor"` sempre.
- Dichiarazione MNT-05 (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) esposta dal modulo `metadata.py` dell'agente.
