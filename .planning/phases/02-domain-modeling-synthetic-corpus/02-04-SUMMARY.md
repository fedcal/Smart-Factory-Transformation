---
phase: 02
plan: 04
subsystem: synthetic-corpus
tags: [corpus, sop, validation, nx, bilingual, quality_grading, weaving, dyeing, spinning]
dependency_graph:
  requires:
    - "02-01: sop.schema.json + it.yaml glossary bootstrap"
  provides:
    - "simulators/synthetic-corpus Nx project (validate-frontmatter + validate-pairing targets)"
    - "3 corpus validator scripts (frontmatter, pairing, bilingual-mirror)"
    - "5 IT SOPs covering 4 asset families (draft-unreviewed per D-25)"
    - "pytest inventory scaffold (7 tests)"
  affects:
    - "02-05: EN translations + remaining 15 SOPs (drops --allow-missing-en)"
    - "02-07: plan-03 human review pass promotes status to reviewed"
    - "Phase 5: Knowledge Layer ingestion defaults to status=reviewed filter"
tech_stack:
  added:
    - "python-frontmatter 1.1.0 (dev dep: frontmatter parsing in validators)"
    - "jsonschema 4.26+ with Draft202012Validator (SOP frontmatter schema validation)"
  patterns:
    - "Validator script shape: validate-nx-graph.py analog (argparse + Path + error accumulation)"
    - "Nx project: nx:run-commands (not @nxlv/python:run-commands) for workspace-level scripts"
    - "Graceful empty-corpus: validators exit 0 before content exists (bootstrap-safe)"
key_files:
  created:
    - scripts/validate-corpus-frontmatter.py
    - scripts/validate-corpus-pairing.py
    - scripts/validate-bilingual-mirror.py
    - tests/test_corpus_inventory.py
    - simulators/synthetic-corpus/project.json
    - simulators/synthetic-corpus/README.md
    - simulators/synthetic-corpus/it/loom/SOP-LOOM-001-troubleshoot-broken-end-it.md
    - simulators/synthetic-corpus/it/loom/SOP-LOOM-002-warp-tension-drift-it.md
    - simulators/synthetic-corpus/it/dyeing/SOP-DYE-001-bath-preparation-it.md
    - simulators/synthetic-corpus/it/spinning/SOP-SPN-001-spindle-calibration-it.md
    - simulators/synthetic-corpus/it/quality_grading/SOP-QLT-001-four-point-grading-it.md
  modified:
    - pyproject.toml (added jsonschema>=4.23,<5 + python-frontmatter>=1.1,<2 + pyyaml>=6.0,<7 to dev deps)
    - packages/sft-domain/src/sft_domain/schemas/sop.schema.json (copied to worktree)
decisions:
  - "Validators skip non-SOP files via FILENAME_PATTERN filter (README.md, etc.) — D-26 filename convention is the discriminant"
  - "Default argparse paths use WORKSPACE_ROOT / ... (absolute) to avoid relative-path resolution failure when called from arbitrary cwd"
  - "project.json includes validate-bilingual-mirror target (in addition to the two required by plan) for complete corpus CI coverage"
  - "sop.schema.json copied to worktree packages path so default schema resolution works without --schema-file override"
metrics:
  duration: "~45 minutes"
  completed: "2026-05-17"
  tasks: 2
  files: 14
---

# Phase 2 Plan 04: Synthetic Corpus Validators + 5 IT SOPs Summary

Corpus validation framework (3 scripts + pytest inventory) + synthetic-corpus Nx project bootstrapped + 5 Italian SOPs authored covering all 4 Phase 2 asset families with `status: draft-unreviewed` per D-25 hybrid workflow.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Corpus validators + pytest scaffold | `535f0c3` | `scripts/validate-corpus-{frontmatter,pairing}.py`, `scripts/validate-bilingual-mirror.py`, `tests/test_corpus_inventory.py`, `pyproject.toml` |
| 2 | Nx project + README + 5 IT SOPs | `e0ac213` | `simulators/synthetic-corpus/project.json`, `README.md`, 5 IT SOP files under `it/{loom,dyeing,spinning,quality_grading}/` |

## What Was Built

**Task 1 — 3 Corpus Validators + pytest scaffold**

- `scripts/validate-corpus-frontmatter.py`: validates YAML frontmatter against `sop.schema.json` (Draft202012Validator), enforces fixed H2 section order per D-26, checks filename convention and lang suffix match. Graceful empty-corpus exit 0.
- `scripts/validate-corpus-pairing.py`: groups SOPs by `id`, asserts 1 IT + 1 EN per id (with `--allow-missing-en` for Plan 02-04 IT-only phase), validates semantic field consistency between pairs.
- `scripts/validate-bilingual-mirror.py`: checks H1 + first 5 H2 heading structure match between `docs/docs/*.md` and `docs/docs/en/*.md` (with `--allow-missing-en` flag). Excludes `en/` and `assets/` dirs.
- `tests/test_corpus_inventory.py`: 7 pytest tests (4 parametrized by asset family) covering corpus dir existence, distribution per family, status enum validity, filename/lang consistency. Skip gracefully on empty corpus.
- `pyproject.toml` updated: added `jsonschema>=4.23,<5`, `python-frontmatter>=1.1,<2`, `pyyaml>=6.0,<7` to dev dependency-groups.

**Task 2 — Nx Project + 5 IT SOPs**

