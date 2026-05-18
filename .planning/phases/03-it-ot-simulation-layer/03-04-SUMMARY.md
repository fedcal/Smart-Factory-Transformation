---
phase: 03-it-ot-simulation-layer
plan: "04"
subsystem: ot-bridge
tags: [asyncua, nats-jetstream, asyncpg, timescaledb, pydantic-frozen, data-diode, prometheus]

# Dependency graph
requires:
  - phase: 03-01-sft-assets
    provides: "Asset, Tag, AssetFamily, load_assets_dict, load_tag_dict — risoluzione asset_family e unit in normalizer"
  - phase: 01-foundation-monorepo
    provides: "services/ot-bridge scaffold, docker-compose, NATS + TimescaleDB services"

provides:
  - "SensorEvent Pydantic v2 frozen+extra=forbid con @field_validator tz-aware enforcement"
  - "AuditEvent frozen per audit.ot.bridge OQ3 contract"
  - "normalize_datachange() pure function OPC-UA DataChangeNotification → SensorEvent"
  - "NatsPublisher JetStream publish su sensor.events/sensor.alarms/audit.ot.bridge (D-52)"
  - "TimescaleWriter asyncpg pool min_size=10 max_size=20 statement_cache_size=0 command_timeout=10.0 + executemany batch=500 flush=100ms"
  - "OpcUaSubscriber asyncua subscribe-only (D-51 Layer 3) con publishing_interval=50ms queue handoff"
  - "main.py asyncio orchestrator con SIGINT/SIGTERM graceful shutdown + AuditEvent lifecycle"
  - "scripts/nats-bootstrap-streams.py idempotente — SENSOR_EVENTS WorkQueue 7d + AUDIT_OT Limits 30d"
  - "Dockerfile multi-stage python:3.12-slim — container sft-ot-bridge buildable"
  - "Prometheus metrics: ingest_latency_histogram, events_published_total, asyncpg_pool_size_used_gauge"

affects:
  - "03-05-timescale-migration — schema sensor_events deve matchare $1..$7 INSERT SQL"
  - "03-06-compose-integration — Dockerfile + env vars OPCUA_URL/NATS_URL/TIMESCALE_DSN"
  - "03-07-load-test — asyncpg pool config e batch write path"
  - "Phase 4 agents — NATS subjects sensor.events.<family>.<asset_id>.<tag_id>"

# Tech tracking
tech-stack:
  added:
    - "asyncua>=1.1.8 — OPC-UA client subscribe-only"
    - "nats-py>=2.14 — NATS JetStream publisher"
    - "asyncpg>=0.30 — PostgreSQL/TimescaleDB async pool"
    - "structlog>=25.5 — JSON structured logging"
    - "prometheus-client>=0.21 — Prometheus metrics endpoint"
  patterns:
    - "Data-diode application layer (D-51 Layer 3): zero write API calls verified by CI grep gate"
    - "Subject hierarchy D-52: sensor.events.<family>.<asset_id>.<tag_id> + sensor.alarms + audit.ot"
    - "asyncpg pool: statement_cache_size=0 mandatory for TimescaleDB (Pitfall 6)"
    - "TDD RED/GREEN: test written before implementation, 14 tests cover all behaviors"
    - "NaN→None mapping for JSON-safe SensorEvent.value (A-002 sensor disconnect)"
    - "Queue handoff pattern: OPC-UA callback → asyncio.Queue → worker task (Pitfall 1)"
    - "Idempotent JetStream bootstrap: add_stream → BadRequestError → update_stream (Pitfall 3)"

key-files:
  created:
    - "services/ot-bridge/src/svc_ot_bridge/models.py — SensorEvent + AuditEvent Pydantic frozen"
    - "services/ot-bridge/src/svc_ot_bridge/normalizer.py — pure normalize_datachange()"
    - "services/ot-bridge/src/svc_ot_bridge/nats_publisher.py — NatsPublisher + subject derivation"
    - "services/ot-bridge/src/svc_ot_bridge/timescale_writer.py — TimescaleWriter asyncpg batch"
    - "services/ot-bridge/src/svc_ot_bridge/metrics.py — Prometheus metrics"
    - "services/ot-bridge/src/svc_ot_bridge/opcua_client.py — OpcUaSubscriber asyncua"
    - "services/ot-bridge/src/svc_ot_bridge/main.py — asyncio orchestrator"
    - "services/ot-bridge/Dockerfile — multi-stage build"
    - "services/ot-bridge/tests/conftest.py + test_normalizer.py + test_subject_derivation.py + test_publisher.py + test_writer.py"
    - "scripts/nats-bootstrap-streams.py — NATS bootstrap idempotente"
  modified:
    - "services/ot-bridge/pyproject.toml — deps asyncua/nats-py/asyncpg/pydantic/structlog/prometheus-client/sft-assets"
    - "services/ot-bridge/project.json — implicitDependencies += sft-assets"
    - "services/ot-bridge/src/svc_ot_bridge/__init__.py — barrel export"

