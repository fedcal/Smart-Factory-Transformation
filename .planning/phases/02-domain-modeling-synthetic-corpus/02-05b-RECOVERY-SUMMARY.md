---
phase: "02"
plan: "05b"
subsystem: domain-docs-en
tags: [bilingual-mirror, domain-pages, translation, en, textile]
dependency_graph:
  requires: [02-02-domain-pages-IT]
  provides: [EN-domain-index, EN-process-pages, EN-role-pages]
  affects: [validate-bilingual-mirror, docs-nav]
tech_stack:
  added: []
  patterns: [bilingual-mirror-structure, mermaid-flowchart-translated, bold-token-glossary-linkage]
key_files:
  created:
    - docs/docs/en/domain/index.md
    - docs/docs/en/domain/processes/weaving.md
    - docs/docs/en/domain/processes/spinning.md
    - docs/docs/en/domain/processes/warping.md
    - docs/docs/en/domain/processes/dyeing.md
    - docs/docs/en/domain/processes/finishing.md
    - docs/docs/en/domain/roles/operator.md
    - docs/docs/en/domain/roles/technician.md
    - docs/docs/en/domain/roles/quality-manager.md
    - docs/docs/en/domain/roles/shift-supervisor.md
  modified: []
decisions:
  - "IT domain pages (10 files) recovered from master via git checkout — worktree branch predated the 02-02 merge"
  - "validate-bilingual-mirror.py copied from master to enable in-worktree validation"
  - "Bold tokens translated to EN equivalents (see Bold Tokens section) to align with future EN glossary"
  - "Mermaid accDescr lines translated to EN; node labels translated; diagram structure preserved"
  - "Admonition label 'Mantis context' preserved unchanged (language-neutral identifier)"
metrics:
  duration_minutes: 15
  completed: "2026-05-18T06:42:00Z"
  tasks_completed: 2
  files_created: 10
  commits: 2
---

# Phase 02 Plan 05b: EN Domain Pages Recovery Summary

EN bilingual mirrors for all 10 IT domain pages (1 index + 5 process + 4 role pages) — H1+H2 symmetry validated by `validate-bilingual-mirror.py` exiting 0.

## What Was Built

10 EN domain pages were created under `docs/docs/en/domain/` mirroring the IT pages in `docs/docs/domain/`. Each page preserves the identical H1+H2 heading structure, Mermaid `flowchart LR` diagrams with translated node labels and accDescr, bold token vocabulary, KPI tables, and Mantis context admonitions.

## Commits

| Commit | Hash | Files |
|--------|------|-------|
| feat(02-05-domain-en): EN domain index + 5 process pages | 1c10bdc | 16 (6 EN new + 10 IT recovered from master) |
| feat(02-05-domain-en): EN domain 4 role pages | 3370f7d | 4 |

## Validation Results

- `python3 scripts/validate-bilingual-mirror.py` → `OK: 14 IT page(s) validated — all have matching EN mirror structure`
- `uv run pytest tests/test_domain_pages.py -q` → `32 passed in 0.14s`

## Recovery Context

This plan is a recovery executor for Plan 02-05 which timed out (stream-idle) before creating the EN domain pages. The worktree branch (`worktree-agent-a6c957aac8576a9fd`) was created from commit `8c2cc5d` which predates the 02-02 domain pages merge. The IT domain files were recovered via `git checkout master -- docs/docs/domain/` before creating the EN mirrors.

## Deviations from Plan

**1. [Rule 3 - Blocking] Recovered IT domain pages from master**
- **Found during:** Task 1 pre-check
- **Issue:** The worktree branch predated the 02-02 merge; `docs/docs/domain/` did not exist in the worktree, making validation impossible
- **Fix:** `git checkout master -- docs/docs/domain/` to restore IT pages; included in batch 1 commit
- **Files modified:** 10 IT domain files staged from master

**2. [Rule 3 - Blocking] Copied validate-bilingual-mirror.py from master**
- **Found during:** Task 1 pre-check
- **Issue:** The validation script did not exist in the worktree
- **Fix:** `git show master:scripts/validate-bilingual-mirror.py > scripts/validate-bilingual-mirror.py`
- **Files modified:** scripts/validate-bilingual-mirror.py (not committed — already present on master)

## Bold Tokens Used in EN Content

The following bold tokens appear in the EN domain pages. These must be covered by the EN glossary (`docs/glossary.md` or equivalent EN glossary file) in a future plan (Recovery-C or Plan 02-06+):

**Process tokens:**
- `**weaving**`, `**spinning**`, `**warping**`, `**dyeing**`, `**finishing**`
- `**warp**`, `**weft**`, `**pick_density**`, `**warp_beam**`, `**yarn_count**`
- `**loom**`, `**heald**`, `**beating_mechanism**`, `**pick_counter**`
- `**ring_frame**`, `**card**`, `**comber**`, `**spindle**`, `**hygrometer**`
- `**warp_tension_sensor**`, `**digital_calliper**`, `**warp_defect**`
- `**jet_dyeing**`, `**dye_bath**`, `**delta_e**`, `**spectrophotometer**`
- `**grey_fabric**`, `**shade_deviation**`, `**streakiness**`, `**roll_inspection**`
- `**finishing_plant**`, `**inspection_table**`, `**automated_warehouse**`
- `**pilling**`, `**halo**`, `**barring**`, `**selvedge_defect**`

**Defect tokens:**
- `**broken_end**`, `**mispick**`, `**slub**`, `**neps**`, `**fibre_contamination**`
- `**yarn_irregularity**`, `**drafting**`

**Role/system tokens:**
- `**opc_ua**`, `**oee**`, `**mtbf**`, `**mttr**`, `**hitl**`, `**nats**`
- `**ear_protection**`, `**durometer**`

**KPI units preserved (no translation):** picks/cm, °C, g/m², Nm, CVm%, dB(A), ICI grade

## Threat Flags

None — this plan creates static documentation files only. No new network endpoints, auth paths, or schema changes introduced.

## Self-Check

- [x] 10 EN domain pages exist at correct paths under `docs/docs/en/domain/`
- [x] Commit `1c10bdc` exists — `feat(02-05-domain-en): EN domain index + 5 process pages`
- [x] Commit `3370f7d` exists — `feat(02-05-domain-en): EN domain 4 role pages`
- [x] `validate-bilingual-mirror.py` exits 0 (no `--allow-missing-en` flag)
- [x] `pytest tests/test_domain_pages.py -q` exits 0 — 32 passed

## Self-Check: PASSED
