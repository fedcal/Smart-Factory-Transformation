---
phase: 04-core-agentic-runtime-hitl
plan: 02
type: execute
wave: 2
depends_on: ["04-01"]
files_modified:
  - infra/migrations/timescale/002_create_hitl_approvals.sql
  - infra/migrations/timescale/003_create_audit_actions.sql
  - infra/migrations/timescale/004_create_budget_executions.sql
  - infra/migrations/timescale/005_create_langgraph_checkpoints.sql
  - scripts/langgraph-init.py
  - tests/integration/test_migrations_idempotent.py
  - tests/integration/test_audit_immutability.py
  - Makefile
autonomous: false
requirements: [CORE-04, CORE-08, CORE-09, HITL-05]
threat_refs: [T-04-Audit-Tamper, T-04-Outbox-Drop]

must_haves:
  truths:
    - "Re-running `python scripts/timescale-migrate.py` after a clean apply produces zero schema changes (idempotency)"
    - "`agent_role` PostgreSQL role exists with INSERT,SELECT on audit.actions and NO UPDATE,DELETE"
    - "An UPDATE or DELETE statement on audit.actions issued as agent_role fails with `permission denied for table actions`"
    - "Re-running `python scripts/langgraph-init.py` after a clean apply exits 0 with no error"
    - "audit.actions is a TimescaleDB hypertable with 30-day chunks and 7-year retention policy"
    - "audit.outbox table exists with the unified subject+payload retry schema (OQ5)"
  artifacts:
    - path: "infra/migrations/timescale/002_create_hitl_approvals.sql"
      provides: "hitl schema + approvals table + indexes"
      contains: "CREATE TABLE IF NOT EXISTS hitl.approvals"
    - path: "infra/migrations/timescale/003_create_audit_actions.sql"
      provides: "audit schema + actions hypertable + REVOKE + agent_role + outbox"
      contains: "REVOKE UPDATE, DELETE ON audit.actions FROM agent_role"
    - path: "infra/migrations/timescale/004_create_budget_executions.sql"
      provides: "budget schema + executions table"
      contains: "CREATE TABLE IF NOT EXISTS budget.executions"
    - path: "infra/migrations/timescale/005_create_langgraph_checkpoints.sql"
      provides: "langgraph schema bootstrap"
      contains: "CREATE SCHEMA IF NOT EXISTS langgraph"
    - path: "scripts/langgraph-init.py"
      provides: "idempotent AsyncPostgresSaver.setup() runner"
      min_lines: 40
  key_links:
    - from: "infra/migrations/timescale/003_create_audit_actions.sql"
      to: "audit.outbox"
      via: "same file"
      pattern: "audit\\.outbox"
    - from: "scripts/langgraph-init.py"
      to: "langgraph-checkpoint-postgres.AsyncPostgresSaver"
      via: "await saver.setup()"
      pattern: "AsyncPostgresSaver"
---

<objective>
Wave 2 Plan A: ship the SQL schema substrate that every Phase 4 plan depends on:
- `002_create_hitl_approvals.sql` (D-55 approval queue, OLTP table)
- `003_create_audit_actions.sql` (D-56 audit hypertable + outbox + agent_role + REVOKE — per OQ1 + OQ5)
- `004_create_budget_executions.sql` (D-60 budget executions OLTP)
- `005_create_langgraph_checkpoints.sql` (langgraph schema bootstrap — actual tables created by AsyncPostgresSaver.setup via scripts/langgraph-init.py)
- `scripts/langgraph-init.py` (idempotent setup runner)
- `[BLOCKING]` migration push task: runs `python scripts/timescale-migrate.py` after all SQL files are in place, BEFORE any subsequent wave's integration tests.

Purpose: enforce append-only audit at DB layer (HITL-05); create the persistence foundation for CORE-04 (checkpointer), CORE-08 (episodic memory queries `audit.actions WHERE thread_id`), CORE-09 (budget UPSERT), and the entire HITL cycle.

