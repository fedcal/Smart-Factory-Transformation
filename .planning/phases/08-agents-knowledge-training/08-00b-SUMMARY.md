---
phase: 08-agents-knowledge-training
plan: 00b
subsystem: agents/knowledge
tags: [wave-0, test-scaffold, nyquist, hitl, knowledge-agents, tdd-red]
dependency_graph:
  requires: []
  provides:
    - apps/agents/knowledge/shift-handover/tests (8 contract tests)
    - apps/agents/knowledge/training-coach/tests (16 contract tests)
    - apps/agents/knowledge/knowledge-curator/tests (17 contract tests)
    - apps/agents/knowledge/documentation-synthesizer/tests (14 contract tests)
  affects:
    - 08-04-PLAN (shift-handover impl — reads test contracts)
    - 08-05-PLAN (training-coach impl — reads test contracts)
    - 08-06-PLAN (knowledge-curator impl — reads test contracts)
    - 08-07-PLAN (documentation-synthesizer impl — reads test contracts)
tech_stack:
  added: []
  patterns:
    - Phase 6/7 Wave 0 test scaffold convention (def test_placeholder bodies, no module-level skip)
    - pytest asyncio_mode=auto + import-mode=importlib per-package pyproject.toml
    - AsyncMock pool/audit_writer conftest pattern (mirrors rca-specialist)
    - BGE_M3_DEVICE=cpu autouse fixture for test isolation
key_files:
  created:
    - apps/agents/knowledge/shift-handover/tests/__init__.py
    - apps/agents/knowledge/shift-handover/tests/conftest.py
    - apps/agents/knowledge/shift-handover/tests/test_aggregator.py
    - apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py
    - apps/agents/knowledge/training-coach/tests/__init__.py
    - apps/agents/knowledge/training-coach/tests/conftest.py
    - apps/agents/knowledge/training-coach/tests/test_quiz_scoring.py
    - apps/agents/knowledge/training-coach/tests/test_difficulty.py
    - apps/agents/knowledge/training-coach/tests/test_hitl_lifecycle.py
    - apps/agents/knowledge/knowledge-curator/tests/__init__.py
    - apps/agents/knowledge/knowledge-curator/tests/conftest.py
    - apps/agents/knowledge/knowledge-curator/tests/test_dedup.py
    - apps/agents/knowledge/knowledge-curator/tests/test_staleness.py
    - apps/agents/knowledge/knowledge-curator/tests/test_reuse_rate.py
    - apps/agents/knowledge/documentation-synthesizer/tests/__init__.py
    - apps/agents/knowledge/documentation-synthesizer/tests/conftest.py
    - apps/agents/knowledge/documentation-synthesizer/tests/test_translator.py
    - apps/agents/knowledge/documentation-synthesizer/tests/test_hitl_preindex.py
    - apps/agents/knowledge/documentation-synthesizer/tests/test_citation_provenance.py
  modified:
    - apps/agents/knowledge/shift-handover/pyproject.toml
    - apps/agents/knowledge/training-coach/pyproject.toml
    - apps/agents/knowledge/knowledge-curator/pyproject.toml
    - apps/agents/knowledge/documentation-synthesizer/pyproject.toml
decisions:
  - "Wave 0 test scaffold uses pytest.fail() bodies naming the unimplemented contract; no module-level pytest.skip (Phase 6/7 decision)"
  - "pytest asyncio_mode=auto + import-mode=importlib added to all 4 knowledge agent pyproject.toml (Rule 2 auto-fix)"
  - "conftest.py clash when running pytest apps/agents/knowledge is a pre-existing monorepo issue identical to Phase 7 — accepted, per-agent execution is the intended nx workflow"
metrics:
  duration: 25min
  completed: "2026-05-24T10:00:54Z"
  tasks: 1
  files: 23
---

# Phase 8 Plan 00b: Knowledge Agent Test Scaffolds Summary

**One-liner:** Phase 8 Wave 0-B Nyquist scaffold — 11 agent test files + 4 conftests + 4 __init__.py covering ShiftHandover dual-supervisor HITL, TrainingCoach quiz scoring and no-double-write TRAINING_SESSION contract (W4/CR-02), KnowledgeCurator SHA-256+BGE-M3 dedup/staleness/reuse-rate, and DocumentationSynthesizer anchor re-anchoring + TRN-05 opaque-output rejection.

## What Was Built

Wave 0-B scaffolds the complete acceptance surface for the four Phase 8 Knowledge cluster agents. Each test file contains explicit `pytest.fail()` contract bodies (not module-level `pytest.skip`) that name the behavioral contract the Wave 2-3 implementation must satisfy. This is the Nyquist rule applied to Phase 8: tests exist before implementation.

### Files created per agent

