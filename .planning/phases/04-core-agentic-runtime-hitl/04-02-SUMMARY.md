---
phase: 04-core-agentic-runtime-hitl
plan: 02
subsystem: pg-migrations-wave2-substrate
tags: [migrations, timescaledb, audit, hitl, budget, langgraph, revoke, agent_role, outbox, wave-2]
requires:
  - "04-01 (sft-agents SDK foundation — Pydantic models referenced by future writers of audit.actions / hitl.approvals)"
provides:
  - "hitl schema + hitl.approvals (D-55) with partial index idx_approvals_tier_status WHERE status='pending'"
  - "audit schema + audit.actions hypertable (D-56) with 30-day chunks + 7-year retention policy"
  - "audit.outbox (OQ5 unified subject+payload retry queue) with idx_outbox_next_attempt WHERE attempts<10"
  - "budget schema + budget.executions (D-60) with composite PK (thread_id, agent_id) for UPSERT"
  - "langgraph schema (placeholder) + scripts/langgraph-init.py creating public.checkpoint* tables via AsyncPostgresSaver.setup()"
  - "agent_role NOLOGIN (OQ1) with INSERT,SELECT on audit.actions + REVOKE UPDATE,DELETE (HITL-05 DB-layer enforcement)"
  - "make migrate-phase4 / make migrate-phase4-dry targets chaining timescale-migrate + langgraph-init"
  - "2 integration test files (11 tests total) gated by @pytest.mark.integration"
affects:
  - "Unblocks Wave 3 (Plan 04-03 LLM adapter — depends on langgraph checkpoint tables)"
  - "Unblocks Wave 3 (Plan 04-04 memory — depends on audit.actions for episodic queries CORE-08)"
  - "Unblocks Wave 4 (Plan 04-05 supervisor — checkpointer hot path)"
  - "Unblocks Wave 4 (Plan 04-06 HITL cycle — depends on hitl.approvals + audit.outbox + budget.executions)"
  - "Unblocks Wave 4 (Plan 04-07 API gateway — reads hitl.approvals)"
  - "Unblocks Wave 4 (Plan 04-08 replay — reads audit.actions via thread_id index)"
tech_stack:
  added:
    - "TimescaleDB 2.18.0-pg16 hypertable on audit.actions (30-day chunks, 7-year retention)"
    - "pgcrypto extension (gen_random_uuid for UUID defaults on audit + hitl)"
    - "PostgreSQL agent_role (NOLOGIN; Phase 11 binds login users via SealedSecrets)"
  patterns:
    - "Idempotent migrations: CREATE … IF NOT EXISTS + DO $$ pg_roles guard + if_not_exists policy flag"
    - "REVOKE-as-defense-in-depth: REVOKE UPDATE,DELETE on audit.actions FROM agent_role survives accidental future GRANTs"
    - "Dual-side HITL CHECK constraint on audit.actions: (decision NOT LIKE 'hitl_%') OR (motivation IS NOT NULL AND approval_id IS NOT NULL)"
    - "Composite PK (ts, id) on audit.actions — required by TimescaleDB hypertable partition column inclusion in PK"
    - "Partial index idx_approvals_tier_status WHERE status='pending' — small index covering the dominant HITL queue scan"
    - "SET LOCAL ROLE inside async transaction — required for asyncpg-based DB-role privilege tests (SET LOCAL is tx-scoped)"
    - "Unified subject+payload outbox (OQ5) — single table backs multi-subject NATS retry loop"
key_files:
  created:
    - "infra/migrations/timescale/002_create_hitl_approvals.sql (40 lines) — D-55 verbatim"
    - "infra/migrations/timescale/003_create_audit_actions.sql (154 lines) — D-56 hypertable + outbox + agent_role + REVOKE"
    - "infra/migrations/timescale/004_create_budget_executions.sql (36 lines) — D-60 composite PK"
    - "infra/migrations/timescale/005_create_langgraph_checkpoints.sql (19 lines) — schema placeholder + docs"
    - "scripts/langgraph-init.py (134 lines) — idempotent AsyncPostgresSaver.setup() runner"
    - "tests/integration/test_migrations_idempotent.py (267 lines, 7 tests)"
    - "tests/integration/test_audit_immutability.py (207 lines, 4 tests)"
  modified:
    - "Makefile — new targets migrate-phase4 + migrate-phase4-dry"
