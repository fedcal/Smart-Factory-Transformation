---
phase: 02-domain-modeling-synthetic-corpus
plan: 02
subsystem: documentation
tags: [mkdocs, mermaid, pytest, domain-analysis, textile, italian]

# Dependency graph
requires:
  - phase: 02-01
    provides: "Bootstrap glossary it.yaml (73 terms) — all bold tokens validated against this"
  - phase: 01-07-mkdocs
    provides: "MkDocs Material + pymdownx.superfences mermaid custom_fence + admonition extension"
provides:
  - "10 IT domain analysis pages under docs/docs/domain/ (1 index + 5 processes + 4 roles)"
  - "pytest structural test suite (32 tests) covering H2 contract, Mermaid, Mantis admonition, ≤8-node rule"
  - "tests/conftest.py with module-scoped pathlib.Path fixtures (domain_dir, processes_dir, roles_dir)"
affects:
  - "02-05 EN translation (mirrors this IT structure)"
  - "02-06 CI wiring (runs tests/test_domain_pages.py in nx target)"
  - "02-07 MkDocs nav update (adds Dominio section with these pages)"
  - "Phase 5 Knowledge Layer (BGE-M3 chunk-indexing these pages as retrieval units)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mermaid flowchart LR with accDescr accessibility annotation (RESEARCH Pitfall 2)"
    - "MkDocs !!! note admonition for Mantis-specific context (D-23 pattern)"
    - "pathlib.Path-only test fixtures (no os.path) for security V12 / T-02-10"
    - "pytest parametrize over process/role names for DRY structural assertions"

key-files:
  created:
    - docs/docs/domain/index.md
    - docs/docs/domain/processes/weaving.md
    - docs/docs/domain/processes/spinning.md
    - docs/docs/domain/processes/warping.md
    - docs/docs/domain/processes/dyeing.md
    - docs/docs/domain/processes/finishing.md
    - docs/docs/domain/roles/operator.md
    - docs/docs/domain/roles/technician.md
    - docs/docs/domain/roles/quality-manager.md
    - docs/docs/domain/roles/shift-supervisor.md
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_domain_pages.py
  modified: []

key-decisions:
  - "D-21 enforced: exactly 5 process pages (weaving/spinning/warping/dyeing/finishing) — no quality page; quality_grading is documented as asset_family scope in index.md blockquote"
  - "Bold token discipline: all **bold** terms validated against it.yaml before commit — 0 glossary-coverage debt introduced"
  - "test_process_mermaid_node_count is single source of truth for ≤8-node rule (D-22) — no redundant heuristic in content"
  - "conftest.py fixtures use __file__-relative pathlib.Path so tests work from any cwd"

patterns-established:
  - "Domain page structure: H1 + intro + Mermaid flowchart LR (≤8 nodes, accDescr) + Asset coinvolti + KPI + Pain point + Mantis context admonition + Riferimenti"
  - "Role page structure: H1 + intro + Responsabilità + Interazione tipica + Decisione critica + Pain point + Mantis context admonition + Riferimenti"
  - "Pytest structural tests via class-based parametrize: TestIndexPage / TestProcessSections / TestProcessMermaid / TestRoleSections / TestMantisAdmonition"

requirements-completed: [DOC-05]

# Metrics
duration: 45min
completed: 2026-05-17
---

# Phase 02 Plan 02: Domain Analysis IT Summary

**Italian-language textile domain analysis: 10 Markdown pages (1 index + 5 processes + 4 roles) with Mermaid process flows, KPI tables, pain points, Mantis admonitions — plus 32-test pytest suite enforcing the D-22/D-23 structural contract**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-05-17T19:00:00Z
- **Completed:** 2026-05-17T19:36:32Z
- **Tasks:** 2/2
- **Files created:** 13

## Accomplishments

- 10 IT domain pages authored: 1 overview index, 5 process pages (weaving/spinning/warping/dyeing/finishing), 4 role pages (operator/technician/quality-manager/shift-supervisor)
- Every process page: Mermaid `flowchart LR` ≤7 nodes with `accDescr:` accessibility annotation, 4 required H2 sections, Mantis context admonition
- Every role page: 4 required H2 sections (Responsabilità / Interazione tipica / Decisione critica giornaliera / Pain point), Mantis admonition
- 32 pytest tests: 3 index tests, 5 process-section parametrized, 5 mermaid-presence parametrized, 5 mermaid-node-count parametrized, 4 role-section parametrized, 10 mantis-admonition parametrized — all pass (0.05s)
- 0 glossary-coverage debt: all bold tokens validated against 73-term it.yaml bootstrap glossary before commit

## Task Commits

