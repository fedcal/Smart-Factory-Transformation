---
phase: 2
plan: "02-06"
subsystem: validation-scripts-ci-integration
tags: [validation, ci, makefile, nx, assumption-register, glossary-scripts, wave3]
depends_on:
  requires: ["02-01", "02-02", "02-03", "02-04", "02-05"]
  provides: ["validate-coverage-script", "generate-glossary-script", "nx-validate-glossary", "makefile-validate-all", "ci-validate-content", "assumption-register-50"]
  affects: ["scripts/", "packages/sft-domain/project.json", "Makefile", ".github/workflows/ci.yml", "docs/docs/assumptions/"]
tech_stack:
  added: []
  patterns: ["idempotent-generator", "lang-matched-coverage", "nx-run-commands", "ci-content-validation"]
key_files:
  created:
    - scripts/validate-glossary-coverage.py
    - scripts/generate-glossary-pages.py
    - docs/docs/glossary.md
    - docs/docs/en/glossary.md
    - docs/docs/assumptions/A-031.md ... A-050.md (20 file)
    - docs/docs/en/assumptions/A-031.md ... A-050.md (20 file)
  modified:
    - packages/sft-domain/project.json (validate-glossary target)
    - Makefile (validate-corpus, generate-glossary, generate-assumptions, validate-glossary, validate-all)
    - .github/workflows/ci.yml (step "Validate content")
decisions:
  - "validate-coverage usa fallback cross-lingua per token IT nei SOP EN"
  - "generate-glossary --check exit 2 su drift: CI-safe idempotency check"
  - "validate-all usa uv run per dipendenze Python del progetto (frontmatter, jsonschema)"
  - "CI step usa || true su target Nx non universali (validate-frontmatter non su tutti i progetti)"
metrics:
  duration: "Eseguito in 02-05c recovery batch"
  completed: "2026-05-18"
  tasks: 3
  files_created: 44
  files_modified: 3
---

# Phase 2 Plan 02-06: SUMMARY Consolidato

**One-liner:** Script validate-glossary-coverage.py (D-32 lang-matched bold coverage) + generate-glossary-pages.py idempotente (D-29) + Nx target validate-glossary + Makefile validate-all + step CI "Validate content".

## Breakdown Deliverable

### Script 1: validate-glossary-coverage.py (D-32)

- Estrae token `**bold**` da corpus IT/EN + domain pages + assumption pages
- Normalizza (lowercase, snake_case, strip field labels, step headings filtrati)
- Lookup lang-matched con fallback cross-lingua per riferimenti IT in SOP EN
- Exit 1 su token mancanti da glossario; exit 0 con STALE warnings stdout (>5% soglia)
- Risultato corrente: 70 IT + 103 EN token coperti, exit 0

### Script 2: generate-glossary-pages.py (D-29)

- Genera `docs/docs/glossary.md` (IT, 153 termini, 1736 righe)
- Genera `docs/docs/en/glossary.md` (EN, 158 termini, 1791 righe)
- Ordinamento stabile: categoria → termine alfabetico
- Supporta `--dry-run` (preview) e `--check` (drift detection, exit 2)
- Nessun timestamp — output identico tra esecuzioni successive

### Nx Target: validate-glossary (packages/sft-domain/project.json)

```json
"validate-glossary": {
  "executor": "@nxlv/python:run-commands",
  "options": {
    "command": "python3 ../../scripts/validate-glossary-schema.py && python3 ../../scripts/validate-glossary-coverage.py",
    "cwd": "."
  }
}
```

### Makefile Targets

| Target | Funzione |
|--------|---------|
| `validate-corpus` | validate-corpus-frontmatter + pairing + bilingual-mirror (via uv run) |
| `generate-glossary` | genera pagine glossario IT/EN (idempotente) |
| `generate-assumptions` | genera pagine assumption register IT/EN (idempotente) |
| `validate-glossary` | validate-glossary-schema + validate-glossary-coverage |
| `validate-all` | validate-glossary + validate-corpus + assumption schema/components + drift check |

### CI Step: "Validate content"

Aggiunto dopo "Validate Nx dependency graph", prima di "Nx Affected Lint":
- `npx nx run-many --target=validate-glossary,...` (|| true per target selettivi)
- Python validators diretti: schema glossario, copertura, assumption schema/components
- Drift check: genera + --check per glossario e assumption pages

## Deviazioni

**[Rule 2 - Missing] 42 assumption pages mancanti rigenerare** — vedasi `02-05c-RECOVERY-SUMMARY.md`.

## Self-Check: PASSED

- [x] `scripts/validate-glossary-coverage.py` — exit 0 su corpus attuale
- [x] `scripts/generate-glossary-pages.py` — generato, --check exit 0
- [x] `docs/docs/glossary.md` — 1736 righe
- [x] `docs/docs/en/glossary.md` — 1791 righe
- [x] `packages/sft-domain/project.json` — validate-glossary target
- [x] `Makefile` — 5 nuovi target + .PHONY
- [x] `.github/workflows/ci.yml` — step "Validate content"
- [x] `make validate-all` — exit 0