decisions:
  - "OQ1 resolved: agent_role created in Phase 4 as NOLOGIN. Phase 11 binds real login users."
  - "OQ5 resolved: single audit.outbox table with subject TEXT discriminator (not per-subject tables)."
  - "W3 driver clarification documented in scripts/langgraph-init.py module docstring: langgraph-checkpoint-postgres>=3.1 uses psycopg3 (not asyncpg) — statement_cache_size=0 is NOT required and must not be added. This prevents a future contributor from misapplying the asyncpg Pitfall-6 tuning."
  - "agent_role GRANTs on budget.executions are placed in 004_create_budget_executions.sql (not 003), because the budget schema does not yet exist when 003 runs. 003's grant block guards with EXISTS check so it is safe either way."
  - "DO $$ EXCEPTION WHEN OTHERS RAISE NOTICE blocks wrap GRANT/REVOKE in 003 + 004 — keeps re-runs non-fatal while still surfacing unexpected errors."
metrics:
  duration: "~8 minutes wall-clock"
  completed_date: "2026-05-18"
  tasks_completed: 2
  tasks_pending_checkpoint: 1
  files_created: 7
  files_modified: 1
  lines_total: 857
  integration_tests_passing: 11
  integration_tests_failing: 0
---

# Phase 4 Plan 02: PostgreSQL Wave 2 Substrate Summary

Plan 04-02 ships the PostgreSQL schema substrate every Phase 4 plan depends on: 4 idempotent SQL migrations (`002_create_hitl_approvals.sql`, `003_create_audit_actions.sql`, `004_create_budget_executions.sql`, `005_create_langgraph_checkpoints.sql`) + `scripts/langgraph-init.py` + a `make migrate-phase4` target + 11 integration tests verifying idempotency, hypertable registration, 7-year retention, and the DB-layer REVOKE of UPDATE/DELETE on `audit.actions` from `agent_role` (HITL-05 / T-04-Audit-Tamper mitigation). Tasks 1-2 (autonomous) are committed; Task 3 ([BLOCKING] migration push) awaits human verification against a live compose stack.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 04-02-01 | SQL migrations 002-005 + idempotency integration test | `b872999` | infra/migrations/timescale/002_create_hitl_approvals.sql, 003_create_audit_actions.sql, 004_create_budget_executions.sql, 005_create_langgraph_checkpoints.sql, tests/integration/test_migrations_idempotent.py |
| 04-02-02 | langgraph-init script + Makefile target + audit immutability test | `12e0514` | scripts/langgraph-init.py, tests/integration/test_audit_immutability.py, Makefile |

## Tasks Pending (Checkpoint)

| Task | Type | Gate | Awaiting |
|------|------|------|----------|
| 04-02-03 | checkpoint:human-verify | blocking | Human operator runs `make migrate-phase4` against the live dev-stack PostgreSQL + verifies 9 acceptance steps (see `<how-to-verify>` in PLAN). Until then Wave 3+4 are not green-lit. |

## Verification Results (Tasks 1-2)

```bash
$ cd "/media/federicocalo/D1/prj/Smart Factory Transformation/.claude/worktrees/agent-ac25d4e1d3472dde0"

# Plan-defined automated verify (Task 1)
$ grep -c "IF NOT EXISTS\|if_not_exists\|DO \$\$" infra/migrations/timescale/002_create_hitl_approvals.sql infra/migrations/timescale/003_create_audit_actions.sql infra/migrations/timescale/004_create_budget_executions.sql infra/migrations/timescale/005_create_langgraph_checkpoints.sql
infra/migrations/timescale/002_create_hitl_approvals.sql:6
infra/migrations/timescale/003_create_audit_actions.sql:12
infra/migrations/timescale/004_create_budget_executions.sql:2
infra/migrations/timescale/005_create_langgraph_checkpoints.sql:2

$ grep -n "REVOKE UPDATE, DELETE ON audit.actions FROM agent_role" infra/migrations/timescale/003_create_audit_actions.sql
150:  REVOKE UPDATE, DELETE ON audit.actions FROM agent_role;

# Plan-defined automated verify (Task 2)
$ python3 -c "import ast; ast.parse(open('scripts/langgraph-init.py').read()); print('ast ok')"
ast ok
$ grep -n "AsyncPostgresSaver.from_conn_string\|saver.setup()" scripts/langgraph-init.py
80:        async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
81:            await saver.setup()
$ grep -n "migrate-phase4" Makefile
16:.PHONY: … migrate-phase4 migrate-phase4-dry …
193:migrate-phase4:
197:migrate-phase4-dry:

# Integration test suite (testcontainers + asyncpg)
$ uv run pytest tests/integration/test_migrations_idempotent.py tests/integration/test_audit_immutability.py -m integration --tb=short
============================= test session starts ==============================
…
collected 11 items
tests/integration/test_migrations_idempotent.py .......                  [ 63%]
tests/integration/test_audit_immutability.py ....                        [100%]
============================= 11 passed in 12.79s ==============================

# Makefile dry-run smoke
$ uv run --package sft-agents make migrate-phase4-dry
[dry-run] Migration files that would be applied:
  001_create_sensor_events.sql
  002_create_hitl_approvals.sql
  003_create_audit_actions.sql
  004_create_budget_executions.sql
  005_create_langgraph_checkpoints.sql
{"event":"langgraph_init_dry_run","level":"info",…}
```

