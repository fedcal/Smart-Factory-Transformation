# Phase 8: Agents — Knowledge & Training - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-24
**Phase:** 8-agents-knowledge-training
**Areas discussed:** ShiftHandover trigger & sources, TrainingCoach competency model, KnowledgeCurator dedup & staleness, DocumentationSynthesizer SOP synthesis, TRN audit ActionType taxonomy, HITL policy per agent, operator persona source, gateway endpoint exposure

---

## ShiftHandover

| Option | Description | Selected |
|--------|-------------|----------|
| Boundary schedulato + manuale | Confini fissi configurabili + avvio manuale on-demand | ✓ |
| Solo manuale | Supervisore avvia esplicitamente | |
| Event-driven | Compilazione al primo evento dopo il boundary | |

| Option | Description | Selected |
|--------|-------------|----------|
| audit.actions cross-cluster | Singola fonte di verità | |
| audit.actions + query dirette tabelle | Audit + alerts/work_orders/downtime_events | ✓ |
| You decide | Lascia a ricerca/planning | |

| Option | Description | Selected |
|--------|-------------|----------|
| Due approvazioni sequenziali uscente→entrante | Passaggio di consegne, due righe audit | ✓ |
| Due approvazioni parallele | Indipendenti, qualsiasi ordine | |
| Singola approvazione, due firmatari | Un gate, due firmatari | |

**User's choice:** Boundary schedulato + manuale; fonti audit + query dirette; sign-off sequenziale uscente→entrante.
**Notes:** Vincolo <3 min e dual-supervisor sign-off da criterio #1.

---

## TrainingCoach

| Option | Description | Selected |
|--------|-------------|----------|
| Scelta multipla deterministica | Scoring esatto, testabile senza LLM | ✓ |
| Risposta libera valutata da LLM | LLM-judge, non deterministico | |
| Ibrido MC + 1 aperta | MC + bonus aperta | |

| Option | Description | Selected |
|--------|-------------|----------|
| Per ruolo/persona + difficoltà dinamica | Contenuto per ruolo + difficoltà adattiva | ✓ |
| Solo per ruolo/persona | Difficoltà fissa | |
| Solo difficoltà dinamica | Nessuna personalizzazione ruolo | |

| Option | Description | Selected |
|--------|-------------|----------|
| Soglia configurabile (default 80%) + HITL | Pass ≥ soglia config, signoff supervisore | ✓ |
| Soglia fissa 70% + HITL | Soglia hardcoded | |
| You decide | Calibrazione a planning | |

**User's choice:** MC deterministica; adattività ruolo + difficoltà; soglia configurabile 0.80 + HITL supervisore.

---

## KnowledgeCurator

| Option | Description | Selected |
|--------|-------------|----------|
| Similarità embedding (cosine) | BGE-M3 cosine con soglia | |
| Hash esatto | SHA-256 testo normalizzato | |
| Ibrido hash + embedding | Exact-dup veloce poi near-dup | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Per tipo documento, configurabile | Soglie d'età per tipo | ✓ |
| Globale fissa (180gg) | Soglia unica | |
| Basata su ultimo riferimento | Stale se non citato da N giorni | |

| Option | Description | Selected |
|--------|-------------|----------|
| % citazioni distinte su corpus | Doc distinti citati / indicizzati | ✓ |
| Conteggio recuperi RAG per doc | Hit retrieval per documento | |
| You decide | Definizione a planning | |

**User's choice:** Dedup ibrido hash+embedding; staleness per tipo doc configurabile; reuse KPI = % doc distinti citati su corpus.

---

## DocumentationSynthesizer

| Option | Description | Selected |
|--------|-------------|----------|
| Generazione IT+EN simultanea | Una chiamata, stesse citazioni | |
| Genera IT poi traduci EN | Due passate | ✓ |
| You decide | Strategia a planning | |

| Option | Description | Selected |
|--------|-------------|----------|
| Per failure mode + asset, finestra configurabile | Eventi storici filtrati | ✓ |
| Per singolo evento/intervento | Un evento significativo | |
| Per asset, tutta la storia | Nessuna finestra | |

| Option | Description | Selected |
|--------|-------------|----------|
| Template SOP fisso a sezioni + citazioni inline | Schema fisso, source_uri inline | ✓ |
| Struttura libera guidata da LLM | LLM decide sezioni | |
| You decide | Template a planning | |

**User's choice:** IT poi traduci EN; eventi per failure mode + asset con finestra configurabile; template SOP fisso a sezioni con citazioni inline.
**Notes:** Scelta translate-pass → rischio drift citazioni; mitigazione richiesta (ri-ancorare source_uri dopo traduzione) — registrata come vincolo D-DS-01.

---

## TRN audit ActionType taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| 4 type, uno per agente | HANDOVER_REPORT/TRAINING_SIGNOFF/KNOWLEDGE_CURATION/SOP_DRAFT | |
| Set granulare (6+) | Separa sotto-azioni | ✓ |
| You decide | Definizione a planning | |

**User's choice:** Set granulare (6+) — finalizzazione valori a planning.

---

## HITL policy per agent

| Option | Description | Selected |
|--------|-------------|----------|
| Gate sugli output che cambiano stato | ShiftHandover dual / TrainingCoach signoff / DocSynth pre-index; KnowledgeCurator autonomo | ✓ |
| Tutti always-supervisor | Ogni output via HITL | |
| You decide | Calibrazione a planning | |

**User's choice:** Gate sugli output che cambiano stato; KnowledgeCurator autonomo.

---

## Operator persona source (TrainingCoach)

| Option | Description | Selected |
|--------|-------------|----------|
| Registry sintetico Mantis esistente | Riusa ruoli/persona esistenti | ✓ |
| Config dedicata personas.yaml | Nuovo file config | |
| You decide | Individuazione a planning | |

**User's choice:** Registry sintetico Mantis esistente.

---

## Gateway endpoint exposure

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror 07-10: router dedicato + subgraph | knowledge_agents.py + build_knowledge_subgraph | ✓ |
| Endpoint generico unico | /v1/agents/knowledge con target_agent | |
| You decide | Forma a planning | |

**User's choice:** Router dedicato + build_knowledge_subgraph, mirror 07-10.

---

## Claude's Discretion

- Nomi/numero esatti dei valori enum ActionType (set granulare, finalizzati a planning)
- Meccaniche interne di retrieval/grounding via pipeline sft-knowledge
- Dettagli architetturali/layout pacchetti (pattern agente Fasi 6/7)

## Deferred Ideas

None — la discussione è rimasta nello scope di fase. Agenti supply-chain (Fase 9) e UI (Fase 10) emersi solo come confini.
