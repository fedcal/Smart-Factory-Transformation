-- Source: D-49 + docs.timescale.com/api/latest/compression/
-- File: infra/migrations/timescale/001_create_sensor_events.sql
-- Phase 3 — Plan 03-05
-- Idempotent: safe to run multiple times.
-- NOTE: Using legacy compression API (TimescaleDB 2.18.x); migration to columnstore (hypercore)
--       deferred to Phase 11 if/when hypercore semantics settles (Pitfall 2).
--
-- OQ2 Resolution: SINGLE hypertable with `source` column to distinguish
--   'live'            — real-time OPC-UA events from sim-textile via ot-bridge
--   'replay_cmapss'   — NASA C-MAPSS turbofan dataset replay (Phase 3 Plan 03-07)
--   'replay_uci'      — UCI Manufacturing dataset replay (Phase 3 Plan 03-07)
-- No separate replay hypertable in Phase 3.

CREATE TABLE IF NOT EXISTS sensor_events (
  asset_id      TEXT NOT NULL,
  tag_id        TEXT NOT NULL,
  timestamp_utc TIMESTAMPTZ NOT NULL,
  value         DOUBLE PRECISION,
  unit          TEXT,
  quality_code  SMALLINT,
  source        TEXT NOT NULL DEFAULT 'live'  -- 'live' | 'replay_cmapss' | 'replay_uci' (OQ2)
);

-- Create hypertable partitioned by timestamp_utc with 1-day chunks (D-49)
-- if_not_exists => TRUE makes this idempotent on re-run
SELECT create_hypertable(
  'sensor_events',
  'timestamp_utc',
  chunk_time_interval => INTERVAL '1 day',
  if_not_exists => TRUE
);

-- Compression config: enable only if not already enabled (idempotent via DO block)
-- segmentby=(asset_id, tag_id) for efficient per-asset/per-tag decompression
-- orderby=(timestamp_utc DESC) matches typical "latest N readings" query pattern
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM timescaledb_information.hypertables
    WHERE hypertable_name = 'sensor_events' AND compression_enabled = true
  ) THEN
    ALTER TABLE sensor_events SET (
      timescaledb.compress,
      timescaledb.compress_segmentby = 'asset_id, tag_id',
      timescaledb.compress_orderby = 'timestamp_utc DESC'
    );
  END IF;
END $$;

-- Compression policy: compress chunks older than 7 days (D-49 hot/warm tier)
-- if_not_exists => TRUE makes this idempotent on re-run
SELECT add_compression_policy(
  'sensor_events',
  compress_after => INTERVAL '7 days',
  if_not_exists => TRUE
);

-- Retention policy: drop chunks older than 90 days (D-49; A-007 dataset >= 90d coverage)
-- if_not_exists => TRUE makes this idempotent on re-run
-- NOTE: Audit tables (agent.actions, hitl.decisions) will have separate 7-year retention (Phase 11)
SELECT add_retention_policy(
  'sensor_events',
  drop_after => INTERVAL '90 days',
  if_not_exists => TRUE
);

-- Composite indexes for typical agent query patterns (Phase 4 agents):
--   idx_sensor_events_asset_time — per-asset time-ordered queries (AnomalyDetector, PredictiveMaintenance)
--   idx_sensor_events_tag_time   — per-tag time-ordered queries (cross-asset tag analytics)
CREATE INDEX IF NOT EXISTS idx_sensor_events_asset_time
  ON sensor_events (asset_id, timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_events_tag_time
  ON sensor_events (tag_id, timestamp_utc DESC);
