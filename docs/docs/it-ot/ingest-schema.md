# Schema di ingest sensori

Documentazione dello schema di ingest della pipeline IT/OT — IOT-09.

**Fonte:** `packages/sft-assets/src/sft_assets/registry.yaml` (Source: commit Phase 3)

---

## Asset registry

**Path file:** `packages/sft-assets/src/sft_assets/registry.yaml`

Il registry contiene 30 asset reali distribuiti su 5 famiglie. Ogni asset ha:

- `asset_id` — identificatore univoco (pattern `^[A-Z]+-\d{2}$`)
- `asset_family` — famiglia di asset (`loom`, `spinning`, `warping`, `dyeing`, `finishing`)
- `line_id` — linea produttiva di appartenenza
- `opcua_namespace` — namespace OPC-UA (pattern `urn:mantis:<family>:<asset_id>`)
- `tags` — lista di tag con `tag_id`, `unit`, `sample_rate_hz`, `semantic_type`
- `status` — stato operativo (`active`)

### Tabella riepilogativa per famiglia

| Famiglia   | Conteggio | Asset ID range    | Tag per asset | Tag distinti principali                                        |
|------------|-----------|-------------------|---------------|----------------------------------------------------------------|
| `loom`     | 12        | LOOM-01..LOOM-12  | 5             | warp_tension, pick_density, creel_speed, broken_pick_count, loom_temperature |
| `spinning` | 8         | SPIN-01..SPIN-08  | 5             | spindle_speed, yarn_tension, roller_temperature, broken_end_count, spindle_vibration |
| `warping`  | 4         | WARP-01..WARP-04  | 5             | beam_tension, creel_feed_rate, warp_speed, tension_imbalance, yarn_count |
| `dyeing`   | 4         | DYE-01..DYE-04    | 6             | bath_temperature, bath_ph, dye_flow_rate, drum_speed, steam_pressure, liquor_ratio |
| `finishing`| 2         | STEN-01..STEN-02  | 5             | fabric_tension, oven_temperature, humidity_level, web_speed, chain_tension |
| **Totale** | **30**    |                   | **~50 tag**   |                                                                |

### Esempio YAML — LOOM-01

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

### Esempio YAML — DYE-01

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

24 tag distinti nell'intera piattaforma:

| `tag_id`            | Unità          | `sample_rate_hz` | `semantic_type` | Famiglia principale |
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

## Unità di misura

| Unità        | Grandezza fisica                  | Famiglia principale     |
|--------------|-----------------------------------|-------------------------|
| `N`          | Forza (Newton)                    | loom, warping, finishing |
| `picks_per_cm` | Densità di trama               | loom                    |
| `rpm`        | Velocità angolare (giri/min)      | loom, spinning, dyeing  |
| `count`      | Conteggio eventi discreti         | loom, spinning          |
| `degC`       | Temperatura (gradi Celsius)       | loom, spinning, dyeing, finishing |
| `cN`         | Forza (centi-Newton) — filatura   | spinning                |
| `mm_s`       | Vibrazione (mm/s RMS)             | spinning                |
| `m_min`      | Velocità lineare (m/min)          | warping                 |
| `pct`        | Percentuale generica              | warping                 |
| `l_min`      | Portata liquido (litri/min)       | dyeing                  |
| `bar`        | Pressione (bar)                   | dyeing                  |
| `pH`         | Acidità soluzione acquosa         | dyeing                  |
| `ratio`      | Rapporto adimensionale            | dyeing                  |
| `pct_rh`     | Umidità relativa (% RH)           | finishing               |

---

## SensorEvent JSON sample

Esempio di payload pubblicato su NATS da `ot-bridge` (serializzazione `SensorEvent.model_dump_json()`):

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

**Campi:**

| Campo              | Tipo       | Note                                                             |
|--------------------|------------|------------------------------------------------------------------|
| `asset_id`         | `str`      | Match `^[A-Z]+-\d{2}$`                                          |
| `asset_family`     | `str`      | Enum: `loom`, `spinning`, `warping`, `dyeing`, `finishing`       |
| `tag_id`           | `str`      | Tag del tag dictionary                                           |
| `timestamp_utc`    | `datetime` | UTC ISO-8601 — emesso da sim-textile, NON modificato da ot-bridge (A-004) |
| `value`            | `float`    | Valore numerico del sensore; `null` per fault injection NaN      |
| `unit`             | `str`      | Da tag dictionary                                                |
| `quality_code`     | `int`      | OPC-UA StatusCode: `0` = Good, `0x80AF0000` = BadOutOfService    |
| `source`           | `str`      | `live`, `replay_cmapss`, `replay_uci`                            |
| `server_received_ts` | `datetime` | Timestamp arrivo ot-bridge (UTC); usato per misura skew        |

---

## NATS subject hierarchy (D-52)

