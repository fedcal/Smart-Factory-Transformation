---
phase: 05-knowledge-layer-rag-graph
plan: 13
subsystem: knowledge-ingest
tags: [gap-closure, eval, disclaimer, cli-safety, knw-03, in-05]
dependency_graph:
  requires: []
  provides: [IN-05-closed, KNW-03-disclaimer-propagated]
  affects: [docs/eval, docs/docs/knowledge-layer, services/knowledge-ingest/scripts]
tech_stack:
  added: []
  patterns: [TDD RED-GREEN, argparse-safer-defaults, mkdocs-material-admonitions]
key_files:
  created:
    - services/knowledge-ingest/tests/test_run_ab_eval_disclaimer.py
  modified:
    - services/knowledge-ingest/scripts/run_ab_eval.py
    - docs/docs/knowledge-layer/eval-results.md
    - docs/docs/en/knowledge-layer/eval-results.md
    - docs/eval/rag-ab-test-bge-m3-vs-e5.md
decisions:
  - "Path (A) chosen for KNW-03 gap closure: add disclaimer + rename flag; live eval deferred to Phase 8 KnowledgeCurator"
  - "--skip-eval (default True, unsafe) renamed to --stub (default False, opt-in); no-flag raises NotImplementedError"
  - "Disclaimer phrase '⚠ Preliminary stub metrics — pending real eval run' propagated verbatim across all 3 surfaces"
metrics:
  duration: "~25 min"
  completed: "2026-05-24"
  tasks_total: 2
  tasks_completed: 2
  files_created: 1
  files_modified: 4
---

# Phase 5 Plan 13: KNW-03 Eval Disclaimer & --stub Flag — Summary

**One-liner:** Replaced unsafe `--skip-eval` (default True) with opt-in `--stub` (default False); propagated "⚠ Preliminary stub metrics" disclaimer to all three eval-results surfaces (IT MkDocs, EN MkDocs, canonical doc); 4 regression tests enforce the new CLI contract.

---

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 RED | Add failing regression tests for --stub flag | d5601a5 | `tests/test_run_ab_eval_disclaimer.py` (created) |
| 1 GREEN | Rename --skip-eval to --stub with safer default | bf964a7 | `scripts/run_ab_eval.py` |
| 2 | Add disclaimer admonition to IT/EN MkDocs pages; update canonical doc | 0ecc554 | `eval-results.md` (IT), `eval-results.md` (EN), `rag-ab-test-bge-m3-vs-e5.md` |

---

## Gap Closed

**Gap 3 from 05-VERIFICATION.md** (KNW-03 PARTIAL / IN-05):

Before this plan:
- `--skip-eval` defaulted to `True` → CI silently produced stub metrics as if measured
- MkDocs IT/EN eval-results pages published stub numbers **without disclaimer**
- Only the canonical `docs/eval/` doc carried the "Preliminary run notice"

After this plan:
- `--stub` (default `False`) requires explicit opt-in; no-flag invocation raises `NotImplementedError` with a Phase 8 KnowledgeCurator pointer
- All three published surfaces carry the disclaimer phrase: "⚠ Preliminary stub metrics — pending real eval run"
- Phase 8 deferral explicitly recorded in the canonical doc (new "Deferred follow-up" section)
- 4 regression tests guard the new CLI contract permanently

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ValueError when testset path is outside workspace root**
- **Found during:** Task 1 GREEN (test execution)
- **Issue:** `_render_deliverable` called `testset_path.relative_to(WORKSPACE_ROOT)` unconditionally; the test used `tmp_path` which is outside the workspace, triggering `ValueError`
- **Fix:** Added `try/except ValueError` fallback that uses the absolute path as-is when the testset is outside the workspace
- **Files modified:** `services/knowledge-ingest/scripts/run_ab_eval.py`
- **Commit:** bf964a7

---

## Verification Results

All acceptance criteria met:

- `grep -c '"--skip-eval"' services/knowledge-ingest/scripts/run_ab_eval.py` → 0
- `grep -c '"--stub"' services/knowledge-ingest/scripts/run_ab_eval.py` → 1
- `grep -c 'NotImplementedError' services/knowledge-ingest/scripts/run_ab_eval.py` → 5 (≥ 2)
- `grep -c "Phase 8" services/knowledge-ingest/scripts/run_ab_eval.py` → 14 (≥ 1)
- `grep -c "Preliminary stub metrics" services/knowledge-ingest/scripts/run_ab_eval.py` → 2 (≥ 1)
- All 4 tests in `test_run_ab_eval_disclaimer.py` PASS
- `grep -c "Preliminary stub metrics" docs/docs/knowledge-layer/eval-results.md` → 1 (≥ 1)
- `grep -c "Preliminary stub metrics" docs/docs/en/knowledge-layer/eval-results.md` → 1 (≥ 1)
- `grep -c "Preliminary stub metrics" docs/eval/rag-ab-test-bge-m3-vs-e5.md` → 1 (≥ 1)
- `grep -c "Phase 8" docs/eval/rag-ab-test-bge-m3-vs-e5.md` → 7 (≥ 1)
- `grep -c "\-\-skip-eval" docs/docs/knowledge-layer/eval-results.md docs/docs/en/knowledge-layer/eval-results.md docs/eval/rag-ab-test-bge-m3-vs-e5.md` → 0 per file
- `grep -c "^!!! warning" docs/docs/knowledge-layer/eval-results.md` → 1 (≥ 1)
- `grep -c "^!!! warning" docs/docs/en/knowledge-layer/eval-results.md` → 1 (≥ 1)
- Full unit suite: 83 passed, 31 deselected (no regressions)

---

## Known Stubs

The eval metrics in all three documents remain deterministic stubs from `_stub_summary()`.
This is **intentional and documented**: the disclaimer admonition on all three surfaces makes
the stub origin explicit. Phase 8 KnowledgeCurator will replace these with live measurements.

---

## Threat Flags

None — this plan closes T-05-13-01 (Repudiation: stub numbers published without disclaimer)
and T-05-13-02 (Tampering: forgotten flag silently produces stubs). No new security surface introduced.

## Self-Check: PASSED

- `services/knowledge-ingest/tests/test_run_ab_eval_disclaimer.py` — FOUND (created)
- `services/knowledge-ingest/scripts/run_ab_eval.py` — FOUND (modified)
- `docs/docs/knowledge-layer/eval-results.md` — FOUND (modified)
- `docs/docs/en/knowledge-layer/eval-results.md` — FOUND (modified)
- `docs/eval/rag-ab-test-bge-m3-vs-e5.md` — FOUND (modified)
- Commits d5601a5, bf964a7, 0ecc554 — all present in git log