key-decisions:
  - "IOT-04 NATS subjects D-52 locked: sensor.events.<family>.<asset_id>.<tag_id> + sensor.alarms + audit.ot.bridge"
  - "IOT-05 D-51 Layer 3: subscribe-only asyncua.Client, CI grep gate verifica zero write API calls"
  - "IOT-06 asyncpg writer: statement_cache_size=0 mandatory (TimescaleDB piano dinamico incompatibile con prepared cache)"
  - "OQ3 resolution: solo ot-bridge pubblica su audit.ot.bridge — sim-textile NON pubblica audit"
  - "Pitfall 1 mitigation: callback datachange_notification solo queue.put_nowait(), worker task fa il lavoro pesante"
  - "Pitfall 3 mitigation: bootstrap script try add_stream → except BadRequestError → update_stream (idempotent)"
  - "Pitfall 6: asyncpg pool statement_cache_size=0 + command_timeout=10.0 per TimescaleDB"
  - "NaN→None mapping: opcua_value NaN → SensorEvent.value=None (JSON-safe, A-002 sensor disconnect)"

patterns-established:
  - "Pattern: Pydantic v2 frozen + @field_validator tz-aware enforcement per tutti i modelli datetime"
  - "Pattern: CI grep gate D-51 = grep -rE (set_value|write_attribute|write_value) exit 1"
  - "Pattern: CI grep gate SQL injection = grep -rE 'f\"(INSERT|SELECT|UPDATE|DELETE)' exit 1"
  - "Pattern: argparse + --dry-run + WORKSPACE_ROOT per script NATS bootstrap (Pattern S-3 + S-4)"

requirements-completed: [IOT-04, IOT-05]

# Metrics
duration: 35min
completed: 2026-05-18
---

# Phase 3 Plan 04: OT Bridge Implementation Summary

**ot-bridge container implementato — data-diode OPC-UA→NATS JetStream + asyncpg TimescaleDB writer con CI grep gates D-51/SQL/tz-naive verdi e 14/14 unit test.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-05-18T12:45:00Z
- **Completed:** 2026-05-18T13:20:00Z
- **Tasks:** 2/2
- **Files modified:** 15 (10 creati + 5 modificati)

## Accomplishments

### Task 1: SensorEvent + normalizer + publisher + writer (TDD RED/GREEN)

**TDD RED phase** (commit `6250724`): 14 test scritti prima dell'implementazione — confermato fallimento su `ModuleNotFoundError`.

**TDD GREEN phase** (commit `569cb41`): implementazione completa, tutti 14 test verde:

- `SensorEvent` Pydantic v2 frozen+extra=forbid: campi `asset_id, asset_family, tag_id, timestamp_utc, value, unit, quality_code, source, server_received_ts`. Validator `tzinfo is not None` su entrambi i timestamp (T-03-04-tz-naive).
- `AuditEvent` frozen per OQ3: `ts, level, event_type, details` — solo ot-bridge pubblica su `audit.ot.bridge`.
- `normalize_datachange()` pure function: risolve `asset_family` e `unit` da `sft-assets` `load_assets_dict()` + `load_tag_dict()`; NaN→None (A-002).
- `NatsPublisher`: `derive_event_subject/derive_alarm_subject/derive_audit_subject` (D-52); `publish_event` pubblica anche su alarm subject se `quality_code != 0`.
- `TimescaleWriter`: `_INSERT_SQL` costante con `$1..$7` placeholder; pool `min_size=10 max_size=20 statement_cache_size=0 command_timeout=10.0` (Pitfall 6); buffer `batch_size=500` + flush `100ms`.
- `metrics.py`: Prometheus `nats_pending_acks_gauge`, `ingest_latency_histogram`, `events_published_total`, `asyncpg_pool_size_used_gauge`.

### Task 2: asyncua client + main orchestrator + Dockerfile + NATS bootstrap (commit `d11b91f`)

- `OpcUaSubscriber`: asyncua `Client` subscribe-only; `publishing_interval=50ms, samples_per_publish=10` (Pitfall 1); callback `datachange_notification` = solo `queue.put_nowait()` senza lavoro pesante; drop esplicito + log se queue piena.
- `main.py`: asyncio `run()` orchestra NatsPublisher + TimescaleWriter + OpcUaSubscriber via `Queue(maxsize=10000)`; SIGINT/SIGTERM graceful shutdown; `AuditEvent bridge_start/bridge_stop` (OQ3); `TIMESCALE_DSN` required con fail-fast.
- `Dockerfile`: multi-stage `python:3.12-slim`; `uv==0.5.0` nel builder; `USER 1000:1000`; `EXPOSE 8080`.
- `nats-bootstrap-streams.py`: idempotente `add_stream → BadRequestError → update_stream` (Pitfall 3); `SENSOR_EVENTS` WorkQueue 7d + `AUDIT_OT` Limits 30d; `--dry-run` exit 0.

## Test Results

```
14 passed in 0.56s
```

| Test | Status |
|------|--------|
| test_normalize_basic | PASS |
| test_nan_value | PASS |
| test_immutability | PASS |
| test_timestamp_tz_required | PASS |
| test_quality_code_alarm_passthrough | PASS |
| test_publish_event | PASS |
| test_publish_audit | PASS |
| test_event_subject | PASS |
| test_alarm_subject | PASS |
| test_audit_subject | PASS |
| test_executemany_placeholder | PASS |
| test_batch_size | PASS |
| test_flush_interval | PASS |
| test_pool_config | PASS |

