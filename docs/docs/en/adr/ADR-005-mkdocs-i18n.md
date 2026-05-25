---
tags:
  - adr
  - architecture
  - docs
---

# ADR-005 — Documentation with MkDocs Material + bilingual i18n

- **Status:** Accepted
- **Phase:** Phase 1 (Docs Foundation)
- **Date:** 2026

## Context

The project requires publishable, navigable and **bilingual (IT/EN)** technical
documentation, aligned with the code and versionable. Requirements:

- Markdown source versioned alongside the code (docs-as-code);
- bilingual content with a single translated navigation structure;
- diagrams as text (Mermaid), no binary assets in the docs repo;
- a build verifiable in CI in strict mode (zero warnings).

## Decision

We adopt **MkDocs Material** with the **mkdocs-static-i18n** plugin in
`docs_structure: folder` mode: Italian pages live in `docs/docs/`, English
mirrors in `docs/docs/en/`, with `nav_translations` to translate navigation
entries. Diagrams are in **Mermaid** (superfences). The build runs as
`mkdocs build --strict` in CI.

Reference:

- `docs/mkdocs.yml` — Material theme, `i18n` plugin, `nav_translations`,
  Mermaid superfences.
- `docs/docs/` (IT) + `docs/docs/en/` (EN) structure.

## Consequences

**Positive**

- docs-as-code: documentation evolves with the code in the same repo;
- bilingual IT/EN with translated navigation and a single structure source;
- diagrams versioned as text (readable diffs), no binaries;
- strict build in CI: broken links and warnings block the pipeline.

**Negative / trade-off**

- burden of keeping EN mirrors aligned with IT pages;
- `--strict` requires discipline on links and nav (but prevents regressions).

Decision implemented in the Phase 1 docs foundation.
