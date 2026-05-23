---
phase: 07-agents-maintenance-reliability
plan: 05
plan_id: 07-05
subsystem: maintenance-data-plane
tags: [timescale, hypertable, continuous-aggregate, simulator, nats, downtime]
requires:
  - 07-00 (Wave-0 placeholders 008/test_migration_008.py + test_downtime_generator.py)
  - 07-02 (failure_modes.yaml maintenance taxonomy / MaintenanceSpec model)
provides:
  - maintenance.downtime_events hypertable (D-DA-01)
  - maintenance.oee_hourly continuous aggregate (D-DA-03)
  - DowntimeEvent Pydantic model (frozen + tz-aware) on NATS subject
    maintenance.downtime.<asset_id>
  - DowntimeEventGenerator async task (mirror quality_event_generator)
affects:
  - 07-09 (DowntimeAnalyzer — will consume the hypertable + CAGG)
  - 07-12 (E2E scenarios — live event stream available)
tech_stack:
  added: []
  patterns:
    - "TimescaleDB continuous aggregate WITH (timescaledb.continuous) + WITH NO DATA + refresh policy (07-RESEARCH Pattern 7)"
    - "Idempotent migration: IF NOT EXISTS / create_hypertable(if_not_exists=>TRUE) / add_continuous_aggregate_policy(if_not_exists=>TRUE)"
    - "Per-asset random.Random(asset_id) deterministic seeding (Pattern S-6 inherited from 06-09)"
    - "Pydantic v2 frozen + extra=forbid + field_validator tz-aware (D-DA-01)"
key_files:
  created:
    - infra/migrations/timescale/008_create_downtime_events.sql
    - simulators/sim-textile/src/sim_textile/downtime_event_generator.py
  modified:
    - infra/migrations/timescale/tests/test_migration_008.py (Wave 0 stub -> 8 testcontainers tests)
    - simulators/sim-textile/tests/test_downtime_generator.py (Wave 0 stub -> 13 unit tests)
decisions:
  - "CAGG refresh policy start_offset = 3h (not 2h as in PATTERNS skeleton): TimescaleDB 2.18 requires (start_offset - end_offset) >= 2 * bucket_width; with bucket=1h + end=5min, start must exceed 2h5min — 3h leaves a 55-minute safety margin. Pitfall 4 still satisfied (3h << sensor_events 90d retention)."
  - "DowntimeEvent payload uses event_id: str (UUID string) instead of UUID type to keep JSON-roundtrip symmetry trivial across NATS boundary."
  - "Hypertable PK is composite (event_id, timestamp) because TimescaleDB requires the time column in every unique index on a hypertable; UUIDv4 collisions remain application-side negligible."
  - "AssetFamily -> taxonomy mapping: LOOM/WARPING -> 'weaving' (failure_modes uses domain string, not the asset family enum value). FINISHING currently has no maintenance entries -> generator skip + warn-log."
  - "Materialized view created WITH NO DATA to avoid long synchronous refresh at migration time; refresh policy schedules incremental updates every 5 minutes."
metrics:
  duration_min: 16
  completed: 2026-05-23
---

# Phase 7 Plan 05: Downtime Data Plane (Hypertable + CAGG + Simulator) — Summary

Two coupled deliverables — TimescaleDB persistence (migration 008) and live
event stream (sim-textile DowntimeEventGenerator) — that satisfy MNT-04 data
foundation + MNT-05 taxonomy consumption, unblocking DowntimeAnalyzer (07-09)
and E2E scenarios (07-12).

## What Changed

### Migration 008 — `008_create_downtime_events.sql`

- **Schema**: new `maintenance` schema.
- **Hypertable**: `maintenance.downtime_events` partitioned by `timestamp`,
  composite PK `(event_id, timestamp)`. Columns mirror D-DA-01 exactly:
  `event_id` UUID (default `gen_random_uuid()`), `asset_id`, `reason_code`,
  `duration_min` (CHECK >= 0), `severity` (CHECK in minor|major|critical),
  `work_order_id`/`dye_lot_id` nullable, `source` (default `'simulator'`),
  `timestamp` TIMESTAMPTZ, `inserted_at` default `NOW()`.
- **Continuous aggregate**: `maintenance.oee_hourly` —
  `SELECT asset_id, time_bucket('1 hour', timestamp) AS hour_bucket,
   SUM(duration_min)::BIGINT AS total_downtime_min, COUNT(*)::BIGINT AS event_count`.
  Created `WITH NO DATA`.
- **Refresh policy**: `start_offset='3 hours'`, `end_offset='5 minutes'`,
  `schedule_interval='5 minutes'`. (Deviation from PATTERNS skeleton — see
  Deviations section below.)
- **Indexes**: `idx_downtime_asset_time (asset_id, timestamp DESC)` +
  `idx_downtime_reason_time (reason_code, timestamp DESC)` for Pareto /
  per-asset OEE queries.
