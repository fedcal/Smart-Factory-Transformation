---
phase: 08-agents-knowledge-training
plan: 00a
type: execute
wave: 1
depends_on: []
files_modified:
  - infra/migrations/timescale/010_extend_audit_knw.sql
  - infra/migrations/timescale/tests/test_migration_010.py
  - packages/sft-agents/src/sft_agents/models/enums.py
autonomous: true
requirements: [TRN-02, TRN-03, TRN-04, TRN-05]
must_haves:
  truths:
    - "Migration 010 admits all 7 Phase 8 ActionType values and still admits legacy values (regression guard)"
    - "ActionType enum and migration 010 CHECK constraint are in lockstep (7 new values, identical strings)"
    - "Migration 010 is idempotent (double-apply is a no-op) and the Decision CHECK is untouched"
  artifacts:
    - path: "infra/migrations/timescale/010_extend_audit_knw.sql"
      provides: "audit.actions action_type CHECK extended with 7 Phase 8 values"
      contains: "HANDOVER_SIGNOFF"
    - path: "packages/sft-agents/src/sft_agents/models/enums.py"
      provides: "7 Phase 8 ActionType enum members"
      contains: "SOP_DRAFT"
    - path: "infra/migrations/timescale/tests/test_migration_010.py"
      provides: "Migration 010 admit/reject/idempotency/regression tests"
      contains: "_PHASE8_ACTION_TYPES"
  key_links:
    - from: "packages/sft-agents/src/sft_agents/models/enums.py"
      to: "infra/migrations/timescale/010_extend_audit_knw.sql"
      via: "identical action_type string literals (lockstep)"
      pattern: "HANDOVER_DRAFT|SOP_DRAFT|STALE_FLAG"
---

<objective>
Wave 1 foundation A for Phase 8: extend the audit ActionType enum + TimescaleDB CHECK constraint in lockstep (D-X-01), with its migration integration test. This is the shared audit vocabulary all four knowledge agents write.

Purpose: Establishes the audit action_type set the agent waves depend on; agent plans (08-02/05/06/07) reference these enum members.
Output: Migration 010, 7 new enum members, and the migration 010 integration test.

Split note: 08-00 was split into 08-00a (migration + enum + migration test, this plan) and 08-00b (agent test scaffolds) to keep each plan's files_modified under the 15-file threshold. Both are independent Wave 1 plans with disjoint files.
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
</context>

<tasks>

<task type="auto">
  <name>Task 1: Migration 010 + ActionType enum lockstep (D-X-01)</name>
  <files>infra/migrations/timescale/010_extend_audit_knw.sql, packages/sft-agents/src/sft_agents/models/enums.py</files>
  <read_first>
    - infra/migrations/timescale/009_extend_audit_mnt.sql (exact DROP+ADD CHECK analog)
    - packages/sft-agents/src/sft_agents/models/enums.py (existing ActionType tail, Phase 7 block lines ~115-120)
    - 08-PATTERNS.md section "010_extend_audit_knw.sql" and section "enums.py" (verbatim patterns, lines 57-171)
    - 08-CONTEXT.md D-X-01 (granular 7-value set)
  </read_first>
  <action>
    Create infra/migrations/timescale/010_extend_audit_knw.sql mirroring 009_extend_audit_mnt.sql verbatim: drop the audit_actions_action_type_chk constraint IF EXISTS, then add it back with action_type IN listing ALL prior-phase values (Phases 1-5 baseline, Phase 6, Phase 7) UNCHANGED plus the 7 Phase 8 values HANDOVER_DRAFT, HANDOVER_SIGNOFF, TRAINING_SESSION, TRAINING_SIGNOFF, KNOWLEDGE_DEDUP, STALE_FLAG, SOP_DRAFT. Header comment references Phase 8 / Plan 08-00a / D-X-01 and states idempotent re-run safety. Do NOT touch the Decision CHECK constraint. Then append 7 matching members to the ActionType enum under a section header comment "Phase 8 additions — keep in lockstep with migration 010 (D-X-01)", each with inline D-XX description comment per PATTERNS lines 160-168. Enum string values MUST be byte-identical to the SQL literals.
  </action>
  <verify>
    <automated>cd "/run/media/federicocalo/D/prj/Smart Factory Transformation" && python -c "from pathlib import Path; sql=Path('infra/migrations/timescale/010_extend_audit_knw.sql').read_text(); enum=Path('packages/sft-agents/src/sft_agents/models/enums.py').read_text(); vals=['HANDOVER_DRAFT','HANDOVER_SIGNOFF','TRAINING_SESSION','TRAINING_SIGNOFF','KNOWLEDGE_DEDUP','STALE_FLAG','SOP_DRAFT']; assert all(v in sql for v in vals); assert all(v in enum for v in vals); assert 'DROP CONSTRAINT IF EXISTS' in sql; assert 'OEE_REPORT' in sql and 'ANOMALY_ALERT' in sql; print('lockstep OK')"</automated>
  </verify>
  <acceptance_criteria>
    - 010_extend_audit_knw.sql contains the 7 new literals AND every legacy literal (WRITE_PLC_SETPOINT, ANOMALY_ALERT, OEE_REPORT present).
    - ActionType enum contains 7 new members with values equal to their names.
    - Command `python -c "from sft_agents.models.enums import ActionType; assert ActionType.SOP_DRAFT.value=='SOP_DRAFT'"` succeeds.
  </acceptance_criteria>
  <done>Migration 010 and ActionType enum carry an identical 7-value Phase 8 set; no legacy value removed.</done>
