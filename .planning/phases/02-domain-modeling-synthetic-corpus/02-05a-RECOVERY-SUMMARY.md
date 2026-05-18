---
phase: "02"
plan: "05a"
subsystem: synthetic-corpus
tags: [corpus, sop, bilingual, quality, weaving, dyeing, spinning]
dependency_graph:
  requires: [02-05-corpus-it-partial]
  provides: [02-05-corpus-complete, bilingual-corpus-40-sops]
  affects: [corpus-validators, rag-retrieval]
tech_stack:
  added: []
  patterns: [bilingual-sop-pairs, aql-acceptance-table, four-point-grading]
key_files:
  created:
    - simulators/synthetic-corpus/it/quality_grading/SOP-QLT-005-lot-acceptance-it.md
    - simulators/synthetic-corpus/en/loom/SOP-LOOM-001-troubleshoot-broken-end-en.md
    - simulators/synthetic-corpus/en/loom/SOP-LOOM-002-warp-tension-drift-en.md
    - simulators/synthetic-corpus/en/loom/SOP-LOOM-003-shuttle-jam-en.md
    - simulators/synthetic-corpus/en/loom/SOP-LOOM-004-selvage-fault-en.md
    - simulators/synthetic-corpus/en/loom/SOP-LOOM-005-defect-cleanup-en.md
    - simulators/synthetic-corpus/en/dyeing/SOP-DYE-001-bath-preparation-en.md
    - simulators/synthetic-corpus/en/dyeing/SOP-DYE-002-color-matching-procedure-en.md
    - simulators/synthetic-corpus/en/dyeing/SOP-DYE-003-shade-verification-en.md
    - simulators/synthetic-corpus/en/dyeing/SOP-DYE-004-fastness-check-en.md
    - simulators/synthetic-corpus/en/dyeing/SOP-DYE-005-post-dyeing-wash-en.md
    - simulators/synthetic-corpus/en/spinning/SOP-SPN-001-spindle-calibration-en.md
    - simulators/synthetic-corpus/en/spinning/SOP-SPN-002-drafting-cylinder-cleanup-en.md
    - simulators/synthetic-corpus/en/spinning/SOP-SPN-003-ring-rail-adjustment-en.md
    - simulators/synthetic-corpus/en/spinning/SOP-SPN-004-slub-control-en.md
    - simulators/synthetic-corpus/en/spinning/SOP-SPN-005-preventive-lubrication-en.md
    - simulators/synthetic-corpus/en/quality_grading/SOP-QLT-001-four-point-grading-en.md
    - simulators/synthetic-corpus/en/quality_grading/SOP-QLT-002-broken-end-detection-en.md
    - simulators/synthetic-corpus/en/quality_grading/SOP-QLT-003-mispick-analysis-en.md
    - simulators/synthetic-corpus/en/quality_grading/SOP-QLT-004-shade-deviation-report-en.md
    - simulators/synthetic-corpus/en/quality_grading/SOP-QLT-005-lot-acceptance-en.md
  modified: []
decisions:
  - "EN translations preserve IT related_glossary token keys unchanged (bilingual glossary-loader contract)"
  - "validate-corpus-pairing requires full IT+EN corpus in same worktree; 19 existing IT SOPs copied from master branch"
  - "AQL sampling table (ISO 2859-1) embedded inline in SOP-QLT-005 for both IT and EN"
metrics:
  duration_min: 45
  completed_date: "2026-05-18"
  tasks_completed: 2
  files_created: 21
---

# Phase 02 Plan 05a: Recovery Summary — SOP-QLT-005 IT + 20 EN SOPs

**One-liner:** Corpus completato con SOP-QLT-005 IT (lot acceptance + AQL table) e 20 traduzioni EN industriali, raggiungendo 40 SOP bilingui validati (20 IT + 20 EN, 5 famiglie).

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | SOP-QLT-005 IT — Procedura di accettazione lotto | ed016e9 | 1 file IT |
| 2a | 5 EN SOPs — loom family | dfa125b | LOOM-001..005 EN |
| 2b | 5 EN SOPs — dyeing family | 4b90554 | DYE-001..005 EN |
| 2c | 5 EN SOPs — spinning family | 1c8fe2d | SPN-001..005 EN |
| 2d | 5 EN SOPs — quality_grading family | afe0fc9 | QLT-001..005 EN |
| 2e | 19 IT SOPs (existing) mirrored in worktree | cac045f | pairing validator gate |

## SOP-QLT-005 IT Details

- **Titolo:** Procedura di accettazione lotto
- **Frontmatter:** asset_family: quality_grading, role: quality-manager, hazard_level: low, estimated_duration_min: 60
- **Prerequisiti:** SOP-QLT-001, SOP-QLT-004
- **related_glossary:** accettazione_lotto, aql, livello_qualita_accettabile, ispezione_4_punti, lotto_tintoriale
- **Asset:** inspection table
- Contiene tabella di campionamento AQL inline (soglie Prima/Seconda/Rifilo) + regole decisione per Ac/Re
- Completa distribuzione 5+5+5+5 (loom/dyeing/spinning/quality_grading)

## EN Translation Approach

- **Meccanica:** traduzione fedele, registro industriale inglese (factory-floor)
- **H2 rinominati:** Scope / Prerequisites / Tools and PPE / Step-by-step Procedure / Verification / Troubleshooting / References
- **lang: en**, slug suffix `-en`, title tradotto
- **related_glossary:** token IT invariati (contract con glossary-loader bilingue)
- **Unita' preservate:** picks/cm, °C, bar, Nm, Shore A, delta_E CMC
- **Termini tecnici IT in bold** mantenuti nel testo EN dove servono come anchor al glossario

## Validation Results

```
validate-corpus-frontmatter: OK — 40 SOP(s) validated, 0 errors
validate-corpus-pairing:     OK — 20 SOP id(s), 20 IT + 20 EN
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] 19 IT SOPs assenti nel worktree**
- **Found during:** esecuzione validate-corpus-pairing
- **Issue:** Il worktree era creato su un branch che non aveva la cronologia del corpus IT (19 SOP su master, non nel branch worktree-agent). Il validator validate-corpus-pairing richiede corpus IT+EN nella stessa directory.
- **Fix:** Copiati i 19 file IT dal branch master nel working tree del worktree e committati separatamente (chore commit `cac045f`). I file sono identici a master:15e6b30.
- **Files modified:** 19 IT SOPs (loom/dyeing/spinning/quality_grading)
- **Commit:** cac045f

## Known Stubs

None — tutti i 21 nuovi file sono SOP completi con contenuto industriale reale.

## Threat Flags

None — nessun endpoint di rete, path di autenticazione o schema DB introdotto. I file sono documenti Markdown statici.

## Self-Check: PASSED

- [x] SOP-QLT-005 IT creato: `simulators/synthetic-corpus/it/quality_grading/SOP-QLT-005-lot-acceptance-it.md` — commit ed016e9
- [x] 20 EN SOPs creati in 4 batch — commit dfa125b, 4b90554, 1c8fe2d, afe0fc9
- [x] validate-corpus-frontmatter: 40 SOP, 0 errori
- [x] validate-corpus-pairing: 20 IT + 20 EN, OK
- [x] Branch: worktree-agent-a2e6cf5a6350ae08e (corretto)
- [x] Nessuna modifica a STATE.md o ROADMAP.md
