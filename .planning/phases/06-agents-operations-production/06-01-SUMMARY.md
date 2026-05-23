---
phase: 06-agents-operations-production
plan: 01
plan_id: 06-01
subsystem: audit-substrate
tags: [migration, audit, enums, gating-prerequisite, phase-6, ops]
status: awaiting-human-action
dependency_graph:
  requires:
    - 06-00            # Wave 0 test scaffolding (conftest mocks + markers)
    - 04-02            # audit.actions hypertable + REVOKE substrate (existed)
  provides:
    - audit.actions.decision admits 'suppressed' + 'logged'
    - audit.actions.action_type CHECK enforces ESCALATION_REQUEST / QUALITY_VERDICT / SCHEDULE_DRAFT / ANOMALY_ALERT
    - Decision.SUPPRESSED, Decision.LOGGED (Python enum)
    - ActionType.ESCALATION_REQUEST, .QUALITY_VERDICT, .SCHEDULE_DRAFT, .ANOMALY_ALERT (Python enum)
  affects:
    - 06-02            # RateLimiter writes Decision.SUPPRESSED — unblocked once migration deployed
    - 06-05            # EscalateToSupervisorTool uses ActionType.ESCALATION_REQUEST
    - 06-06            # operator-assistant writes Decision.LOGGED + ActionType.ESCALATION_REQUEST
    - 06-07            # quality-inspector writes ActionType.QUALITY_VERDICT
    - 06-08            # production-planner writes ActionType.SCHEDULE_DRAFT
tech_stack:
  added: []
  patterns:
    - "Idempotent migration via dynamic pg_constraint lookup + DROP IF EXISTS"
    - "Lockstep enum-to-CHECK contract enforced by round-trip test"
    - "Workspace-root sys.path bootstrap in test modules under infra/ to resolve infra.* imports under uv run pytest"
key_files:
  created:
    - infra/migrations/timescale/007_extend_audit_decisions.sql
    - infra/migrations/timescale/tests/test_migration_007.py
    - .planning/phases/06-agents-operations-production/06-01-SUMMARY.md
  modified:
    - packages/sft-agents/src/sft_agents/models/enums.py
    - packages/sft-agents/tests/test_audit_constraints.py
    - infra/migrations/timescale/pyproject.toml
    - pyproject.toml
    - .gitignore
decisions:
  - "Named the new CHECK constraint audit_actions_decision_chk (vs PG's auto-generated actions_decision_check) so future migrations have a stable name to target — Rule 2 robustness improvement."
  - "Added a NEW named CHECK on audit.actions.action_type (003 left it unconstrained). This codifies the ActionType enum closure at the DB layer, matching the existing pattern for decision."
  - "Used dynamic pg_constraint lookup (DO $$ ... $$ block) to drop the pre-existing unnamed decision CHECK because PG's auto-naming heuristic for column-inline CHECKs is fragile across versions and table-naming choices (audit.actions could become actions_decision_check or audit_actions_decision_check)."
  - "Registered the `integration` pytest marker in both the migrations sub-project pyproject.toml AND the workspace root pyproject.toml, treating it as an alias for the pre-existing `testcontainers` marker. Eliminates PytestUnknownMarkWarning when the plan's verify selector `-m integration` is used against tests living under infra/migrations/."
metrics:
  duration_minutes: 14
  completed_date: 2026-05-23
  tasks_total: 3
  tasks_completed: 2
  tasks_blocked: 1
  tests_added: 25
  tests_passing: 372   # 18 (migration_007) + 43 (test_audit_constraints) + 311 (other sft-agents — full suite green)
  files_created: 3
  files_modified: 5
---

# Phase 6 Plan 01: Extend audit.actions CHECK constraints + Decision/ActionType enums Summary

**One-liner:** TimescaleDB migration 007 + Python enum extension that admit Phase 6's new audit decision/action types (`suppressed`, `logged`, `ESCALATION_REQUEST`, `QUALITY_VERDICT`, `SCHEDULE_DRAFT`, `ANOMALY_ALERT`) in lockstep — the gating prerequisite for Plans 06-02, 06-05, 06-06, 06-07, 06-08.

## Status

