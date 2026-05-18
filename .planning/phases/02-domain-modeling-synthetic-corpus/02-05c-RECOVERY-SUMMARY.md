---
phase: 2
plan: "02-05c"
subsystem: glossary-coverage-scripts-wiring
tags: [glossary, validation, makefile, ci, nx, wave3]
depends_on:
  requires: ["02-01", "02-02", "02-03", "02-04", "02-05a", "02-05b"]
  provides: ["glossary-≥150-it", "glossary-≥150-en", "validate-coverage-script", "generate-glossary-script", "nx-validate-glossary", "makefile-validate-all", "ci-validate-content"]
  affects: ["docs/docs/glossary.md", "docs/docs/en/glossary.md", "packages/sft-domain", "Makefile", ".github/workflows/ci.yml"]
tech_stack:
  added: []
  patterns: ["idempotent-generator", "lang-matched-bold-coverage", "nx-run-commands-executor"]
key_files:
  created:
    - packages/sft-domain/src/sft_domain/glossary/it.yaml (153 IT terms)
    - packages/sft-domain/src/sft_domain/glossary/en.yaml (158 EN terms)
    - scripts/validate-glossary-coverage.py
    - scripts/generate-glossary-pages.py
    - docs/docs/glossary.md
    - docs/docs/en/glossary.md
    - docs/docs/assumptions/A-031.md ... A-050.md (20 nuovi)
    - docs/docs/en/assumptions/A-031.md ... A-050.md (20 nuovi)
  modified:
    - packages/sft-domain/project.json
    - Makefile
    - .github/workflows/ci.yml
decisions:
  - "validate-glossary-coverage.py usa fallback cross-lingua: token IT in EN SOP checked contro IT glossary (pattern di authoring EN SOPs)"
  - "noise filter step heading: verbi comuni IT+EN + apostrofi + >3 parole esclusi"
  - "make validate-all usa uv run per dipendenze Python non presenti di default"
  - "deviation Rule 2: rigenerati 42 assumption pages mancanti (A-031..A-050 + EN) causa expand register.yaml wave 2"
metrics:
  duration: "~45 min"
  completed: "2026-05-18"
  tasks: 4
  files_created: 50
  files_modified: 6
---

# Phase 2 Plan 02-05c: Recovery-C SUMMARY — Glossary Expansion + Scripts + Wiring

**One-liner:** Espansione glossario IT 78→153 + EN 77→158 termini, scripts validate-coverage + generate-pages idempotenti, target Nx validate-glossary e Makefile validate-all, step CI "Validate content".

## Tasks Completati

| Task | Descrizione | Commit |
|------|-------------|--------|
| 1 | Glossary expansion IT 78→153, EN 77→158 termini (≥150 per lingua) | `bff9e92` |
| 2 | validate-glossary-coverage.py + generate-glossary-pages.py + pagine IT/EN | `52dedc8` |
| 3 | Nx validate-glossary target + Makefile targets (validate-all exit 0) | `9b55e51` |
| 4 | CI step "Validate content" in ci.yml | `3179be5` |

## Verifiche di Successo

- `python3 scripts/validate-glossary-schema.py`: **OK — 153 IT + 158 EN termini**
- `python3 scripts/validate-glossary-coverage.py`: **exit 0 — 70 IT + 103 EN bold token coperti**
- `python3 scripts/generate-glossary-pages.py`: **Written docs/docs/glossary.md (1736 righe) + en/glossary.md (1791 righe)**
- `python3 scripts/generate-glossary-pages.py --check`: **exit 0 (idempotente)**
- `make validate-all`: **exit 0**
- `packages/sft-domain/project.json`: **target validate-glossary presente**
- `.github/workflows/ci.yml`: **step "Validate content" aggiunto**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Regenerated 42 missing assumption pages**
- **Found during:** Task 3 — `make validate-all` → `generate-assumption-pages.py --check` exit 2
- **Issue:** Wave 2 ha espanso `register.yaml` da 30 a 50 entries (commit `e1b6ca0`) ma non ha rigenerato le pagine assumption A-031..A-050 + EN counterpart
- **Fix:** Eseguito `make generate-assumptions` che ha creato 40 nuovi file + aggiornato 2 index
- **Files modified:** `docs/docs/assumptions/A-031.md`..`A-050.md`, `docs/docs/en/assumptions/A-031.md`..`A-050.md`, `docs/docs/assumptions/index.md`, `docs/docs/en/assumptions/index.md`
- **Commit:** `9b55e51`

**2. [Rule 1 - Bug] validate-corpus target usava python3 invece di uv run**
- **Found during:** Task 3 — `make validate-corpus` falliva con `ModuleNotFoundError: No module named 'frontmatter'`
- **Issue:** Scripts come `validate-corpus-frontmatter.py` richiedono `python-frontmatter` disponibile solo via `uv run`
- **Fix:** Aggiornato Makefile per usare `uv run python3 scripts/...` nei target che richiedono dipendenze Python del progetto
- **Commit:** `9b55e51`

### Scelta Implementativa: Cross-language fallback in validate-coverage

I SOP EN usano termini italiani in **bold** come riferimenti cross-linguistici (es. `**telaio**` in SOP EN). Il validate-coverage.py controlla i token EN sia contro il glossario EN (primario) che contro il glossario IT (fallback). Questo rispecchia il pattern di authoring dei SOP EN.

### STALE Terms (warning-only, non bloccanti per D-32)

- IT: 83/153 termini (54%) non referenziati come **bold** nel corpus attuale. Tutti i termini aggiuntivi di Wave 3 (agentic, KPI avanzati, materiali) sono stale perché aggiunti per completezza futura.
- EN: 100/158 termini (63%) stale. Stessa motivazione.
- Exit code: 0 per entrambi. D-32 esplicito: stale è warning-only.

## Known Stubs

Nessuno — tutti i componenti consegnano comportamento reale, non placeholder.

## Self-Check: PASSED

- [x] `packages/sft-domain/src/sft_domain/glossary/it.yaml` — 153 termini schema-valid
- [x] `packages/sft-domain/src/sft_domain/glossary/en.yaml` — 158 termini schema-valid
- [x] `scripts/validate-glossary-coverage.py` — creato, exit 0
- [x] `scripts/generate-glossary-pages.py` — creato, idempotente, --check exit 0
- [x] `docs/docs/glossary.md` — generato (1736 righe)
- [x] `docs/docs/en/glossary.md` — generato (1791 righe)
- [x] `packages/sft-domain/project.json` — target validate-glossary presente
- [x] `Makefile` — target validate-corpus, generate-glossary, generate-assumptions, validate-glossary, validate-all presenti
- [x] `.github/workflows/ci.yml` — step "Validate content" aggiunto
- [x] Commit `bff9e92` — glossary expansion
- [x] Commit `52dedc8` — scripts
- [x] Commit `9b55e51` — wiring
- [x] Commit `3179be5` — CI
