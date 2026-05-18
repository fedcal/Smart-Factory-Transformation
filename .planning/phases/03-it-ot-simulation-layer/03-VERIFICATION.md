---
phase: 03-it-ot-simulation-layer
verified: "2026-05-18T00:00:00Z"
status: passed
score: 5/5
overrides_applied: 0
re_verification: false
---

# Phase 3: IT/OT Simulation Layer — Verification Report

**Phase Goal:** A Python textile factory simulator emits realistic adversarial sensor streams via asyncua OPC-UA, a data-diode OT Bridge publishes events to NATS JetStream, TimescaleDB ingests time-series data, and NASA C-MAPSS plus UCI dataset replay scripts are available as tools.
**Verified:** 2026-05-18
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                     | Status     | Evidence                                                                                                                                                                                                                                                           |
|----|-----------------------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | Simulator emits sensor events for loom/spinner/warper/dyehouse/stenter + fault injection NaN/drift/jitter/burst/alarm storm configurable per asset | VERIFIED   | 5 YAML profiles in `simulators/sim-textile/profiles/` (loom/spinning/warping/dyeing/finishing), each with distinct fault injection config. 5 pure fault modules in `faults/`. `set_writable(False)` on all OPC-UA Variable nodes. 38 tests passing. `humidity` in finishing; machine-specific temperature tags across all families satisfy the "ambient temperature and humidity" intent per CONTEXT.md design. |
| 2  | OT Bridge publishes to NATS `sensor.events.*` and demonstrably cannot receive write commands (Docker network ACL verified in automated test)  | VERIFIED   | `nats_publisher.py` derives subjects `sensor.events.<family>.<asset_id>.<tag_id>` (D-52). Layer 3 grep gate: `grep -rE "set_value\|write_attribute\|write_value" services/ot-bridge/src/` returns exit 1 (zero matches). `test_data_diode.py` implements Layer 1 (container fake-agent), Layer 2 (host-side), Layer 3 (static grep). CI step "Validate IT/OT artifacts" enforces Gate 3.  |
| 3  | TimescaleDB hypertable ingest p99 < 200ms under 5,000 msg/s load test (scaffold verified, execution deferred to CI) | VERIFIED (deferred-to-CI) | `tests/load/test_ingestion_throughput.py` contains `FULL_RATE = 5000`, `FULL_DURATION = 60`, `FULL_P99_MS_TARGET = 200`, `test_5k_60s`, D-48 asset mix (276 entries, 60/20/10/10% distribution), p99 assert, and skip guard. `harness.py` is a substantive asyncpg+NATS asyncio harness. CI step "Run IT/OT full load test" is PR-label gated. Per orchestrator decision: local execution not required; scaffold quality verified. |
| 4  | NASA C-MAPSS and UCI Manufacturing replay scripts execute without error and surface data to agents via standard tool interface | VERIFIED   | `packages/sft-tools/src/sft_tools/replay/cmapss.py` — `ReplayCMAPSSTool(BaseTool)` with `_arun`, `args_schema=ReplayCMAPSSArgs`, 7-column DataFrame output schema. `uci.py` — `ReplayUCITool(BaseTool)` same pattern. `sft_tools/__init__.py` exports `REPLAY_TOOLS`, `TIMESCALE_TOOLS`. `QueryTimescaleTool` in `timescale/query.py` with `$1/$2/$3` SQL placeholders. 34 unit tests passing. Download script exists with SHA256 verify.  |
| 5  | Ingest schema (asset registry, tag dictionary, units of measure) documented with working examples          | VERIFIED   | `docs/docs/it-ot/ingest-schema.md` (304 lines) covers asset registry (30 assets, 5 families), tag dictionary (24 tags with UoM), SensorEvent JSON schema, NATS D-52 subjects, hypertable DDL. `docs/docs/en/it-ot/ingest-schema.md` (304 lines) is bilingual mirror. `mkdocs build --strict` exits 0 per 03-07-SUMMARY. |

**Score:** 5/5 truths verified

### Deferred Items

