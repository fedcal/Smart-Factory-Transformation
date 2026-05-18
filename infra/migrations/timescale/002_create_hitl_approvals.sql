-- Source: D-55 HITL approvals (CONTEXT.md §D-55 lines 131-150)
-- File: infra/migrations/timescale/002_create_hitl_approvals.sql
-- Phase 4 — Plan 04-02
-- Idempotent: safe to run multiple times (CREATE … IF NOT EXISTS + DO $$ guards).
-- Substrate for HITL-04 (approval queue) and Plan 04-06 (HITL cycle implementation).
--
-- DDL drift policy: this file is LOCKED to D-55 verbatim shape.
-- Any change requires updating CONTEXT.md §D-55 first.

-- gen_random_uuid() lives in pgcrypto; ensure extension is available before defaults reference it.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS hitl;

CREATE TABLE IF NOT EXISTS hitl.approvals (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id        TEXT        NOT NULL,
  thread_id       TEXT        NOT NULL,
  tier            TEXT        NOT NULL CHECK (tier IN ('operator','supervisor','manager','safety_interlock')),
  action_type     TEXT        NOT NULL,
  payload_json    JSONB       NOT NULL,
  status          TEXT        NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending','approved','rejected','escalated','timed_out')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sla_deadline    TIMESTAMPTZ NOT NULL,
  decided_at      TIMESTAMPTZ,
  decided_by      TEXT,
  decision_json   JSONB,
  escalated_to_id UUID REFERENCES hitl.approvals(id)
);

-- Partial index covers the dominant query in Plan 04-06: scan pending approvals by tier ordered by SLA.
-- WHERE clause keeps the index small (only `pending` rows; decided rows drop out automatically).
CREATE INDEX IF NOT EXISTS idx_approvals_tier_status
  ON hitl.approvals (tier, status, sla_deadline)
  WHERE status = 'pending';

-- Episodic replay (CORE-08) queries audit.actions JOIN hitl.approvals on thread_id.
CREATE INDEX IF NOT EXISTS idx_approvals_thread_id
  ON hitl.approvals (thread_id);
