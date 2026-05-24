---
phase: 09-agents-supply-chain-economics
plan: 00a
type: execute
wave: 1
depends_on: []
files_modified:
  - infra/migrations/timescale/011_create_scm_schema.sql
  - infra/migrations/timescale/012_extend_audit_scm.sql
  - infra/migrations/timescale/tests/test_migration_011.py
  - infra/migrations/timescale/tests/test_migration_012.py
  - packages/sft-agents/src/sft_agents/models/enums.py
autonomous: true
requirements: [SCM-01, SCM-02, SCM-04, SCM-05]
must_haves:
  truths:
    - "Migration 011 creates the scm.* schema (sku_master, inventory_levels + energy_readings hypertables, historical_orders, enpi_baseline), idempotent on double-apply"
    - "Migration 012 admits all 8 Phase 9 ActionType values and still admits every legacy value (Phases 1-8 regression guard); the Decision CHECK is untouched"
    - "ActionType enum and migration 012 CHECK constraint are in lockstep (8 new values, byte-identical strings)"
  artifacts:
    - path: "infra/migrations/timescale/011_create_scm_schema.sql"
      provides: "scm.* DDL with two hypertables + master/reference tables"
      contains: "CREATE SCHEMA IF NOT EXISTS scm"
    - path: "infra/migrations/timescale/012_extend_audit_scm.sql"
      provides: "audit.actions action_type CHECK extended with 8 Phase 9 values"
      contains: "PURCHASE_RECOMMENDATION_DRAFT"
    - path: "packages/sft-agents/src/sft_agents/models/enums.py"
      provides: "8 Phase 9 ActionType enum members"
      contains: "REORDER_ALERT"
    - path: "infra/migrations/timescale/tests/test_migration_011.py"
      provides: "scm schema creation + idempotency + hypertable smoke tests"
      contains: "scm.energy_readings"
    - path: "infra/migrations/timescale/tests/test_migration_012.py"
      provides: "Migration 012 admit/reject/idempotency/regression tests"
      contains: "_PHASE9_ACTION_TYPES"
  key_links:
    - from: "packages/sft-agents/src/sft_agents/models/enums.py"
      to: "infra/migrations/timescale/012_extend_audit_scm.sql"
      via: "identical action_type string literals (lockstep)"
      pattern: "REORDER_ALERT|ENERGY_PROPOSAL|DEMAND_PLAN_DRAFT"
---

<objective>
Wave 1 foundation A for Phase 9: create the synthetic `scm.*` TimescaleDB schema (migration 011) AND extend the audit ActionType enum + CHECK constraint in lockstep (migration 012), each with its migration integration test. This is the shared data + audit vocabulary all four supply agents depend on.

Purpose: Establishes the queryable time-series source (scm.*) for reorder logic / EnPI baselines / demand history, and the audit action_type set the agent waves write. Agent plans (09-02..09-06) reference these tables and enum members.

Split note: 09-00 is split into 09-00a (this plan — schema migration + audit-enum lockstep migration + their tests) and 09-00b (Nyquist agent test-contract scaffolds) to keep each plan's files_modified under the 15-file threshold. Both are independent Wave 1 plans with disjoint files.