- `simulators/synthetic-corpus/project.json`: Nx `library` project with 3 targets (`validate-frontmatter`, `validate-pairing`, `validate-bilingual-mirror` via `nx:run-commands`), `implicitDependencies: ["sft-domain"]`, cache inputs per target.
- `simulators/synthetic-corpus/README.md`: Documents D-25 hybrid authoring workflow, D-28 factory-floor style, 6-value `asset_family` enum, `process` (D-21, 5 values) vs `asset_family` (SOP scope, 6 values) distinction, Nx target invocations, and the Phase 5 retrieval contract (Open Question #5 resolved: default filter `status: reviewed`).
- 5 IT SOPs (all `status: draft-unreviewed`, `created_in_phase: 2`):
  - `SOP-LOOM-001`: Risoluzione guasto rottura filo ordito (asset_family: weaving, role: operator, hazard: low, 15 min)
  - `SOP-LOOM-002`: Diagnosi e correzione deriva tensione ordito (asset_family: weaving, role: technician, hazard: medium, 30 min)
  - `SOP-DYE-001`: Preparazione bagno colorante per tintura jet dyeing (asset_family: dyeing, role: technician, hazard: medium, 45 min)
  - `SOP-SPN-001`: Calibrazione e verifica fusi filatoio ad anello (asset_family: spinning, role: technician, hazard: low, 25 min)
  - `SOP-QLT-001`: Ispezione tessuto con sistema di classificazione a quattro punti (asset_family: quality_grading, role: quality-manager, hazard: low, 20 min)

## Deviations from Plan

**1. [Rule 1 - Bug] Validators picked up README.md as a SOP file**
- **Found during:** Task 2 first validation run
- **Issue:** `rglob("*.md")` also matched `README.md` which has no SOP frontmatter, causing 11 schema errors and 1 filename error
- **Fix:** Added `FILENAME_PATTERN.match(f.name)` filter to both `validate-corpus-frontmatter.py` and `validate-corpus-pairing.py` to process only files matching `^SOP-[A-Z]+-[0-9]{3}-[a-z0-9-]+-(it|en)\.md$`
- **Files modified:** `scripts/validate-corpus-frontmatter.py`, `scripts/validate-corpus-pairing.py`
- **Commit:** included in `e0ac213`

**2. [Rule 3 - Blocking] Relative path resolution failure in validators**
- **Found during:** Task 2 first validator run (empty corpus test after Task 1)
- **Issue:** Default argparse paths (`Path("simulators/synthetic-corpus")`) were relative and `WORKSPACE_ROOT` was absolute, causing `path.relative_to(WORKSPACE_ROOT)` to raise `ValueError`
- **Fix:** Changed default argparse `default` values to use `WORKSPACE_ROOT / "..."` (absolute paths); added `if not corpus_dir.is_absolute(): corpus_dir = WORKSPACE_ROOT / corpus_dir` guard in validate functions
- **Files modified:** all 3 validator scripts
- **Commit:** included in Task 1/2 commits

**3. [Rule 3 - Blocking] sop.schema.json not present in worktree**
- **Found during:** Task 2 first validation run (schema was in main repo, not worktree)
- **Issue:** The schema file was created by Plan 02-01 in the main repo but not yet in the worktree; validators defaulted to the worktree path and failed with "Schema file not found"
- **Fix:** Copied `sop.schema.json` to `packages/sft-domain/src/sft_domain/schemas/sop.schema.json` in the worktree
- **Files modified:** `packages/sft-domain/src/sft_domain/schemas/sop.schema.json` (added to worktree)
- **Commit:** `e0ac213`

## Known Stubs

None. All 5 SOPs contain complete content in all 7 required H2 sections. The `status: draft-unreviewed` is not a stub — it is the intended state per D-25 (human review happens in Plan 07).

## Threat Flags

No new threat surface introduced beyond what the plan's threat model covered (T-02-16 through T-02-21).

## Self-Check: PASSED

- [x] `scripts/validate-corpus-frontmatter.py` exists and contains `Draft202012Validator`
- [x] `scripts/validate-corpus-pairing.py` exists and contains `--allow-missing-en`
- [x] `scripts/validate-bilingual-mirror.py` exists and contains `--allow-missing-en`
- [x] `tests/test_corpus_inventory.py` exists with 7 collected tests
- [x] `simulators/synthetic-corpus/project.json` parses as valid JSON with required targets
- [x] `simulators/synthetic-corpus/README.md` contains "draft-unreviewed", "Phase 5", "quality_grading"
- [x] All 5 IT SOPs exist at exact paths in `files_modified`
- [x] All 5 SOPs have `status: draft-unreviewed`
- [x] `SOP-QLT-001` has `asset_family: quality_grading` (not `quality`)
- [x] No bare `asset_family: quality` in corpus
- [x] No "Accenture" in corpus
- [x] `python3 scripts/validate-corpus-frontmatter.py` exits 0 (5 SOPs, 0 errors)
- [x] `python3 scripts/validate-corpus-pairing.py --allow-missing-en` exits 0
- [x] `python3 scripts/validate-corpus-pairing.py` (strict) exits 1 (EN files not yet written)
- [x] `uv run pytest tests/test_corpus_inventory.py -q` reports 7 passed
- [x] Commits `535f0c3` (Task 1) and `e0ac213` (Task 2) exist
