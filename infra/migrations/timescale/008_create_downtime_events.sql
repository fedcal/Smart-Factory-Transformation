-- Migration 008: create maintenance.downtime_events hypertable + oee_hourly CAGG
-- File: infra/migrations/timescale/008_create_downtime_events.sql
-- Phase 7 — Plan 07-05 (D-DA-01 + D-DA-03; MNT-04 data foundation)
-- Idempotent: safe to re-run.
--
-- Source: 07-PATTERNS.md Section 9 (lines 393-422) verbatim SQL skeleton +
--         07-RESEARCH.md Pattern 7 (TimescaleDB continuous aggregate) +
--         Pitfall 4 (retention policy > CAGG start_offset — refresh policy
--         start_offset=2h fits within sensor_events 90d retention window).
--
-- Schema introduced:
--   maintenance.downtime_events  — TimescaleDB hypertable (time = timestamp)
--   maintenance.oee_hourly        — continuous aggregate (1h bucket) for OEE.A
--
-- Notes on TimescaleDB version (target 2.18.0-pg16 per infra/compose/core.yml):
--   - `create_hypertable(..., if_not_exists => TRUE)` is natively idempotent.
--   - `CREATE MATERIALIZED VIEW IF NOT EXISTS ... WITH (timescaledb.continuous)`
--     is supported as of TimescaleDB 2.10+; verified on 2.18.0.
--   - `add_continuous_aggregate_policy(..., if_not_exists => TRUE)` is the
--     native idempotency flag (per TimescaleDB API docs).
--
-- DowntimeEvent payload (D-DA-01) columns:
--   event_id       UUID PK (gen_random_uuid() — pgcrypto bundled with pg14+)
--   asset_id       TEXT NOT NULL
--   reason_code    TEXT NOT NULL  (drawn from failure_modes.yaml maintenance
--                                  taxonomy — MNT-05 / D-MNT-TAX, validated
--                                  in-app, no FK to avoid coupling)
--   duration_min   INTEGER NOT NULL CHECK (duration_min >= 0)
--   severity       TEXT NOT NULL CHECK (severity IN ('minor','major','critical'))
--   work_order_id  TEXT NULL
--   dye_lot_id     TEXT NULL
--   source         TEXT NOT NULL DEFAULT 'simulator'
--   timestamp      TIMESTAMPTZ NOT NULL  (hypertable partition key)
--   inserted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
--
-- CAGG `maintenance.oee_hourly` columns:
--   asset_id, hour_bucket, total_downtime_min, event_count
-- Refresh policy: start_offset='3 hours', end_offset='5 minutes', schedule='5 minutes'.
-- (start_offset is 3h to satisfy the TimescaleDB rule
--  (start_offset - end_offset) >= 2 * bucket_width = 2h).
-- This satisfies Pitfall 4 (start_offset << sensor_events retention=90 days).

CREATE SCHEMA IF NOT EXISTS maintenance;

CREATE TABLE IF NOT EXISTS maintenance.downtime_events (
  event_id      UUID NOT NULL DEFAULT gen_random_uuid(),
  asset_id      TEXT NOT NULL,
  reason_code   TEXT NOT NULL,
  duration_min  INTEGER NOT NULL CHECK (duration_min >= 0),
  severity      TEXT NOT NULL CHECK (severity IN ('minor','major','critical')),
  work_order_id TEXT NULL,
  dye_lot_id    TEXT NULL,
  source        TEXT NOT NULL DEFAULT 'simulator',
  timestamp     TIMESTAMPTZ NOT NULL,
  inserted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (event_id, timestamp)
);

-- Convert to hypertable partitioned by `timestamp` (idempotent via if_not_exists).
-- TimescaleDB constraint: hypertable PK must include the time column — hence the
-- composite (event_id, timestamp) PK above. Unique-event-id semantics is preserved
-- by application code (UUIDv4 collision negligible).
SELECT create_hypertable(
  'maintenance.downtime_events',
  'timestamp',
  if_not_exists => TRUE
);

-- Composite indexes for Pareto + per-asset OEE queries (07-09 DowntimeAnalyzer).
CREATE INDEX IF NOT EXISTS idx_downtime_asset_time
  ON maintenance.downtime_events (asset_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_downtime_reason_time
  ON maintenance.downtime_events (reason_code, timestamp DESC);

-- Continuous aggregate: 1-hour OEE.A roll-up per asset.
-- The view name `oee_hourly` matches D-DA-03; the materialization hypertable is
-- created implicitly by TimescaleDB. WITH NO DATA avoids long synchronous refresh
-- at migration time; the refresh policy below schedules incremental refresh.
CREATE MATERIALIZED VIEW IF NOT EXISTS maintenance.oee_hourly
  WITH (timescaledb.continuous) AS
SELECT
  asset_id,
  time_bucket(INTERVAL '1 hour', timestamp) AS hour_bucket,
  SUM(duration_min)::BIGINT AS total_downtime_min,
  COUNT(*)::BIGINT AS event_count
FROM maintenance.downtime_events
GROUP BY asset_id, hour_bucket
WITH NO DATA;

-- Continuous aggregate refresh policy (D-DA-03 + Pitfall 4):
--   start_offset = INTERVAL '3 hours' — window of unmaterialized data to refresh.
--                                       TimescaleDB requires
--                                       (start_offset - end_offset) >= 2 * bucket_width.
--                                       With 1h bucket + 5min end_offset, start must
--                                       exceed 2h5min — 3h leaves safety margin.
--   end_offset   = INTERVAL '5 minutes' — stay 5min behind real-time to avoid
--                                         races with in-flight inserts
--   schedule_interval = INTERVAL '5 minutes' — run every 5min
-- Native idempotency via if_not_exists.
-- Pitfall 4 (07-RESEARCH): start_offset (3h) is well within sensor_events 90d
-- retention window — no risk of refreshing dropped chunks.
SELECT add_continuous_aggregate_policy(
  'maintenance.oee_hourly',
  start_offset => INTERVAL '3 hours',
  end_offset => INTERVAL '5 minutes',
  schedule_interval => INTERVAL '5 minutes',
  if_not_exists => TRUE
);
