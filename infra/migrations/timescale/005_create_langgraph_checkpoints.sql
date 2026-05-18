-- File: infra/migrations/timescale/005_create_langgraph_checkpoints.sql
-- Phase 4 — Plan 04-02
-- Idempotent: only CREATE SCHEMA IF NOT EXISTS.
--
-- IMPORTANT — schema vs. tables (Pitfall §2 in 04-RESEARCH.md):
--   The actual LangGraph checkpoint tables (`checkpoints`, `checkpoint_blobs`,
--   `checkpoint_migrations`) are created by `await AsyncPostgresSaver.setup()`
--   in `scripts/langgraph-init.py`. The Python library
--   `langgraph-checkpoint-postgres>=3.1` currently creates these tables in the
--   `public` schema (not configurable in Python today — RESEARCH §3 note).
--
--   This migration therefore only ensures the `langgraph` schema exists as a
--   namespace placeholder so future versions of the library (or a manual
--   migration to a non-public schema) have a stable home. Today, do not
--   expect tables here — look in `public.checkpoints` instead.
--
-- See `scripts/langgraph-init.py` for the actual table bootstrap (idempotent).

CREATE SCHEMA IF NOT EXISTS langgraph;