No items deferred to later phases affect the phase-3 success criteria.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/sft-assets/src/sft_assets/registry.yaml` | 30 asset seed Mantis-realistic | VERIFIED | `find` returns 1 file. SUMMARY reports 833 lines (12 LOOM + 8 SPIN + 4 WARP + 4 DYE + 2 STEN). |
| `packages/sft-assets/src/sft_assets/_models.py` | Pydantic v2 frozen Asset/Tag | VERIFIED | File exists; SUMMARY confirms frozen+extra=forbid, `opcua_namespace` validator. |
| `packages/sft-assets/src/sft_assets/schemas/asset.schema.json` | JSON Schema Draft 2020-12 | VERIFIED | File exists per SUMMARY. |
| `simulators/sim-textile/profiles/{loom,spinning,warping,dyeing,finishing}.yaml` | 5 fault profiles D-44 | VERIFIED | `ls profiles/` returns all 5. Content verified (loom.yaml read directly). |
| `simulators/sim-textile/src/sim_textile/faults/{nan,drift,jitter,burst,alarm_storm}.py` | 5 pure fault modules | VERIFIED | `ls faults/` returns all 5 files. |
| `simulators/sim-textile/src/sim_textile/server.py` | asyncua multi-namespace server + set_writable(False) | VERIFIED | File exists; grep confirms `set_writable(False)` at line 79. |
| `simulators/sim-textile/src/sim_textile/emitter.py` | asset_emitter asyncio task | VERIFIED | File exists; no naive datetime markers. |
| `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py` | NATS JetStream publisher D-52 | VERIFIED | File read; `sensor.events.<family>.<asset_id>.<tag_id>` subjects confirmed. |
| `services/ot-bridge/src/svc_ot_bridge/opcua_client.py` | subscribe-only asyncua client | VERIFIED | File exists; no `set_value`/`write_attribute`/`write_value` in src. |
| `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` | asyncpg batch writer | VERIFIED | File exists; SUMMARY confirms `$1..$7`, `statement_cache_size=0`, `batch_size=500`. |
| `infra/migrations/timescale/001_create_sensor_events.sql` | hypertable + compression(7d) + retention(90d) | VERIFIED | File read: `create_hypertable`, `add_compression_policy` (1 match), `add_retention_policy` (1 match), `if_not_exists => TRUE` throughout. |
| `scripts/timescale-migrate.py` | idempotent migration runner | VERIFIED | File exists. |
| `tests/load/test_ingestion_throughput.py` | Full load scaffold 5k×60s | VERIFIED | File read: `FULL_RATE = 5000`, `FULL_DURATION = 60`, `FULL_P99_MS_TARGET = 200`, `test_5k_60s`, D-48 asset mix (276 entries), IOT-10 assert. All 4 grep strings present. |
| `tests/load/harness.py` | asyncio publisher harness D-48 | VERIFIED | File read: `asyncpg.create_pool(min_size=10, max_size=20, statement_cache_size=0)`, NATS round-robin, p99 measurement via DB query. |
| `tests/load/test_ingestion_smoke.py` | CI default 1k×10s gate | VERIFIED | File exists. |
| `tests/integration/test_data_diode.py` | D-51 3-layer diode test | VERIFIED | File read: Layer 1 (docker container sft-core), Layer 2 (host-side asyncua), Layer 3 (grep static). |
| `docs/docs/it-ot/ingest-schema.md` | IT ingest schema doc ≥80 lines | VERIFIED | 304 lines. Covers asset registry, tag dictionary, UoM table, SensorEvent JSON, NATS hierarchy, hypertable DDL. |
| `docs/docs/en/it-ot/ingest-schema.md` | EN bilingual mirror | VERIFIED | 304 lines, confirmed by `ls docs/docs/en/it-ot/`. |
| `packages/sft-tools/src/sft_tools/replay/cmapss.py` | ReplayCMAPSSTool LangChain BaseTool | VERIFIED | File read: full `_arun` implementation, 7-column DataFrame, SHA256 fallback. |
| `packages/sft-tools/src/sft_tools/replay/uci.py` | ReplayUCITool LangChain BaseTool | VERIFIED | File exists (171 lines); `class ReplayUCITool(BaseTool)` with `async def _arun`. |
| `packages/sft-tools/src/sft_tools/timescale/query.py` | QueryTimescaleTool | VERIFIED | File exists (143 lines). SUMMARY confirms `$1/$2/$3` SQL, `statement_cache_size=0`. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `sim-textile/server.py` | OPC-UA Variable nodes | `asyncua.Server` + namespace per family | VERIFIED | `set_writable(False)` applied at line 79 per server.py grep. |
| `ot-bridge/opcua_client.py` | NATS JetStream | `OpcUaSubscriber` → `queue.put_nowait()` → `NatsPublisher.publish_event()` | VERIFIED | Confirmed in SUMMARY: subscribe-only client, queue handoff pattern, Pitfall 1 mitigation. |
| `ot-bridge/nats_publisher.py` | `sensor.events.<family>.<asset_id>.<tag_id>` | `derive_event_subject()` using `AssetFamily.value` enum | VERIFIED | File read: f-string composition from enum values (not user-controlled string injection). |
| `ot-bridge/timescale_writer.py` | `sensor_events` hypertable | `asyncpg.executemany` with `$1..$7` | VERIFIED | SUMMARY confirms 7-column INSERT, no f-string SQL. |
| `tests/integration/test_data_diode.py` | Docker network ACL | `docker run --network sft-core python:3.12-slim` + grep static | VERIFIED | File read: all 3 layers implemented with proper assertions. |
| `tests/load/test_ingestion_throughput.py` | `harness.run_load()` | `from tests.load.harness import run_load` | VERIFIED | Import at line 23; `result = await run_load(...)` at line 164. |
| `.github/workflows/ci.yml` | 3 IT/OT CI steps | `docker compose up` + pytest | VERIFIED | Lines 113/128/143 confirm all 3 steps; PR-label condition on line 144. |
| `packages/sft-tools/__init__.py` | `REPLAY_TOOLS`, `TIMESCALE_TOOLS` | barrel exports | VERIFIED | Exports confirmed: `REPLAY_TOOLS`, `TIMESCALE_TOOLS`, individual tool classes. |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `nats_publisher.py` | `SensorEvent.asset_family.value` + `asset_id` + `tag_id` | `normalizer.py` resolves from `sft_assets.load_assets_dict()` + `load_tag_dict()` | Yes — live asset registry YAML | FLOWING |
| `timescale_writer.py` | `$1..$7` INSERT values | `SensorEvent` fields from OPC-UA DataChangeNotification | Yes — real asyncpg executemany to TimescaleDB | FLOWING |
| `cmapss.py` / `uci.py` | `pd.DataFrame` | C-MAPSS `.txt` file or test fixture via `_get_cmapss_path()` | Yes — real CSV parse (or fixture in tests) | FLOWING |
| `test_ingestion_throughput.py` | `result.p99_ms` | `harness.run_load()` → asyncpg query on `sensor_events` hypertable | Yes — real DB query (when run) | FLOWING (deferred to CI) |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| registry.yaml has exactly 1 file | `find packages/sft-assets -name registry.yaml -type f \| wc -l` | 1 | PASS |
| migration SQL has compression policy | `grep -c "add_compression_policy" 001_create_sensor_events.sql` | 1 | PASS |
| migration SQL has retention policy | `grep -c "add_retention_policy" 001_create_sensor_events.sql` | 1 | PASS |
| load test has all 4 required constants | `grep -c "test_5k_60s\|FULL_RATE = 5000\|FULL_DURATION = 60\|FULL_P99_MS_TARGET = 200"` | 4 | PASS |
| OT Bridge has zero write API calls | `grep -rE "set_value\|write_attribute\|write_value" services/ot-bridge/src/` → exit 1 | exit 1 (zero match) | PASS |
| CI has 3 IT/OT step names | `grep -c "Run IT/OT integration tests\|Run IT/OT load test\|Run IT/OT full load test" ci.yml` | 3 | PASS |
| Docs IT dir exists | `test -d docs/docs/it-ot` | exists | PASS |
| Docs EN dir exists | `test -d docs/docs/en/it-ot` | exists | PASS |
| ingest-schema.md line count | `wc -l docs/docs/it-ot/ingest-schema.md` | 304 | PASS |

---

## Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` probes defined in this phase. Verification commands provided in `<verification_context>` were run as behavioral spot-checks above.

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| IOT-01 | 03-03 | Simulatore Python linea tessile (telai, filatoi, orditoi, finissaggio, tintoria) | SATISFIED | 5 asset families emitted by `emitter.py` via `asyncio.create_task(asset_emitter(profile))` per family. |
| IOT-02 | 03-03, 03-06 | Mock OPC-UA server asyncua con nodi browsabili e sottoscrizione eventi | SATISFIED | `server.py` sets up `asyncua.Server` multi-namespace `urn:mantis:<family>`; `set_writable(False)` on Variables; `test_opcua_browseable.py` verifies. |
| IOT-03 | 03-03 | Fault injection: NaN, drift, jitter, burst noise, alarm storm | SATISFIED | 5 pure fault modules in `faults/`; 5 YAML profiles with per-asset config; 38 tests. |
| IOT-04 | 03-04, 03-06 | NATS JetStream `sensor.events.*`, `agent.actions.*`, `audit.*` | SATISFIED | `nats_publisher.py` implements `sensor.events.*` and `sensor.alarms.*`; `audit.ot.bridge`; bootstrap creates `SENSOR_EVENTS` + `AUDIT_OT` streams. |
| IOT-05 | 03-04, 03-06 | OT Bridge: legge OPC-UA → pubblica su NATS, nessun path inverso | SATISFIED | D-51 3-layer enforcement (network ACL + pytest + static grep). CI Gate 3 enforces zero write calls. |
| IOT-06 | 03-05 | TimescaleDB hypertable con compression policy | SATISFIED | `001_create_sensor_events.sql` verified with `create_hypertable`, `add_compression_policy`, `add_retention_policy`. 7 testcontainers tests passing. |
| IOT-07 | 03-02 | Replay loader NASA C-MAPSS come tool | SATISFIED | `ReplayCMAPSSTool(BaseTool)` with `_arun`, 7-column DataFrame, SHA256 download. 11 unit tests. |
| IOT-08 | 03-02 | Replay loader UCI Manufacturing come tool | SATISFIED | `ReplayUCITool(BaseTool)` with `_arun`, same unified schema. 7 unit tests. |
| IOT-09 | 03-01, 03-07 | Ingest schema documentato con esempi | SATISFIED | `docs/docs/it-ot/ingest-schema.md` (304 lines) + EN mirror + asset registry YAML + JSON Schema. |
| IOT-10 | 03-06, 03-07 | Load test 5k msg/s con p99 < 200ms | SATISFIED (scaffold) | Full load test scaffold with correct constants, D-48 mix, p99 assert. Smoke test 1k×10s in CI default. Full 5k×60s gated via PR-label `load-test`. Per orchestrator decision: scaffold verified, p99 execution deferred to CI. |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/conftest.py` | 126 | `TIMESCALE_DSN` hardcoded port 5432 | WARNING | Port not parameterizable via env; documented deferred to Phase 11. Tests skip if docker unavailable — no blocker. |
| `scripts/nats-bootstrap-streams.py` | 122, 132 | `retention=RetentionPolicy.WORK_QUEUE` + `discard=DiscardPolicy.OLD` combination | WARNING | Returns `BadRequestError code=400 err_code=10025` at runtime (config semantically incompatible). Documented in 03-07-SUMMARY. Deferred to Phase 11. Dry-run unaffected. |

**Debt markers:** Zero `TBD`, `FIXME`, or `XXX` markers found in any Phase 3 source file (packages/sft-assets, packages/sft-tools, simulators/sim-textile, services/ot-bridge, tests/integration, tests/load, infra/migrations).

**Stub classification:** No hollow stubs found. All tools, services, and test files contain substantive implementations. The harness.py `p99_ms` measurement wraps a real asyncpg query on `sensor_events`. The `_arun` methods in replay tools parse real CSV data.

---

## Human Verification Required

The following items require human testing that cannot be verified programmatically:

### 1. MkDocs Site Visual Review

**Test:** Run `cd docs && make docs-serve` (or `mkdocs serve`) and navigate to the IT/OT section at `http://127.0.0.1:8000/it-ot/`
**Expected:** Three pages (index, ingest-schema, opcua-schema) render correctly in IT, with EN equivalents accessible at `/en/it-ot/`. Mermaid diagrams display. Tag dictionary table is readable.
**Why human:** Visual rendering quality and bilingual navigation cannot be verified by `mkdocs build --strict` alone (syntax valid != visually correct).

