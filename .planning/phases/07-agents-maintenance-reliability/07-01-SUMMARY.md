---
phase: 07-agents-maintenance-reliability
plan: 01
subsystem: database
tags: [timescaledb, postgres, asyncpg, pydantic, enum, audit, migration, testcontainers]

# Dependency graph
requires:
  - phase: 06-agents-operations-production
    provides: "audit.actions table + audit_actions_action_type_chk CHECK constraint (Plan 06-01 / migration 007); Decision + ActionType enum extension pattern"
  - phase: 04-foundation
    provides: "audit.actions base table (migration 003); REVOKE UPDATE/DELETE for agent_role"
provides:
  - "Migration 009_extend_audit_mnt.sql: extends audit.actions.action_type CHECK to admit 5 Phase 7 ActionType values"
  - "ActionType.RUL_ESTIMATE / RCA_CHAIN / COACH_STEP / DOWNTIME_VERDICT / OEE_REPORT importable from sft_agents.models.enums"
  - "Round-trip integration test (20 testcontainer cases) guarding enum-vs-CHECK drift"
  - "Decision-enum-unchanged sanity test (D-AE-MNT explicit guard)"
affects:
  - 07-04-PLAN (build_maintenance_subgraph + request_help)
  - 07-06-PLAN (predictive-maintenance writes RUL_ESTIMATE)
  - 07-07-PLAN (rca-specialist writes RCA_CHAIN)
  - 07-08-PLAN (maintenance-coach writes COACH_STEP)
  - 07-09-PLAN (downtime-analyzer writes DOWNTIME_VERDICT + OEE_REPORT)
  - All Phase 7 agents (gating prerequisite — without migration 009 their audit INSERTs fail PG CHECK constraint)

# Tech tracking
tech-stack:
  added: []   # no new dependencies; reuses asyncpg + testcontainers + pytest from Phase 4/6
  patterns:
    - "Idempotent DROP+ADD CHECK on named constraint (mirror of migration 007)"
    - "Enum-vs-CHECK lockstep extension pattern: PR contains migration SQL + enum edit + round-trip tests in one atomic feat() commit pair"
    - "Decision-enum-unchanged sanity assertion via pg_constraint introspection (guards D-AE-MNT)"

key-files:
  created:
    - "infra/migrations/timescale/009_extend_audit_mnt.sql"
  modified:
    - "infra/migrations/timescale/tests/test_migration_009.py (Wave 0 stub → 7-test matrix, 20 parametrized cases)"
    - "packages/sft-agents/src/sft_agents/models/enums.py (ActionType extended with 5 Phase 7 values + docstring)"
    - "packages/sft-agents/tests/test_audit_constraints.py (added TestPhase7ActionTypeEnum + TestPhase7DecisionEnumUnchanged)"

key-decisions:
  - "Followed D-AE-MNT exactly: 5 new ActionType members, ZERO new Decision values. Migration 009 leaves the decision CHECK constraint untouched."
  - "Mirrored migration 007 pattern 1:1 (idempotent DROP IF EXISTS + ADD on named constraint audit_actions_action_type_chk). No DO block needed because the action_type constraint was already named by 007 — only the decision constraint in 007 needed dynamic lookup."
  - "_run_baseline_migrations() in test_migration_009.py applies files with name < '009', which currently means 001..007 (008 SQL is not yet implemented). The helper will pick up 008 automatically when it lands in plan 07-02."
  - "TestPhase7DecisionEnumUnchanged asserts Decision.__members__ is exactly the Phase 6 set — protects against accidental Decision drift in future Phase 7 plans that would diverge from migration 009."

patterns-established:
  - "Phase-extension migration template: copy 007 → bump filename → DROP+ADD named CHECK with extended IN list → write mirror test_migration_NNN.py with the same 6-test matrix (pre-rejects, post-admits, parametrized over new + legacy values, sister-enum unchanged, idempotent double-apply)."
  - "Enum-extension docstring template: add a 'Phase N extensions' block before the 'Migration ...' line, then add members with inline comments referencing the originating decision tag (D-PM-04, etc.)."

