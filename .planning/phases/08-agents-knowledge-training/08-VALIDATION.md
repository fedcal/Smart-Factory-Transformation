---
phase: 8
slug: agents-knowledge-training
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-24
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Formalized from `08-RESEARCH.md` § Validation Architecture. All Wave 0 test scaffolds are created by plan **08-00b**; migration test by **08-00a**.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio + testcontainers (Phase 1+ locked) |
| **Config file** | Per-package `pyproject.toml` (`apps/agents/knowledge/*/pyproject.toml`, `packages/*/pyproject.toml`) |
| **Quick run command** | `pytest apps/agents/knowledge/<agent>/tests/ -x` |
| **Full suite command** | `nx run-many --target=test --projects=sft-agents,trn-shift-handover,trn-training-coach,trn-knowledge-curator,trn-documentation-synthesizer` |
| **Estimated runtime** | ~30-50 seconds (quick, per-agent), ~3-5 min (full with testcontainers) |

---

## Sampling Rate

- **After every task commit:** `pytest apps/agents/knowledge/<agent>/tests/ -x -q` (agent under development, <30s typical)
- **After every plan wave:** `nx run-many --target=test --projects=sft-agents,trn-*` (full coverage report)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30s (per-task quick), 300s (per-wave full)

---

## Per-Task Verification Map (Phase Requirements → Test Map)

| Req ID | Behavior | Plan | Test Type | Automated Command | File Exists | Status |
|--------|----------|------|-----------|-------------------|-------------|--------|
| D-X-01 | Migration 010: new ActionType values INSERT successfully; existing values still work; idempotent | 08-00a | integration | `pytest infra/migrations/timescale/tests/test_migration_010.py -m integration -x` | ❌ W0 (08-00a) | ⬜ pending |
| TRN-03 | ShiftHandover cross-cluster audit aggregation (mock asyncpg → structured report); no ops.alerts/ops.work_orders tables (D-SH-02) | 08-02 | unit | `pytest apps/agents/knowledge/shift-handover/tests/test_aggregator.py -x` | ❌ W0 (08-00b) | ⬜ pending |
| TRN-03 | ShiftHandover dual-supervisor sequential interrupt — first HANDOVER_SIGNOFF row written BETWEEN interrupts, second after second resume; exactly 2 rows | 08-04 | unit | `pytest apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py -x` | ❌ W0 (08-00b) | ⬜ pending |
| TRN-02 | TrainingCoach deterministic quiz scoring (pass/fail without LLM-judge, index equality) | 08-05 | unit | `pytest apps/agents/knowledge/training-coach/tests/test_quiz_scoring.py -x` | ❌ W0 (08-00b) | ⬜ pending |
| TRN-02 | TrainingCoach dynamic difficulty adaption (rises on correct, falls on incorrect, capped) | 08-05 | unit | `pytest apps/agents/knowledge/training-coach/tests/test_difficulty.py -x` | ❌ W0 (08-00b) | ⬜ pending |
| TRN-02 | TrainingCoach competency sign-off HITL — exactly 1 TRAINING_SIGNOFF row on resume; exactly 1 TRAINING_SESSION row total for a passing session (no double-write) | 08-05 | unit | `pytest apps/agents/knowledge/training-coach/tests/test_hitl_lifecycle.py -x` | ❌ W0 (08-00b) | ⬜ pending |
| D-KC-01 | KnowledgeCurator exact-dup SHA-256 detection | 08-06 | unit | `pytest apps/agents/knowledge/knowledge-curator/tests/test_dedup.py::test_exact_dup -x` | ❌ W0 (08-00b) | ⬜ pending |
| D-KC-01 | KnowledgeCurator near-dup BGE-M3 cosine threshold boundary | 08-06 | unit | `pytest apps/agents/knowledge/knowledge-curator/tests/test_dedup.py::test_near_dup_threshold -x` | ❌ W0 (08-00b) | ⬜ pending |
| D-KC-02 | KnowledgeCurator staleness boundary per doc_type with injected `now` | 08-06 | unit | `pytest apps/agents/knowledge/knowledge-curator/tests/test_staleness.py -x` | ❌ W0 (08-00b) | ⬜ pending |
| D-KC-03 | KnowledgeCurator reuse-rate KPI: distinct cited / total indexed from mock asyncpg | 08-06 | unit | `pytest apps/agents/knowledge/knowledge-curator/tests/test_reuse_rate.py -x` | ❌ W0 (08-00b) | ⬜ pending |
| TRN-04 | DocumentationSynthesizer citation re-anchoring: all IT [SRC:N] anchors present in EN output (MissingAnchorError on drift) | 08-07 | unit | `pytest apps/agents/knowledge/documentation-synthesizer/tests/test_translator.py -x` | ❌ W0 (08-00b) | ⬜ pending |
| TRN-04 | DocumentationSynthesizer HITL: no Qdrant indexing before interrupt returns; exactly 1 SOP_DRAFT row on resume | 08-07 | unit | `pytest apps/agents/knowledge/documentation-synthesizer/tests/test_hitl_preindex.py -x` | ❌ W0 (08-00b) | ⬜ pending |
| TRN-05 | All agent outputs include source_uri + timestamp in citations (citation/provenance validator rejects opaque output) | 08-07 | unit | `pytest apps/agents/knowledge/documentation-synthesizer/tests/test_citation_provenance.py -x` | ❌ W0 (08-00b) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 (test scaffold, mirror Phase 6/7 pattern) DEVE creare:

**Migration test (created by 08-00a):**
- [ ] `infra/migrations/timescale/tests/test_migration_010.py`

**Agent test scaffolds (created by 08-00b — `tests/__init__.py` + `tests/conftest.py` per agent):**
- [ ] `apps/agents/knowledge/shift-handover/tests/test_aggregator.py`
- [ ] `apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py`
- [ ] `apps/agents/knowledge/training-coach/tests/test_quiz_scoring.py`
- [ ] `apps/agents/knowledge/training-coach/tests/test_difficulty.py`
- [ ] `apps/agents/knowledge/training-coach/tests/test_hitl_lifecycle.py`
- [ ] `apps/agents/knowledge/knowledge-curator/tests/test_dedup.py`
- [ ] `apps/agents/knowledge/knowledge-curator/tests/test_staleness.py`
- [ ] `apps/agents/knowledge/knowledge-curator/tests/test_reuse_rate.py`
- [ ] `apps/agents/knowledge/documentation-synthesizer/tests/test_translator.py`
- [ ] `apps/agents/knowledge/documentation-synthesizer/tests/test_hitl_preindex.py`
- [ ] `apps/agents/knowledge/documentation-synthesizer/tests/test_citation_provenance.py`
- [ ] All 4 `apps/agents/knowledge/*/src/trn_*/` module files implemented in Waves 2-3 (currently only `__init__.py` present)

**Scaffold convention:** No module-level `pytest.skip`. Each test file uses explicit test functions that assert the named contract, or a `def test_placeholder` body that fails with a clear message naming the unimplemented contract (per the STATE Phase 6 Wave 0 decision).

**Mock LLM strategy per Phase 8:**
- **KnowledgeCurator**: NO LLM mock needed — SHA-256 dedup is deterministic; near-dup uses mock Qdrant `query_points` returning score_threshold-filtered points. Staleness/reuse-rate are pure/SQL.
- **TrainingCoach**: LLM used only for quiz *generation* (mockable); scoring path is index-equality (NO LLM, asserted deterministic). HITL lifecycle uses `patch(...agent.interrupt, _simulated_interrupt)` + AsyncMock audit_writer (Pattern J).
- **ShiftHandover**: NO LLM mock needed for the dual-signoff lifecycle test (narrative summary stubbed); aggregator test uses mock asyncpg rows → deterministic report. Dual-interrupt asserted via Pattern J (`GraphInterrupt` on first run of each interrupt, audit-write call-count assertions).
- **DocumentationSynthesizer**: translator/citation tests are deterministic (regex anchor presence). HITL pre-index uses Pattern J; assert no Qdrant `upsert` before `interrupt()` returns.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration 010 push to dev TimescaleDB | D-X-01 | Live PG required; testcontainers covers schema not the running cluster | `make migrate-timescale` then verify `audit_actions_action_type_chk` includes the 7 new Phase 8 values |
| Real-LLM smoke for TrainingCoach quiz generation + DocumentationSynthesizer IT→EN (Qwen2.5 via Ollama) | TRN-02, TRN-04 | Semantic quality of generated questions / translation requires human judgment | `pytest tests/e2e/knowledge/ -m real-llm` then review generated MCQ correctness + EN citation fidelity |
| Dual-supervisor HITL approval queue surfacing | TRN-03 | UI consumer ships in Phase 10 | Inspect `audit.actions WHERE decision='hitl_supervisor' AND action_type='HANDOVER_SIGNOFF'` (expect 2 rows per handover) |
| KnowledgeCurator near-dup threshold tuning on real corpus | D-KC-01 | Threshold calibration needs real near-duplicate SOP pairs | Run dedup over the synthetic corpus; review flagged near-dups against the 0.92 boundary (Pitfall §6) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies declared
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (1 migration test + 11 agent test files + 4 conftests + 4 `__init__.py`)
- [ ] No watch-mode flags in CI commands
- [ ] Feedback latency < 30s (per-task) / < 300s (per-wave)
- [ ] `nyquist_compliant: true` set in frontmatter (toggled by plan-checker after coverage verification)

**Approval:** pending
