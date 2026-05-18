# Sensor Ingest Schema

Documentation of the IT/OT pipeline ingest schema — IOT-09.

**Source:** `packages/sft-assets/src/sft_assets/registry.yaml` (Source: Phase 3 commit)

---

## Asset registry

**File path:** `packages/sft-assets/src/sft_assets/registry.yaml`

The registry contains 30 real assets distributed across 5 families. Each asset has:

- `asset_id` — unique identifier (pattern `^[A-Z]+-\d{2}$`)
- `asset_family` — asset family (`loom`, `spinning`, `warping`, `dyeing`, `finishing`)
- `line_id` — production line
- `opcua_namespace` — OPC-UA namespace (pattern `urn:mantis:<family>:<asset_id>`)
- `tags` — list of tags with `tag_id`, `unit`, `sample_rate_hz`, `semantic_type`
- `status` — operational status (`active`)

### Summary table by family

| Family     | Count | Asset ID range    | Tags per asset | Main distinct tags                                             |
|------------|-------|-------------------|----------------|----------------------------------------------------------------|
| `loom`     | 12    | LOOM-01..LOOM-12  | 5              | warp_tension, pick_density, creel_speed, broken_pick_count, loom_temperature |
| `spinning` | 8     | SPIN-01..SPIN-08  | 5              | spindle_speed, yarn_tension, roller_temperature, broken_end_count, spindle_vibration |
| `warping`  | 4     | WARP-01..WARP-04  | 5              | beam_tension, creel_feed_rate, warp_speed, tension_imbalance, yarn_count |
| `dyeing`   | 4     | DYE-01..DYE-04    | 6              | bath_temperature, bath_ph, dye_flow_rate, drum_speed, steam_pressure, liquor_ratio |
| `finishing`| 2     | STEN-01..STEN-02  | 5              | fabric_tension, oven_temperature, humidity_level, web_speed, chain_tension |
| **Total**  | **30**|                   | **~50 tags**   |                                                                |

### YAML example — LOOM-01

```yaml
- asset_id: LOOM-01
  asset_family: loom
  line_id: weaving-line-1
  opcua_namespace: "urn:mantis:loom:LOOM-01"
  tags:
    - tag_id: warp_tension
      unit: N
      sample_rate_hz: 10.0
      semantic_type: tension
    - tag_id: pick_density
      unit: picks_per_cm
      sample_rate_hz: 1.0
      semantic_type: density
    - tag_id: creel_speed
      unit: rpm
      sample_rate_hz: 5.0
      semantic_type: speed
    - tag_id: broken_pick_count
      unit: count
      sample_rate_hz: 1.0
      semantic_type: density
    - tag_id: loom_temperature
      unit: degC
      sample_rate_hz: 2.0
      semantic_type: temperature
  status: active
```

### YAML example — DYE-01

```yaml
- asset_id: DYE-01
  asset_family: dyeing
  line_id: dyeing-line-1
  opcua_namespace: "urn:mantis:dyeing:DYE-01"
  tags:
    - tag_id: bath_temperature
      unit: degC
      sample_rate_hz: 1.0
      semantic_type: temperature
    - tag_id: bath_ph
      unit: pH
      sample_rate_hz: 0.5
      semantic_type: chemistry
    - tag_id: dye_flow_rate
      unit: l_min
      sample_rate_hz: 1.0
      semantic_type: flow
    - tag_id: liquor_ratio
      unit: ratio
      sample_rate_hz: 0.1
      semantic_type: ratio
  status: active
```

---

## Tag dictionary

24 distinct tags across the entire platform:

| `tag_id`            | Unit           | `sample_rate_hz` | `semantic_type` | Main family         |
|---------------------|----------------|------------------|-----------------|---------------------|
| `warp_tension`      | N              | 10.0             | tension         | loom                |
| `pick_density`      | picks_per_cm   | 1.0              | density         | loom                |
| `creel_speed`       | rpm            | 5.0              | speed           | loom                |
| `broken_pick_count` | count          | 1.0              | density         | loom                |
| `loom_temperature`  | degC           | 2.0              | temperature     | loom                |
| `spindle_speed`     | rpm            | 5.0              | speed           | spinning            |
| `yarn_tension`      | cN             | 5.0              | tension         | spinning            |
| `roller_temperature`| degC           | 1.0              | temperature     | spinning            |
| `broken_end_count`  | count          | 1.0              | density         | spinning            |
| `spindle_vibration` | mm_s           | 10.0             | vibration       | spinning            |
| `beam_tension`      | N              | 2.0              | tension         | warping             |
| `creel_feed_rate`   | m_min          | 1.0              | speed           | warping             |
| `warp_speed`        | m_min          | 2.0              | speed           | warping             |
| `tension_imbalance` | pct            | 1.0              | imbalance       | warping             |
| `yarn_count`        | count          | 0.5              | density         | warping             |
| `bath_temperature`  | degC           | 1.0              | temperature     | dyeing              |
| `bath_ph`           | pH             | 0.5              | chemistry       | dyeing              |
| `dye_flow_rate`     | l_min          | 1.0              | flow            | dyeing              |
| `drum_speed`        | rpm            | 1.0              | speed           | dyeing              |
| `steam_pressure`    | bar            | 1.0              | pressure        | dyeing              |
| `liquor_ratio`      | ratio          | 0.1              | ratio           | dyeing              |
| `fabric_tension`    | N              | 2.0              | tension         | finishing           |
| `oven_temperature`  | degC           | 1.0              | temperature     | finishing           |
| `humidity_level`    | pct_rh         | 1.0              | humidity        | finishing           |

---

## Units of measure

| Unit         | Physical quantity                 | Main family             |
|--------------|-----------------------------------|-------------------------|
| `N`          | Force (Newton)                    | loom, warping, finishing |
| `picks_per_cm` | Weft density                    | loom                    |
| `rpm`        | Angular velocity (revolutions/min)| loom, spinning, dyeing  |
| `count`      | Discrete event count              | loom, spinning          |
| `degC`       | Temperature (degrees Celsius)     | loom, spinning, dyeing, finishing |
| `cN`         | Force (centi-Newton) — spinning   | spinning                |
| `mm_s`       | Vibration (mm/s RMS)              | spinning                |
| `m_min`      | Linear velocity (m/min)           | warping                 |
| `pct`        | Generic percentage                | warping                 |
| `l_min`      | Liquid flow rate (liters/min)     | dyeing                  |
| `bar`        | Pressure (bar)                    | dyeing                  |
| `pH`         | Solution acidity                  | dyeing                  |
| `ratio`      | Dimensionless ratio               | dyeing                  |
| `pct_rh`     | Relative humidity (% RH)          | finishing               |

---

## SensorEvent JSON sample

Example payload published on NATS by `ot-bridge` (`SensorEvent.model_dump_json()` serialization):

```json
{
  "asset_id": "LOOM-01",
  "asset_family": "loom",
  "tag_id": "warp_tension",
  "timestamp_utc": "2026-05-18T12:00:00+00:00",
  "value": 25.3,
  "unit": "N",
  "quality_code": 0,
  "source": "live",
  "server_received_ts": "2026-05-18T12:00:00.045+00:00"
}
```

**Fields:**

| Field              | Type       | Notes                                                            |
|--------------------|------------|------------------------------------------------------------------|
| `asset_id`         | `str`      | Matches `^[A-Z]+-\d{2}$`                                        |
| `asset_family`     | `str`      | Enum: `loom`, `spinning`, `warping`, `dyeing`, `finishing`       |
| `tag_id`           | `str`      | Tag from tag dictionary                                          |
| `timestamp_utc`    | `datetime` | UTC ISO-8601 — emitted by sim-textile, NOT modified by ot-bridge (A-004) |
| `value`            | `float`    | Numeric sensor value; `null` for NaN fault injection            |
| `unit`             | `str`      | From tag dictionary                                              |
| `quality_code`     | `int`      | OPC-UA StatusCode: `0` = Good, `0x80AF0000` = BadOutOfService    |
| `source`           | `str`      | `live`, `replay_cmapss`, `replay_uci`                            |
| `server_received_ts` | `datetime` | ot-bridge arrival timestamp (UTC); used for skew measurement |

---

## NATS subject hierarchy (D-52)

| Subject pattern                                     | Description                                   | Example                                          |
|-----------------------------------------------------|-----------------------------------------------|--------------------------------------------------|
| `sensor.events.<family>.<asset_id>.<tag_id>`        | Normalized sensor event                       | `sensor.events.loom.LOOM-01.warp_tension`        |
| `sensor.alarms.<family>.<asset_id>`                 | Aggregated alarm storm (burst fault injection)| `sensor.alarms.dyeing.DYE-01`                    |
| `audit.ot.<service>`                                | Structured log for Phase 11 governance        | `audit.ot.bridge`                                |