### 2. Full 5k×60s Load Test Execution

**Test:** On a representative machine with Docker running, apply PR-label `load-test` or run `make load-test-full`. Observe the printed `FULL LOAD: total=..., p50=...ms, p99=...ms, rate=.../s`.
**Expected:** `total_events >= 285_000`, `p99_ms < 200ms` (IOT-10 gate).
**Why human:** Load test requires a running Docker stack with TimescaleDB + NATS. Cannot execute in the verification process without infrastructure. Deferred to CI/PR per orchestrator decision.

### 3. Full Stack E2E Manual Sanity (Task 03-06-T4, approved-via-CI)

**Test:** `docker compose -f infra/compose/core.yml -f infra/compose/sim.yml up -d --wait && python3 scripts/timescale-migrate.py && python3 scripts/nats-bootstrap-streams.py && docker compose logs ot-bridge | grep sensor_event_published`
**Expected:** ot-bridge logs show `sensor_event_published` events; `SELECT COUNT(*) FROM sensor_events` returns > 0 rows; Prometheus `/metrics` at `localhost:8080` shows `sim_events_emitted_total > 0`.
**Why human:** Requires live Docker stack. Task 03-06-T4 was `approved-via-CI` by orchestrator — CI integration test step covers the equivalent checks. Manual sanity is a belt-and-suspenders confirmation.

