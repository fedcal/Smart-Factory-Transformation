-- =============================================================================
-- DATI SINTETICI - SOLO PER SVILUPPO E TEST
-- Questo file contiene dati sintetici generati per la dimostrazione del
-- sistema Mantis Textile Group. I valori NON provengono da dati aziendali reali
-- e NON devono essere usati in produzione.
--
-- SYNTHETIC DATA - DEV/TEST ONLY
-- This file contains SYNTHETIC data generated for the Mantis Textile Group
-- demonstration. Values do NOT originate from real company data and MUST NOT
-- be used in production environments.
--
-- File: infra/migrations/timescale/seed/scm_mantis_seed.sql
-- Phase 9 — Plan 09-01 (SCM-05: Mantis synthetic dataset)
--
-- NON-NUMBERED SEED FILE: this file must NOT match the `[0-9][0-9][0-9]_*.sql`
-- migration glob so numbered migrations remain idempotent. Apply manually or
-- via the seed runner in dev/test only.
--
-- Re-run safety:
--   scm.sku_master, scm.enpi_baseline, scm.historical_orders: ON CONFLICT DO NOTHING
--     (these tables have PRIMARY KEY constraints — idempotent).
--   scm.inventory_levels, scm.energy_readings: guarded DELETE before INSERT
--     (TimescaleDB hypertables without PK — ON CONFLICT without a conflict target
--     is a no-op, so re-runs would duplicate rows without the DELETE guards below).
-- Tables populated:
--   scm.sku_master          (6 SKUs: yarn x2, dye, spare, fabric x2)
--   scm.enpi_baseline       (dyeing + finishing ISO 50001 EnPI)
--   scm.inventory_levels    (recent snapshot; >=1 row below reorder_point)
--   scm.energy_readings     (dyeing + finishing readings; mix peak/off-peak)
--   scm.historical_orders   (>=18 months, jersey ~12000kg/mo, twill ~8000kg/mo)
-- =============================================================================

-- ──────────────────────────────────────────────────────────────────────────────
-- 1. scm.sku_master — 6 SKUs realistici per Mantis Textile Group (SINTETICI)
-- ──────────────────────────────────────────────────────────────────────────────
INSERT INTO scm.sku_master
    (sku_id, sku_name, category, unit, reorder_point, reorder_qty,
     lead_time_days, unit_cost_eur, sku_group)
VALUES
    -- Filati (raw_yarn)
    ('SKU-YARN-NE20-BLU', 'Filato Ne20 Blu cotone pettinato',
     'raw_yarn', 'kg', 850.00, 2000.00, 7, 3.2000, 'yarn'),
    ('SKU-YARN-NE30-BIA', 'Filato Ne30 Bianco cotone pettinato',
     'raw_yarn', 'kg', 1200.00, 3000.00, 7, 2.8500, 'yarn'),
    -- Colorante (accessory)
    ('SKU-DYE-REACT-BLU', 'Colorante Reattivo Blu navale 2G',
     'accessory', 'kg', 50.00, 150.00, 14, 28.5000, 'dye'),
    -- Ricambio (spare_part)
    ('SKU-SPARE-NEEDLE-L', 'Aghi telaio rapier formato Large',
     'spare_part', 'pcs', 200.00, 500.00, 21, 0.8500, 'spare'),
    -- Tessuti finiti (fabric) — usati per DemandForecaster grouping
    ('SKU-FAB-JERSEY-BLU', 'Jersey Blu indaco 140gsm — tela di maglia',
     'fabric', 'kg', 500.00, 1500.00, 5, 8.4000, 'jersey'),
    ('SKU-FAB-TWILL-GRY', 'Twill Grigio antracite 180gsm — armatura diagonale',
     'fabric', 'kg', 300.00, 900.00, 5, 10.2000, 'twill')
ON CONFLICT (sku_id) DO NOTHING;


