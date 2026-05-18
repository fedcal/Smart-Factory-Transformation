-- Source: D-56 audit hypertable + OQ5 unified outbox + OQ1 agent_role resolution
-- File: infra/migrations/timescale/003_create_audit_actions.sql
-- Phase 4 — Plan 04-02
-- Idempotent: CREATE … IF NOT EXISTS / DO $$ guards / if_not_exists policy flags.
--
-- HITL-05 enforcement: REVOKE UPDATE, DELETE on audit.actions from agent_role.
-- Mechanically prevents any app-tier code path from mutating audit history
-- (T-04-Audit-Tamper mitigation — verified by tests/integration/test_audit_immutability.py).
--
-- OQ1 resolution: agent_role created NOLOGIN here in Phase 4. Phase 11 binds
-- login users to it via SealedSecrets / IRSA.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS audit;

-- ---------------------------------------------------------------------------
-- audit.actions: append-only forensic record (D-56)
-- ---------------------------------------------------------------------------
-- PK must include the time partitioning column `ts` per TimescaleDB requirement.
-- Dual-side HITL constraint (D-56 + HITL-07): when decision is a hitl_* tier,
-- motivation AND approval_id MUST be present. When decision='auto', approval_id IS NULL.
CREATE TABLE IF NOT EXISTS audit.actions (
  id               UUID        NOT NULL DEFAULT gen_random_uuid(),
  ts               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  action_id        UUID        NOT NULL,
  agent_id         TEXT        NOT NULL,
  thread_id        TEXT        NOT NULL,
  cluster          TEXT        NOT NULL,
  action_type      TEXT        NOT NULL,
  evidence_panel   JSONB       NOT NULL,
  decision         TEXT        NOT NULL CHECK (
                     decision IN (
                       'auto',
                       'hitl_operator',
                       'hitl_supervisor',
                       'hitl_manager',
                       'interlock_reject',
                       'rolled_back',
                       'timed_out',
                       'governor_alert',
                       'escalated'
                     )
                   ),
  decision_actor   TEXT,
  motivation       TEXT,
  budget_snapshot  JSONB,
  approval_id      UUID REFERENCES hitl.approvals(id),
  PRIMARY KEY (ts, id),
  CONSTRAINT audit_actions_hitl_motivation_chk CHECK (
    decision NOT LIKE 'hitl_%'
    OR (
      motivation  IS NOT NULL
      AND char_length(motivation) > 0
      AND approval_id IS NOT NULL
    )
  )
);

-- Convert to hypertable with 30-day chunks (D-56). if_not_exists makes re-runs no-ops.
SELECT create_hypertable(
  'audit.actions',
  'ts',
  chunk_time_interval => INTERVAL '30 days',
  if_not_exists       => TRUE
);

-- 7-year retention (regulatory floor for audit/forensic data).
SELECT add_retention_policy(
  'audit.actions',
  drop_after    => INTERVAL '7 years',
  if_not_exists => TRUE
);

-- Episodic replay (CORE-08): "all actions for thread X newest-first".
CREATE INDEX IF NOT EXISTS idx_audit_thread_id_ts
  ON audit.actions (thread_id, ts DESC);

-- Governor / alert review: "all governor_alert / interlock_reject newest-first".
CREATE INDEX IF NOT EXISTS idx_audit_decision_ts
  ON audit.actions (decision, ts DESC);

-- ---------------------------------------------------------------------------
-- audit.outbox: unified subject+payload retry queue (OQ5 resolution)
-- ---------------------------------------------------------------------------
-- Backs the NATS publish retry loop (lands in Plan 04-06). Single table with
-- `subject TEXT` is the OQ5 chosen design (vs per-subject tables).
CREATE TABLE IF NOT EXISTS audit.outbox (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  subject         TEXT        NOT NULL,
  payload_json    JSONB       NOT NULL,
  attempts        INT         NOT NULL DEFAULT 0,
  last_attempt_at TIMESTAMPTZ,
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partial index: retry loop scans only rows still eligible (attempts < 10) ordered by next_attempt_at.
CREATE INDEX IF NOT EXISTS idx_outbox_next_attempt
  ON audit.outbox (next_attempt_at)
  WHERE attempts < 10;

-- ---------------------------------------------------------------------------
-- agent_role: idempotent creation (OQ1 — Phase 4 creates NOLOGIN)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_role') THEN
    CREATE ROLE agent_role NOLOGIN;
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- Privilege grants for agent_role + REVOKE on audit.actions (HITL-05 enforcement)
-- ---------------------------------------------------------------------------
-- Wrapped in DO $$ so GRANT/REVOKE statements that reference cross-schema objects
-- don't abort the migration if a target schema/table is unexpectedly missing on re-run.
DO $$
BEGIN
  -- USAGE on each schema (required before any object-level grant)
  GRANT USAGE ON SCHEMA audit  TO agent_role;
  GRANT USAGE ON SCHEMA hitl   TO agent_role;
  -- budget schema may not yet exist on first apply of 003 if executed before 004; guard it.
  IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'budget') THEN
    GRANT USAGE ON SCHEMA budget TO agent_role;
  END IF;

  -- audit.actions: INSERT + SELECT only (no UPDATE, no DELETE — T-04-Audit-Tamper mitigation)
  GRANT INSERT, SELECT ON audit.actions TO agent_role;

  -- audit.outbox: app code reads, writes, and updates retry counters
  GRANT INSERT, SELECT, UPDATE, DELETE ON audit.outbox TO agent_role;

  -- hitl.approvals: INSERT new approvals + SELECT to poll; UPDATE only the decision columns
  GRANT INSERT, SELECT ON hitl.approvals TO agent_role;
  GRANT UPDATE (status, decided_at, decided_by, decision_json, escalated_to_id)
    ON hitl.approvals TO agent_role;

  -- budget.executions: INSERT, SELECT, UPDATE — applied only when budget schema exists
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'budget' AND table_name = 'executions'
  ) THEN
    GRANT INSERT, SELECT, UPDATE ON budget.executions TO agent_role;
  END IF;

  -- HITL-05 hard enforcement: revoke any UPDATE/DELETE on audit.actions
  -- (Defense-in-depth — never granted above, but explicit REVOKE survives
  -- accidental future grants made manually.)
  REVOKE UPDATE, DELETE ON audit.actions FROM agent_role;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE '003_create_audit_actions.sql GRANT/REVOKE block: %', SQLERRM;
END $$;