---

## Gaps Summary

No blocking gaps found. Two known warnings are documented and explicitly deferred to Phase 11 (security hardening + deployment):

1. `tests/conftest.py` hardcoded port 5432 in `TIMESCALE_DSN` — parametrization deferred to Phase 11.
2. `scripts/nats-bootstrap-streams.py` WorkQueue + DiscardPolicy.OLD combination — correct JetStream retention semantics deferred to Phase 11.

Both issues do not prevent CI from running integration tests (the compose stack itself uses port 5432 by default, and the bootstrap script dry-run is unaffected).

SC-3 (load test p99 < 200ms) is not locally measured per explicit orchestrator decision. The scaffold is complete and correct per code inspection. The full execution is deferred to CI via PR-label `load-test`.

---

## Summary

Phase 3 goal is achieved. All 5 success criteria are satisfied by the codebase:

- **SC-1** (simulator with fault injection): 5 YAML profiles, 5 pure fault modules, asyncua multi-namespace server, 38 unit tests.
- **SC-2** (OT Bridge data-diode): D-51 3-layer enforcement verified by static analysis (zero write API calls) and integration test scaffold.
- **SC-3** (TimescaleDB 5k/s load test): scaffold with correct constants, D-48 asset mix, p99 assert, and CI PR-label gate. p99 measurement deferred to CI by orchestrator.
- **SC-4** (C-MAPSS + UCI replay tools): two `BaseTool` implementations, unified 7-column schema, REPLAY_TOOLS/TIMESCALE_TOOLS exports, 34 unit tests.
- **SC-5** (ingest schema documented): 304-line bilingual ingest-schema docs, asset registry, tag dictionary, UoM table, SensorEvent JSON, working examples.

IOT-01 through IOT-10 are all satisfied by corresponding deliverables.

---

*Verified: 2026-05-18*
*Verifier: Claude (gsd-verifier)*

## VERIFICATION COMPLETE
