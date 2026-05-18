---
phase: 3
slug: it-ot-simulation-layer
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-18
updated: 2026-05-18
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `03-RESEARCH.md` § Validation Architecture (single source of truth).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24+ (Phase 1 lock) + testcontainers-python for integration |
| **Config file** | `pyproject.toml` per Nx project (`[tool.pytest.ini_options]`) + workspace-root `tests/conftest.py` (Plan 03-06) |
| **Quick run command** | `npx nx affected --target=test` |
| **Full suite command** | `npx nx run-many --target=test --all && uv run --with pytest --with pytest-asyncio --with testcontainers --with asyncpg --with asyncua --with nats-py -- python -m pytest tests/integration tests/load -m "not load_full"` |
| **Phase gate** | `uv run pytest tests/load/test_ingestion_throughput.py --full-load-test` (PR-label `load-test`) + smoke 1k×10s default in CI |
| **Estimated runtime** | ~5 s (Nx affected) / ~60 s (full unit + smoke) / ~120 s (full integration incl. data-diode docker spin-up) / ~75 s (full load test 5k×60s) |

---

## Sampling Rate

- **After every task commit:** `npx nx affected --target=test` (auto-scoped to modified project)
- **After every plan wave:** `npx nx run-many --target=test --all` + smoke load test (1k×10s)
- **Before `/gsd:verify-work`:** Full unit + integration green + smoke load + manual full load test (5k×60s) via PR label
- **Max feedback latency:** 5 s (Nx affected) / 60 s (wave merge) / 75 s (full load gate)

---

## Per-Task Verification Map