1. **Task 1: Author the 5 process pages + index (IT)** — `4d29e18` (feat)
2. **Task 2: Author the 4 role pages (IT) + pytest structural tests** — `515d39e` (feat)

## Files Created/Modified

- `docs/docs/domain/index.md` — Domain overview + 5-node flowchart LR (filatura→orditura→tessitura→tintura→finissaggio) + process vs asset_family distinction + links to process/role pages
- `docs/docs/domain/processes/weaving.md` — Tessitura: telaio/subbio/liccio/cassa_battente assets, oee/densita_trama/mtbf/mttr KPIs, rottura_filo/mispick pain points
- `docs/docs/domain/processes/spinning.md` — Filatura: filatoio_anello/carda/fuso/igrometro assets, irregolarita_filato KPI, rottura_filo/neps pain points
- `docs/docs/domain/processes/warping.md` — Orditura: subbio/misuratore_tensione_ordito assets, difetto_catena/contaminazione_fibra pain points
- `docs/docs/domain/processes/dyeing.md` — Tintura: jet_dyeing/spettrofotometro/bagno_colorante assets, delta_e KPI, deviazione_tono/screziatura pain points
- `docs/docs/domain/processes/finishing.md` — Finissaggio: impianto_finissaggio/tavolo_ispezione assets, pilling KPI, aloni/rigatura pain points
- `docs/docs/domain/roles/operator.md` — Front-line loom/spinning operator; stop/continue decision on rottura_filo
- `docs/docs/domain/roles/technician.md` — Preventive/corrective maintenance; repair-on-spot vs planned downtime decision
- `docs/docs/domain/roles/quality-manager.md` — 4-point grading owner; accept/downgrade/reject lotto decision on delta_e
- `docs/docs/domain/roles/shift-supervisor.md` — Turno coordinator + HITL Tier 2 escalation point
- `tests/__init__.py` — Empty package marker (first repo-level pytest)
- `tests/conftest.py` — Module-scoped fixtures domain_dir/processes_dir/roles_dir via __file__-relative pathlib.Path
- `tests/test_domain_pages.py` — 32 structural tests across 5 test classes

## Decisions Made

- D-21 process boundary enforced without a `quality` page: the index.md blockquote explicitly documents that `quality_grading` is an `asset_family` scope (cross-cutting inspection) not a linear process, referencing `sop.schema.json` for the complete 6-value enum.
- Bold token discipline applied: pain point headers that were initially bolded (e.g., "Variabilità pick density", "Solidità colore insufficiente") were reformulated as plain text with individual glossary terms bolded — preventing false positives in Plan 06 glossary coverage check.
- `test_process_mermaid_node_count` in `tests/test_domain_pages.py` is the single source of truth for ≤8-node rule per acceptance criteria — no regex heuristic added in Task 1.
- `conftest.py` fixtures use `__file__`-relative paths so `uv run pytest` works from the repo root without needing to set `PYTHONPATH` or `testpaths`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Bold token validation pass before commit**
- **Found during:** Task 1 authoring
- **Issue:** Initial draft had non-glossary phrases bolded (pain point headers, descriptive clauses) that would have caused Plan 06 glossary coverage check to emit false positives
- **Fix:** Extracted all `**bold**` tokens from all pages and validated each against the 73-term `it.yaml` glossary before staging; reformulated any non-glossary bold text
- **Files modified:** All 6 process pages + index.md
- **Verification:** `grep -oh '**...**'` + diff against `grep "^- term:"` in it.yaml — 0 missing terms
- **Committed in:** 4d29e18 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — correctness/downstream CI)
**Impact on plan:** Essential for Plan 06 glossary coverage CI to pass without false positives. No scope creep.

## Issues Encountered

None — plan executed within scope. The `uv run pytest` command created a `.venv` in the worktree on first run (expected behavior for a new worktree environment).

## Threat Surface Scan

No new security-relevant surface introduced. All files are static Markdown content and a pure-Python test file. No network endpoints, auth paths, or schema changes at trust boundaries.

## Known Stubs

None — all pages are substantive content. EN counterparts are intentionally deferred to Plan 02-05 (Wave 3) per the plan objective; no stub EN files were created.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 02-03 (Assumption Register) and 02-04 (SOP corpus) can proceed in parallel — they do not depend on these domain pages
- Plan 02-05 (EN translation) requires these IT pages as source — ready
- Plan 02-06 (CI wiring) requires `tests/test_domain_pages.py` — ready; 32 tests pass
- Plan 02-07 (MkDocs nav update) requires these pages to exist — ready; will add `Dominio:` nav entry

---
*Phase: 02-domain-modeling-synthetic-corpus*
*Completed: 2026-05-17*
