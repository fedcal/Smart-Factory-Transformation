---
tags:
  - adr
  - architecture
  - knowledge
---

# ADR-002 — Retrieval ibrido con Qdrant + BGE-M3

- **Status:** Accepted
- **Fase:** Phase 5 (Knowledge Layer)
- **Data:** 2026

## Context

Il knowledge layer deve recuperare documenti tecnici (SOP, manuali, knowledge di
dominio) in **italiano e inglese**, con qualità di retrieval robusta su query
miste e terminologia tecnica tessile. Requisiti:

- supporto multilingue nativo (corpus IT/EN);
- retrieval ibrido dense + sparse per coniugare similarità semantica e
  matching lessicale di termini tecnici;
- self-hosting (nessuna dipendenza da servizi di embedding cloud);
- filtraggio per ACL/metadati a livello di vector store.

Un retrieval puramente dense perde i match lessicali esatti (codici macchina,
sigle); un puro keyword search perde la similarità semantica cross-lingua.

## Decision

Adottiamo **Qdrant** come vector store e **BGE-M3** come modello di embedding
multilingue, in modalità **hybrid retrieval (dense + sparse)**. La scelta di
BGE-M3 è supportata da una valutazione A/B contro `multilingual-e5-large`
documentata nei risultati di eval del knowledge layer.

Riferimento codice e docs:

- `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py` —
  `RetrievalPipeline` (hybrid + audit `restricted`).
- [Risultati A/B BGE-M3 vs multilingual-e5-large](../knowledge-layer/eval-results.md).
- [Pipeline di retrieval ibrida](../knowledge-layer/retrieval-pipeline.md).

## Consequences

**Positive**

- qualità di retrieval superiore su corpus IT/EN (validata A/B);
- match lessicale + semantico nella stessa pipeline;
- filtri ACL/metadati applicati nativamente da Qdrant.

**Negative / trade-off**

- BGE-M3 ha footprint di calcolo maggiore rispetto a embedding più leggeri;
- la modalità ibrida aumenta la complessità di indicizzazione (sparse + dense).

Decisione implementata e validata nel knowledge layer di Phase 5.