Output: 4 SQL migrations + 1 Python setup script + 2 integration test files verifying idempotency + immutability + Makefile target.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md
@.planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md
@.planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md
@.planning/phases/04-core-agentic-runtime-hitl/04-VALIDATION.md
@infra/migrations/timescale/001_create_sensor_events.sql
@infra/migrations/timescale/migrate.py
@scripts/timescale-migrate.py
@Makefile

<interfaces>
DDLs locked verbatim from CONTEXT.md:

hitl.approvals (D-55, CONTEXT.md lines 131-150):
  id UUID PK DEFAULT gen_random_uuid()
  agent_id TEXT NOT NULL
  thread_id TEXT NOT NULL
  tier TEXT NOT NULL CHECK IN (operator|supervisor|manager|safety_interlock)
  action_type TEXT NOT NULL
  payload_json JSONB NOT NULL
  status TEXT NOT NULL DEFAULT 'pending' CHECK IN (pending|approved|rejected|escalated|timed_out)
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  sla_deadline TIMESTAMPTZ NOT NULL
  decided_at TIMESTAMPTZ
  decided_by TEXT
  decision_json JSONB
  escalated_to_id UUID REFERENCES hitl.approvals(id)

Partial index: idx_approvals_tier_status ON (tier, status, sla_deadline) WHERE status = 'pending'
Additional: idx_approvals_thread_id ON (thread_id) for episodic queries

audit.actions (D-56, CONTEXT.md lines 165-184):
  id UUID PK DEFAULT gen_random_uuid()
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW()
  action_id UUID NOT NULL
  agent_id TEXT NOT NULL
  thread_id TEXT NOT NULL
  cluster TEXT NOT NULL
  action_type TEXT NOT NULL
  evidence_panel JSONB NOT NULL
  decision TEXT NOT NULL CHECK IN (auto|hitl_operator|hitl_supervisor|hitl_manager|interlock_reject|rolled_back|timed_out|governor_alert|escalated)
  decision_actor TEXT
  motivation TEXT
  budget_snapshot JSONB
  approval_id UUID REFERENCES hitl.approvals(id)
  PRIMARY KEY ordering on (ts, id) — TimescaleDB hypertable requires partitioning column in PK

  hypertable: chunk_time_interval => INTERVAL '30 days'
  retention: add_retention_policy 7 years (7 * 365 days = 2555 days)
  index: idx_audit_thread_id_ts ON (thread_id, ts DESC) for episodic replay
  index: idx_audit_decision_ts ON (decision, ts DESC) for governor query

audit.outbox (OQ5 unified outbox per RESEARCH §Open Questions):
  id UUID PK DEFAULT gen_random_uuid()
  subject TEXT NOT NULL
  payload_json JSONB NOT NULL
  attempts INT NOT NULL DEFAULT 0
  last_attempt_at TIMESTAMPTZ
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

  index: idx_outbox_next_attempt ON (next_attempt_at) WHERE attempts < 10

budget.executions (D-60, CONTEXT.md lines 324-336):
  thread_id TEXT NOT NULL
  agent_id TEXT NOT NULL
  tokens_total INT NOT NULL DEFAULT 0
  cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0
  duration_ms INT NOT NULL DEFAULT 0
  step_count INT NOT NULL DEFAULT 0
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  last_step_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  PRIMARY KEY (thread_id, agent_id)

langgraph schema (delegated to AsyncPostgresSaver.setup):
  005 SQL only creates schema; tables `checkpoints, checkpoint_blobs, checkpoint_migrations` are created by `await saver.setup()` from langgraph-checkpoint-postgres 3.1+

