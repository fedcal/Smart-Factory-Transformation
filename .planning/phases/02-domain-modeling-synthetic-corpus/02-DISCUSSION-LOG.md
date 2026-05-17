---
phase: 2
phase_name: Domain Modeling & Synthetic Corpus
discussed_at: "2026-05-17"
mode: default
areas_selected: 4
areas_discussed: 4
---

# Phase 2 Discussion Log

Human-readable transcript of the discussion that produced `02-CONTEXT.md`. Used for audits and retrospectives — NOT consumed by downstream agents.

## Gray Area Selection

**Question:** Quali gray area vuoi discutere per la Fase 2? (multi-select)

Options presented:
- [x] Granularità Domain Analysis
- [x] Approccio authoring corpus SOP
- [x] Glossario: formato e collocazione
- [x] Assumption Register struttura

User selected: **all four**.

---

## Area 1: Granularità Domain Analysis

### Q1.1 — Struttura

**Question:** Come organizzare la Domain Analysis?

Options:
1. Split per processo + ruolo *(Recommended)*
2. Monolitico con sezioni TOC
3. Ibrido: overview monolitico + deep-dive per processo

**Selected:** Split per processo + ruolo → **D-21**

### Q1.2 — Profondità

**Question:** Quanto dettaglio processo va incluso?

Options:
1. Process flow + asset + KPI + pain point *(Recommended)*
2. Solo descrittivo + pain point
3. Deep technical: include parametri operativi

**Selected:** Process flow + asset + KPI + pain point → **D-22**

### Q1.3 — Mantis specificity

**Question:** Quanto ancorare il contenuto a Mantis Textile Group specificamente?

Options:
1. Generico textile + riferimenti Mantis in sidebar *(Recommended)*
2. Mantis-first, generico in appendice
3. Completamente generico, senza menzioni Mantis

**Selected:** Generico + sidebar Mantis context → **D-23**

### Q1.4 — Bilingue

**Question:** Bilingue IT/EN strategia per la Domain Analysis?

Options:
1. IT prima, EN deferred a Phase 14 *(Recommended)*
2. Entrambe complete in Phase 2
3. Solo EN, IT come stub

**Selected:** **Entrambe complete in Phase 2** (override del Recommended) → **D-24**

> Override rationale (user-driven): allineamento commitment bilingue del progetto, no rinvio.

---

## Area 2: Approccio authoring corpus SOP

### Q2.1 — Authoring

**Question:** Come generare i 20+ SOP bilingui (10 IT + 10 EN)?

Options:
1. Hybrid: LLM-draft + human review *(Recommended)*
2. Pure LLM-generated (no review)
3. Hand-written da te / domain expert in Phase futura

**Selected:** Hybrid → **D-25**

### Q2.2 — Formato

**Question:** Formato e struttura del SOP?

Options:
1. Frontmatter YAML + sezioni standardizzate *(Recommended)*
2. Prosa narrativa + tag tassonomici
3. Markdown loose con sezioni convenzionali

**Selected:** Frontmatter YAML + sezioni standardizzate → **D-26**

### Q2.3 — Topic mix

**Question:** Distribuzione topic SOP sui 4 asset/processi citati?

Options:
1. Bilanciato: 5+5+5+5 *(Recommended)*
2. Minimo KNW-10: 10 IT + 10 EN stesso topic
3. Weighted by complexity

**Selected:** Bilanciato 5+5+5+5 → **D-27**

### Q2.4 — Stile

**Question:** Stile narrativo dei SOP?

Options:
1. Factory-floor realistico *(Recommended)*
2. Pedagogico-tutorial
3. Misto 70/30

**Selected:** Factory-floor realistico → **D-28** (tutorial variants deferred to Phase 7)

---

## Area 3: Glossario: formato e collocazione

### Q3.1 — Source-of-truth

**Question:** Dove vive la fonte canonica del glossario?

Options:
1. Doppio canale: dati in sft-domain + render MkDocs *(Recommended)*
2. Solo MkDocs Markdown
3. Solo sft-domain + plugin MkDocs gen

**Selected:** Doppio canale → **D-29**

### Q3.2 — Layout

**Question:** Granularità e organizzazione del glossario?

Options:
1. Unificato textile + agentic con tag categoria *(Recommended)*
2. Separati: glossario-textile + glossario-agentic
3. Strutturato per processo: glossari nested

**Selected:** Unificato con tag categoria → **D-30**

### Q3.3 — Coverage

**Question:** Numero termini target nel glossario seed di Phase 2?

Options:
1. ~80 termini per lingua *(Recommended)*
2. ~40 termini per lingua (minimo MVP)
3. ~150 termini per lingua (esaustivo)

**Selected:** **~150 termini per lingua** (override del Recommended) → **D-31**

> Override rationale (user-driven): glossario di valore come reference indipendente, non filler.

### Q3.4 — Cross-ref validation

**Question:** Validazione consistency glossario ↔ corpus SOP ↔ domain analysis?

Options:
1. CI check coverage *(Recommended)*
2. No validazione
3. Linting warning-only

**Selected:** CI check coverage → **D-32**

---

## Area 4: Assumption Register struttura

### Q4.1 — Formato

**Question:** Formato dell'Assumption Register?

Options:
1. YAML strutturato + render MkDocs *(Recommended)*
2. Markdown table singola
3. Per-component files

**Selected:** YAML strutturato + render MkDocs → **D-33**

### Q4.2 — Tagging

**Question:** Tagging / categorizzazione delle assumptions?

Options:
1. Doppio asse: category + affected_components[] *(Recommended)*
2. Solo per agente (1 dei 16)
3. Solo per cluster

**Selected:** Doppio asse → **D-34**

### Q4.3 — Evoluzione

**Question:** Meccanismo evoluzione delle assumption nel tempo?

Options:
1. Living doc con audit trail git *(Recommended)*
2. ADR-style immutabile + supersedes
3. Phase-snapshots

**Selected:** Living doc + audit trail git → **D-35**

### Q4.4 — Seed count

**Question:** Numero assumption seed da inserire in Phase 2?

Options:
1. ~25 assumption seed *(Recommended)*
2. ~10 assumption seed (minimo MVP)
3. ~50 assumption seed (esaustivo)

**Selected:** **~50 assumption seed** (override del Recommended) → **D-36**

> Override rationale (user-driven): copertura paranoica utile per audit Phase 11 (gsd-secure-phase).

---

## Deferred Ideas Captured

- TrainingCoach pedagogical SOP variants → Phase 7
- Deep-technical process parameters (RPM/tensioni reali) → Phase 7+
- Defect taxonomy strutturata YAML → Phase 6
- OEPV glossary entries beyond 10 seed → Phase 11
- ADR formali (DOC-13) for Phase 2 decisions → Phase 14 (DOC polish)

## Claude's Discretion Items

Documented in CONTEXT.md `<claudes_discretion>` section. Notable:
- MkDocs nav: append, not rewrite
- pydantic + jsonschema for validation
- Mermaid `flowchart LR` max 8 nodes
- python-frontmatter library
- Synthetic-corpus NOT in MkDocs i18n (it's a dataset)

## Overrides Recap

User overrode 3 of 4 "Recommended" defaults toward more ambitious scopes:
- D-24: IT+EN both complete in Phase 2 (vs deferring EN to Phase 14)
- D-31: ~150 terms per language (vs ~80)
- D-36: ~50 assumptions seeded (vs ~25)

This sets Phase 2 as a substantial content phase. Planner should size waves accordingly.
