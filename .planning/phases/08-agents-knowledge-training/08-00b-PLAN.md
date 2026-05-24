---
phase: 08-agents-knowledge-training
plan: 00b
type: execute
wave: 1
depends_on: []
files_modified:
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
autonomous: true
requirements: [TRN-02, TRN-03, TRN-04, TRN-05]
must_haves:
  truths:
    - "Every Phase 8 agent test file exists with bodies that name the contract under test (no module-level skip)"
    - "Each test file plus 4 conftests and 4 tests/__init__.py exist and collect without import errors in the test files themselves"
    - "The TrainingCoach HITL lifecycle scaffold asserts exactly 1 TRAINING_SIGNOFF row AND exactly 1 TRAINING_SESSION row total for a passing session (no double-write, W4/CR-02)"
  artifacts:
    - path: "apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py"
      provides: "Dual-supervisor sequential interrupt audit-ordering contract"
      contains: "HANDOVER_SIGNOFF"
    - path: "apps/agents/knowledge/training-coach/tests/test_hitl_lifecycle.py"
      provides: "Single-interrupt sign-off + single TRAINING_SESSION contract"
      contains: "TRAINING_SESSION"
    - path: "apps/agents/knowledge/documentation-synthesizer/tests/test_citation_provenance.py"
      provides: "TRN-05 opaque-output rejection contract"
      contains: "source_uri"
  key_links:
    - from: "apps/agents/knowledge/*/tests/test_*.py"
      to: "apps/agents/knowledge/*/src/trn_*/ (Wave 2-3 modules)"
      via: "import path named in each placeholder body"
      pattern: "trn_"
---

<objective>
Wave 1 foundation B for Phase 8: scaffold every Phase 8 agent test file so downstream waves implement against a known contract (Nyquist rule — tests exist before implementation).

Purpose: Defines the acceptance surface for the agent waves (08-02/04/05/06/07). Each test file names the behavioral contract it will enforce.
Output: 4× tests/__init__.py, 4× tests/conftest.py, and 11 agent test files with contract-naming bodies.