> Updated by planner Step 8 (2026-05-18). Plan IDs sono `03-NN`; Task IDs sono `03-NN-T<N>` (Plan NN, Task <N>).
> Tutti i test file sono creati nel rispettivo Plan (Wave 0 dependency = creazione del file di test all'interno dello stesso Plan che lo verifica).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-T1 | 03-01 | 1 | IOT-09 | T-V5-yaml + T-V12-asset | Pacchetto sft-assets: Pydantic frozen + JSON Schema Draft 2020-12 self-valid + yaml.safe_load only | schema/unit | `uv run --project packages/sft-assets pytest packages/sft-assets/tests -x -v` | ✅ creato in 03-01-T1 | ⬜ pending |
| 03-01-T2 | 03-01 | 1 | IOT-09 | T-V12-asset | Asset registry 30 asset Mantis-realistic, breakdown 12+8+4+4+2, validate via CLI script | unit | `python3 scripts/validate-asset-registry.py && uv run --project packages/sft-assets pytest packages/sft-assets/tests -k registry` | ✅ creato in 03-01-T1 (test_registry_validation.py) + 03-01-T2 (validate-asset-registry.py) | ⬜ pending |
| 03-02-T1 | 03-02 | 1 | IOT-07 + IOT-08 | T-V5-pydantic + T-V5-sql | LangChain Tools (replay_cmapss, replay_uci, query_timescale) con args_schema Pydantic v2 + ReplayRecord frozen + $1..$N placeholder SQL | unit | `uv run --project packages/sft-tools pytest packages/sft-tools/tests -x -v` | ✅ creato in 03-02-T1 | ⬜ pending |
| 03-02-T2 | 03-02 | 1 | IOT-07 + IOT-08 | T-V5-sql + replay tamper | Download script SHA256 verify + gitignored data dir | unit | `python3 scripts/download-replay-datasets.py --dry-run --dataset all` | ✅ creato in 03-02-T2 | ⬜ pending |
| 03-03-T1 | 03-03 | 2 | IOT-03 | T-V5-pydantic | Fault state machine pure functions (nan/drift/jitter/burst/alarm_storm) + 5 YAML profile + JSON Schema | unit | `uv run --project simulators/sim-textile pytest simulators/sim-textile/tests -x -v && python3 scripts/validate-fault-profiles.py` | ✅ creato in 03-03-T1 | ⬜ pending |
| 03-03-T2 | 03-03 | 2 | IOT-01 + IOT-02 (server-side) | T-DATA-DIODE Layer 0 | asyncua server multi-namespace + Variable set_writable(False); emitter UTC datetime + Prometheus metrics | unit | `uv run --project simulators/sim-textile pytest simulators/sim-textile/tests/test_emitter.py -x -v` | ✅ creato in 03-03-T2 | ⬜ pending |
| 03-04-T1 | 03-04 | 2 | IOT-04 + IOT-05 (Layer 3) | T-V5-sql + T-V5-pydantic + T-DATA-DIODE Layer 3 | SensorEvent + normalizer + subject derivation + NATS publisher + asyncpg writer (executemany $1..$7, statement_cache_size=0, min/max pool 10/20) | unit | `uv run --project services/ot-bridge pytest services/ot-bridge/tests -x -v && ! grep -rE "(set_value|write_attribute|write_value)" services/ot-bridge/src/` | ✅ creato in 03-04-T1 | ⬜ pending |
| 03-04-T2 | 03-04 | 2 | IOT-04 + IOT-05 | T-NATS-subject + T-DATA-DIODE | asyncua client subscribe-only + main asyncio orchestrator + idempotent NATS bootstrap script (Pitfall 3) | smoke/script | `python3 scripts/nats-bootstrap-streams.py --dry-run --server nats://localhost:4222` | ✅ creato in 03-04-T2 | ⬜ pending |
| 03-05-T1 | 03-05 | 2 | IOT-06 | T-V5-sql | TimescaleDB hypertable + compression(7d) + retention(90d) + indici; migration idempotent (CREATE IF NOT EXISTS + DO block + if_not_exists=>TRUE) | unit/integration | `uv run -m pytest infra/migrations/timescale/tests -m testcontainers -x -v` | ✅ creato in 03-05-T1 (test_migration_idempotent.py) | ⬜ pending |
| 03-05-T2 | 03-05 | 2 | IOT-06 | T-V5-sql | [BLOCKING] schema-push: applicare migration al dev compose stack TimescaleDB | manual/integration | `python3 scripts/timescale-migrate.py` (dopo `docker compose up timescaledb`) | ✅ runtime check | ⬜ pending |
| 03-06-T1 | 03-06 | 3 | IOT-02 + IOT-04 + IOT-05 | T-DATA-DIODE Layer 1 | docker-compose dual-network sft-ot + sft-core; NATS realineato; ot-bridge è unico container dual-network | unit | `docker compose -f infra/compose/core.yml -f infra/compose/sim.yml config` exit 0 | ✅ creato in 03-06-T1 | ⬜ pending |
| 03-06-T2 | 03-06 | 3 | IOT-02 + IOT-04 + IOT-05 + IOT-10 (smoke) | T-DATA-DIODE Layer 1+2+3 + T-PERF | 3-layer data-diode test + OPC-UA browseable + NATS subjects + E2E sim→Timescale + smoke 1k×10s p99<200ms | integration/load | `uv run pytest tests/integration tests/load/test_ingestion_smoke.py -v -m integration` | ✅ creato in 03-06-T2 | ⬜ pending |
| 03-06-T3 | 03-06 | 3 | IOT-02..10 enforcement | tutti | CI workflow esteso con 3 step (validate, integration, smoke load) + workspace dev deps | integration | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` + Github Actions run | ✅ modified in 03-06-T3 | ⬜ pending |
| 03-06-T4 | 03-06 | 3 | IOT-05 manual | T-DATA-DIODE | Manual checkpoint: avvio stack + log inspection + verifica E2E + assert TimescaleDB ha dati | manual | (vedi how-to-verify 11 step) | ⚠ Manual-Only | ⬜ pending |
| 03-07-T1 | 03-07 | 4 | IOT-10 (full) | T-PERF | Full load test 5k×60s steady-state asset mix D-48, p99 < 200ms; PR-label gated in CI | load | `uv run pytest tests/load/test_ingestion_throughput.py -v -m load_full --full-load-test` | ✅ creato in 03-07-T1 | ⬜ pending |
| 03-07-T2 | 03-07 | 4 | IOT-09 | — | MkDocs docs/docs/it-ot/ 3 pagine IT + 3 EN mirror; mkdocs strict build verde | integration | `cd docs && mkdocs build --strict` | ✅ Phase 1 (docs-deploy.yml) + 03-07-T2 (file creati) | ⬜ pending |
| 03-07-T3 | 03-07 | 4 | IOT-09 + IOT-10 review | — | Manual checkpoint: mkdocs preview review + (opzionale) full load test sanity | manual | (vedi how-to-verify Plan 03-07 Task 3) | ⚠ Manual-Only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements (Wave 0 = scaffolding richiesto da test, integrato nei rispettivi Plan)

Wave 0 (foundation) MUST ship the following before any downstream task runs. All paths are new in Phase 3 and creati IN-PLAN (no separate Wave 0 plan).

**New Nx packages (Plan 03-01 + 03-02):**
- [x] `packages/sft-assets/{pyproject.toml,project.json,src/sft_assets/,tests/}` — registry + Pydantic loader (Plan 03-01-T1)
- [x] `packages/sft-tools/{pyproject.toml,project.json,src/sft_tools/,tests/}` — LangChain Tools (Plan 03-02-T1)

**Pydantic models + loader (Plan 03-01-T1):**
- [x] `packages/sft-assets/src/sft_assets/_models.py` — `Asset`, `Tag`, `AssetFamily`, `SemanticType`
- [x] `packages/sft-assets/src/sft_assets/_loader.py` — `load_assets`, `load_assets_dict`, `load_tag_dict` lru_cache
- [x] `packages/sft-assets/src/sft_assets/schemas/asset.schema.json` — Draft 2020-12
- [x] `packages/sft-tools/src/sft_tools/replay/{cmapss.py,uci.py,models.py}` — BaseTool + ReplayRecord (Plan 03-02-T1)
- [x] `packages/sft-tools/src/sft_tools/timescale/query.py` — QueryTimescaleTool (Plan 03-02-T1)

**sim-textile (Plan 03-03):**
- [x] `simulators/sim-textile/src/sim_textile/{main.py,server.py,emitter.py,faults/*,profile_loader.py,metrics.py,models.py,cli.py}`
- [x] `simulators/sim-textile/profiles/{loom,spinning,warping,dyeing,finishing}.yaml` (5)
- [x] `simulators/sim-textile/schemas/fault-profile.schema.json`
- [x] `simulators/sim-textile/Dockerfile`
- [x] `simulators/sim-textile/tests/{conftest.py,test_emitter.py,test_faults.py,test_profile_loader.py,test_profile_validation.py}`

**ot-bridge (Plan 03-04):**
- [x] `services/ot-bridge/src/svc_ot_bridge/{main.py,opcua_client.py,normalizer.py,nats_publisher.py,timescale_writer.py,models.py,metrics.py}`
- [x] `services/ot-bridge/Dockerfile`
- [x] `services/ot-bridge/tests/{conftest.py,test_normalizer.py,test_subject_derivation.py,test_publisher.py,test_writer.py}`

**Infra migrations (Plan 03-05):**
- [x] `infra/migrations/timescale/{001_create_sensor_events.sql,migrate.py,tests/test_migration_idempotent.py}` — Hypertable + compression + retention (D-49)
- [x] `scripts/timescale-migrate.py` — CLI wrapper
- [x] `scripts/nats-bootstrap-streams.py` — Idempotent JetStream `SENSOR_EVENTS` + `AUDIT_OT` stream creation (Plan 03-04-T2)
- [x] `scripts/download-replay-datasets.py` — SHA256 verify (Plan 03-02-T2)
- [x] `scripts/validate-asset-registry.py` (Plan 03-01-T2)
- [x] `scripts/validate-fault-profiles.py` (Plan 03-03-T1)

**Integration tests + load test (Plan 03-06):**
- [x] `tests/conftest.py` — compose_stack session-scoped fixture
- [x] `tests/integration/test_data_diode.py` — D-51 Layer 1+2+3
- [x] `tests/integration/test_e2e_sim_to_timescale.py` — Roundtrip
- [x] `tests/integration/test_nats_subjects.py` — Subject hierarchy + JetStream durability
- [x] `tests/integration/test_opcua_browseable.py` — Namespace + writable=False
- [x] `tests/load/harness.py` — D-48 asyncio harness
- [x] `tests/load/test_ingestion_smoke.py` — 1k × 10s (CI default)
- [x] `tests/load/test_ingestion_throughput.py::test_5k_60s` — 5k × 60s (PR-label `load-test`) — Plan 03-07-T1

**docker-compose + CI wiring (Plan 03-06):**
- [x] `infra/compose/sim.yml` — add `sim-textile` + `ot-bridge` services + dual-network sft-ot / sft-core
- [x] `infra/compose/core.yml` — confirm `networks: sft-core` top-level
- [x] `.github/workflows/ci.yml` — add "Validate IT/OT artifacts" + "Run IT/OT integration tests" + "Run IT/OT load test (smoke)" + (Plan 03-07) "Run IT/OT full load test (PR-label gated)"
- [x] Workspace root `pyproject.toml` `[dependency-groups] dev` — add `testcontainers`, `asyncpg`, `asyncua`, `nats-py`

**Docs (Plan 03-07-T2):**
- [x] `docs/docs/it-ot/{index.md,opcua-schema.md,ingest-schema.md}` (IT)
- [x] `docs/docs/en/it-ot/` mirror (EN)
- [x] `docs/mkdocs.yml` — nav extension

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Schema-push verso TimescaleDB del dev compose stack | IOT-06 | Richiede docker running localmente (CI fa l'equivalente via Plan 03-06 Task 3) | Plan 03-05 Task 2 (BLOCKING checkpoint) — 6 step di verifica |
| Full 5k×60s load test su hardware rappresentativo | IOT-10 | PR-label `load-test` gated; troppo costoso per ogni PR | Plan 03-07 Task 1 + CI conditional step; report p99 in PR description |
| C-MAPSS dataset license / redistribution compliance | IOT-07 | NASA C-MAPSS license: download-on-demand (A10) | `scripts/download-replay-datasets.py` con SHA256; mai committato in repo (gitignored) |
| OPC-UA endpoint security hardening per production | A-018 | PoC NoSecurity; production needs Sign+Encrypt | Deferred a Phase 11 security hardening |
| Docker network ACL su alternative orchestrators (Podman, K8s) | IOT-05 | docker-compose enforcement test runs solo su docker | Phase 11 NetworkPolicy YAML su K8s; manual verification then |
| Data-diode Layer 2 host-side edge (DNS shared) | IOT-05 | Caveat A5: host docker DNS può false-pass | Documentato in `tests/integration/README.md`; Layer 1 (container-based fake-agent) è gate primario |
| Full stack avvio + log inspection + manual E2E | Phase 3 sign-off | Manual sanity prima di chiudere Phase 3 | Plan 03-06 Task 4 (11 step) |
| Docs preview review (MkDocs serve) | IOT-09 | Manual visual review del rendering | Plan 03-07 Task 3 |

---

## Validation Sign-Off

- [x] Tutti i task hanno `<automated>` verify o sono marked Manual-Only con instructions complete
- [x] Sampling continuity: no 3 consecutive task senza automated verify (i 3 checkpoint manuali sono distribuiti — 03-05-T2, 03-06-T4, 03-07-T3)
- [x] Wave 0 covers all MISSING references in Per-Task Verification Map (`File Exists` colonna risolta in-Plan)
- [x] No watch-mode flags (tutti i comandi exit deterministically)
- [x] Feedback latency < 75 s (full load gate)
- [x] CI grep gates in place: `yaml.load`, f-string SQL, OPC-UA write calls, `datetime.now()` naive, `pydantic.v1` (Plan 03-06-T3)
- [x] `nyquist_compliant: true` set in frontmatter (Per-Task Verification Map è completa con Task IDs reali e Wave 0 dependencies risolte)

**Approval:** ✅ ready for execution (planner ↦ checker)