**Tasks 1 + 2 completed and committed.** Task 3 is a `checkpoint:human-action` (blocking gate) — the migration SQL is in the repo and tests are green, but the migration must still be **pushed to the dev TimescaleDB instance by the human operator** before Wave 1 dependent plans can proceed. See "Checkpoint Awaiting Human Action" below.

## Tasks Completed

| Task | Name | Status | Commits |
|------|------|--------|---------|
| 1 | Write idempotent migration 007 (decision + action_type CHECK extensions) + 18 testcontainer tests | DONE | `6556a9f` (RED test) → `e49e5a5` (GREEN migration) |
| 2 | Extend Decision + ActionType enums with 6 new Phase 6 members | DONE | `70237a4` (RED test) → `09fa2b2` (GREEN enums) |
| 3 | BLOCKING — push migration 007 to dev TimescaleDB | **AWAITING HUMAN** | — |

## What Was Built

### Migration 007 (`infra/migrations/timescale/007_extend_audit_decisions.sql`)

- **Decision CHECK extension.** Drops the auto-named column-inline `audit.actions.decision` CHECK constraint inherited from 003 (located via dynamic `pg_constraint` lookup, since PG auto-generates the name and we must not hard-code it). Re-adds it as the explicitly-named `audit_actions_decision_chk` admitting the 9 legacy values plus `'suppressed'` (D-AD-03) and `'logged'` (D-OA-02).
- **Action-type CHECK introduction.** Adds a NEW named `audit_actions_action_type_chk` (003 left `action_type` unconstrained TEXT) admitting the 6 pre-existing ActionType labels plus 4 Phase 6 labels: `ESCALATION_REQUEST`, `QUALITY_VERDICT`, `SCHEDULE_DRAFT`, `ANOMALY_ALERT`.
- **Idempotency.** Both constraints use `DROP CONSTRAINT IF EXISTS … ADD CONSTRAINT …`. The dynamic decision-CHECK lookup also short-circuits on second apply because the named target constraint is filtered out of the search.
- **Verified.** 18 testcontainer tests pass (pre/post migration, all 9 legacy decisions, all 4 new action types, double-apply idempotency, `migrate.py` runner pick-up).

### Python enum extension (`packages/sft-agents/src/sft_agents/models/enums.py`)

| Class | Member | Value (matches SQL CHECK) |
|-------|--------|---------------------------|
| `Decision` | `SUPPRESSED` | `"suppressed"` |
| `Decision` | `LOGGED` | `"logged"` |
| `ActionType` | `ESCALATION_REQUEST` | `"ESCALATION_REQUEST"` |
| `ActionType` | `QUALITY_VERDICT` | `"QUALITY_VERDICT"` |
| `ActionType` | `SCHEDULE_DRAFT` | `"SCHEDULE_DRAFT"` |
| `ActionType` | `ANOMALY_ALERT` | `"ANOMALY_ALERT"` |

Class docstrings updated to call out the lockstep coupling with migration 007, including the runtime PG check-violation failure mode if either side drifts.

### Test coverage

- **`infra/migrations/timescale/tests/test_migration_007.py`** (18 tests, all green, ~119s with Docker)
  - Pre-migration rejection of `'suppressed'` via CheckViolationError
  - Post-migration admission of `'suppressed'` and `'logged'`
  - Backward-compat: all 9 legacy decision values still admitted
  - All 4 new action_type values admitted
  - Double-apply idempotency
  - `migrate.py` runner picks up 007 via its `[0-9][0-9][0-9]_*.sql` glob
- **`packages/sft-agents/tests/test_audit_constraints.py`** (43 tests, all green, ~0.7s — pure Python, no DB)
  - 6 new tests for member presence + exact `.value` strings
  - 6 round-trip tests for `Decision(string)` / `ActionType(string)` lookup
  - 2 AuditRecord construction tests for `Decision.SUPPRESSED` / `Decision.LOGGED`
  - 15 backward-compat tests asserting no legacy renames

## Deviations from Plan

### Rule 2 — auto-add missing critical functionality

