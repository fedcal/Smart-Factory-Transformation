---
phase: 08-agents-knowledge-training
plan: 09
subsystem: knowledge-cluster
tags:
  - e2e
  - documentation
  - TRN-05
  - SC-5
dependency_graph:
  requires:
    - 08-04 (ShiftHandover agent)
    - 08-05 (TrainingCoach agent)
    - 08-06 (KnowledgeCurator agent)
    - 08-07 (DocumentationSynthesizer agent)
    - 08-08 (knowledge_agents.py HTTP router)
  provides:
    - E2E coverage of all four knowledge agents with citation provenance gate
    - Bilingual IT/EN cluster documentation
    - mkdocs nav wiring for Knowledge cluster
  affects:
    - apps/api-gateway/tests/test_knowledge_cluster_e2e.py
    - docs/docs/agents/knowledge/knowledge-cluster.md
    - docs/docs/en/agents/knowledge/knowledge-cluster.md
    - docs/mkdocs.yml
tech_stack:
  added: []
  patterns:
    - Mock supervisor graph E2E (mirrors Phase 7 07-12 pattern)
    - SOPCitationValidator negative test gate (TRN-05 enforcement)
    - Bilingual docs IT canonical + EN parallel (mirrors 07-11 pattern)
key_files:
  created:
    - apps/api-gateway/tests/test_knowledge_cluster_e2e.py
    - docs/docs/agents/knowledge/knowledge-cluster.md
    - docs/docs/en/agents/knowledge/knowledge-cluster.md
  modified:
    - docs/mkdocs.yml
decisions:
  - "E2E uses mock supervisor graph (AsyncMock ainvoke) — same LLM_BACKEND=mock pattern as Phase 7; real testcontainer stack deferred to Phase 11"
  - "MagicMock(spec=SOPDraft) used for negative TRN-05 assertions to bypass Pydantic frozen model constraints while preserving duck-typed validator behavior"
  - "Knowledge cluster docs placed in agents/knowledge/ subfolder (not a flat knowledge-cluster.it.md) to match the mkdocs i18n plugin folder structure"
metrics:
  duration: "~40 minutes"
  completed_date: "2026-05-24T11:36:00Z"
  tasks: 2
  files: 4
requirements:
  - TRN-02
  - TRN-03
  - TRN-04
  - TRN-05
---

# Phase 8 Plan 09: Knowledge Cluster E2E + Bilingual Docs Summary

**One-liner:** E2E test suite covering all four knowledge agents with dual-signoff, training-signoff, autonomous curator, and SOP HITL assertions, plus TRN-05 negative gate rejecting uncited outputs; IT/EN bilingual docs and mkdocs nav wired for the knowledge cluster.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Four-agent E2E + TRN-05 opaque-output rejection | `936faf6` | `apps/api-gateway/tests/test_knowledge_cluster_e2e.py` |
| 2 | Bilingual cluster docs + mkdocs nav | `dd7d741` | `docs/docs/agents/knowledge/knowledge-cluster.md`, `docs/docs/en/agents/knowledge/knowledge-cluster.md`, `docs/mkdocs.yml` |

## What Was Built

### Task 1: E2E Test Suite (test_knowledge_cluster_e2e.py)

Six tests marked `integration + asyncio` covering the full knowledge cluster:

1. **`test_shift_handover_dual_signoff_audit_rows`** — Three sequential graph invocations simulate compile + dual supervisor sign-off; asserts exactly 2 `HANDOVER_SIGNOFF` events with `source_uri` + `timestamp` (D-SH-03, TRN-05).

2. **`test_training_coach_pass_and_signoff`** — Session POST returns `competency_result` with RAG citations; resume POST records `TRAINING_SIGNOFF` with provenance (D-TC-03, TRN-05).

3. **`test_knowledge_curator_dedup_and_stale_no_hitl`** — Ingest POST returns synchronous 200 (never 202); curation report carries both `KNOWLEDGE_DEDUP` + `STALE_FLAG` events with `source_uri` + `timestamp`; exactly one graph call (D-KC-04).

4. **`test_documentation_synthesizer_draft_hitl_qdrant`** — Draft POST returns 202 supervisor_pending; no `SOP_DRAFT` row before HITL; second invocation simulates post-approval — `SOP_DRAFT` written + `qdrant_upserted=True` (D-DS-03, TRN-04).