## Must-Haves Truth Table (Plan Frontmatter `must_haves.truths`)

| # | Truth Statement | Status | Evidence |
|---|-----------------|--------|----------|
| 1 | Re-running migrate is idempotent (zero schema changes) | PASS | `test_phase4_migrations_idempotent` — snapshot diff is `[]` |
| 2 | `agent_role` PostgreSQL role exists with INSERT,SELECT on `audit.actions` and NO UPDATE,DELETE | PASS | `test_agent_role_exists_and_revoke_effective` + `test_privilege_matrix_via_has_table_privilege` |
| 3 | UPDATE/DELETE on `audit.actions` as `agent_role` fails with `permission denied` | PASS | `test_agent_role_cannot_update`, `test_agent_role_cannot_delete` |
| 4 | Re-running `langgraph-init.py` exits 0 with no error | PENDING (live verify) | Dry-run smoke confirms script structure; full live run is Task 04-02-03 step 8 |
| 5 | `audit.actions` is a hypertable with 30-day chunks + 7-year retention policy | PASS | `test_audit_actions_is_hypertable`, `test_audit_retention_policy_seven_years` |
| 6 | `audit.outbox` exists with unified subject+payload retry schema (OQ5) | PASS | `test_phase4_schemas_and_tables_exist` (verifies `('audit','outbox')` in snapshot) + `test_outbox_partial_index_exists` |

## Public Schema (Final)

| Schema | Object | Purpose | Used By |
|--------|--------|---------|---------|
| `hitl` | `approvals` | D-55 approval queue (operator/supervisor/manager/safety_interlock) | Plan 04-06 HITL cycle, Plan 04-07 API gateway |
| `audit` | `actions` (hypertable) | D-56 forensic record, partitioned ts (30d), retained 7y | Every Plan 04-* writes here; Plan 04-08 replay reads |
| `audit` | `outbox` | OQ5 NATS retry queue (subject + payload + attempts) | Plan 04-06 (writes), Plan 04-06 retry loop (reads) |
| `budget` | `executions` | D-60 per-thread/per-agent token + cost + duration counters | Plan 04-06 budget guardrail (UPSERT) |
| `langgraph` | (schema only) | Placeholder; actual tables in `public.checkpoint*` | Plan 04-03 LLM adapter, Plan 04-05 supervisor checkpointer |
| `public` | `checkpoints`, `checkpoint_blobs`, `checkpoint_migrations` | Created by `AsyncPostgresSaver.setup()` (run via `scripts/langgraph-init.py`) | LangGraph runtime |

## agent_role Privilege Matrix (Final)

| Object | INSERT | SELECT | UPDATE | DELETE |
|--------|:------:|:------:|:------:|:------:|
| `audit.actions` | YES | YES | **NO (REVOKE)** | **NO (REVOKE)** |
| `audit.outbox` | YES | YES | YES | YES |
| `hitl.approvals` | YES | YES | YES (column-scoped: status, decided_at, decided_by, decision_json, escalated_to_id) | NO (default) |
| `budget.executions` | YES | YES | YES | NO (default) |

UPDATE column-scoping on `hitl.approvals` mechanically prevents agent code from forging `created_at`, `sla_deadline`, or `payload_json` (i.e. the immutable approval-request facts).

## CHECK Constraints on audit.actions