- **Idempotency**: all DDL uses `IF NOT EXISTS` / `if_not_exists=>TRUE`; second
  apply is a no-op (verified by `test_post_migration_idempotent_double_apply`).

### Simulator — `downtime_event_generator.py`

- **`DowntimeEvent`** Pydantic v2 model: frozen + extra=forbid + `field_validator`
  on `timestamp` (rejects naive). `severity` Literal; `duration_min` ge=0;
  `source` Literal[simulator|operator].
- **`downtime_event_emitter`** async task: pubblica su NATS subject
  `maintenance.downtime.<asset_id>`. Per-asset `random.Random(asset_id)` seed
  (deterministic). Re-raises `asyncio.CancelledError`. Rate-limited via
  Bernoulli-per-tick (2/min nominal, 8/min faulted).
- **`start_downtime_event_tasks`** factory: mirror diretto di
  `start_quality_event_tasks` per integrazione nel sim emitter loop opzionale.
- **Taxonomy integration**: `reason_code` pescato dalla
  `failure_modes.yaml` maintenance subkey via `load_failure_modes()` filtrato
  per asset family (mapping `LOOM/WARPING -> weaving`, `SPINNING -> spinning`,
  `DYEING -> dyeing`).
- **`duration_min` derivation**: base = `MaintenanceSpec.mttr_target_minutes`,
  scalato per severity (minor 0.5x, major 1.0x, critical 2.0x) + jitter +-50%,
  clamp `[0, 10080]`.
- **No-taxonomy fallback**: famiglie senza entries (oggi `FINISHING`) loggano
  warn one-shot e proseguono il loop async senza emettere — preserva il
  cancellation-contract senza crash.

### Reason-code -> Asset-family Mapping (from `failure_modes.yaml`)

| asset_family (enum) | taxonomy key | reason_codes attivi (MNT-05)                                                  |
| ------------------- | ------------ | ----------------------------------------------------------------------------- |
| LOOM                | weaving      | WEAVING-BE-001 (broken_end, 30min), WEAVING-MP-002 (mispick, 15min), WEAVING-SF-003 (selvage_fault, 45min) |
| WARPING             | weaving      | (same as LOOM — entrambe le family condividono la taxonomy weaving)           |
| SPINNING            | spinning     | SPINNING-SL-001 (slub, 20min), SPINNING-NP-002 (neppy, 25min)                 |
| DYEING              | dyeing       | DYEING-SD-001 (shade_deviation, 60min), DYEING-UD-002 (unlevel_dyeing, 90min) |
| FINISHING           | (none)       | — generator skip + warn-log                                                   |

## Tests

### Migration (testcontainers, TimescaleDB 2.18.0-pg16)

| Test                                                            | Verifica                                          |
| --------------------------------------------------------------- | ------------------------------------------------- |
| test_post_migration_creates_downtime_events_table               | pg_tables row presente                            |
| test_post_migration_creates_hypertable                          | timescaledb_information.hypertables row presente  |
| test_post_migration_creates_oee_hourly_caggr                    | continuous_aggregates row + refresh policy job   |
| test_post_migration_insert_downtime_event_then_refresh_caggr    | INSERT 3 -> refresh -> oee_hourly returns 90min/3 |
| test_post_migration_idempotent_double_apply                     | second apply no-op                                |
| test_post_migration_check_constraint_severity                   | severity='invalid' raises CheckViolationError     |
| test_post_migration_check_constraint_duration                   | duration_min=-1 raises CheckViolationError        |
| test_post_migration_creates_indexes                             | both Pareto indexes present                       |

**Risultato**: 8/8 passed (50.5s, testcontainers cold-start).

### Simulator (unit, mock NATS via AsyncMock)

| Test                                                | Verifica                                                              |
| --------------------------------------------------- | --------------------------------------------------------------------- |
| test_downtime_event_is_frozen_and_extra_forbid      | frozen + extra=forbid invariants                                      |
| test_downtime_event_rejects_naive_datetime          | field_validator tz-aware                                              |
| test_downtime_event_severity_literal                | Literal[minor|major|critical]                                         |
| test_downtime_event_duration_min_ge_zero            | duration_min >= 0                                                     |
| test_downtime_event_json_roundtrip                  | model_dump_json -> model_validate equality                            |
| test_publishes_to_correct_subject                   | subject == maintenance.downtime.<asset_id>                            |
| test_payload_validates_as_downtime_event            | payload JSON valido + source='simulator'                              |
| test_reason_code_drawn_from_failure_modes_taxonomy  | reason_code in expected_codes(family='weaving')                       |
| test_rate_limited_under_nominal                     | <=5 events in 15 sim-seconds (limite nominale 2/min)                  |
| test_severity_distribution_skews_to_minor           | minor >= 55%, critical <= 25% su sample >=50                         |
| test_cancellation_graceful                          | asyncio.CancelledError re-raised                                      |
| test_skip_when_family_has_no_maintenance_taxonomy   | FINISHING -> 0 publish, no crash                                      |
| test_per_asset_rng_determinism                      | due run con stesso asset_id -> stesso prefisso reason_code            |