5. **`test_trn05_opaque_output_rejected_by_sop_citation_validator`** — Negative gate: `SOPCitationValidator` raises `ValidationError` on (a) empty citations list, (b) missing `source_uri`, (c) missing `retrieved_at`. Positive case: valid draft passes (TRN-05, SC-5).

6. **`test_all_agents_produce_cited_outputs`** — Positive sweep across all four agents in a single app; each response asserted to carry `source_uri` + `retrieved_at` where applicable.

All tests use `AsyncMock` supervisor graphs and `LLM_BACKEND=mock` — no live infrastructure.

**Verification:** `uv run python -m pytest apps/api-gateway/tests/test_knowledge_cluster_e2e.py -v` → `6 passed`.

### Task 2: Bilingual Documentation + Nav

- **`docs/docs/agents/knowledge/knowledge-cluster.md`** (IT canonical): describes all four agents with sections for Strumenti Utilizzati / Fonti Dati / HITL Tier / KPI Impattati / Invocazione / Audit Footprint. Includes TRN-05/SC-5 provenance guarantee section.
- **`docs/docs/en/agents/knowledge/knowledge-cluster.md`** (EN parallel): mirrors IT structure, translated consistently.
- **`docs/mkdocs.yml`**: added `Knowledge` section under `Agenti` nav, with `Knowledge Cluster` page linked. Added `Knowledge` and `Knowledge Cluster` to `nav_translations` for the EN locale.

**Verification:** `python3 -m mkdocs build --strict` → `Documentation built in 3.62 seconds` (no errors, no warnings).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MagicMock incompatible with frozen Pydantic SOPDraft for negative TRN-05 tests**
- **Found during:** Task 1, test_trn05_opaque_output_rejected_by_sop_citation_validator
- **Issue:** SOPDraft `citations: list[RagCitation]` is validated by Pydantic — `MagicMock` objects cannot be passed as citations to the model constructor (`Input should be a valid dictionary or instance of RagCitation`).
- **Fix:** Used `MagicMock(spec=SOPDraft)` with duck-typed inner citation objects (`_BadCitURI`, `_BadCitTS` classes) passed directly to `validator.validate()` bypassing the Pydantic model constructor — the SOPCitationValidator iterates citations duck-typed (checks `.source_uri` and `.retrieved_at` attributes directly).
- **Files modified:** `apps/api-gateway/tests/test_knowledge_cluster_e2e.py`
- **Commit:** `936faf6` (included in Task 1 commit)

**2. [Rule 2 - Missing] docs_structure=folder requires EN docs in docs/en/ subfolder**
- **Found during:** Task 2
- **Issue:** The mkdocs i18n plugin configured with `docs_structure: folder` expects EN translations under `docs/docs/en/<path>`, not as `<file>.en.md` siblings (which is the `docs_structure: suffix` approach). The plan specified `docs/agents/knowledge-cluster.en.md` but the project uses folder structure.
- **Fix:** Created `docs/docs/en/agents/knowledge/knowledge-cluster.md` matching the pattern of existing EN docs (e.g. `docs/docs/en/agents/maintenance/predictive-maintenance.md`).
- **Files modified:** `docs/docs/en/agents/knowledge/knowledge-cluster.md` (created at correct path)
- **Commit:** `dd7d741`

## Known Stubs

None — all content is substantive and sourced from agent metadata (CONTEXT.md, RESEARCH.md, agent code).

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. E2E test file is test-only (no production surface).

## Self-Check: PASSED

- [x] `apps/api-gateway/tests/test_knowledge_cluster_e2e.py` exists and collects 6 tests
- [x] `docs/docs/agents/knowledge/knowledge-cluster.md` exists
- [x] `docs/docs/en/agents/knowledge/knowledge-cluster.md` exists
- [x] `docs/mkdocs.yml` updated with Knowledge nav section
- [x] `git log --oneline` confirms commits `936faf6` and `dd7d741`
- [x] `mkdocs build --strict` green
- [x] `pytest --co -q` collects 6 tests
- [x] Zero Accenture references in new docs
- [x] SC-5 satisfied: negative TRN-05 test rejects uncited outputs; positive sweep confirms all agents return cited responses