requirements-completed: [MNT-01, MNT-02, MNT-03, MNT-04]

# Metrics
duration: ~12 min (autonomous tasks 1+2; Task 3 awaiting human dev-DB push)
completed: 2026-05-23
---

# Phase 7 Plan 01: Audit ActionType Extension Summary

**Migration 009 + Python enum extend audit.actions.action_type CHECK with 5 Phase 7 ActionType values (RUL_ESTIMATE, RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT, OEE_REPORT); Decision enum bytewise unchanged per D-AE-MNT.**

## Performance

- **Duration:** ~12 min (Tasks 1–2 autonomous; Task 3 pending human dev-DB push)
- **Started:** 2026-05-23T17:28:46Z (approx — first commit `a42bbad`)
- **Completed (autonomous portion):** 2026-05-23T17:40:57Z
- **Tasks:** 2 of 3 (Task 3 is a `checkpoint:human-action` gate)
- **Files modified:** 4

## Accomplishments

- **Migration 009 idempotent SQL** authored and tested: DROP IF EXISTS + ADD `audit_actions_action_type_chk` CHECK with the full extended IN list (Phase 1-5 + Phase 6 + 5 Phase 7 values).
- **ActionType enum** extended in lockstep — same `.value` strings as the SQL CHECK; backward-compatible (no rename, no removal).
- **20 testcontainer integration tests** (7 test functions, 13 parametrized expansions) all green: pre-migration rejects `RUL_ESTIMATE`, post-migration admits all 5 new values, all 10 legacy Phase 1-6 values still insert, Decision CHECK definition bytewise unchanged, idempotent double-apply works, full `migrate()` runner picks up 009 automatically.
- **Decision-unchanged sanity test** (`TestPhase7DecisionEnumUnchanged`) compiled into the Python side at `packages/sft-agents/tests/test_audit_constraints.py` — guards against accidental Decision drift in future Phase 7 plans.
- **Full sft-agents test suite** still green: 388 passed / 4 skipped (no regression).

## Task Commits

Each task was committed atomically following the TDD RED → GREEN cycle:

1. **Task 1 (RED): failing test matrix for migration 009** — `a42bbad` (test)
2. **Task 1 (GREEN): migration 009 SQL** — `ec6b4dc` (feat)
3. **Task 2 (RED): failing Phase 7 ActionType + Decision-unchanged tests** — `ec8932f` (test)
4. **Task 2 (GREEN): ActionType extended with 5 Phase 7 values** — `b108608` (feat)

Task 3 is `checkpoint:human-action` (BLOCKING) — no commit produced; awaits dev-DB push by the operator. See CHECKPOINT block at end of this document.

## Files Created/Modified

- **Created** `infra/migrations/timescale/009_extend_audit_mnt.sql` — idempotent DROP+ADD named CHECK extending `audit.actions.action_type` with 5 Phase 7 values; Decision CHECK untouched.
- **Modified** `infra/migrations/timescale/tests/test_migration_009.py` — replaced the Wave 0 `pytest.skip` stub with the full 7-test matrix (6 from 07-PATTERNS.md Section 11 + the bonus `migrate.py` runner test). 20 parametrized cases total.
- **Modified** `packages/sft-agents/src/sft_agents/models/enums.py` — `ActionType` extended with `RUL_ESTIMATE`, `RCA_CHAIN`, `COACH_STEP`, `DOWNTIME_VERDICT`, `OEE_REPORT`; docstring "Phase 7 extensions" block added; `# Phase 7 additions — keep in lockstep with migration 009 (D-AE-MNT).` marker comment.
- **Modified** `packages/sft-agents/tests/test_audit_constraints.py` — added `TestPhase7ActionTypeEnum` (parametrized over 5 values) and `TestPhase7DecisionEnumUnchanged` (exact-set assertion on `Decision.__members__`).

## Decisions Made

