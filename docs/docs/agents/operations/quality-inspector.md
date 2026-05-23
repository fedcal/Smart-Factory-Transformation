---
lang: it
agent: quality-inspector
requirements:
  - OPS-05
tags:
  - agents
  - operations
  - OPS-04
  - OPS-05
---

# QualityInspector

## Panoramica

`QualityInspector` consuma eventi di qualità (`QualityEvent`) emessi sul bus
NATS dalla linea tessile di **Mantis Textile Group** — difetti rilevati
durante tessitura, finissaggio o tintoria — e li classifica per severità
(`minor` / `major` / `critical`) tramite un grader LLM. Sulla base della
severità (con override per-difetto da `failure_modes.yaml`) l'agente decide
se l'azione correttiva è auto-loggabile o se richiede approvazione umana.

L'identificativo del lotto di tintura (`dye_lot_id`) è propagato in ogni
azione proposta e in ogni riga di audit (invariante D-QI-04 — tracciabilità
per lotto).

## Strumenti Utilizzati

| Tool | Origine | Funzione |
|------|---------|----------|
| `rag_search` | Phase 5 (`sft_knowledge.tools.rag`) | Recupera SOP correlate al `defect_type` per arricchire il `QualityVerdict`. |

Il **grader LLM** (`grade_quality_event` in `ops_quality_inspector.grader`)
non è un tool LangChain ma una funzione pura che invoca direttamente il
modello: questo isola il rischio T-V6-llm-hallucination — un fallback
conservativo viene applicato quando la `ValidationError` viene sollevata
sull'output Pydantic.

## Fonti Dati

- **NATS JetStream** — subject `quality.events.>` consumato (input);
  `audit.actions.qi-consumer` per idempotenza.
- **YAML domain** — `failure_modes.yaml` (override severity → tier).
- **Qdrant** — collezione `sop_chunks` (per le citazioni nel verdict).
- **PostgreSQL** — tabelle `audit.actions` e `approval_actions`.

## HITL Tier

La routing è definita da `_DEFAULT_SEVERITY_TIER` con override per-difetto
in `failure_modes.yaml` (l'override può solo **innalzare** il tier,
mai abbassarlo — `_max_tier`).

| Severity | Tier | Approvatore | Note |
|----------|------|-------------|------|
| `minor` | `auto-log` (nessun HITL) | n/a | Scritta riga `Decision.AUTO` in `audit.actions`. |
| `major` | `supervisor` (Tier.SUPERVISOR) | Caposquadra di turno | Routing via `human_approval_node`. |
| `critical` | `manager+safety` (Tier.MANAGER + SAFETY_INTERLOCK) | Manager produzione + responsabile qualità | `SafetyInterlockMiddleware.check` chiamato anche se l'azione `QUALITY_VERDICT` non scrive PLC (forensic uniformity, Pitfall §9). |

## KPI Impattati

- **Defect Rate (4pt system)** — il counter dei difetti permette di tracciare
  la qualità rotolo per rotolo (standard ASTM D5430).
- **Scrap Rate** — i difetti `critical` con full-width portano a scarto
  immediato; il tracking permette di calcolare la frazione persa per lotto.
- **Dye Lot Deviation** — `dye_lot_id` traccia anomalie cromatiche
  che derivano da deviazioni del bagno tintoria.

## Invocazione

- **Trigger**: Consumer NATS push (`quality.events.>`) — l'agente è invocato
  per ogni evento pubblicato dal simulatore di linea o dal feed reale.
- **Endpoint API**: `POST /v1/agents/quality-inspector/grade` (Plan 06-12,
  modalità sincrona per ispezioni manuali da supervisor UI).
- **Thread ID**: convenzione `ops.quality-inspector.<event_id>`.
- **Idempotenza**: `action_id = event.event_id` su `audit.actions` per
  prevenire doppia scrittura su retry NATS.

## Footprint Audit

- Una riga `audit.actions` per `QualityEvent` processato, con
  `agent_id = "quality-inspector"`, `cluster = "ops"`,
  `action_type = QUALITY_VERDICT`.
- `evidence_panel`: contiene `tool_calls=[grade_quality_event]` sintetico,
  `rag_citations` (SOP rilevanti), `model = "log-only@quality-inspector"`
  per le righe deterministiche di auto-log.
- `decision`: `AUTO` (minor) / `PENDING_APPROVAL` (major/critical).
- Dichiarazione OPS-05 (`tool_inventory`, `data_sources`, `hitl_tier`,
  `kpis_impacted`) esposta dal modulo `metadata.py` dell'agente.