Execution note: worktrees are DISABLED this session — executors run SEQUENTIALLY on the main tree. Wave/dependency numbers still drive ordering; same-wave plans (00a, 00b) have disjoint files_modified.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/09-agents-supply-chain-economics/09-CONTEXT.md
@.planning/phases/09-agents-supply-chain-economics/09-RESEARCH.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Migration 011 — scm.* schema DDL + hypertables</name>
  <files>infra/migrations/timescale/011_create_scm_schema.sql, infra/migrations/timescale/tests/test_migration_011.py</files>
  <read_first>
    - infra/migrations/timescale/001_create_sensor_events.sql (CREATE TABLE + create_hypertable idempotent pattern)
    - infra/migrations/timescale/008_create_downtime_events.sql (relational-table-with-timestamp analog)
    - infra/migrations/timescale/tests/test_migration_010.py (test fixture/helpers/baseline-glob structure to copy)
    - 09-RESEARCH.md Pattern 5 (verbatim scm.* DDL: sku_master, inventory_levels, energy_readings, historical_orders, enpi_baseline)
  </read_first>
  <action>
    Create infra/migrations/timescale/011_create_scm_schema.sql, idempotent (mirror the IF NOT EXISTS style of 001/008). Header comment references Phase 9 / Plan 09-00a / D-DATA (new synthetic scm.* schema). Emit, verbatim from 09-RESEARCH.md Pattern 5: `CREATE SCHEMA IF NOT EXISTS scm;` then `scm.sku_master` (sku_id PK, sku_name, category CHECK IN ('raw_yarn','accessory','spare_part','fabric'), unit, reorder_point NUMERIC, reorder_qty NUMERIC, lead_time_days INT DEFAULT 7, unit_cost_eur NUMERIC, sku_group DEFAULT 'default'); `scm.inventory_levels` (ts TIMESTAMPTZ, sku_id FK, quantity, location DEFAULT 'main_warehouse', source DEFAULT 'manual') then `SELECT create_hypertable('scm.inventory_levels','ts', if_not_exists => TRUE);`; `scm.energy_readings` (ts TIMESTAMPTZ, asset_id, process CHECK IN ('dyeing','finishing','spinning','weaving','other'), kwh, kg_processed nullable, shift DEFAULT 'day', is_peak_hour BOOLEAN DEFAULT FALSE) then create_hypertable on ts; `scm.historical_orders` (order_id PK, sku_id FK, sku_group, order_date TIMESTAMPTZ, delivery_date nullable, quantity_kg, unit_price_eur, customer_type DEFAULT 'b2b', season nullable); `scm.enpi_baseline` (process PK, kwh_per_kg_target, kwh_per_kg_actual_ytd nullable, baseline_year DEFAULT 2024, notes). Do NOT seed data here (seed is a separate non-numbered file in 09-01). Then create test_migration_011.py by copying the test_migration_010.py fixture/baseline-glob structure: apply all baseline files whose name sorts before 011, then apply 011; assert (a) schema scm exists, (b) all 5 tables exist (information_schema or to_regclass), (c) inventory_levels and energy_readings are hypertables (query timescaledb_information.hypertables / _timescaledb_catalog), (d) the category and process CHECK constraints reject an invalid value, (e) double-applying 011 is a no-op (idempotent). Mark integration tests with the integration marker; use testcontainers PostgresContainer image timescale/timescaledb:2.18.0-pg16.
  </action>
  <verify>
    <automated>cd "/run/media/federicocalo/D/prj/Smart Factory Transformation" && python -c "from pathlib import Path; sql=Path('infra/migrations/timescale/011_create_scm_schema.sql').read_text(); req=['CREATE SCHEMA IF NOT EXISTS scm','scm.sku_master','scm.inventory_levels','scm.energy_readings','scm.historical_orders','scm.enpi_baseline','create_hypertable']; missing=[r for r in req if r not in sql]; assert not missing, missing; assert sql.count('create_hypertable')>=2, 'need 2 hypertables'; print('scm DDL OK')" && python -m pytest infra/migrations/timescale/tests/test_migration_011.py --co -q 2>&1 | grep -c "::test_" | python -c "import sys; n=int(sys.stdin.read() or 0); assert n>=5, f'only {n} tests'; print(f'{n} tests collected')"</automated>
  </verify>
  <acceptance_criteria>
    - 011 contains all 5 scm tables + the schema create + at least 2 create_hypertable calls.
    - test_migration_011.py collects >= 5 tests; with Docker `pytest ...test_migration_011.py -m integration -x` is green.
    - Re-applying 011 twice is a no-op (idempotency test green).
  </acceptance_criteria>
  <done>scm.* schema migration lands idempotently with two hypertables and its integration test.</done>
</task>