**JetStream stream:** `SENSOR_EVENTS` with `WorkQueuePolicy` retention + `maxAge: 7d` (aligned with D-49 compression tier).

**Consumer durability Phase 4+:** `agent.<agent_name>.consumer` (consumer names defined in Phase 4).

Agents can subscribe selectively via wildcard:

```
sensor.events.loom.>          # all tags from all looms
sensor.events.*.LOOM-01.>     # all tags from LOOM-01 only
sensor.events.loom.LOOM-01.*  # all tags of LOOM-01 in loom namespace
```

---

## TimescaleDB hypertable

**Migration file:** `infra/migrations/timescale/001_create_sensor_events.sql`

### DDL

```sql
CREATE TABLE IF NOT EXISTS sensor_events (
  asset_id      TEXT NOT NULL,
  tag_id        TEXT NOT NULL,
  timestamp_utc TIMESTAMPTZ NOT NULL,
  value         DOUBLE PRECISION,
  unit          TEXT,
  quality_code  SMALLINT,
  source        TEXT NOT NULL DEFAULT 'live'
  -- source: 'live' | 'replay_cmapss' | 'replay_uci'
);

-- Hypertable partitioned by timestamp_utc with 1-day chunks (D-49)
SELECT create_hypertable(
  'sensor_events',
  'timestamp_utc',
  chunk_time_interval => INTERVAL '1 day',
  if_not_exists => TRUE
);

-- Compression: segment by (asset_id, tag_id), order DESC
ALTER TABLE sensor_events SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'asset_id, tag_id',
  timescaledb.compress_orderby = 'timestamp_utc DESC'
);
SELECT add_compression_policy('sensor_events', INTERVAL '7 days', if_not_exists => TRUE);

-- Retention: drop chunks older than 90 days (A-007 dataset >= 90d)
SELECT add_retention_policy('sensor_events', INTERVAL '90 days', if_not_exists => TRUE);
```

### Columns

| Column         | Type              | Notes                                             |
|----------------|-------------------|---------------------------------------------------|
| `asset_id`     | `TEXT NOT NULL`   | Logical FK to registry.yaml                       |
| `tag_id`       | `TEXT NOT NULL`   | Tag from tag dictionary                           |
| `timestamp_utc`| `TIMESTAMPTZ NOT NULL` | UTC source timestamp (not modified by bridge) |
| `value`        | `DOUBLE PRECISION`| Nullable for NaN fault injection                  |
| `unit`         | `TEXT`            | From tag dictionary                               |
| `quality_code` | `SMALLINT`        | OPC-UA StatusCode                                 |
| `source`       | `TEXT NOT NULL`   | `live`, `replay_cmapss`, `replay_uci`             |

### Policies (D-49)

| Policy       | Configuration          | Rationale                                       |
|--------------|------------------------|-------------------------------------------------|
| Chunk        | `1 day`                | Optimal for time-range queries per asset        |
| Compression  | After `7 days`         | Hot tier 7d; warm tier compressed               |
| Retention    | Drop after `90 days`   | A-007: dataset ≥ 90d coverage for Phase 6-7     |

### Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_sensor_events_asset_time
  ON sensor_events (asset_id, timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_events_tag_time
  ON sensor_events (tag_id, timestamp_utc DESC);
```

---

## Query patterns example

Query patterns for Phase 4+ agents (`sft-tools.timescale.query`):

```sql
-- All warp_tension readings from LOOM-01 in the last 24 hours
SELECT asset_id, tag_id, timestamp_utc, value, unit, quality_code
FROM sensor_events
WHERE asset_id = $1 AND tag_id = $2
  AND timestamp_utc > NOW() - INTERVAL '24 hours'
ORDER BY timestamp_utc DESC;

-- Last N events for an asset (all tags)
SELECT tag_id, timestamp_utc, value, unit
FROM sensor_events
WHERE asset_id = $1
  AND timestamp_utc > NOW() - INTERVAL '1 hour'
ORDER BY timestamp_utc DESC
LIMIT $2;

-- Anomalies above threshold on warp_tension in last 6 hours
SELECT asset_id, tag_id, timestamp_utc, value
FROM sensor_events
WHERE tag_id = 'warp_tension'
  AND value > $1
  AND timestamp_utc > NOW() - INTERVAL '6 hours'
ORDER BY value DESC;
```

---

*References: [OPC-UA Schema](opcua-schema.md) | [IT/OT Overview](index.md)*
