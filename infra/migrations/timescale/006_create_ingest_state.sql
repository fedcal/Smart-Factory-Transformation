-- Migration 006: knowledge.ingest_state — track ingest state per source_uri for incremental reindex (D-68, KNW-07, TRN-01 scaffold)
-- File: infra/migrations/timescale/006_create_ingest_state.sql
-- Phase 5 — Plan 05-06
-- Idempotent: safe to re-run.
--
-- Schema (D-68 LOCKED — 05-CONTEXT.md lines 459-471):
--   knowledge.ingest_state tracks which source_uri has been indexed at which
--   content_hash + version, so the indexer can early-exit on unchanged inputs
--   (D-68 incremental reindex invariant) and surface stale rows (TRN-01).
--
-- The agent_role GRANT is conditional on the role pre-existing (mirrors the
-- pattern in 004_create_budget_executions.sql lines 28-37) so this migration
-- can run cleanly in dev / testcontainer environments where roles are not
-- yet provisioned.

CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.ingest_state (
  source_uri    TEXT        PRIMARY KEY,
  content_hash  TEXT        NOT NULL,
  version       TEXT        NOT NULL,
  indexed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  chunk_count   INT         NOT NULL,
  collection    TEXT        NOT NULL,
  acl_level     TEXT        NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ingest_state_version
  ON knowledge.ingest_state (version);

-- Conditional GRANT to agent_role — mirror 004 lines 28-37 exactly.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_role') THEN
    GRANT USAGE ON SCHEMA knowledge TO agent_role;
    GRANT INSERT, SELECT, UPDATE ON knowledge.ingest_state TO agent_role;
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE '006_create_ingest_state.sql GRANT block: %', SQLERRM;
END $$;