- **D-AE-MNT strict adherence**: 5 new ActionType values, ZERO new Decision values. Migration 009 leaves the decision CHECK constraint definition byte-identical to its post-007 state. A dedicated test (`test_post_migration_decision_enum_unchanged`) verifies this via `pg_constraint` introspection.
- **Mirror of migration 007**: copied the structural DROP+ADD pattern verbatim. The action_type CHECK was already named (`audit_actions_action_type_chk`) when 007 introduced it, so 009 needs no dynamic lookup DO block — a flat `DROP CONSTRAINT IF EXISTS … ADD CONSTRAINT …` suffices.
- **Baseline helper future-proofing**: `_run_baseline_migrations(dsn)` selects files with `name < '009'`. Currently that means 001..007; once 008 is implemented in plan 07-02 the helper will automatically include it without code changes.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes triggered. No package installs (D-AE-MNT plan modifies SQL + Python enum only).

**Note (informational, NOT a deviation):** the security warning in the objective about Phase 6 slopsquatted npm packages was honored — `package.json` was NOT touched in this plan. All Python deps remain unchanged (asyncpg, testcontainers, pytest already present in `pyproject.toml`).

## Issues Encountered

- Initial pytest invocation via `cd packages/sft-agents && uv sync && uv run pytest …` picked up a system-level pytest (3.13) that lacked Pydantic in its import path. Resolved by invoking from the workspace root (`uv run --project packages/sft-agents pytest …`) so the workspace-scoped 3.12 venv with all sft-* dependencies is used. No code change required.

## TDD Gate Compliance

Both Task 1 and Task 2 followed strict RED → GREEN:

- **Task 1 RED**: `a42bbad` (test) — 20 cases failed because `009_extend_audit_mnt.sql` did not yet exist.
- **Task 1 GREEN**: `ec6b4dc` (feat) — all 20 cases pass.
- **Task 2 RED**: `ec8932f` (test) — `TestPhase7ActionTypeEnum` failed because `ActionType.RUL_ESTIMATE` did not exist.
- **Task 2 GREEN**: `b108608` (feat) — all 54 cases in `test_audit_constraints.py` pass.

No REFACTOR commits required (code was already in final form).

## Verification Evidence

```
pytest infra/migrations/timescale/tests/test_migration_009.py -m integration -x
  → 20 passed in 124.44s

pytest packages/sft-agents/tests/test_audit_constraints.py -x
  → 54 passed in 0.27s

pytest packages/sft-agents/tests/    # full suite, regression check
  → 388 passed, 4 skipped in 28.49s

python -c "from sft_agents.models.enums import ActionType, Decision; \
           assert ActionType.RUL_ESTIMATE.value == 'RUL_ESTIMATE' …"
  → OK
```

## Next Phase Readiness

- **Task 3 GATE (human-action) still open**: migration 009 SQL is in the repo and tested against testcontainers, but the dev TimescaleDB has NOT yet been migrated. All downstream Phase 7 agent plans (07-04, 07-06, 07-07, 07-08, 07-09) MUST wait for the operator to push 009 to dev-DB before their audit INSERTs can succeed at runtime.
- **Plans 07-02 onward** are unblocked from a code standpoint (the SQL + enum lockstep is in place); they MUST add `009` to their CI testcontainer fixtures (the `_run_baseline_migrations` helper at `infra/migrations/timescale/tests/test_migration_009.py` is the canonical example).
- No new `USER-SETUP.md` was generated. The only manual action is Task 3 (dev-DB migration), documented in the CHECKPOINT block below.

## Self-Check: PASSED

- File `infra/migrations/timescale/009_extend_audit_mnt.sql` — present, 52 lines.
- File `infra/migrations/timescale/tests/test_migration_009.py` — present, full matrix (no longer the Wave 0 stub).
- File `packages/sft-agents/src/sft_agents/models/enums.py` — contains `RUL_ESTIMATE`, `RCA_CHAIN`, `COACH_STEP`, `DOWNTIME_VERDICT`, `OEE_REPORT`.
- File `packages/sft-agents/tests/test_audit_constraints.py` — contains `TestPhase7ActionTypeEnum` and `TestPhase7DecisionEnumUnchanged`.
- Commits `a42bbad`, `ec6b4dc`, `ec8932f`, `b108608` all present in `git log --oneline -10`.
- STATE.md / ROADMAP.md NOT modified (per parallel-executor constraint).

