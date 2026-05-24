---
phase: 08-agents-knowledge-training
plan: "07"
subsystem: knowledge
tags: [documentation-synthesizer, bilingual-sop, hitl, qdrant-indexing, tdd, trn-05, cr-02]
dependency_graph:
  requires: ["08-00a", "08-00b"]
  provides: ["DocumentationSynthesizer", "SOPDraft", "SOPCitationValidator", "HistoricalEventAggregator"]
  affects: ["Qdrant sop collection", "audit.actions SOP_DRAFT rows"]
tech_stack:
  added: []
  patterns:
    - "CR-02: interrupt() DIRECTLY in __call__ — no double-write, no side-effects on first run"
    - "CR-03: approval_id=None for pending HITL rows"
    - "CR-01: saver=None RuntimeError guard"
    - "Pitfall §1: [SRC:N] anchor preservation through IT→EN translation"
    - "TRN-05: citation provenance — source_uri + timestamp mandatory on every citation"
    - "D-DS-02: JSONB query via Python-computed TIMESTAMPTZ window (WR-03)"
    - "Pattern E: ClassVar SQL constants for $N parameterization gate"
key_files:
  created:
    - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/models.py
    - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/event_aggregator.py
    - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/sop_builder.py
    - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/translator.py
    - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/validators.py
    - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/agent.py
    - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/metadata.py
    - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/prompts.py
  modified:
    - apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/__init__.py
    - apps/agents/knowledge/documentation-synthesizer/tests/test_translator.py
    - apps/agents/knowledge/documentation-synthesizer/tests/test_citation_provenance.py
    - apps/agents/knowledge/documentation-synthesizer/tests/test_hitl_preindex.py
decisions:
  - "SOPDraft uses frozen Pydantic model with field_validator enforcing all 5 SECTION_KEYS_IT"
  - "JSONB window query: compute window_start as Python datetime, pass as $1 TIMESTAMPTZ (WR-03)"
  - "SOPTranslator iterates SECTION_KEYS_IT per-section for granular LLM calls"
  - "_write_audit fires with approval_id=None (CR-03 fix) after interrupt() returns"
  - "saver=None guard raises RuntimeError at __init__ not at __call__ time"
metrics:
  duration_minutes: 10
  completed_date: "2026-05-24"
  tasks_completed: 2
  files_created: 9
  files_modified: 4
  tests_passing: 14
---

# Phase 08 Plan 07: DocumentationSynthesizer Summary

**One-liner:** Bilingual SOP draft (IT+EN) from historical RCA/downtime/coach events with [SRC:N] citation anchors, SOPCitationValidator (TRN-05), and supervisor HITL gating Qdrant indexing (D-DS-03, CR-02).

## What Was Built

SC-4 satisfied: the DocumentationSynthesizer agent aggregates historical audit events by failure_mode + asset (JSONB query, D-DS-02), generates a fixed-section Italian SOP with [SRC:N] citation anchors (D-DS-01), translates to English preserving every anchor (Pitfall §1 mitigation), validates citation provenance (TRN-05), and gates Qdrant indexing behind supervisor HITL (interrupt() directly in __call__, CR-02 fix).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | SOPDraft models + event_aggregator + sop_builder + translator + validators | e25cb06 | models.py, event_aggregator.py, sop_builder.py, translator.py, validators.py |
| 2 | DocumentationSynthesizer node + metadata/prompts + __init__ | 743720d | agent.py, metadata.py, prompts.py, __init__.py |

## Test Results

All 14 tests pass: `pytest apps/agents/knowledge/documentation-synthesizer/tests/ -x -q` → **14 passed**

| Test File | Tests | Contract |
|-----------|-------|----------|
| test_translator.py | 5 | IT→EN anchor preservation + MissingAnchorError on drift |
| test_citation_provenance.py | 5 | TRN-05 opaque-output rejection (source_uri + timestamp) |
| test_hitl_preindex.py | 4 | CR-02 ordering: no upsert/audit before interrupt returns |

## Architecture Decisions

### D-DS-02 JSONB window query (Open Q4)
INTERVAL cannot be parameterized in asyncpg. The window start datetime is computed in Python (`datetime.now(UTC) - timedelta(days=window_days)`) and passed as `$1 TIMESTAMPTZ`. The `evidence_panel->>'failure_mode'` and `->>'asset_id'` JSONB operators filter on the existing `audit.actions` table without any schema change (SC-4, D-DS-02).

### CR-02 ordering: interrupt() directly in __call__
`interrupt()` is called directly in `DocumentationSynthesizer.__call__()` (not via a tool). On the first execution, LangGraph raises `GraphInterrupt` at that point, unwinding the stack. `indexer.upsert()` and `_write_audit()` appear strictly after `interrupt()` in the code — they execute only on the resumed invocation.

### CR-03: approval_id=None
The `SOP_DRAFT` audit row uses `approval_id=None` (pending HITL). The UUID is never fabricated for pending rows.

### CR-01: saver guard
`saver=None` raises `RuntimeError` at construction time, not lazily at invocation time.

### Pitfall §1: citation re-anchoring
`SOPTranslator` calls the LLM per-section with an explicit instruction to preserve every `[SRC:N]` marker. After translation, `_verify_anchor_parity()` extracts anchors from IT and EN text and raises `MissingAnchorError` on the first absent anchor.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Implementation Notes

1. **Test scaffold conversion:** The Wave 0 scaffolded tests had `pytest.fail(...)` as stubs. These were replaced with proper test implementations using mock LLMs and the `unittest.mock.patch` pattern (Pattern J from 08-PATTERNS.md).

2. **LLM mock unlimited responses:** The test `_make_agent()` helper uses a side_effect function (rather than a fixed side_effect list) to handle multiple invocations across first-run and resume without `StopAsyncIteration` errors.

3. **SOPDraft sections_en placeholder:** `SOPBuilder.build()` returns a `SOPDraft` where `sections_en` is a copy of `sections_it` (placeholder). The agent calls `_translate_en()` to produce a new immutable `SOPDraft` with the real EN sections. This pattern avoids mutating the frozen model.

## Known Stubs

None — all data flows are wired. The SOPBuilder uses a real LLM call + fallback parser; the HistoricalEventAggregator uses real asyncpg; the SOPTranslator validates anchors; the SOPCitationValidator enforces TRN-05.

## Threat Flags

No new threat surface beyond what the plan's threat model covers:
- T-08-13 (citation spoofing) mitigated by SOPCitationValidator.validate() checking anchor_map + source_uri
- T-08-14 (unapproved indexing) mitigated by indexer.upsert() strictly after interrupt() returns

## Self-Check: PASSED

Files verified:
- `/run/media/federicocalo/D/prj/Smart Factory Transformation/apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/models.py` — FOUND
- `/run/media/federicocalo/D/prj/Smart Factory Transformation/apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/agent.py` — FOUND
- `/run/media/federicocalo/D/prj/Smart Factory Transformation/apps/agents/knowledge/documentation-synthesizer/src/trn_documentation_synthesizer/validators.py` — FOUND

Commits verified:
- e25cb06 — FOUND (feat(08-07): SOPDraft models + event_aggregator...)
- 743720d — FOUND (feat(08-07): DocumentationSynthesizer node...)
