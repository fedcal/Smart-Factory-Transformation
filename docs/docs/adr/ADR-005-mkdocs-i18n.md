---
tags:
  - adr
  - architecture
  - docs
---

# ADR-005 — Documentazione con MkDocs Material + i18n bilingue

- **Status:** Accepted
- **Fase:** Phase 1 (Docs Foundation)
- **Data:** 2026

## Context

Il progetto richiede una documentazione tecnica pubblicabile, navigabile e
**bilingue (IT/EN)**, allineata al codice e versionabile. Requisiti:

- sorgente Markdown versionata insieme al codice (docs-as-code);
- contenuto bilingue con un'unica struttura di navigazione tradotta;
- diagrammi come testo (Mermaid), niente asset binari nel repo docs;
- build verificabile in CI in modalità strict (zero warning).

## Decision

Adottiamo **MkDocs Material** con il plugin **mkdocs-static-i18n** in modalità
`docs_structure: folder`: le pagine in italiano vivono in `docs/docs/`, i mirror
inglesi in `docs/docs/en/`, con `nav_translations` per tradurre le voci di
navigazione. I diagrammi sono in **Mermaid** (superfences). La build gira in
`mkdocs build --strict` in CI.

Riferimento:

- `docs/mkdocs.yml` — tema Material, plugin `i18n`, `nav_translations`,
  superfences Mermaid.
- struttura `docs/docs/` (IT) + `docs/docs/en/` (EN).

## Consequences

**Positive**

- docs-as-code: la documentazione evolve con il codice nello stesso repo;
- bilingue IT/EN con navigazione tradotta e un'unica fonte di struttura;
- diagrammi versionabili come testo (diff leggibili), niente binari;
- build strict in CI: i link rotti e i warning bloccano la pipeline.

**Negative / trade-off**

- onere di mantenere i mirror EN allineati alle pagine IT;
- `--strict` richiede disciplina sui link e sul nav (ma previene regressioni).

Decisione implementata nella foundation docs di Phase 1.
