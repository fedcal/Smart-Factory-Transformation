---
tags:
  - adr
  - architecture
  - agents
---

# ADR-001 — Supervisor pattern con LangGraph

- **Status:** Accepted
- **Fase:** Phase 4 (Core Agentic Runtime + HITL)
- **Data:** 2026

## Context

La piattaforma deve orchestrare più agenti specializzati (operations,
maintenance, knowledge, supply) coordinandone l'invocazione, la condivisione di
stato e i punti di approvazione umana. I requisiti chiave:

- routing deterministico verso l'agente o il cluster competente;
- gestione di stato condiviso tra step (messaggi, contesto di dominio);
- punti di interruzione human-in-the-loop nativi, senza polling custom;
- guard-rail contro loop costosi (excessive agency).

Un'orchestrazione ad-hoc (catene imperative o chiamate dirette) renderebbe
difficile inserire interruzioni controllate e tracciare il flusso decisionale.

## Decision

Adottiamo il **supervisor pattern** implementato con **LangGraph**: un grafo
supervisore instrada le richieste verso gli agenti, mantiene lo stato e usa
l'`interrupt()` nativo di LangGraph per sospendere il grafo nei punti di
approvazione (HITL). Le invocazioni impongono un `recursion_limit` esplicito
come guard-rail di autonomia.

Riferimento codice:

- `packages/sft-agents/src/sft_agents/runtime/supervisor.py` — `safe_invoke`
  (interrupt nativo + recursion guard).
- `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py` —
  `build_invocation_config` (`recursion_limit=25`).

## Consequences

**Positive**

- interruzioni HITL native e riprese tramite resume-payload, senza polling;
- stato del grafo serializzabile e tracciabile (correlazione OTEL/Langfuse);
- guard-rail di ricorsione che evita loop costosi (`GraphRecursionError → 503`).

**Negative / trade-off**

- accoppiamento all'API LangGraph; un cambio di runtime richiederebbe il
  re-wiring del grafo;
- la curva di apprendimento del modello a grafo è superiore a una catena lineare.

Decisione implementata e verificabile nel runtime agentico di Phase 4.
