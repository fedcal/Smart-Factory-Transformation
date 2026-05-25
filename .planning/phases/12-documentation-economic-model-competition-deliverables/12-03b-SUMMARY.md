---
phase: 12-documentation-economic-model-competition-deliverables
plan: 03b
subsystem: docs
tags: [docs, adr, readme, contributing, community, mkdocs, i18n]
dependency_graph:
  requires: [12-00]
  provides: [adr-section-published, root-readme, contributing-guide]
  affects:
    - docs/docs/adr/
    - docs/docs/en/adr/
    - README.md
    - CONTRIBUTING.md
tech_stack:
  added: []
  patterns:
    - "ADR MADR-like (Title/Status/Context/Decision/Consequences) tracciate a fase implementata (SC-3)"
    - "Mirror IT/EN via mkdocs-static-i18n; nav_translations identity per titoli ADR"
    - "Root community files (README/CONTRIBUTING) standard GitHub che linkano alla sezione docs"
key_files:
  created:
    - docs/docs/adr/index.md
    - docs/docs/adr/ADR-001-langgraph-supervisor.md
    - docs/docs/adr/ADR-002-qdrant-bge-m3.md
    - docs/docs/adr/ADR-003-self-hosted-llm.md
    - docs/docs/adr/ADR-004-hitl-tiers.md
    - docs/docs/adr/ADR-005-mkdocs-i18n.md
    - docs/docs/en/adr/index.md
    - docs/docs/en/adr/ADR-001-langgraph-supervisor.md
    - docs/docs/en/adr/ADR-002-qdrant-bge-m3.md
    - docs/docs/en/adr/ADR-003-self-hosted-llm.md
    - docs/docs/en/adr/ADR-004-hitl-tiers.md
    - docs/docs/en/adr/ADR-005-mkdocs-i18n.md
    - README.md
    - CONTRIBUTING.md
  modified:
    - docs/mkdocs.yml
decisions:
  - "5 ADR tracciate a fasi implementate: ADR-001 LangGraph supervisor (Phase 4), ADR-002 Qdrant+BGE-M3 (Phase 5), ADR-003 LLM self-hosted/Ollama (Phase 1/4), ADR-004 HITL 4-tier (Phase 4), ADR-005 MkDocs i18n (Phase 1) — SC-3"
  - "CODE_OF_CONDUCT.md DEFERRED su richiesta esplicita utente (resume 2026-05-25): DOC-16 resta parziale; README/CONTRIBUTING contengono già il link al file futuro"
  - "README badge shields.io ![License]/![Docs] ammessi: file root non parte del build mkdocs, il vincolo SC-5 no-binary-images riguarda il sito docs"
metrics:
  duration_min: 20
  completed_date: "2026-05-25"
  tasks_completed: 2
  files_created: 14
  files_modified: 1
---

# Phase 12 Plan 03b: ADR + README + CONTRIBUTING Summary

Pubblicate 5 ADR (DOC-13) in formato MADR-like nel sito MkDocs (IT+EN + index + nav), ciascuna tracciata a una decisione realmente implementata con citazione della fase: LangGraph supervisor (Phase 4), Qdrant+BGE-M3 hybrid (Phase 5), LLM self-hosted via Ollama (Phase 1/4), HITL 4-tier approval (Phase 4), MkDocs Material i18n (Phase 1). Creati i file community root `README.md` (DOC-14: quick start, struttura repo, link docs/CONTRIBUTING/LICENSE Apache 2.0) e `CONTRIBUTING.md` (Conventional Commits, pre-commit, test `nx affected`/pytest, build docs strict). LICENSE Apache 2.0 invariata. `mkdocs build --strict` verde; nessun riferimento al brand originale.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | 5 ADR tracciate + index + nav (DOC-13) | 09896d9 | docs/docs/adr/* + EN mirror + mkdocs.yml |
| 2 | README root + CONTRIBUTING (DOC-14/DOC-16) | 4ba2753 | README.md, CONTRIBUTING.md |

## Verification

- Task 1: 5 ADR IT+EN presenti; `ADR-001` contiene `Decision` + `LangGraph`; `mkdocs build --strict` exit 0 — PASS
- Task 2 automated: `README` ha `Quick`/`CONTRIBUTING`/`Apache`; `CONTRIBUTING` contiene `commit`; LICENSE presente — PASS
- Brand-scrub (`accenture`) su README/CONTRIBUTING — PASS (no-brand-ok)
- `mkdocs build --strict` finale exit 0, 61 nav element tradotti EN — PASS
- LICENSE-EXCEPTIONS.md referenziato dal README esiste — PASS

## Deviations from Plan

### Deferred (su richiesta utente)

**1. CODE_OF_CONDUCT.md non creato**
- **Issue:** Il plan (Task 2, DOC-16) richiedeva `CODE_OF_CONDUCT.md` (Contributor Covenant). In sede di resume (2026-05-25) l'utente ha esplicitamente chiesto di saltarlo.
- **Impatto:** DOC-16 resta **parziale** — CONTRIBUTING + LICENSE Apache 2.0 presenti, manca il Code of Conduct. `README.md` e `CONTRIBUTING.md` contengono un link `[Code of Conduct](CODE_OF_CONDUCT.md)` attualmente non risolto (link markdown root, NON verificato dal build mkdocs → non rompe `--strict`).
- **Azione futura:** creare `CODE_OF_CONDUCT.md` per chiudere DOC-16, oppure rimuovere i due link se la decisione è definitiva.

### Finalizzazione differita

Il plan era stato eseguito a metà in una sessione precedente: Task 1 committato (`09896d9`), file di Task 2 (`README.md`, `CONTRIBUTING.md`) creati ma **untracked** e SUMMARY/STATE non scritti. Questa finalizzazione (sessione resume 2026-05-25) ha committato Task 2 (`4ba2753`) e prodotto questo SUMMARY.

## Known Stubs

- `CODE_OF_CONDUCT.md` — assente (deferred, vedi sopra). DOC-16 parziale.

## Threat Flags

Nessuna nuova superficie di sicurezza — solo documentazione. T-12-03b-01 (brand in file pubblici) mitigato: brand-scrub PASS su README/CONTRIBUTING e ADR. T-12-03b-02 (ADR non tracciata a codice) mitigato: ogni ADR cita la fase di implementazione; verifica SC-3 finale demandata a 12-05.

## Self-Check: PASSED

- `09896d9` (Task 1) e `4ba2753` (Task 2) presenti in git log
- 12 file ADR (IT+EN) + index + README + CONTRIBUTING esistono su filesystem
- `mkdocs build --strict` exit 0
- nessuna stringa vietata nei file tracciati
- CODE_OF_CONDUCT.md deferred e documentato come known stub
