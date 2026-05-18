---
phase: 3
slug: it-ot-simulation-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-18
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `03-RESEARCH.md` § Validation Architecture (single source of truth).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24+ (Phase 1 lock) + testcontainers-python for integration |
| **Config file** | `pyproject.toml` per Nx project (`[tool.pytest.ini_options]`) + workspace-root `tests/conftest.py` for cross-project fixtures |
| **Quick run command** | `npx nx affected --target=test` |
| **Full suite command** | `npx nx run-many --target=test --all && uv run --with pytest --with pytest-asyncio --with testcontainers -- python -m pytest tests/integration -m "not slow"` |
| **Phase gate** | `uv run -- python -m pytest tests/load/test_ingestion_throughput.py::test_5k_60s --full-load-test` (PR-label `load-test`) + smoke 1k×10s default in CI |
| **Estimated runtime** | ~5 s (Nx affected) / ~60 s (full unit + smoke) / ~120 s (full integration incl. data-diode docker spin-up) / ~75 s (full load test) |

---

## Sampling Rate

- **After every task commit:** `npx nx affected --target=test` (auto-scoped to modified project)
- **After every plan wave:** `npx nx run-many --target=test --all` + smoke load test (1k×10s)
- **Before `/gsd:verify-work`:** Full unit + integration green + smoke load + manual full load test (5k×60s) via PR label
- **Max feedback latency:** 5 s (Nx affected) / 60 s (wave merge) / 75 s (full load gate)

---

## Per-Task Verification Map