## CI Grep Gates

| Gate | Command | Status |
|------|---------|--------|
| D-51 Layer 3 (no write API) | `grep -rE "(set_value\|write_attribute\|write_value)" services/ot-bridge/src/` | PASS (exit 1, zero match) |
| SQL injection (no f-string) | `grep -rE 'f"(INSERT\|SELECT\|UPDATE\|DELETE)' services/ot-bridge/src/` | PASS (exit 1, zero match) |
| naive datetime | `grep -rE "datetime\.now\(\)" services/ot-bridge/src/` | PASS (exit 1, zero match) |

## NATS Bootstrap Script

```
python3 scripts/nats-bootstrap-streams.py --dry-run --server nats://localhost:4222
# → EXIT 0, stdout: SENSOR_EVENTS + AUDIT_OT configs + "would create/update"
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CI grep gate D-51 falso positivo su docstrings**
- **Found during:** Task 1 verifiche finali
- **Issue:** I docstring in `__init__.py`, `normalizer.py`, `nats_publisher.py` citavano i pattern proibiti (`set_value`, `write_attribute`, `write_value`) nei commenti "ZERO chiamate..." — il grep colpiva i commenti oltre al codice eseguibile.
- **Fix:** Riformulato i docstring per descrivere il vincolo senza citare le parole chiave vietate. Es: "D-51 Layer 3: subscribe-only OPC-UA client, zero write API calls".
- **Files modified:** `__init__.py`, `normalizer.py`, `nats_publisher.py`

**2. [Rule 1 - Bug] asyncpg pool mock context manager incompatibilità**
- **Found during:** Task 1 test_writer.py TestBatchSize e TestPoolConfig
- **Issue 1:** `pool.acquire.return_value.__aenter__` non funziona correttamente con `AsyncMock` — il context manager asincrono richiedeva un `MagicMock` con `__aenter__`/`__aexit__` separati.
- **Issue 2:** `asyncpg.create_pool` patch con `return_value=AsyncMock()` causava `TypeError: object AsyncMock can't be used in 'await' expression` — la patch doveva usare `AsyncMock(return_value=pool_instance)` come coroutine.
- **Fix:** Refactoring conftest `mock_pool` fixture + TestPoolConfig patch corretto.
- **Files modified:** `tests/conftest.py`, `tests/test_writer.py`

**3. [Rule 1 - Bug] `nats-bootstrap-streams.py` dry-run importava `nats` inutilmente**
- **Found during:** Task 2 verifica `python3 scripts/nats-bootstrap-streams.py --dry-run`
- **Issue:** `import nats` era all'inizio della funzione `bootstrap()`, prima della guardia `if dry_run`. In ambienti senza `nats-py` installato, il `--dry-run` falliva con `ModuleNotFoundError`.
- **Fix:** Spostato `import nats` e `from nats.js.api import ...` dopo la guardia `if dry_run: return 0`. Aggiunto dizionari spec per la stampa dry-run senza dipendenza da StreamConfig.

## Known Stubs

Nessuno — tutti i componenti sono cablati con logica reale (nessun placeholder hardcoded).

- `TimescaleWriter` richiede un DB reale per write (testato con mock). Test di integrazione in Plan 03-06.
- `OpcUaSubscriber` richiede un server OPC-UA reale (sim-textile). Test di integrazione in Plan 03-06.
- `NatsPublisher` richiede NATS reale per publish. Test di integrazione in Plan 03-06.

## Threat Flags

Nessuna superficie di sicurezza aggiuntiva rispetto a quella documentata nel threat model del piano.

I threat register T-03-04-diode-app, T-03-04-sql, T-03-04-tz-naive sono tutti mitigati con CI gate verdi.

## TDD Gate Compliance

- RED gate: commit `6250724` — `test(03-04-sensor-event): add failing tests RED phase`
- GREEN gate: commit `569cb41` — `feat(03-04-sensor-event): SensorEvent + normalizer + publisher + writer — GREEN phase`
- REFACTOR: non necessario (codice già pulito)

## Self-Check: PASSED

- services/ot-bridge/src/svc_ot_bridge/models.py — FOUND
- services/ot-bridge/src/svc_ot_bridge/normalizer.py — FOUND
- services/ot-bridge/src/svc_ot_bridge/nats_publisher.py — FOUND
- services/ot-bridge/src/svc_ot_bridge/timescale_writer.py — FOUND
- services/ot-bridge/src/svc_ot_bridge/metrics.py — FOUND
- services/ot-bridge/src/svc_ot_bridge/opcua_client.py — FOUND
- services/ot-bridge/src/svc_ot_bridge/main.py — FOUND
- services/ot-bridge/Dockerfile — FOUND
- scripts/nats-bootstrap-streams.py — FOUND
- Commit 6250724 — FOUND
- Commit 569cb41 — FOUND
- Commit d11b91f — FOUND