</task>

<task type="auto">
  <name>Task 2: Migration 010 integration test</name>
  <files>infra/migrations/timescale/tests/test_migration_010.py</files>
  <read_first>
    - infra/migrations/timescale/tests/test_migration_009.py (exact analog — fixtures, helpers, 6+1 test structure)
    - 08-PATTERNS.md section "test_migration_010.py" (lines 99-141 — test matrix, fixture, helper, what-to-change list)
  </read_first>
  <action>
    Copy test_migration_009.py to test_migration_010.py. Replace 009 with 010 in all strings, rename the new-values tuple to _PHASE8_ACTION_TYPES (the 7 new values), rename _MIGRATION_009 to _MIGRATION_010, and extend _LEGACY_ACTION_TYPES to include all Phase 7 values (RUL_ESTIMATE, RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT, OEE_REPORT) for regression. Update the baseline-migration glob sentinel so the baseline runner applies files whose name sorts before 010, then apply 010_extend_audit_knw.sql. Implement the 7-test structure from PATTERNS lines 131-139: pre-migration rejects HANDOVER_DRAFT, post-migration admits HANDOVER_DRAFT, parametrized admit-all-Phase8, parametrized legacy-still-ok, decision-enum-unchanged, idempotent-double-apply, migrate-runner-picks-up-010. Mark integration tests with the integration marker and use testcontainers PostgresContainer image timescale/timescaledb:2.18.0-pg16.
  </action>
  <verify>
    <automated>cd "/run/media/federicocalo/D/prj/Smart Factory Transformation" && python -m pytest infra/migrations/timescale/tests/test_migration_010.py --co -q 2>&1 | grep -c "::test_" | python -c "import sys; n=int(sys.stdin.read() or 0); assert n>=7, f'only {n} tests'; print(f'{n} tests collected')"</automated>
  </verify>
  <acceptance_criteria>
    - At least 7 test functions collected.
    - _PHASE8_ACTION_TYPES has exactly the 7 Phase 8 values; _LEGACY_ACTION_TYPES includes Phase 6 and Phase 7 values.
    - With Docker: `pytest infra/migrations/timescale/tests/test_migration_010.py -m integration -x` is green.
  </acceptance_criteria>
  <done>Migration 010 test collects and (with Docker) passes admit/reject/idempotency/regression cases.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| migration runner to DB | DDL applied to audit.actions; must not weaken existing constraints |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-08-01 | Tampering | migration 010 CHECK constraint | mitigate | Regression test asserts all legacy action_types still admitted; Decision CHECK untouched |
| T-08-02 | Tampering | enum/SQL lockstep drift | mitigate | Verify step asserts byte-identical 7-value set in both files |
| T-08-SC | Tampering | npm/pip/cargo installs | accept | No package installs in Phase 8 (RESEARCH Package Legitimacy Audit: none new) |
</threat_model>

<verification>
- `python -m pytest infra/migrations/timescale/tests/test_migration_010.py --co -q` collects >=7 tests.
- Enum import succeeds for all 7 new members.
- Lockstep verify command (Task 1) passes.
</verification>

<success_criteria>
Migration 010 + enum lockstep landed with its integration test; downstream agent waves can reference the 7 new ActionType members.
</success_criteria>

<output>
Create `.planning/phases/08-agents-knowledge-training/08-00a-SUMMARY.md` when done.
</output>