> Filled by planner during Step 8. Each task in every PLAN.md MUST map to one row here (or flagged Manual-Only).
> `File Exists` column resolves to ✅ after Wave 0 ships the script/test file; ❌ W0 means Wave 0 must create it before the task can run.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD-by-planner | TBD | 1 | IOT-09 | T-V5-yaml + T-V12-asset | Asset registry YAML schema-valid + JSON Schema Draft 2020-12 enforced | schema | `pytest packages/sft-assets/tests/test_registry_validation.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 1 | IOT-07 | T-V5-pydantic | `replay_cmapss` LangChain Tool returns DataFrame schema-valid (ReplayRecord) | unit | `pytest packages/sft-tools/tests/test_replay_cmapss.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 1 | IOT-08 | T-V5-pydantic | `replay_uci` LangChain Tool returns DataFrame schema-valid | unit | `pytest packages/sft-tools/tests/test_replay_uci.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 2 | IOT-01 | T-V5-pydantic | Simulator emits events for all 5 asset families | unit | `pytest simulators/sim-textile/tests/test_emitter.py -k test_all_families_emit` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 2 | IOT-02 | T-V5-pydantic | OPC-UA server browseable + asset_family namespace URI `urn:mantis:<family>:<id>` | integration | `pytest tests/integration/test_opcua_browseable.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 2 | IOT-03 | T-V5-pydantic | Fault injection NaN/drift/jitter/burst/alarm produce correct events per profile | unit | `pytest simulators/sim-textile/tests/test_faults.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 2 | IOT-04 | T-NATS-subject | NATS publishes on `sensor.events.<family>.<asset_id>.<tag>` with valid JetStream stream | integration | `pytest tests/integration/test_nats_subjects.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 2 | IOT-05 | T-DATA-DIODE | OT Bridge data-diode enforced (3-layer: docker ACL + pytest + grep static analysis) | integration | `pytest tests/integration/test_data_diode.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 2 | IOT-06 | T-V5-sql | TimescaleDB hypertable created + compression_policy(7d) + retention_policy(90d) idempotent | unit | `pytest infra/migrations/timescale/tests/test_migration_idempotent.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 3 | IOT-04+IOT-06 | T-E2E | E2E: sim → ot-bridge → NATS → TimescaleDB roundtrip (<5s) | integration | `pytest tests/integration/test_e2e_sim_to_timescale.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 4 | IOT-10 | T-PERF | Smoke load test 1k msg/s × 10s, p99 < 200ms (CI default) | load | `pytest tests/load/test_ingestion_smoke.py` | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 4 | IOT-10 | T-PERF | Full load test 5k msg/s × 60s steady-state realistic mix, p99 < 200ms | load | `pytest tests/load/test_ingestion_throughput.py::test_5k_60s --full-load-test` (PR-label) | ❌ W0 | ⬜ pending |
| TBD-by-planner | TBD | 4 | IOT-09 | — | Ingest schema docs in MkDocs + mkdocs strict build green | integration | `cd docs && mkdocs build --strict` | ✅ Phase 1 (docs-deploy.yml) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 (foundation) MUST ship the following before any downstream task runs. All paths are new in Phase 3.

**New Nx packages:**
- [ ] `packages/sft-assets/{pyproject.toml,project.json,src/sft_assets/,tests/}` — registry + Pydantic loader
- [ ] `packages/sft-tools/{pyproject.toml,project.json,src/sft_tools/,tests/}` — LangChain Tools

**Pydantic models:**
- [ ] `packages/sft-assets/src/sft_assets/models.py` — `Asset`, `Tag` (frozen + extra=forbid)
- [ ] `packages/sft-assets/src/sft_assets/loader.py` — `load_assets()`, `load_assets_dict()`, `load_tag_dict()` with `lru_cache`
- [ ] `packages/sft-assets/src/sft_assets/registry.yaml` — ~30 asset seed (12 looms + 8 spinning + 4 warping + 4 dyeing + 2 stenter)
- [ ] `packages/sft-assets/src/sft_assets/schemas/asset.schema.json` — JSON Schema Draft 2020-12
- [ ] `packages/sft-tools/src/sft_tools/replay/{cmapss.py,uci.py,models.py}` — LangChain Tools + `ReplayRecord` Pydantic
- [ ] `packages/sft-tools/src/sft_tools/timescale/query.py` — `query_timescale` Tool

**sim-textile fill-in:**
- [ ] `simulators/sim-textile/src/sim_textile/{main.py,server.py,emitter.py,faults.py,profiles/loader.py,metrics.py,models.py}`
- [ ] `simulators/sim-textile/profiles/{loom,spinning,warping,dyeing,finishing}.yaml` (5 YAML fault profiles)
- [ ] `simulators/sim-textile/Dockerfile`
- [ ] `simulators/sim-textile/tests/{conftest.py,test_emitter.py,test_faults.py,test_profile_loader.py}`

**ot-bridge fill-in:**
- [ ] `services/ot-bridge/src/svc_ot_bridge/{main.py,client.py,publisher.py,writer.py,models.py}`
- [ ] `services/ot-bridge/Dockerfile`
- [ ] `services/ot-bridge/tests/{conftest.py,test_client.py,test_publisher.py,test_writer.py}`

**Infra migrations:**
- [ ] `infra/migrations/timescale/{0001_sensor_events_hypertable.sql,migrate.py,tests/test_migration_idempotent.py}` — Hypertable + compression + retention (D-49)
- [ ] `scripts/setup-jetstream-stream.py` — Idempotent JetStream `SENSOR_EVENTS` stream creation

**Workspace integration tests + load test:**
- [ ] `tests/conftest.py` — workspace-root docker-compose lifecycle fixture (testcontainers)
- [ ] `tests/integration/test_data_diode.py` — D-51 Layer 2 (write attempt timeout) + Layer 3 (grep static analysis)
- [ ] `tests/integration/test_e2e_sim_to_timescale.py` — Roundtrip
- [ ] `tests/integration/test_nats_subjects.py` — Subject hierarchy + JetStream durability
- [ ] `tests/integration/test_opcua_browseable.py` — Namespace + browse path
- [ ] `tests/load/harness.py` — asyncio harness (D-48)
- [ ] `tests/load/test_ingestion_smoke.py` — 1k × 10s (CI default)
- [ ] `tests/load/test_ingestion_throughput.py::test_5k_60s` — 5k × 60s (PR-label `load-test`)

**docker-compose + CI wiring:**
- [ ] `docker-compose.yml` — add `sim-textile` + `ot-bridge` services + `ot-network` + `it-network` (dual-network ACL D-51)
- [ ] `.github/workflows/ci.yml` — add "Run IT/OT integration tests" step + "Run IT/OT load test (smoke)" step
- [ ] Workspace root `pyproject.toml` `[dependency-groups] dev` — add `testcontainers`
- [ ] `docs/docs/it-ot/{index.md,opcua-schema.md,ingest-schema.md}` + `docs/docs/en/it-ot/` mirror (IOT-09)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full 5k msg/s × 60s load test on representative hardware | IOT-10 | Requires Docker + TimescaleDB warm-up + p99 measurement; too expensive for every PR | Run via PR label `load-test` triggered on PRs touching `sim-textile/`, `ot-bridge/`, `infra/migrations/timescale/`, or `tests/load/`. Report p99 in PR description. |
| C-MAPSS dataset license / redistribution compliance | IOT-07 | NASA C-MAPSS license requires download-on-demand (Pitfall A10) | Verify `scripts/download-replay-datasets.py` downloads from NASA URL with SHA256 checksum at first invocation; never committed to repo |
| OPC-UA endpoint security hardening for production | A-018 | PoC uses NoSecurity policy; production needs Sign+Encrypt + cert chain | Deferred to Phase 11 security hardening; documented in `<deferred>` of CONTEXT.md |
| Docker network ACL on alternative orchestrators (Podman, K8s) | IOT-05 | docker-compose enforcement test runs on docker only | Phase 11 deploys NetworkPolicy YAML on K8s; manual verification then |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies declared
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references in Per-Task Verification Map (`File Exists = ❌ W0`)
- [ ] No watch-mode flags (all commands exit deterministically)
- [ ] Feedback latency < 75 s (full load gate)
- [ ] CI grep gates in place (yaml.load, f-string SQL, OPC-UA write calls, datetime.now() naive, pydantic.v1)
- [ ] `nyquist_compliant: true` set in frontmatter after planner fills Per-Task Verification Map and Wave 0 dependencies are wired

**Approval:** pending
