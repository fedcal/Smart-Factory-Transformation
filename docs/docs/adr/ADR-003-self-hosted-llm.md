---
tags:
  - adr
  - architecture
  - llm
---

# ADR-003 — LLM self-hosted via Ollama

- **Status:** Accepted
- **Fase:** Phase 1 (infra) / Phase 4 (runtime)
- **Data:** 2026

## Context

La piattaforma elabora dati operativi e documentazione tecnica potenzialmente
sensibili (parametri di processo, anomalie, knowledge proprietaria). Vincoli:

- **data residency / privacy**: i dati non devono lasciare il perimetro
  on-premise;
- costi prevedibili e indipendenti dal volume di token;
- possibilità di girare in ambienti air-gapped (officina/IT-OT);
- portabilità tra CPU e GPU NVIDIA.

Una dipendenza da API LLM cloud violerebbe i requisiti di residency e
introdurrebbe costi variabili e una dipendenza di rete esterna.

## Decision

Adottiamo **inferenza LLM self-hosted via Ollama**, eseguita all'interno dello
stack containerizzato del progetto. Lo stack di sviluppo avvia Ollama con
profili CPU e GPU; nessuna chiamata a servizi di inferenza esterni.

Riferimento:

- `make up` / `make up-gpu` — avvio dello stack con Ollama (CPU/GPU).
- [LLM Serving](../architecture/llm-serving.md).
- integrazione runtime in `packages/sft-agents` (client LLM verso l'endpoint
  Ollama locale).

## Consequences

**Positive**

- nessun dato esce dal perimetro on-premise (privacy/residency);
- costi di inferenza fissi e prevedibili;
- funziona in ambienti air-gapped; profili CPU e GPU.

**Negative / trade-off**

- qualità/latenza vincolate dall'hardware locale rispetto ai modelli frontier
  cloud;
- onere operativo di gestione e aggiornamento dei modelli locali.

Decisione implementata nell'infra (Phase 1) e consumata dal runtime (Phase 4).