-- ──────────────────────────────────────────────────────────────────────────────
-- 2. scm.enpi_baseline — ISO 50001 EnPI kWh/kg per Mantis (SINTETICO)
--    Tintoria (dyeing): 8% sopra baseline (YTD 4.12 vs target 3.80)
--    Finissaggio (finishing): entro baseline (YTD 2.18 vs target 2.20)
-- ──────────────────────────────────────────────────────────────────────────────
INSERT INTO scm.enpi_baseline
    (process, kwh_per_kg_target, kwh_per_kg_actual_ytd, baseline_year, notes)
VALUES
    ('dyeing',    3.8000, 4.1200, 2024,
     'SINTETICO — Tintoria Mantis: 4 vasche 500kg, 2 cicli/giorno. '
     'YTD 2024 superiore al target del 8.4%. Opportunita ottimizzazione '
     'schedule energy-off-peak.'),
    ('finishing', 2.2000, 2.1800, 2024,
     'SINTETICO — Finissaggio Mantis: 2 stentatoi 1200kg/h. '
     'YTD 2024 entro baseline (-0.9%). Processo efficiente.'),
    ('spinning',  4.5000, 4.6500, 2024,
     'SINTETICO — Filatura Mantis: 12 telai rapier 850kg/turno. '
     'YTD 2024 superiore al target del 3.3%.'),
    ('weaving',   1.8000, 1.7500, 2024,
     'SINTETICO — Tessitura Mantis: consumo energia ridotto. '
     'YTD 2024 entro baseline.')
ON CONFLICT (process) DO NOTHING;


-- ──────────────────────────────────────────────────────────────────────────────
-- 3. scm.inventory_levels — Snapshot inventario recente (SINTETICO)
--    Include >=1 riga SOTTO il reorder_point per InventoryManager
--    (SKU-FAB-JERSEY-BLU: qty=310 < reorder_point=500 → trigger reorder)
--
--    Guard idempotenza: DELETE delle righe sintetiche prima di re-inserire.
--    scm.inventory_levels è una TimescaleDB hypertable senza PRIMARY KEY,
--    quindi ON CONFLICT senza colonna di conflitto è un no-op (nessuna protezione
--    contro duplicati). Il DELETE sui source='wms_sync'/'manual' garantisce
--    idempotenza su double-load in dev/test.
-- ──────────────────────────────────────────────────────────────────────────────
DELETE FROM scm.inventory_levels
WHERE source IN ('wms_sync', 'manual')
  AND sku_id IN (
      'SKU-FAB-JERSEY-BLU', 'SKU-FAB-TWILL-GRY',
      'SKU-YARN-NE20-BLU', 'SKU-YARN-NE30-BIA',
      'SKU-DYE-REACT-BLU', 'SKU-SPARE-NEEDLE-L'
  );

INSERT INTO scm.inventory_levels (ts, sku_id, quantity, location, source)
VALUES
    -- Jersey BLU: SOTTO reorder_point (310 < 500) → InventoryManager deve segnalare
    (NOW() - INTERVAL '2 hours', 'SKU-FAB-JERSEY-BLU', 310.000,
     'main_warehouse', 'wms_sync'),
    -- Twill GRY: sopra reorder_point (780 > 300) → OK
    (NOW() - INTERVAL '2 hours', 'SKU-FAB-TWILL-GRY', 780.000,
     'main_warehouse', 'wms_sync'),
    -- Filato NE20: leggermente sopra soglia (900 > 850)
    (NOW() - INTERVAL '1 hour', 'SKU-YARN-NE20-BLU', 900.000,
     'raw_material_store', 'wms_sync'),
    -- Filato NE30: ben sopra soglia (2100 > 1200)
    (NOW() - INTERVAL '1 hour', 'SKU-YARN-NE30-BIA', 2100.000,
     'raw_material_store', 'wms_sync'),
    -- Colorante BLU: sopra soglia (75 > 50)
    (NOW() - INTERVAL '30 minutes', 'SKU-DYE-REACT-BLU', 75.000,
     'chemical_store', 'manual'),
    -- Aghi: SOTTO reorder_point (150 < 200) → secondo caso di riordino
    (NOW() - INTERVAL '30 minutes', 'SKU-SPARE-NEEDLE-L', 150.000,
     'maintenance_store', 'manual'),
    -- Letture storiche Jersey (ieri — per trend)
    (NOW() - INTERVAL '26 hours', 'SKU-FAB-JERSEY-BLU', 520.000,
     'main_warehouse', 'wms_sync'),
    (NOW() - INTERVAL '50 hours', 'SKU-FAB-JERSEY-BLU', 680.000,
     'main_warehouse', 'wms_sync')
