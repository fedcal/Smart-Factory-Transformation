-- Source: D-60 budget executions (CONTEXT.md §D-60 lines 324-336)
-- File: infra/migrations/timescale/004_create_budget_executions.sql
-- Phase 4 — Plan 04-02
-- Idempotent: safe to re-run.
-- Substrate for CORE-09 (per-thread/per-agent budget tracking, UPSERT pattern).
--
-- Composite PRIMARY KEY (thread_id, agent_id) supports:
--   INSERT ... ON CONFLICT (thread_id, agent_id) DO UPDATE SET tokens_total = ..., cost_usd = ...
-- which is the hot-path executed once per LangGraph node step in Plan 04-06.

CREATE SCHEMA IF NOT EXISTS budget;

CREATE TABLE IF NOT EXISTS budget.executions (
  thread_id     TEXT             NOT NULL,
  agent_id      TEXT             NOT NULL,
  tokens_total  INT              NOT NULL DEFAULT 0,
  cost_usd      DOUBLE PRECISION NOT NULL DEFAULT 0,
  duration_ms   INT              NOT NULL DEFAULT 0,
  step_count    INT              NOT NULL DEFAULT 0,
  started_at    TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
  last_step_at  TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
  PRIMARY KEY (thread_id, agent_id)
);

-- Grant agent_role privileges here (003 cannot, because budget schema may not yet exist
-- if migrations run out-of-order in tests). DO $$ guards if agent_role doesn't yet exist.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_role') THEN
    GRANT USAGE ON SCHEMA budget TO agent_role;
    GRANT INSERT, SELECT, UPDATE ON budget.executions TO agent_role;
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE '004_create_budget_executions.sql GRANT block: %', SQLERRM;
END $$;