**Risultato**: 13/13 passed (1.01s) + 6/6 regression quality_generator passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CAGG refresh policy start_offset bumped 2h -> 3h**

- **Found during:** Task 1 (test_post_migration_creates_downtime_events_table)
- **Issue:** `add_continuous_aggregate_policy(start_offset=>'2 hours', end_offset=>'5 minutes', ...)`
  raises `InvalidParameterValueError: policy refresh window too small` —
  TimescaleDB 2.18 enforces `(start_offset - end_offset) >= 2 * bucket_width`.
  With bucket=1h and end=5min, start must exceed 2h5min.
- **Fix:** start_offset bumped from `INTERVAL '2 hours'` to `INTERVAL '3 hours'`.
  Adds 55-minute safety margin; Pitfall 4 still satisfied (3h << sensor_events
  90d retention window).
- **Files modified:** `infra/migrations/timescale/008_create_downtime_events.sql`
- **Commit:** 3e74f3d

### Architectural Decisions Implicit in Plan

- **Composite PK `(event_id, timestamp)`**: TimescaleDB requires hypertable
  uniqueness to include the partition column. Plan SQL skeleton had `event_id`
  as sole PK which would fail `create_hypertable`. Composite PK is the standard
  workaround; UUIDv4 collisions remain negligible.
- **AssetFamily -> taxonomy key map**: plan implied direct family-name match
  but `failure_modes.yaml` uses string "weaving" for both LOOM and WARPING
  enums. Explicit `_FAMILY_TAXONOMY_KEY` dict makes the mapping discoverable.
- **`event_id: str` (not UUID)**: Plan D-DA-01 spec said `UUID4`. Used `str`
  for clean JSON round-trip across NATS; format constrained to UUID via
  application code (`str(uuid4())`).

## Authentication Gates / Checkpoints

**Task 2 (pending): checkpoint:human-action — Push migration 008 to dev TimescaleDB.**

Migration 008 is in repo + testcontainers tests green (50.5s). The actual push
to the dev TimescaleDB instance requires manual `psql` verification per the
plan (mirror 07-01 pattern):

```bash
make migrate-timescale   # or: python infra/migrations/timescale/migrate.py up
```

Then verify:

```bash
psql "$TIMESCALE_DSN" -c "SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_schema='maintenance';"
psql "$TIMESCALE_DSN" -c "SELECT view_name, materialization_hypertable_name FROM timescaledb_information.continuous_aggregates WHERE view_schema='maintenance';"
psql "$TIMESCALE_DSN" -c "INSERT INTO maintenance.downtime_events (asset_id, reason_code, duration_min, severity, source, timestamp) VALUES ('LOOM-01', 'WEAVING-BE-001', 30, 'minor', 'simulator', NOW()) RETURNING event_id;"
psql "$TIMESCALE_DSN" -c "CALL refresh_continuous_aggregate('maintenance.oee_hourly', NULL, NULL); SELECT * FROM maintenance.oee_hourly LIMIT 5;"
```

The first two queries must return rows; INSERT must succeed; final SELECT must
show the synthesized row.

## Threat Flags

None — the migration adds new schema/hypertable with the same trust boundaries
already covered by Phase 3 baseline; the simulator extension publishes on
`maintenance.downtime.*` (mirror of existing `quality.events.*` subject family,
inherited STRIDE register).

## Self-Check: PASSED

- `infra/migrations/timescale/008_create_downtime_events.sql` — FOUND (commit 3e74f3d)
- `infra/migrations/timescale/tests/test_migration_008.py` — FOUND (commit 3e74f3d, 8 tests passing)
- `simulators/sim-textile/tests/test_downtime_generator.py` — FOUND (commit d8945e6, 13 tests passing)
- `simulators/sim-textile/src/sim_textile/downtime_event_generator.py` — FOUND (commit 306df71)
- Commit 3e74f3d — FOUND in git log
- Commit d8945e6 — FOUND in git log
- Commit 306df71 — FOUND in git log
- No STATE.md / ROADMAP.md / package.json modifications — confirmed (parallel executor isolation)

## TDD Gate Compliance

- RED commit (`test(07-05): ...`) — present at d8945e6
- GREEN commit (`feat(07-05): ...downtime_event_generator`) — present at 306df71
- Migration commit (Task 1) — single-commit TDD (SQL + testcontainers test
  written together; standard pattern per 07-01 / 06-01 precedent).