-- No ON CONFLICT clause: duplicate protection is handled by the DELETE guard above.
-- (ON CONFLICT DO NOTHING without a conflict target is a no-op on tables without PK)
;


-- ──────────────────────────────────────────────────────────────────────────────
-- 4. scm.energy_readings — Letture energetiche tintoria + finissaggio (SINTETICO)
--    Mix peak (06:00-22:00) / off-peak (22:00-06:00)
--    Sufficiente per calcolo EnPI e % off-peak
--
--    Guard idempotenza: DELETE delle righe sintetiche prima di re-inserire.
--    scm.energy_readings è una TimescaleDB hypertable senza PRIMARY KEY,
--    quindi ON CONFLICT senza colonna di conflitto è un no-op (nessuna protezione
--    contro duplicati). Il DELETE sui asset_id sintetici garantisce idempotenza
--    su double-load in dev/test.
-- ──────────────────────────────────────────────────────────────────────────────
DELETE FROM scm.energy_readings
WHERE asset_id IN (
    'tintoria-01', 'tintoria-02',
    'stentatoio-01', 'stentatoio-02',
    'telaio-01', 'telaio-02',
    'rapier-01', 'rapier-02'
);

INSERT INTO scm.energy_readings
    (ts, asset_id, process, kwh, kg_processed, shift, is_peak_hour)
VALUES
    -- Tintoria (dyeing) — turno giorno (peak)
    (NOW() - INTERVAL '8 hours',  'tintoria-01', 'dyeing', 515.50, 125.00, 'day',     TRUE),
    (NOW() - INTERVAL '7 hours',  'tintoria-01', 'dyeing', 502.30, 122.00, 'day',     TRUE),
    (NOW() - INTERVAL '6 hours',  'tintoria-02', 'dyeing', 498.80, 121.50, 'day',     TRUE),
    (NOW() - INTERVAL '5 hours',  'tintoria-02', 'dyeing', 510.20, 124.00, 'day',     TRUE),
    -- Tintoria (dyeing) — turno sera (peak)
    (NOW() - INTERVAL '4 hours',  'tintoria-01', 'dyeing', 521.40, 126.50, 'evening', TRUE),
    (NOW() - INTERVAL '3 hours',  'tintoria-01', 'dyeing', 509.70, 123.00, 'evening', TRUE),
    -- Tintoria (dyeing) — turno notte (off-peak, efficienza maggiore)
    (NOW() - INTERVAL '10 hours', 'tintoria-02', 'dyeing', 488.60, 121.00, 'night',   FALSE),
    (NOW() - INTERVAL '11 hours', 'tintoria-02', 'dyeing', 495.10, 122.50, 'night',   FALSE),
    (NOW() - INTERVAL '12 hours', 'tintoria-01', 'dyeing', 490.30, 122.00, 'night',   FALSE),
    -- Tintoria giorno precedente (peak)
    (NOW() - INTERVAL '32 hours', 'tintoria-01', 'dyeing', 520.00, 126.00, 'day',     TRUE),
    (NOW() - INTERVAL '31 hours', 'tintoria-02', 'dyeing', 505.50, 123.00, 'day',     TRUE),
    -- Finissaggio (finishing) — turno giorno (peak)
    (NOW() - INTERVAL '8 hours',  'stentatoio-01', 'finishing', 263.40, 120.00, 'day',     TRUE),
    (NOW() - INTERVAL '7 hours',  'stentatoio-01', 'finishing', 258.70, 118.50, 'day',     TRUE),
    (NOW() - INTERVAL '6 hours',  'stentatoio-02', 'finishing', 261.20, 119.50, 'day',     TRUE),
    -- Finissaggio (finishing) — turno notte (off-peak)
    (NOW() - INTERVAL '10 hours', 'stentatoio-01', 'finishing', 252.80, 116.00, 'night',   FALSE),
    (NOW() - INTERVAL '11 hours', 'stentatoio-02', 'finishing', 255.60, 117.50, 'night',   FALSE),
    -- Finissaggio giorno precedente
    (NOW() - INTERVAL '32 hours', 'stentatoio-01', 'finishing', 260.00, 119.00, 'day',     TRUE),
    (NOW() - INTERVAL '31 hours', 'stentatoio-02', 'finishing', 265.30, 121.50, 'day',     TRUE),
    -- Filatura (spinning) — campione
    (NOW() - INTERVAL '8 hours',  'telaio-01', 'spinning', 93.20, 20.00, 'day', TRUE),
    (NOW() - INTERVAL '8 hours',  'telaio-02', 'spinning', 91.50, 20.00, 'day', TRUE),
    -- Tessitura (weaving) — campione
    (NOW() - INTERVAL '8 hours',  'rapier-01', 'weaving', 36.80, 21.00, 'day', TRUE),
    (NOW() - INTERVAL '8 hours',  'rapier-02', 'weaving', 35.90, 20.50, 'day', TRUE)