<task type="auto">
  <name>Task 2: Migration 012 + ActionType enum lockstep + migration test</name>
  <files>infra/migrations/timescale/012_extend_audit_scm.sql, packages/sft-agents/src/sft_agents/models/enums.py, infra/migrations/timescale/tests/test_migration_012.py</files>
  <read_first>
    - infra/migrations/timescale/010_extend_audit_knw.sql (exact DROP+ADD CHECK analog with full legacy value list)
    - packages/sft-agents/src/sft_agents/models/enums.py (ActionType tail — Phase 8 block ends at SOP_DRAFT line ~138; append after it)
    - infra/migrations/timescale/tests/test_migration_010.py (test matrix, _LEGACY_ACTION_TYPES, baseline-glob sentinel)
    - 09-CONTEXT.md "Carried forward" (the 7 proposed action types) and Decisions block
  </read_first>
  <action>
    Create infra/migrations/timescale/012_extend_audit_scm.sql mirroring 010_extend_audit_knw.sql verbatim: DROP CONSTRAINT IF EXISTS the audit_actions_action_type_chk, then ADD it back with action_type IN listing EVERY prior value (Phase 1-5 baseline + Phase 6 + Phase 7 + the 7 Phase 8 values HANDOVER_DRAFT..SOP_DRAFT) UNCHANGED, PLUS the 8 Phase 9 values: REORDER_ALERT, PURCHASE_RECOMMENDATION_DRAFT, PURCHASE_SIGNOFF, ENERGY_PROPOSAL, ENERGY_SIGNOFF, DEMAND_PLAN_DRAFT, DEMAND_PLAN_SIGNOFF, COST_REPORT. Header comment references Phase 9 / Plan 09-00a / lockstep + idempotent re-run safety. Do NOT touch the Decision CHECK. Then append those same 8 members to the ActionType enum under a section header comment "Phase 9 additions — keep in lockstep with migration 012", each with an inline description comment (REORDER_ALERT = SCM-01 reorder alert; PURCHASE_RECOMMENDATION_DRAFT = SCM-01 procurement draft; PURCHASE_SIGNOFF = SCM-01 supervisor sign-off; ENERGY_PROPOSAL = SCM-02 off-peak proposal draft; ENERGY_SIGNOFF = SCM-02 supervisor sign-off; DEMAND_PLAN_DRAFT = SCM-04 demand plan draft; DEMAND_PLAN_SIGNOFF = SCM-04 ProductionPlanner publish sign-off; COST_REPORT = SCM-03 CostAnalyzer autonomous ROI/OEPV report row, Decision.AUTO). Enum string values MUST equal their member names byte-for-byte (matching the SQL literals). Then create test_migration_012.py by copying test_migration_010.py: rename _MIGRATION_010 → _MIGRATION_012 / file → 012_extend_audit_scm.sql, define _PHASE9_ACTION_TYPES = the 7 new values, extend _LEGACY_ACTION_TYPES to include all Phase 8 values (HANDOVER_DRAFT, HANDOVER_SIGNOFF, TRAINING_SESSION, TRAINING_SIGNOFF, KNOWLEDGE_DEDUP, STALE_FLAG, SOP_DRAFT) for regression, set the baseline glob sentinel to `< "012"`, and implement the 7-test structure (pre-012 rejects REORDER_ALERT, post-012 admits REORDER_ALERT, parametrized admit-all-Phase9, parametrized legacy-still-ok incl Phase 8, decision-enum-unchanged, idempotent double-apply, migrate-runner-picks-up-012).
  </action>
  <verify>
    <automated>cd "/run/media/federicocalo/D/prj/Smart Factory Transformation" && python -c "from pathlib import Path; sql=Path('infra/migrations/timescale/012_extend_audit_scm.sql').read_text(); enum=Path('packages/sft-agents/src/sft_agents/models/enums.py').read_text(); vals=['REORDER_ALERT','PURCHASE_RECOMMENDATION_DRAFT','PURCHASE_SIGNOFF','ENERGY_PROPOSAL','ENERGY_SIGNOFF','DEMAND_PLAN_DRAFT','DEMAND_PLAN_SIGNOFF','COST_REPORT']; assert all(v in sql for v in vals), [v for v in vals if v not in sql]; assert all(v in enum for v in vals), [v for v in vals if v not in enum]; assert 'DROP CONSTRAINT IF EXISTS' in sql; assert 'SOP_DRAFT' in sql and 'OEE_REPORT' in sql and 'ANOMALY_ALERT' in sql, 'legacy regression'; print('lockstep OK')" && python -c "from sft_agents.models.enums import ActionType; assert ActionType.REORDER_ALERT.value=='REORDER_ALERT' and ActionType.DEMAND_PLAN_SIGNOFF.value=='DEMAND_PLAN_SIGNOFF'; print('enum import OK')" && python -m pytest infra/migrations/timescale/tests/test_migration_012.py --co -q 2>&1 | grep -c "::test_" | python -c "import sys; n=int(sys.stdin.read() or 0); assert n>=7, f'only {n} tests'; print(f'{n} tests collected')"</automated>
  </verify>
  <acceptance_criteria>
    - 012 contains the 8 new literals AND every legacy literal (SOP_DRAFT, OEE_REPORT, ANOMALY_ALERT present).
    - ActionType enum contains 8 new members with value == name (incl. COST_REPORT).
    - test_migration_012.py collects >= 7 tests; with Docker is green for admit/reject/idempotency/regression.
  </acceptance_criteria>
  <done>Migration 012 and ActionType enum carry an identical 8-value Phase 9 set (incl. COST_REPORT); no legacy value removed; Decision CHECK untouched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| migration runner to DB | DDL creates scm.* + extends audit.actions CHECK; must not weaken existing constraints |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-01 | Tampering | migration 012 CHECK constraint | mitigate | Regression test asserts all legacy action_types (incl. Phase 8) still admitted; Decision CHECK untouched |
| T-09-02 | Tampering | enum/SQL lockstep drift | mitigate | Verify step asserts byte-identical 7-value set in both files |
| T-09-03 | Tampering | scm.* category/process CHECK | mitigate | DDL CHECK constraints; migration 011 test rejects an invalid category/process value |
| T-09-SC | Tampering | npm/pip/cargo installs | accept | No package installs in Phase 9 (RESEARCH Package Legitimacy Audit: none new; statsmodels approved-but-unused) |
</threat_model>

<verification>
- `python -m pytest infra/migrations/timescale/tests/test_migration_011.py --co -q` collects >=5 tests.
- `python -m pytest infra/migrations/timescale/tests/test_migration_012.py --co -q` collects >=7 tests.
- Enum import succeeds for all 7 new members; lockstep verify command passes.
</verification>

<success_criteria>
scm.* schema + audit enum/CHECK lockstep landed with their integration tests; downstream agent waves can query scm.* and write the 7 new ActionType members.
</success_criteria>

<output>
Create `.planning/phases/09-agents-supply-chain-economics/09-00a-SUMMARY.md` when done.
</output>
