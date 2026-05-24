-- Migration 011: create scm.* schema — Supply Chain & Economics data foundation.
-- File: infra/migrations/timescale/011_create_scm_schema.sql
-- Phase 9 — Plan 09-00a
-- Idempotent: safe to re-run (all DDL uses IF NOT EXISTS).
--
-- D-DATA: New synthetic scm.* TimescaleDB schema for the four Supply Chain &
-- Economics agents (InventoryManager, EnergyOptimizer, CostAnalyzer,
-- DemandForecaster). NOT derived from existing tables — standalone synthetic
-- Mantis Textile Group data source.
--
-- Tables introduced:
--   scm.sku_master          — reference table: SKU definitions + reorder parameters
--   scm.inventory_levels    — TimescaleDB hypertable: stock levels per SKU per location
--   scm.energy_readings     — TimescaleDB hypertable: energy consumption per process/shift
--   scm.historical_orders   — relational: historical order records for DemandForecaster
--   scm.enpi_baseline       — reference: ISO 50001 EnPI kWh/kg targets per process
--
-- Hypertables: scm.inventory_levels (ts), scm.energy_readings (ts).
--
-- CHECK constraints:
--   scm.sku_master.category IN ('raw_yarn','accessory','spare_part','fabric')
--   scm.energy_readings.process IN ('dyeing','finishing','spinning','weaving','other')
--
-- Seed data is NOT included here — seeding is done in a separate non-numbered
-- file (infra/migrations/timescale/seed/scm_mantis_seed.sql, Plan 09-01).
--
-- Source: 09-RESEARCH.md Pattern 5 (verbatim scm.* DDL) + IF NOT EXISTS idempotency
--         pattern from 001_create_sensor_events.sql and 008_create_downtime_events.sql.

CREATE SCHEMA IF NOT EXISTS scm;

-- ──────────────────────────────────────────────────────────────────────────────
-- scm.sku_master — SKU reference table
-- Defines every tracked SKU: raw yarn, accessories, spare parts, fabric.
-- Used by InventoryManager (reorder logic) and DemandForecaster (grouping).
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scm.sku_master (
    sku_id          TEXT PRIMARY KEY,
    sku_name        TEXT NOT NULL,
    category        TEXT NOT NULL CHECK (category IN ('raw_yarn','accessory','spare_part','fabric')),
    unit            TEXT NOT NULL,                          -- 'kg', 'pcs', 'roll'
    reorder_point   NUMERIC(10,2) NOT NULL,                -- reorder threshold quantity
    reorder_qty     NUMERIC(10,2) NOT NULL,                -- quantity to order on reorder
    lead_time_days  INTEGER NOT NULL DEFAULT 7,            -- supplier lead time in days
    unit_cost_eur   NUMERIC(10,4) NOT NULL,                -- cost per unit in EUR
    sku_group       TEXT NOT NULL DEFAULT 'default'        -- grouping key for DemandForecaster
);

-- ──────────────────────────────────────────────────────────────────────────────
-- scm.inventory_levels — stock level readings (TimescaleDB hypertable)
-- InventoryManager queries this to detect when quantity < reorder_point.
-- Partition key: ts (TIMESTAMPTZ).
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scm.inventory_levels (
    ts          TIMESTAMPTZ NOT NULL,
    sku_id      TEXT NOT NULL REFERENCES scm.sku_master(sku_id),
    quantity    NUMERIC(12,3) NOT NULL,
    location    TEXT NOT NULL DEFAULT 'main_warehouse',
    source      TEXT NOT NULL DEFAULT 'manual'
);

-- Convert to TimescaleDB hypertable (idempotent via if_not_exists).
SELECT create_hypertable('scm.inventory_levels', 'ts', if_not_exists => TRUE);

-- Index for efficient "latest level per SKU" queries (DISTINCT ON pattern).
CREATE INDEX IF NOT EXISTS idx_inv_levels_sku_ts
    ON scm.inventory_levels (sku_id, ts DESC);

-- ──────────────────────────────────────────────────────────────────────────────
-- scm.energy_readings — energy consumption per asset/process/shift (TimescaleDB hypertable)
-- EnergyOptimizer reads this to compute kWh/kg EnPI against ISO 50001 baseline.
-- Partition key: ts (TIMESTAMPTZ).
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scm.energy_readings (
    ts              TIMESTAMPTZ NOT NULL,
    asset_id        TEXT NOT NULL,
    process         TEXT NOT NULL CHECK (process IN ('dyeing','finishing','spinning','weaving','other')),
    kwh             NUMERIC(10,4) NOT NULL,
    kg_processed    NUMERIC(10,4),                          -- nullable when measurement unavailable
    shift           TEXT NOT NULL DEFAULT 'day',            -- 'day', 'evening', 'night'
    is_peak_hour    BOOLEAN NOT NULL DEFAULT FALSE
);

-- Convert to TimescaleDB hypertable (idempotent via if_not_exists).
SELECT create_hypertable('scm.energy_readings', 'ts', if_not_exists => TRUE);

-- Index for per-asset/per-process queries (EnergyOptimizer rolling window).
CREATE INDEX IF NOT EXISTS idx_energy_asset_ts
    ON scm.energy_readings (asset_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_energy_process_ts
    ON scm.energy_readings (process, ts DESC);

-- ──────────────────────────────────────────────────────────────────────────────
-- scm.historical_orders — order history (relational with timestamp)
-- DemandForecaster reads this to build monthly demand series per sku_group.
-- NOT a hypertable — order frequency is too low for time-series partitioning.
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scm.historical_orders (
    order_id        TEXT PRIMARY KEY,
    sku_id          TEXT NOT NULL REFERENCES scm.sku_master(sku_id),
    sku_group       TEXT NOT NULL,
    order_date      TIMESTAMPTZ NOT NULL,
    delivery_date   TIMESTAMPTZ,                            -- nullable: scheduled future delivery
    quantity_kg     NUMERIC(12,3) NOT NULL,
    unit_price_eur  NUMERIC(10,4) NOT NULL,
    customer_type   TEXT NOT NULL DEFAULT 'b2b',
    season          TEXT                                    -- 'spring','summer','autumn','winter'
);

-- Index for DemandForecaster time-range queries grouped by sku_group.
CREATE INDEX IF NOT EXISTS idx_hist_orders_sku_group_date
    ON scm.historical_orders (sku_group, order_date DESC);

CREATE INDEX IF NOT EXISTS idx_hist_orders_sku_id_date
    ON scm.historical_orders (sku_id, order_date DESC);

-- ──────────────────────────────────────────────────────────────────────────────
-- scm.enpi_baseline — ISO 50001 Energy Performance Indicator baseline per process
-- EnergyOptimizer reads this to compare actual kWh/kg against target.
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scm.enpi_baseline (
    process                 TEXT PRIMARY KEY,
    kwh_per_kg_target       NUMERIC(8,4) NOT NULL,         -- ISO 50001 target kWh/kg
    kwh_per_kg_actual_ytd   NUMERIC(8,4),                  -- YTD actual (nullable until computed)
    baseline_year           INTEGER NOT NULL DEFAULT 2024,
    notes                   TEXT
);