Split note: 08-00 was split into 08-00a (migration + enum + migration test) and 08-00b (agent test scaffolds, this plan) to keep each plan's files_modified under the 15-file threshold. Both are independent Wave 1 plans with disjoint files — 08-00b touches only `apps/agents/knowledge/*/tests/`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/08-agents-knowledge-training/08-CONTEXT.md
@.planning/phases/08-agents-knowledge-training/08-RESEARCH.md
@.planning/phases/08-agents-knowledge-training/08-PATTERNS.md
@.planning/phases/08-agents-knowledge-training/08-VALIDATION.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Agent test scaffolds (Nyquist — tests before impl)</name>
  <files>apps/agents/knowledge/shift-handover/tests, apps/agents/knowledge/training-coach/tests, apps/agents/knowledge/knowledge-curator/tests, apps/agents/knowledge/documentation-synthesizer/tests</files>
  <read_first>
    - apps/agents/maintenance/rca-specialist/tests/conftest.py and test_interrupt_audit_lifecycle.py (HITL test analog)
    - apps/agents/maintenance/downtime-analyzer/tests/test_oee.py and test_repository.py (pure-function + asyncpg test analogs)
    - 08-RESEARCH.md section "Validation Architecture" Phase Requirements to Test Map (exact file list + behaviors) and 08-VALIDATION.md Per-Task Verification Map
    - 08-PATTERNS.md Pattern J (mock interrupt + count audit writes), section test_dual_signoff.py (lines 636-666)
  </read_first>
  <action>
    For each of the 4 agents create tests/__init__.py and tests/conftest.py (mirror rca-specialist conftest: AsyncMock pool and audit_writer fixtures, BGE_M3_DEVICE=cpu env). Then create the test files from the RESEARCH Test Map. Use explicit test functions that assert the named contract, or a def test_placeholder body that fails with a clear message naming the unimplemented contract (NOT module-level pytest.skip — per the STATE Phase 6 Wave 0 decision). Files and their named contracts:
    - shift-handover/tests/test_aggregator.py (ShiftAggregator builds structured report from mock asyncpg audit + downtime rows; alerts derived from action_type='ANOMALY_ALERT', NO ops.alerts/ops.work_orders tables).
    - shift-handover/tests/test_dual_signoff.py (two sequential interrupts; exactly 2 HANDOVER_SIGNOFF rows; first row written BETWEEN the interrupts, second after the second resume).
    - training-coach/tests/test_quiz_scoring.py (deterministic score = correct/total by index, no LLM, D-TC-01).
    - training-coach/tests/test_difficulty.py (next_difficulty rises/falls and is capped, D-TC-02).
    - training-coach/tests/test_hitl_lifecycle.py (single interrupt on pass; exactly 1 TRAINING_SIGNOFF row on resume; AND exactly 1 TRAINING_SESSION row TOTAL for a passing session — the TRAINING_SESSION write occurs after interrupt() returns so it is NOT replayed/double-written on resume, W4/CR-02; on fail: no interrupt, no TRAINING_SIGNOFF, still exactly 1 TRAINING_SESSION).
    - knowledge-curator/tests/test_dedup.py with test_exact_dup and test_near_dup_threshold (D-KC-01).
    - knowledge-curator/tests/test_staleness.py (is_stale boundary per doc_type with injected now, D-KC-02).
    - knowledge-curator/tests/test_reuse_rate.py (distinct cited / total indexed from mock asyncpg, D-KC-03).
    - documentation-synthesizer/tests/test_translator.py (every SRC anchor in IT survives in EN, missing raises MissingAnchorError, TRN-04).
    - documentation-synthesizer/tests/test_hitl_preindex.py (no Qdrant upsert before interrupt returns; exactly 1 SOP_DRAFT row on resume).
    - documentation-synthesizer/tests/test_citation_provenance.py (SOPCitationValidator rejects any output lacking source_uri+timestamp, TRN-05 — canonical opaque-output rejection test).
    Each placeholder references the agent module path it will import once Waves 2-3 land.
  </action>
  <verify>
    <automated>cd "/run/media/federicocalo/D/prj/Smart Factory Transformation" && python -m pytest apps/agents/knowledge -q --co 2>&1 | tail -2; python -c "from pathlib import Path; base=Path('apps/agents/knowledge'); files=['shift-handover/tests/test_aggregator.py','shift-handover/tests/test_dual_signoff.py','training-coach/tests/test_quiz_scoring.py','training-coach/tests/test_difficulty.py','training-coach/tests/test_hitl_lifecycle.py','knowledge-curator/tests/test_dedup.py','knowledge-curator/tests/test_staleness.py','knowledge-curator/tests/test_reuse_rate.py','documentation-synthesizer/tests/test_translator.py','documentation-synthesizer/tests/test_hitl_preindex.py','documentation-synthesizer/tests/test_citation_provenance.py']; missing=[f for f in files if not (base/f).exists()]; assert not missing, missing; print('all 11 test files present')"</automated>
  </verify>
  <acceptance_criteria>
    - All 11 named test files plus 4 conftest.py and 4 tests/__init__.py exist.
    - No file uses a module-level pytest.skip (grep -L confirms placeholder-body convention).
    - test_hitl_lifecycle.py names both the single-TRAINING_SIGNOFF and the exactly-1-TRAINING_SESSION-total contracts (grep finds TRAINING_SESSION).
    - `pytest apps/agents/knowledge --co` collects without import errors in the test files themselves.
  </acceptance_criteria>
  <done>Every Phase 8 agent behavior from the RESEARCH Test Map has a corresponding test file with a contract-naming body.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test scaffold to agent impl | placeholder contracts gate Wave 2-3 implementation; no runtime trust boundary crossed |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-08-03 | Tampering | test scaffold completeness | mitigate | Verify step asserts all 11 files present; no module-level skip masks an unimplemented contract |
| T-08-SC | Tampering | npm/pip/cargo installs | accept | No package installs in Phase 8 (RESEARCH Package Legitimacy Audit: none new) |
</threat_model>

<verification>
- `python -m pytest apps/agents/knowledge --co` collects without test-file import errors.
- All 11 test files + 4 conftests + 4 tests/__init__.py present.
- test_hitl_lifecycle.py asserts exactly 1 TRAINING_SESSION row total for a passing session.
</verification>

<success_criteria>
All 11 agent test files + conftests scaffolded with contract-naming bodies; downstream waves have a fixed acceptance surface including the no-double-write TRAINING_SESSION contract.
</success_criteria>

<output>
Create `.planning/phases/08-agents-knowledge-training/08-00b-SUMMARY.md` when done.
</output>