1. `CHECK (decision IN ('auto','hitl_operator','hitl_supervisor','hitl_manager','interlock_reject','rolled_back','timed_out','governor_alert','escalated'))` — enum closure matches `Decision` Pydantic enum from Plan 04-01.
2. `audit_actions_hitl_motivation_chk`: `(decision NOT LIKE 'hitl_%') OR (motivation IS NOT NULL AND char_length(motivation) > 0 AND approval_id IS NOT NULL)` — DB-layer enforcement of HITL-07 (motivation required) + D-56 dual-side rule (`approval_id` required for any hitl_* decision). Pydantic validates at API boundary; CHECK validates at storage boundary. Defense-in-depth.

## Deviations from Plan

### [Rule 1 - Bug] SET LOCAL ROLE requires explicit asyncpg transaction

- **Found during:** First execution of `test_agent_role_cannot_update` / `test_agent_role_cannot_delete` (initial RED state, 2 tests failed `DID NOT RAISE InsufficientPrivilegeError`)
- **Issue:** `SET LOCAL ROLE agent_role` is scoped to the current transaction. asyncpg's `conn.execute()` outside an explicit transaction runs in autocommit mode where SET LOCAL is a no-op, so the UPDATE/DELETE was running as superuser and succeeding.
- **Fix:** Wrap the role switch + protected statement in `async with conn.transaction():` so SET LOCAL applies for the duration of the UPDATE/DELETE. Pattern documented in test docstring for future contributors.
- **Files modified:** `tests/integration/test_audit_immutability.py`
- **Commit:** `12e0514`
- **Impact:** Pure test-layer fix; no production code or SQL altered. The `has_table_privilege` introspection test continued to pass throughout, confirming the SQL REVOKE itself was always correct — the bug was in test exercise mechanics.

### [Rule 2 - Critical functionality] agent_role grants split across 003 and 004

- **Found during:** Authoring 003.
- **Issue:** 003 cannot GRANT on `budget.executions` because that table is created in 004. If a future contributor runs only `003.sql` standalone, the GRANT would error.
- **Fix:** 003 guards the budget GRANT with `IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'budget')` so it is safe either way; 004 also does its own GRANT (with `IF EXISTS … agent_role` guard) so the privileges land regardless of apply order. Documented in 004 comment block.
- **Files modified:** `infra/migrations/timescale/003_create_audit_actions.sql`, `infra/migrations/timescale/004_create_budget_executions.sql`
- **Commit:** `b872999`

## Threats Mitigated

| Threat ID | Disposition | Evidence |
|-----------|-------------|----------|
| T-04-Audit-Tamper | mitigate | `REVOKE UPDATE, DELETE ON audit.actions FROM agent_role` + `audit_actions_hitl_motivation_chk` CHECK + `test_audit_immutability.py` 4-test gate |
| T-04-Outbox-Drop | mitigate | `audit.outbox` table substrate shipped + `idx_outbox_next_attempt WHERE attempts < 10` partial index ready for retry loop (lands in Plan 04-06) |

## Deferred Issues

| Issue | Plan to Address |
|-------|-----------------|
| Live verification of full `make migrate-phase4` against running compose stack | Task 04-02-03 (checkpoint:human-verify) — pending operator |
| Wave 0 stub `packages/sft-agents/tests/test_migrations.py` continues to skip (it targets a `sft_agents.migrations` Python module which is intentionally NOT introduced by 04-02 — migrations stay as `infra/migrations/timescale/*.sql` driven by the existing Phase 3 runner) | No action needed — the stub is harmless; Plan 04-02's idempotency test lives at `tests/integration/test_migrations_idempotent.py`. |

## Known Stubs

None. Plan 04-02 delivers concrete SQL DDL + runnable Python script + passing integration tests.

## Self-Check: PASSED

- `infra/migrations/timescale/002_create_hitl_approvals.sql` — FOUND
- `infra/migrations/timescale/003_create_audit_actions.sql` — FOUND
- `infra/migrations/timescale/004_create_budget_executions.sql` — FOUND
- `infra/migrations/timescale/005_create_langgraph_checkpoints.sql` — FOUND
- `scripts/langgraph-init.py` — FOUND (parses; structlog + AsyncPostgresSaver.setup confirmed)
- `tests/integration/test_migrations_idempotent.py` — FOUND (7 tests passing)
- `tests/integration/test_audit_immutability.py` — FOUND (4 tests passing)
- `Makefile` — modified (migrate-phase4, migrate-phase4-dry targets present)
- Commit `b872999` — verified via `git log`
- Commit `12e0514` — verified via `git log`