agent_role (OQ1 resolution — Phase 4 creates with NOLOGIN):
  CREATE ROLE agent_role NOLOGIN (idempotent via DO block check pg_roles)
  GRANT USAGE ON SCHEMA audit, hitl, budget TO agent_role
  GRANT INSERT, SELECT ON audit.actions, audit.outbox TO agent_role
  GRANT INSERT, SELECT, UPDATE(status, decided_at, decided_by, decision_json, escalated_to_id) ON hitl.approvals TO agent_role
  GRANT INSERT, UPDATE ON budget.executions TO agent_role
  REVOKE UPDATE, DELETE ON audit.actions FROM agent_role
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 04-02-01: SQL migrations 002 + 003 (with REVOKE) + 004 + 005</name>
  <files>infra/migrations/timescale/002_create_hitl_approvals.sql, infra/migrations/timescale/003_create_audit_actions.sql, infra/migrations/timescale/004_create_budget_executions.sql, infra/migrations/timescale/005_create_langgraph_checkpoints.sql, tests/integration/test_migrations_idempotent.py</files>
  <read_first>
    - infra/migrations/timescale/001_create_sensor_events.sql (entire file — exact template for DO $$ idempotent blocks + create_hypertable + add_retention_policy)
    - .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md lines 130-200 (D-55 + D-56 DDLs verbatim)
    - .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md lines 324-336 (D-60 budget.executions DDL)
    - .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md §12 (REVOKE pattern + outbox table + OQ1 agent_role resolution)
    - infra/migrations/timescale/migrate.py (Phase 3 runner — auto-discovers `[0-9][0-9][0-9]_*.sql` glob; no change needed)
  </read_first>
  <pattern_ref>infra/migrations/timescale/001_create_sensor_events.sql:14-65 (DO $$ idempotent + CREATE TABLE IF NOT EXISTS + create_hypertable if_not_exists + add_retention_policy if_not_exists)</pattern_ref>
  <pattern_ref>infra/migrations/timescale/migrate.py:67-72 (asyncpg statement_cache_size=0 for TimescaleDB)</pattern_ref>
  <threat_ref>T-04-Audit-Tamper, T-04-Outbox-Drop</threat_ref>
  <behavior>
    - Migration 002 creates schema hitl, table hitl.approvals matching D-55 DDL exactly, and partial index idx_approvals_tier_status WHERE status='pending'
    - Migration 003 creates schema audit, table audit.actions matching D-56 DDL, makes it a hypertable (30d chunks), adds 7y retention policy, creates audit.outbox, creates agent_role (NOLOGIN, idempotent via pg_roles check), GRANTs INSERT,SELECT to agent_role, REVOKEs UPDATE,DELETE from agent_role
    - Migration 004 creates schema budget, table budget.executions matching D-60 DDL with composite PK
    - Migration 005 creates schema langgraph only (tables created by Task 04-02-02 script)
    - All 4 migrations re-runnable: second run produces zero schema changes (idempotent)
    - DO $$ blocks guard every non-IF-NOT-EXISTS statement (ALTER, GRANT, REVOKE, CREATE ROLE)
  </behavior>
  <action>
    Create `002_create_hitl_approvals.sql` with header comment block (Source D-55 CONTEXT.md lines 131-150 + idempotent pattern from 001) + `CREATE SCHEMA IF NOT EXISTS hitl` + `CREATE TABLE IF NOT EXISTS hitl.approvals (...)` with all 12 columns and CHECK constraints from D-55 + `CREATE INDEX IF NOT EXISTS idx_approvals_tier_status ON hitl.approvals (tier, status, sla_deadline) WHERE status = 'pending'` + `CREATE INDEX IF NOT EXISTS idx_approvals_thread_id ON hitl.approvals (thread_id)`. Create `003_create_audit_actions.sql` with: header comment; `CREATE SCHEMA IF NOT EXISTS audit`; `CREATE EXTENSION IF NOT EXISTS pgcrypto` (for gen_random_uuid in audit + hitl); `CREATE TABLE IF NOT EXISTS audit.actions (id UUID DEFAULT gen_random_uuid(), ts TIMESTAMPTZ NOT NULL DEFAULT NOW(), action_id UUID NOT NULL, agent_id TEXT NOT NULL, thread_id TEXT NOT NULL, cluster TEXT NOT NULL, action_type TEXT NOT NULL, evidence_panel JSONB NOT NULL, decision TEXT NOT NULL CHECK (decision IN ('auto','hitl_operator','hitl_supervisor','hitl_manager','interlock_reject','rolled_back','timed_out','governor_alert','escalated')), decision_actor TEXT, motivation TEXT, budget_snapshot JSONB, approval_id UUID REFERENCES hitl.approvals(id), PRIMARY KEY (ts, id))` (PK must include partitioning column ts for hypertable). Add CHECK constraint: `CHECK (decision NOT LIKE 'hitl_%' OR (motivation IS NOT NULL AND char_length(motivation) > 0 AND approval_id IS NOT NULL))` (HITL-07 + D-56 audit dual-side). Add `SELECT create_hypertable('audit.actions', 'ts', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE)`. Add `SELECT add_retention_policy('audit.actions', INTERVAL '7 years', if_not_exists => TRUE)`. Add `CREATE INDEX IF NOT EXISTS idx_audit_thread_id_ts ON audit.actions (thread_id, ts DESC)` + `idx_audit_decision_ts ON audit.actions (decision, ts DESC)`. Then `CREATE TABLE IF NOT EXISTS audit.outbox (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), subject TEXT NOT NULL, payload_json JSONB NOT NULL, attempts INT NOT NULL DEFAULT 0, last_attempt_at TIMESTAMPTZ, next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())` + `CREATE INDEX IF NOT EXISTS idx_outbox_next_attempt ON audit.outbox (next_attempt_at) WHERE attempts < 10`. Then idempotent role creation: `DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='agent_role') THEN CREATE ROLE agent_role NOLOGIN; END IF; END $$;` Then DO $$ block granting USAGE on schemas audit, hitl, budget to agent_role; GRANT INSERT, SELECT ON audit.actions TO agent_role; GRANT INSERT, SELECT, UPDATE, DELETE ON audit.outbox TO agent_role; GRANT INSERT, SELECT ON hitl.approvals TO agent_role; GRANT UPDATE (status, decided_at, decided_by, decision_json, escalated_to_id) ON hitl.approvals TO agent_role; GRANT INSERT, UPDATE, SELECT ON budget.executions TO agent_role; REVOKE UPDATE, DELETE ON audit.actions FROM agent_role. All wrapped in `DO $$ BEGIN ... EXCEPTION WHEN OTHERS THEN RAISE NOTICE ... END $$;` so re-runs are non-fatal. Create `004_create_budget_executions.sql`: `CREATE SCHEMA IF NOT EXISTS budget` + `CREATE TABLE IF NOT EXISTS budget.executions (...)` with composite PRIMARY KEY (thread_id, agent_id) per D-60. Create `005_create_langgraph_checkpoints.sql`: header comment noting tables created via `scripts/langgraph-init.py` invoking `AsyncPostgresSaver.setup()` (Pitfall §2 from RESEARCH); body: `CREATE SCHEMA IF NOT EXISTS langgraph` (note: per RESEARCH §3 note, langgraph-checkpoint-postgres uses `public` schema not configurable in Python today, so 005 just leaves a placeholder schema and the comment documents that tables will appear under `public.checkpoints`, `public.checkpoint_blobs`, `public.checkpoint_migrations`). Write `tests/integration/test_migrations_idempotent.py` with `@pytest.mark.integration` test using testcontainers PostgreSQL+Timescale image `timescale/timescaledb:latest-pg15`: bring up container; run `python scripts/timescale-migrate.py` once, capture schema snapshot via `SELECT * FROM information_schema.tables WHERE table_schema IN ('hitl','audit','budget','langgraph') ORDER BY table_schema, table_name`; run again; assert snapshot identical; assert hitl.approvals, audit.actions, audit.outbox, budget.executions tables exist; assert audit.actions is in `timescaledb_information.hypertables`; assert retention policy exists via `_timescaledb_config.bgw_job WHERE proc_name='policy_retention'`; assert agent_role exists in pg_roles; assert REVOKE effective via `has_table_privilege('agent_role','audit.actions','UPDATE')` returns false.
  </action>
  <verify>
    <automated>cd "/media/federicocalo/D1/prj/Smart Factory Transformation" && grep -c "IF NOT EXISTS\|if_not_exists\|DO \$\$" infra/migrations/timescale/002_create_hitl_approvals.sql infra/migrations/timescale/003_create_audit_actions.sql infra/migrations/timescale/004_create_budget_executions.sql infra/migrations/timescale/005_create_langgraph_checkpoints.sql && grep -n "REVOKE UPDATE, DELETE ON audit.actions FROM agent_role" infra/migrations/timescale/003_create_audit_actions.sql</automated>
  </verify>
  <done>4 SQL files exist; each contains DO $$ idempotent blocks; 003 contains REVOKE UPDATE, DELETE; integration test file exists with testcontainers fixture</done>
  <commit_scope>feat(04-02-pg-migrations-01): add hitl/audit/budget/langgraph schemas + REVOKE + outbox + agent_role</commit_scope>
