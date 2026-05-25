---
tags:
  - adr
  - architecture
---

# ADR — Architecture Decision Records

Questo registro raccoglie le decisioni architetturali significative adottate
durante lo sviluppo della piattaforma agentica per l'industria tessile
manifatturiera. Ogni ADR segue un formato MADR-like (Title, Status, Context,
Decision, Consequences) e **traccia a una decisione realmente implementata**,
citando la fase di sviluppo e il codice di riferimento (SC-3).

## Registro

| # | Titolo | Stato | Fase | Decisione |
|---|--------|-------|------|-----------|
| [ADR-001](ADR-001-langgraph-supervisor.md) | Supervisor pattern con LangGraph | Accepted | Phase 4 | Orchestrazione agentica via grafo supervisore + HITL nativo |
| [ADR-002](ADR-002-qdrant-bge-m3.md) | Retrieval ibrido Qdrant + BGE-M3 | Accepted | Phase 5 | Vector store Qdrant con embedding multilingue BGE-M3 (dense+sparse) |
| [ADR-003](ADR-003-self-hosted-llm.md) | LLM self-hosted via Ollama | Accepted | Phase 1/4 | Inferenza LLM on-premise, nessuna dipendenza da API cloud |
| [ADR-004](ADR-004-hitl-tiers.md) | Approvazione HITL a 4 livelli | Accepted | Phase 4 | Catena di approvazione human-in-the-loop per ruolo (RBAC) |
| [ADR-005](ADR-005-mkdocs-i18n.md) | Documentazione MkDocs Material + i18n | Accepted | Phase 1 | Sito docs bilingue IT/EN con mkdocs-static-i18n |

## Formato

Ogni ADR documenta:

- **Status** — stato decisionale (`Accepted`, `Superseded`, ...).
- **Context** — il problema e i vincoli che hanno motivato la decisione.
- **Decision** — la scelta adottata.
- **Consequences** — conseguenze positive e negative, trade-off accettati.

!!! note "Tracciabilità (SC-3)"
    Ogni decisione qui registrata è verificabile nel codice e nelle fasi di
    sviluppo citate; le ADR non descrivono decisioni ipotetiche o non
    implementate.