---

## CHECKPOINT REACHED — Task 3 (human-action, BLOCKING)

**Type:** human-action
**Plan:** 07-01
**Progress:** 2/3 tasks complete (Task 3 is the gate)

### Completed Tasks

| Task | Name                                       | Commits                      | Files |
| ---- | ------------------------------------------ | ---------------------------- | ----- |
| 1    | Migration 009 SQL + 7-test matrix (TDD)    | `a42bbad` (test), `ec6b4dc` (feat) | `infra/migrations/timescale/009_extend_audit_mnt.sql`, `infra/migrations/timescale/tests/test_migration_009.py` |
| 2    | ActionType enum extension (TDD)            | `ec8932f` (test), `b108608` (feat) | `packages/sft-agents/src/sft_agents/models/enums.py`, `packages/sft-agents/tests/test_audit_constraints.py` |

### Current Task

**Task 3:** BLOCKING — Push migration 009 to dev TimescaleDB
**Status:** awaiting human action (cannot be automated — dev-DB credentials live outside the agent sandbox)
**Blocked by:** human operator with `$TIMESCALE_DSN` access to the dev cluster

### What was built (Tasks 1+2)

`infra/migrations/timescale/009_extend_audit_mnt.sql` is checked in and proven idempotent against a fresh TimescaleDB 2.18 container. `ActionType` enum in `packages/sft-agents/src/sft_agents/models/enums.py` is extended in lockstep. 20 testcontainer cases + 54 Python-side enum cases all green.

### What the human must do

**Step A — Apply migration 009 to dev DB:**
```bash
# Either via Makefile (preferred if exposed):
make migrate

# Or directly via the runner:
python infra/migrations/timescale/migrate.py --dsn "$TIMESCALE_DSN"
```
Expected output line: `OK [009_extend_audit_mnt.sql]: applied`.

**Step B — Verify the CHECK constraint definition on dev DB:**
```bash
psql "$TIMESCALE_DSN" -c "SELECT conname, pg_get_constraintdef(oid) \
  FROM pg_constraint \
  WHERE conrelid = 'audit.actions'::regclass \
    AND conname LIKE '%action_type%';"
```
The output row for `audit_actions_action_type_chk` must contain ALL of these quoted string literals:
`'RUL_ESTIMATE'`, `'RCA_CHAIN'`, `'COACH_STEP'`, `'DOWNTIME_VERDICT'`, `'OEE_REPORT'`
(in addition to the 10 Phase 1-6 values).

**Step C — Smoke-test an INSERT (must NOT raise `CheckViolationError`):**
```bash
psql "$TIMESCALE_DSN" -c "BEGIN; \
  INSERT INTO audit.actions \
    (action_id, action_type, agent_id, thread_id, decision, ts) \
  VALUES (gen_random_uuid(), 'RUL_ESTIMATE', 'predictive-maintenance', \
          'test-thread', 'auto', NOW()); \
  ROLLBACK;"
```
Expected: `ROLLBACK` (and no `ERROR: new row for relation "actions" violates check constraint`).

**Step D — Confirm Decision CHECK is untouched (D-AE-MNT sanity):**
```bash
psql "$TIMESCALE_DSN" -c "SELECT pg_get_constraintdef(oid) \
  FROM pg_constraint \
  WHERE conrelid = 'audit.actions'::regclass \
    AND conname = 'audit_actions_decision_chk';"
```
Must NOT contain `'rul_estimate'`, `'rca_chain'`, `'coach_step'`, `'downtime_verdict'`, or `'oee_report'`. Should still list `'suppressed'` and `'logged'` (added by migration 007).

### Resume signal

Type `approved — migration 009 pushed` once Steps A-D succeed on dev. Phase 7 downstream plans (07-04, 07-06..07-09) can then proceed.

---

*Phase: 07-agents-maintenance-reliability*
*Plan: 07-01*
*Completed (autonomous portion): 2026-05-23*