**shift-handover (8 tests total):**
- `test_aggregator.py` (4 tests): ShiftAggregator builds HandoverReport from audit.actions cross-cluster query; alerts derived from ANOMALY_ALERT action_type (D-SH-02 resolved — no ops.alerts table); datetime objects for asyncpg params (WR-03)
- `test_dual_signoff.py` (4 tests): Two sequential interrupts; first HANDOVER_SIGNOFF row written between interrupts, second after second resume; 0 writes before interrupt (CR-02); approval_id=None (CR-03)

**training-coach (16 tests total):**
- `test_quiz_scoring.py` (5 tests): Score = correct/total by index equality; no LLM in scoring path (Pitfall §3 guard, D-TC-01); pass threshold default 0.80 (D-TC-03)
- `test_difficulty.py` (5 tests): Rises on correct, falls on wrong, capped at easy/hard (D-TC-02); full session trajectory sequence
- `test_hitl_lifecycle.py` (6 tests): Single interrupt for competency sign-off; exactly 1 TRAINING_SIGNOFF row; exactly 1 TRAINING_SESSION row total (write AFTER interrupt — W4/CR-02 no-double-write contract); 0 writes before interrupt; approval_id=None (CR-03); failing session: no interrupt, no TRAINING_SIGNOFF, 1 TRAINING_SESSION

**knowledge-curator (17 tests total):**
- `test_dedup.py` (6 tests): normalized_sha256 hash; ExactDedupChecker; NearDedupChecker above/below threshold; configurable threshold (D-KC-01, Pitfall §6)
- `test_staleness.py` (7 tests): SOP 365d, runbook 180d, note 90d boundaries with injected now; configurable thresholds (D-KC-02)
- `test_reuse_rate.py` (4 tests): distinct_cited / total_indexed from mock asyncpg; zero-indexed guard; evidence_panel JSONB source; rolling window (D-KC-03)

**documentation-synthesizer (14 tests total):**
- `test_translator.py` (5 tests): All [SRC:N] anchors survive in EN; MissingAnchorError on missing anchor; anchor_map completeness; source_uri invariance; fixed section keys (D-DS-01, TRN-04, Pitfall §1)
- `test_hitl_preindex.py` (4 tests): No Qdrant upsert before interrupt; 1 SOP_DRAFT row on resume; Qdrant fires after audit write; approval_id=None (D-DS-03, CR-02/CR-03)
- `test_citation_provenance.py` (5 tests): TRN-05 canonical opaque-output rejection — SOPCitationValidator rejects empty citations, missing source_uri, missing timestamp, partial invalidity

### Total: 55 tests collected cleanly across 4 agents (per-agent invocation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added pytest dev dependencies + asyncio_mode + import-mode to pyproject.toml**
- **Found during:** Task 1 verification
- **Issue:** The 4 knowledge agent pyproject.toml files had no `[dependency-groups]` dev section, no `[tool.pytest.ini_options]` block, and no `asyncio_mode = "auto"`. Without these, `pytest.mark.asyncio` marks produce `PytestUnknownMarkWarning` and async test collection fails in per-agent mode.
- **Fix:** Added `[dependency-groups] dev = [pytest>=8.0, pytest-asyncio>=0.23]` and `[tool.pytest.ini_options] asyncio_mode = "auto" / addopts = "--import-mode=importlib"` to all 4 pyproject.toml files. Mirrors the downtime-analyzer pattern from Phase 7.
- **Files modified:** All 4 `apps/agents/knowledge/*/pyproject.toml`
- **Commit:** 45b1498

### Known Limitation (Pre-existing, Out of Scope)

The monorepo conftest collision (`ImportPathMismatchError: tests.conftest`) when running `pytest apps/agents/knowledge` in a single invocation is a **pre-existing architectural issue identical to Phase 7** (`pytest apps/agents/maintenance` produces the same error). This is NOT a new issue introduced by this plan. The intended execution model is per-package via nx (`nx run trn-shift-handover:test`) or per-agent pytest invocation. All 55 tests collect cleanly with per-agent invocation. This is documented as a deferred item to the monorepo configuration work (Phase 1 follow-up, out of Phase 8 scope).

## Known Stubs

None — this plan creates test scaffolds only. All test functions call `pytest.fail()` with explicit contract-naming messages. No implementation stubs or placeholder data.

## Threat Flags

None — this plan creates test files only. No new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| All 19 test files exist | PASSED |
| Commit 45b1498 exists | PASSED |
| SUMMARY.md exists | PASSED |
| No pytest.skip at module level | PASSED |
| test_hitl_lifecycle.py contains TRAINING_SESSION | PASSED |
| test_dual_signoff.py contains HANDOVER_SIGNOFF | PASSED |
| test_citation_provenance.py contains source_uri | PASSED |
| 55 tests collect cleanly per-agent | PASSED |
