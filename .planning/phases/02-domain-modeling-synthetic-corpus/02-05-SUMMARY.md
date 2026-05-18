---
phase: 2
plan: "02-05"
subsystem: sop-corpus-en-domain-en-glossary
tags: [sop-corpus, domain-analysis, glossary, bilingual, wave3]
depends_on:
  requires: ["02-01", "02-02", "02-03", "02-04"]
  provides: ["20-sop-en", "10-domain-pages-en", "glossary-≥150-it", "glossary-≥150-en"]
  affects: ["simulators/synthetic-corpus/", "docs/docs/", "packages/sft-domain/src/sft_domain/glossary/"]
tech_stack:
  added: []
  patterns: ["bilingual-mirror", "sop-authoring", "yaml-glossary"]
key_files:
  created:
    - simulators/synthetic-corpus/en/ (20 EN SOP files)
    - docs/docs/en/domain/ (10 EN domain pages)
    - packages/sft-domain/src/sft_domain/glossary/it.yaml (153 terms after 02-05c)
    - packages/sft-domain/src/sft_domain/glossary/en.yaml (158 terms after 02-05c)
decisions:
  - "SOP EN usano bold cross-lingua per termini IT (pattern authoring chiarito in 02-05c)"
  - "Glossary expansion a ≥150 termini in 02-05c (recovery)"
metrics:
  duration: "multi-wave (02-05a + 02-05b + 02-05c)"
  completed: "2026-05-18"
---

# Phase 2 Plan 02-05: SUMMARY Consolidato

**One-liner:** Completamento corpus 20 SOP EN + 10 domain pages EN + espansione glossario IT 78→153 + EN 77→158 (≥150 per lingua D-31) con CI-ready coverage validation.

## Breakdown per Recovery Batch

Questo piano è stato eseguito in 3 recovery batch successivi:

| Batch | Contenuto | Dettagli |
|-------|-----------|---------|
| **02-05a** | SOP-QLT-005 IT + 20 EN SOPs | Vedere `02-05a-RECOVERY-SUMMARY.md` |
| **02-05b** | 10 EN domain pages (5 process + 4 role + index) | Vedere `02-05b-RECOVERY-SUMMARY.md` |
| **02-05c** | Glossary expansion (78→153 IT, 77→158 EN) + scripts + wiring | Vedere `02-05c-RECOVERY-SUMMARY.md` |

## Deliverable Finali

- **Corpus SOP:** 20 IT + 20 EN SOPs in `simulators/synthetic-corpus/` (D-25, D-26, D-27, D-28)
- **Domain Analysis EN:** `docs/docs/en/domain/` — 10 file bilingui specchianti l'IT (D-21, D-24)
- **Glossario IT:** 153 termini in `packages/sft-domain/src/sft_domain/glossary/it.yaml` (D-29, D-30, D-31)
- **Glossario EN:** 158 termini in `packages/sft-domain/src/sft_domain/glossary/en.yaml` (D-29, D-30, D-31)

## Self-Check: PASSED

Riferirsi ai SUMMARY dei singoli batch per i dettagli dei self-check.