| Pattern subject                                     | Descrizione                                   | Esempio                                          |
|-----------------------------------------------------|-----------------------------------------------|--------------------------------------------------|
| `sensor.events.<family>.<asset_id>.<tag_id>`        | Evento sensore normalizzato                   | `sensor.events.loom.LOOM-01.warp_tension`        |
| `sensor.alarms.<family>.<asset_id>`                 | Alarm storm aggregato (burst fault injection) | `sensor.alarms.dyeing.DYE-01`                    |
| `audit.ot.<service>`                                | Log strutturato per governance Phase 11       | `audit.ot.bridge`                                |

**JetStream stream:** `SENSOR_EVENTS` con retention `WorkQueuePolicy` + `maxAge: 7d` (allineato D-49 compression tier).

**Consumer durability Phase 4+:** `agent.<agent_name>.consumer` (nomi consumer definiti in Phase 4).

Gli agenti possono sottoscrivere selettivamente via wildcard:

```
sensor.events.loom.>          # tutti i tag di tutti i loom
sensor.events.*.LOOM-01.>     # tutti i tag di LOOM-01
sensor.events.loom.LOOM-01.*  # tutti i tag di LOOM-01 solo
```

---

## Hypertable TimescaleDB

**File migration:** `infra/migrations/timescale/001_create_sensor_events.sql`

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

-- Hypertable partizionata per timestamp_utc con chunk 1 giorno (D-49)
SELECT create_hypertable(
  'sensor_events',
  'timestamp_utc',
  chunk_time_interval => INTERVAL '1 day',
  if_not_exists => TRUE
);

-- Compression: segmenta per (asset_id, tag_id), ordina DESC
ALTER TABLE sensor_events SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'asset_id, tag_id',
  timescaledb.compress_orderby = 'timestamp_utc DESC'
);
SELECT add_compression_policy('sensor_events', INTERVAL '7 days', if_not_exists => TRUE);

-- Retention: elimina chunk > 90 giorni (A-007 dataset >= 90d)
SELECT add_retention_policy('sensor_events', INTERVAL '90 days', if_not_exists => TRUE);
```

### Colonne

| Colonna        | Tipo              | Note                                              |
|----------------|-------------------|---------------------------------------------------|
| `asset_id`     | `TEXT NOT NULL`   | FK logica verso registry.yaml                     |
| `tag_id`       | `TEXT NOT NULL`   | Tag del tag dictionary                            |
| `timestamp_utc`| `TIMESTAMPTZ NOT NULL` | Timestamp UTC sorgente (non modificato da bridge) |
| `value`        | `DOUBLE PRECISION`| Nullable per fault injection NaN                  |
| `unit`         | `TEXT`            | Da tag dictionary                                 |
| `quality_code` | `SMALLINT`        | OPC-UA StatusCode                                 |
| `source`       | `TEXT NOT NULL`   | `live`, `replay_cmapss`, `replay_uci`             |

### Policy (D-49)

| Policy       | Configurazione         | Rationale                                       |
|--------------|------------------------|-------------------------------------------------|
| Chunk        | `1 day`                | Ottimale per query time-range per asset         |
| Compression  | After `7 days`         | Hot tier 7gg; warm tier compresso               |
| Retention    | Drop after `90 days`   | A-007: dataset ≥ 90gg coverage per Phase 6-7    |

### Indici

```sql
CREATE INDEX IF NOT EXISTS idx_sensor_events_asset_time
  ON sensor_events (asset_id, timestamp_utc DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_events_tag_time
  ON sensor_events (tag_id, timestamp_utc DESC);
```

---

## Query patterns esempio

Pattern di query per agenti Phase 4+ (`sft-tools.timescale.query`):

```sql
-- Tutti i warp_tension di LOOM-01 nelle ultime 24 ore
SELECT asset_id, tag_id, timestamp_utc, value, unit, quality_code
FROM sensor_events
WHERE asset_id = $1 AND tag_id = $2
  AND timestamp_utc > NOW() - INTERVAL '24 hours'
ORDER BY timestamp_utc DESC;

-- Ultimi N eventi per un asset (tutti i tag)
SELECT tag_id, timestamp_utc, value, unit
FROM sensor_events
WHERE asset_id = $1
  AND timestamp_utc > NOW() - INTERVAL '1 hour'
ORDER BY timestamp_utc DESC
LIMIT $2;

-- Anomalie per soglia su warp_tension nelle ultime 6 ore
SELECT asset_id, tag_id, timestamp_utc, value
FROM sensor_events
WHERE tag_id = 'warp_tension'
  AND value > $1
  AND timestamp_utc > NOW() - INTERVAL '6 hours'
ORDER BY value DESC;
```

---

*Riferimenti: [Schema OPC-UA](opcua-schema.md) | [Panoramica IT/OT](index.md)*