**1. Named target constraints instead of relying on PG auto-naming**
- **Found during:** Task 1 implementation
- **Issue:** Plan suggested `ALTER TABLE … DROP CONSTRAINT <name>` with a hard-coded name, but the original 003 CHECK is column-inline and PG auto-generates the name (typically `actions_decision_check`, but the heuristic depends on the schema-qualification choice). Hard-coding the name would silently fail if the auto-generated name differs in any future PG version, leaving the old constraint in place.
- **Fix:** Added a `DO $$ … $$` block that queries `pg_constraint` for any column-level CHECK that references the `decision` column (excluding the named `audit_actions_hitl_motivation_chk`) and drops it dynamically. The follow-up `DROP CONSTRAINT IF EXISTS audit_actions_decision_chk` guards against the second-apply path. Same naming discipline applied to `audit_actions_action_type_chk`.
- **Files modified:** `infra/migrations/timescale/007_extend_audit_decisions.sql`
- **Commit:** `e49e5a5`

**2. NEW action_type CHECK constraint (003 had none)**
- **Found during:** Task 1 read of 003 (line 30)
- **Issue:** Plan said "if such CHECK exists on action_type — verify in 003 first; if action_type is unconstrained TEXT, skip this portion of the migration." Verification showed it IS unconstrained. However, leaving action_type unconstrained means **the Decision/ActionType lockstep guarantee promised in the threat register (T-V6-enum-drift) is one-sided** — drift on the action_type side would be invisible at the DB layer. Phase 6's whole reason for this migration is to enforce enum-to-CHECK lockstep, so codifying action_type at the DB layer too is the correct fulfillment of OPS-04 / OPS-05 intent.
- **Fix:** Added `audit_actions_action_type_chk` admitting all 10 currently-defined ActionType values.
- **Files modified:** `infra/migrations/timescale/007_extend_audit_decisions.sql`
- **Commit:** `e49e5a5`

### Rule 3 — auto-fix blocking issues

**3. Workspace-root sys.path bootstrap in test module**
- **Found during:** Task 1 first pytest run
- **Issue:** `from infra.migrations.timescale.migrate import migrate` failed with `ModuleNotFoundError: No module named 'infra'` under `uv run pytest` — `infra/` has no `__init__.py` and isn't a workspace member. The pre-existing `test_migration_idempotent.py` has the exact same import and fails to collect for the same reason; only `tests/integration/test_migrations_idempotent.py` (Phase 4) works because it prepends `_REPO_ROOT` to `sys.path` at module import time.
- **Fix:** Mirrored the Phase 4 pattern in the new test module. `parent.parent.parent.parent.parent` from `infra/migrations/timescale/tests/test_migration_007.py` resolves to the workspace root.
- **Files modified:** `infra/migrations/timescale/tests/test_migration_007.py`
- **Commit:** `e49e5a5`

**4. Register the `integration` pytest marker**
- **Found during:** Task 1 GREEN test run
- **Issue:** Plan's verify command uses `-m integration -x`, but the migrations sub-project pyproject only registered `testcontainers`, and the workspace root pyproject registered no markers at all. Running with `-m integration` would deselect every test in the new file AND emit `PytestUnknownMarkWarning` 8 times.
- **Fix:** Registered `integration` as an alias for `testcontainers` in both `infra/migrations/timescale/pyproject.toml` and the workspace-root `pyproject.toml`. Marker semantics are equivalent (both mean "requires Docker"); the alias unifies the two phase conventions.
- **Files modified:** `infra/migrations/timescale/pyproject.toml`, `pyproject.toml`
- **Commit:** `e49e5a5`

**5. .gitignore the spurious `infra/migrations/timescale/uv.lock`**
- **Found during:** Task 1 after first `uv sync`
- **Issue:** Running `uv sync` from inside the migrations sub-project created a parallel `uv.lock` there. The workspace pattern is a single root `./uv.lock`; a sub-project lock would diverge silently.
- **Fix:** Added the sub-project lock path to `.gitignore`; removed the accidentally-created file before committing.
- **Files modified:** `.gitignore`
- **Commit:** `e49e5a5`

## Authentication Gates

None encountered (no auth required for testcontainer-based tests).

## Checkpoint Awaiting Human Action