</task>

<task type="auto" tdd="true">
  <name>Task 04-02-02: langgraph-init script + Makefile target + integration test for audit immutability</name>
  <files>scripts/langgraph-init.py, tests/integration/test_audit_immutability.py, Makefile</files>
  <read_first>
    - infra/migrations/timescale/migrate.py (entire file — replicate argparse + asyncio.run + dry-run pattern)
    - scripts/timescale-migrate.py (Phase 3 wrapper around migrate.py — pattern reference)
    - .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md §3 (AsyncPostgresSaver.from_conn_string + saver.setup() pattern; Pitfall §2 autocommit + dict_row when manual conn passed)
    - Makefile (current targets — find migrate target for Phase 3 to extend)
    - services/ot-bridge/src/svc_ot_bridge/timescale_writer.py (asyncpg connect with statement_cache_size=0 + structlog patterns)
  </read_first>
  <pattern_ref>infra/migrations/timescale/migrate.py (argparse + asyncio.run + dry-run flag — replicate intero file's structure for langgraph-init.py)</pattern_ref>
  <pattern_ref>services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:74-91 (asyncpg lifecycle pattern)</pattern_ref>
  <threat_ref>T-04-Audit-Tamper</threat_ref>
  <behavior>
    - `python scripts/langgraph-init.py` exits 0 on first run, creates `public.checkpoints`, `public.checkpoint_blobs`, `public.checkpoint_migrations`
    - Second run exits 0 with no schema changes (AsyncPostgresSaver.setup is idempotent per langgraph 0.4+)
    - Script reads `TIMESCALE_DSN` env var; fails fast with KeyError if absent
    - `make migrate-phase4` target runs `python scripts/timescale-migrate.py` then `python scripts/langgraph-init.py` in sequence
    - `tests/integration/test_audit_immutability.py` connects as `agent_role` (via SET ROLE), inserts audit.actions row, attempts UPDATE → fails with permission denied; attempts DELETE → fails with permission denied; SELECT and INSERT succeed
  </behavior>
  <action>
    Create `scripts/langgraph-init.py`: shebang `#!/usr/bin/env python3`; argparse with `--dsn` (default `os.environ["TIMESCALE_DSN"]`) and `--dry-run`; imports `from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver` + `structlog` + `asyncio`. Function `async def bootstrap(dsn: str, dry_run: bool) -> int`: if dry_run, log and return 0; else `async with AsyncPostgresSaver.from_conn_string(dsn) as saver: await saver.setup()` then return 0. **W3 driver note (statement_cache_size=0 NOT required):** `langgraph-checkpoint-postgres>=3.1` ships `AsyncPostgresSaver` built on **psycopg3 (`psycopg[binary,pool]`)**, NOT asyncpg. The asyncpg-specific PgBouncer constraint requiring `statement_cache_size=0` to disable server-side prepared statements does NOT apply here — psycopg3 uses client-side prepared statements by default and is PgBouncer-transaction-mode-compatible without per-connection tuning. The script therefore takes no driver-tuning parameters; it simply invokes `from_conn_string` which the library configures internally. Document this in the script's module docstring so future readers do not 'helpfully' add an asyncpg pool override. main: `sys.exit(asyncio.run(bootstrap(args.dsn, args.dry_run)))`. Use structlog JSON renderer per ot-bridge/main.py pattern. Failure mode: any exception logs `langgraph_init_failed error=...` and exits 1. Add `[MIGRATION-PUSH]` reference in script docstring noting this script is BLOCKING for Wave 3 and 4. Update `Makefile`: add target `migrate-phase4: ## Apply Phase 4 migrations (002-005) + langgraph-init` body running `python scripts/timescale-migrate.py` (or `cd infra/migrations/timescale && python migrate.py`) then `python scripts/langgraph-init.py` (using $(TIMESCALE_DSN)). Make target accept `DRY_RUN=1` env to forward `--dry-run`. Mark target as `.PHONY`. Update existing `migrate` target (if present) to also include phase4 OR keep separate. Create `tests/integration/test_audit_immutability.py` with `@pytest.mark.integration` + `@pytest.mark.asyncio`: use testcontainers PG fixture; run migrations 001-005 + langgraph-init; connect via asyncpg as superuser; insert valid audit.actions row (with all required cols including evidence_panel JSONB stub + decision='auto' + approval_id=NULL); execute `SET LOCAL ROLE agent_role`; assert INSERT additional row via agent_role succeeds; assert `UPDATE audit.actions SET motivation='x' WHERE id=<row_id>` raises `asyncpg.exceptions.InsufficientPrivilegeError` (or check error message contains "permission denied"); assert `DELETE FROM audit.actions WHERE id=<row_id>` raises same; assert SELECT via agent_role returns the row. Add second test asserting `has_table_privilege('agent_role','audit.actions','SELECT,INSERT')` returns true (via `SELECT has_table_privilege(...)`).
  </action>
  <verify>
    <automated>cd "/media/federicocalo/D1/prj/Smart Factory Transformation" && python -c "import ast; ast.parse(open('scripts/langgraph-init.py').read()); print('ast ok')" && grep -n "AsyncPostgresSaver\.from_conn_string\|saver\.setup\(\)" scripts/langgraph-init.py && grep -nE "psycopg|psycopg3" scripts/langgraph-init.py && grep -n "migrate-phase4" Makefile</automated>
  </verify>
  <done>scripts/langgraph-init.py parses as valid Python with AsyncPostgresSaver.setup() call; Makefile has migrate-phase4 target; test_audit_immutability.py uses asyncpg SET ROLE + asserts permission denied on UPDATE+DELETE</done>
  <commit_scope>feat(04-02-pg-migrations-02): langgraph-init script + makefile target + audit immutability integration test</commit_scope>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 04-02-03 [BLOCKING]: Migration push — apply 002-005 + langgraph-init against running PG</name>
  <what-built>4 idempotent SQL migrations (002 hitl.approvals, 003 audit.actions + outbox + agent_role + REVOKE, 004 budget.executions, 005 langgraph schema) + scripts/langgraph-init.py creating checkpoint tables. All authored in Tasks 04-02-01 and 04-02-02.</what-built>
  <read_first>
    - .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (lines 132-184 — full D-55 + D-56 schemas to verify against)
    - infra/migrations/timescale/migrate.py (the runner being invoked)
    - Makefile migrate-phase4 target (just created)
  </read_first>
  <how-to-verify>
    1. Ensure dev stack is up: `make up` (Phase 1 target — brings up infra/compose/core.yml). Confirm postgres container reachable via `psql $TIMESCALE_DSN -c 'SELECT 1'`.
    2. Run migration push: `make migrate-phase4` (alternatively `python scripts/timescale-migrate.py && python scripts/langgraph-init.py`). Confirm exit code 0 and no Python tracebacks.
    3. Verify schemas exist: `psql $TIMESCALE_DSN -c "\dn"` lists `audit`, `hitl`, `budget`, `langgraph` (and `public`).
    4. Verify tables exist: `psql $TIMESCALE_DSN -c "\dt audit.*"` shows `actions` and `outbox`; `\dt hitl.*` shows `approvals`; `\dt budget.*` shows `executions`; `\dt public.checkpoint*` shows `checkpoints`, `checkpoint_blobs`, `checkpoint_migrations`.
    5. Verify hypertable: `psql $TIMESCALE_DSN -c "SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_schema='audit'"` returns `actions`.
    6. Verify retention policy: `psql $TIMESCALE_DSN -c "SELECT config FROM _timescaledb_config.bgw_job WHERE proc_name='policy_retention'"` includes hypertable_id matching audit.actions (drop_after = 7 years interval).
    7. Verify agent_role + REVOKE: `psql $TIMESCALE_DSN -c "SELECT has_table_privilege('agent_role','audit.actions','UPDATE')"` returns `f`; `SELECT has_table_privilege('agent_role','audit.actions','SELECT')` returns `t`.
    8. Re-run idempotency: `make migrate-phase4` again — exit code 0; `\dt` output identical to step 4.
    9. Run integration tests: `cd "$REPO_ROOT" && uv run pytest tests/integration/test_migrations_idempotent.py tests/integration/test_audit_immutability.py -m integration -v` — both pass.
    
    This task is BLOCKING — Wave 3 and Wave 4 integration tests (HITL cycle, governor, escalation, replay) all depend on these tables existing.
  </how-to-verify>
  <pattern_ref>infra/migrations/timescale/migrate.py (Phase 3 runner — auto-glob `[0-9][0-9][0-9]_*.sql`)</pattern_ref>
  <threat_ref>T-04-Audit-Tamper, T-04-Outbox-Drop</threat_ref>
  <resume-signal>Type "approved" after all 9 verification steps pass; describe any failures with exact psql error output.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| agent_role → audit.actions | Application connection (sft-agents + api-gateway) writes audit; DB-level REVOKE prevents mutation/deletion |
| migrate-script → DDL | Migration runner has full DDL privileges; runs only via Make target, never inline |
| audit row → audit.outbox | NATS publish failures spool to outbox; retry loop reads/writes outbox only |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-Audit-Tamper | Tampering/Repudiation | audit.actions DDL | mitigate | Migration 003 REVOKEs UPDATE,DELETE from agent_role; CHECK constraint enforces motivation+approval_id for hitl_*; test_audit_immutability.py verifies permission_denied via SET ROLE agent_role |
| T-04-Outbox-Drop | Repudiation | audit.outbox table | mitigate | Migration 003 creates audit.outbox + idx_outbox_next_attempt; retry loop (lands Plan 04-06) reads from outbox; this plan ships the table substrate |
| T-04-Audit-Tamper (SQL injection) | Tampering | migration runner | accept | migrate.py reads `.sql` files literally — no user input; threat surface is filesystem only, project-owned |
| T-04-Audit-Tamper (role drift) | Elevation | agent_role grants | mitigate | DO $$ block re-checks pg_roles + GRANT/REVOKE on every migration run (idempotent); Phase 11 will bind to real users via SealedSecrets |
</threat_model>

<verification>
- `make migrate-phase4` exits 0 on first run AND on second run (idempotency)
- `\dn` shows `audit`, `hitl`, `budget`, `langgraph` schemas
- `\dt audit.*` shows `actions` (hypertable) + `outbox`
- `SELECT has_table_privilege('agent_role','audit.actions','UPDATE')` returns false
- `SELECT has_table_privilege('agent_role','audit.actions','INSERT')` returns true
- Integration tests in tests/integration/test_migrations_idempotent.py and test_audit_immutability.py pass under `-m integration`
- Phase 3 migration `001_create_sensor_events.sql` still applies cleanly (no regression)
</verification>

<success_criteria>
- CORE-04 substrate ready: AsyncPostgresSaver.setup() has installed checkpoint tables
- CORE-08 substrate ready: audit.actions hypertable queryable by thread_id for episodic memory replay
- CORE-09 substrate ready: budget.executions UPSERT-able with composite PK
- HITL-05 enforced at DB level: REVOKE UPDATE,DELETE on audit.actions from agent_role verified by automated test
- HITL-04 substrate ready: hitl.approvals queryable by (tier, status, sla_deadline)
- OQ1 resolved: agent_role created in Phase 4 (NOLOGIN; Phase 11 binds login users)
- OQ5 resolved: single unified audit.outbox table
- Wave 3 + Wave 4 unblocked
</success_criteria>

<output>
Create `.planning/phases/04-core-agentic-runtime-hitl/04-02-SUMMARY.md` documenting:
- All 4 migration files + line counts
- agent_role privileges snapshot (output of `\dp audit.*` and `\dp hitl.*`)
- Idempotency proof (second run output)
- Any drift from CONTEXT.md DDLs (should be none)
</output>