-- No ON CONFLICT clause: duplicate protection is handled by the DELETE guard above.
-- (ON CONFLICT DO NOTHING without a conflict target is a no-op on tables without PK)
;


-- ──────────────────────────────────────────────────────────────────────────────
-- 5. scm.historical_orders — 18 mesi di ordini mensili (SINTETICO)
--    Jersey (~12000kg/mese, picco estivo +35%, invernale +20%)
--    Twill (~8000kg/mese, CV ~12%, domanda stabile)
--
--    Generato con generate_series per 19 mesi (gen 2024 - lug 2025)
--    per garantire >=18 bucket mensili per ogni sku_group.
--
--    Stagioni (emisfero nord, tessile): estate = giu/lug/ago, inverno = dic/gen/feb
--    I picchi modellano la domanda di jersey da abbigliamento estivo/invernale.
-- ──────────────────────────────────────────────────────────────────────────────

-- Jersey Blu 140gsm — 19 mesi (gennaio 2024 — luglio 2025)
-- Stagionalita: +35% estate (giu-ago), +20% inverno (dic-feb), base ~12000kg/mese
INSERT INTO scm.historical_orders
    (order_id, sku_id, sku_group, order_date, delivery_date,
     quantity_kg, unit_price_eur, customer_type, season)
SELECT
    'ORD-JRS-' || TO_CHAR(month_start, 'YYYY-MM') AS order_id,
    'SKU-FAB-JERSEY-BLU'                           AS sku_id,
    'jersey'                                        AS sku_group,
    month_start                                     AS order_date,
    month_start + INTERVAL '5 days'                AS delivery_date,
    CASE
        WHEN EXTRACT(MONTH FROM month_start) IN (6, 7, 8)  THEN 16200.000  -- +35% estate
        WHEN EXTRACT(MONTH FROM month_start) IN (12, 1, 2) THEN 14400.000  -- +20% inverno
        ELSE 12000.000                                                        -- base
    END                                             AS quantity_kg,
    8.2000                                          AS unit_price_eur,
    'b2b'                                           AS customer_type,
    CASE
        WHEN EXTRACT(MONTH FROM month_start) IN (3, 4, 5)  THEN 'spring'
        WHEN EXTRACT(MONTH FROM month_start) IN (6, 7, 8)  THEN 'summer'
        WHEN EXTRACT(MONTH FROM month_start) IN (9, 10, 11) THEN 'autumn'
        ELSE 'winter'
    END                                             AS season