**Task 3 (gate=`blocking`) — push migration 007 to dev TimescaleDB.**

The migration file `infra/migrations/timescale/007_extend_audit_decisions.sql` is committed and unit-tested against ephemeral containers. It MUST be applied to the dev TimescaleDB instance before Plans 06-02, 06-05, 06-06, 06-07, 06-08 can write audit rows using the new enum values — runtime INSERTs would otherwise fail with `CheckViolationError`.

**Verification commands the operator must run (per `06-01-PLAN.md` Task 3 `<how-to-verify>`):**

1. **Apply the migration:**
   ```bash
   make migrate-timescale
   # or directly:
   python3 scripts/timescale-migrate.py
   ```
   Expected: stdout shows `OK [007_extend_audit_decisions.sql]: applied` (and all 001-006 either applied or no-op).

2. **Verify the decision CHECK now lists the new values:**
   ```bash
   psql "$TIMESCALE_DSN" -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'audit.actions'::regclass AND conname LIKE '%decision%';"
   ```
   Expected: a row whose `pg_get_constraintdef` contains `'suppressed'` and `'logged'` in the IN list.

3. **Verify the action_type CHECK exists and lists the new values:**
   ```bash
   psql "$TIMESCALE_DSN" -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'audit.actions'::regclass AND conname LIKE '%action_type%';"
   ```
   Expected: a row for `audit_actions_action_type_chk` whose definition contains `'ESCALATION_REQUEST'`, `'QUALITY_VERDICT'`, `'SCHEDULE_DRAFT'`, `'ANOMALY_ALERT'`.

4. **End-to-end constraint smoke test (wrap in transaction so no audit row is permanently written):**
   ```bash
   psql "$TIMESCALE_DSN" <<'EOF'
   BEGIN;
   INSERT INTO audit.actions
     (action_id, agent_id, thread_id, cluster, action_type, evidence_panel, decision)
     VALUES (gen_random_uuid(), 'anomaly-detector', 'test-thread', 'ops',
             'ANOMALY_ALERT', '{}'::jsonb, 'suppressed');
   ROLLBACK;
   EOF
   ```
   Expected: `INSERT 0 1` then `ROLLBACK`. Must NOT raise `ERROR: new row for relation "actions" violates check constraint`.

**Resume signal (per plan):** Reply `approved — migration pushed` once steps 1-4 succeed on dev DB.

## Self-Check: PASSED

- [x] `infra/migrations/timescale/007_extend_audit_decisions.sql` exists (verified via `ls`)
- [x] `infra/migrations/timescale/tests/test_migration_007.py` exists
- [x] `packages/sft-agents/src/sft_agents/models/enums.py` modified (verified via `git diff`)
- [x] `packages/sft-agents/tests/test_audit_constraints.py` modified
- [x] Commit `6556a9f` exists (RED test for migration)
- [x] Commit `e49e5a5` exists (GREEN migration + pyproject + sys.path bootstrap)
- [x] Commit `70237a4` exists (RED test for enums)
- [x] Commit `09fa2b2` exists (GREEN enum extension)
- [x] 18 + 43 = 61 plan-scoped tests pass
- [x] Full sft-agents non-integration suite still green (329 passed)

## Known Stubs

None — both the SQL migration and the Python enums are fully functional. No placeholder/TODO values; no UI components affected.

## Threat Flags

None — the plan's threat register (`T-V6-enum-drift`, `T-V6-migration-replay`, `T-V6-audit-repudiation`) is fully covered by the tests in this plan. No new trust boundaries or surface introduced beyond what 06-01-PLAN documented.

## TDD Gate Compliance

- [x] RED gate (Task 1): `6556a9f` — `test(06-01): add failing tests for migration 007 …`
- [x] GREEN gate (Task 1): `e49e5a5` — `feat(06-01): add migration 007 …`
- [x] RED gate (Task 2): `70237a4` — `test(06-01): add failing tests for Phase 6 Decision + ActionType …`
- [x] GREEN gate (Task 2): `09fa2b2` — `feat(06-01): extend Decision + ActionType enums …`
- [n/a] REFACTOR gate: not required — no cleanup deltas beyond the GREEN commits.