FROM generate_series(
    '2024-01-01 00:00:00+00'::TIMESTAMPTZ,
    '2025-07-01 00:00:00+00'::TIMESTAMPTZ,
    INTERVAL '1 month'
) AS t(month_start)
ON CONFLICT (order_id) DO NOTHING;


-- Twill Grigio 180gsm — 19 mesi (gennaio 2024 — luglio 2025)
-- Domanda stabile ~8000kg/mese con variazione CV~12% modellata per stagione
INSERT INTO scm.historical_orders
    (order_id, sku_id, sku_group, order_date, delivery_date,
     quantity_kg, unit_price_eur, customer_type, season)
SELECT
    'ORD-TWL-' || TO_CHAR(month_start, 'YYYY-MM') AS order_id,
    'SKU-FAB-TWILL-GRY'                            AS sku_id,
    'twill'                                         AS sku_group,
    month_start                                     AS order_date,
    month_start + INTERVAL '6 days'                AS delivery_date,
    CASE
        -- Variazione CV~12%: oscillazioni modeste attorno a 8000kg/mese
        WHEN EXTRACT(MONTH FROM month_start) IN (3, 4, 5)   THEN 8400.000  -- lieve picco primaverile
        WHEN EXTRACT(MONTH FROM month_start) IN (6, 7, 8)   THEN 7600.000  -- lieve calo estivo
        WHEN EXTRACT(MONTH FROM month_start) IN (9, 10, 11) THEN 8200.000  -- autunno stabile
        ELSE 8600.000                                                         -- inverno (cappotti/accessori)
    END                                             AS quantity_kg,
    9.8000                                          AS unit_price_eur,
    'b2b'                                           AS customer_type,
    CASE
        WHEN EXTRACT(MONTH FROM month_start) IN (3, 4, 5)  THEN 'spring'
        WHEN EXTRACT(MONTH FROM month_start) IN (6, 7, 8)  THEN 'summer'
        WHEN EXTRACT(MONTH FROM month_start) IN (9, 10, 11) THEN 'autumn'
        ELSE 'winter'
    END                                             AS season
FROM generate_series(
    '2024-01-01 00:00:00+00'::TIMESTAMPTZ,
    '2025-07-01 00:00:00+00'::TIMESTAMPTZ,
    INTERVAL '1 month'
) AS t(month_start)
ON CONFLICT (order_id) DO NOTHING;


-- Ordini spot filato NE20 Blu (raw_yarn — fornitore principale) — campione trimestrale
INSERT INTO scm.historical_orders
    (order_id, sku_id, sku_group, order_date, delivery_date,
     quantity_kg, unit_price_eur, customer_type, season)
VALUES
    ('ORD-YARN-2024-Q1', 'SKU-YARN-NE20-BLU', 'yarn',
     '2024-01-15 08:00:00+00', '2024-01-22 08:00:00+00',
     6000.000, 3.1500, 'supplier', 'winter'),
    ('ORD-YARN-2024-Q2', 'SKU-YARN-NE20-BLU', 'yarn',
     '2024-04-10 08:00:00+00', '2024-04-17 08:00:00+00',
     7500.000, 3.2000, 'supplier', 'spring'),
    ('ORD-YARN-2024-Q3', 'SKU-YARN-NE20-BLU', 'yarn',
     '2024-07-08 08:00:00+00', '2024-07-15 08:00:00+00',
     8200.000, 3.2500, 'supplier', 'summer'),
    ('ORD-YARN-2024-Q4', 'SKU-YARN-NE20-BLU', 'yarn',
     '2024-10-14 08:00:00+00', '2024-10-21 08:00:00+00',
     7000.000, 3.2000, 'supplier', 'autumn')
ON CONFLICT (order_id) DO NOTHING;
