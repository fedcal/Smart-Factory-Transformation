---
phase: 03-it-ot-simulation-layer
plan: "03"
subsystem: simulator
tags:
  - asyncua
  - opcua
  - fault-injection
  - prometheus
  - pydantic
  - asyncio
  - simulator

requires:
  - phase: 03-01-sft-assets
    provides: "load_assets(), load_tag_dict(), AssetFamily enum — usati da server.py per generazione nodi OPC-UA"

provides:
  - "5 pure fault functions (maybe_nan, apply_drift, apply_jitter, apply_burst, check_alarm_storm) testabili isolatamente"
  - "FaultProfile + EmitterState Pydantic v2 frozen models con validazione range"
  - "5 YAML fault profiles (loom/spinning/warping/dyeing/finishing) conformi D-44"
  - "JSON Schema Draft 2020-12 fault-profile.schema.json"
  - "asyncua Server multi-namespace con set_writable(False) su ogni Variable (IOT-02)"
  - "asset_emitter asyncio task con chain fault injection e datetime.now(UTC) tz-aware (IOT-01)"
  - "Prometheus endpoint /metrics su porta 8080 con sim_events_emitted_total / sim_fault_injected_total / sim_message_rate_per_second"
  - "CLI sim-textile con --profile/--time-scale/--metrics-port/--dry-run + env fallback"
  - "Dockerfile multi-stage python:3.12-slim"
  - "scripts/validate-fault-profiles.py con Draft202012Validator + cross-check registry sft-assets"

affects:
  - "03-04-ot-bridge"
  - "03-06-compose"
  - "phase-04-agents"
  - "phase-06-anomaly-detection"
  - "phase-07-predictive-maintenance"

tech-stack:
  added:
    - "asyncua>=1.1.8 (OPC-UA server asyncio-native)"
    - "prometheus-client>=0.21 (Prometheus metrics endpoint)"
    - "structlog>=24 (JSON structured logging)"
    - "jsonschema>=4.23 (Draft202012Validator per profile validation)"
  patterns:
    - "Pattern S-1: Pydantic v2 frozen + extra=forbid su tutti i modelli"
    - "Pattern S-2: yaml.safe_load esclusivo (CI grep gate)"
    - "Pattern S-5: lru_cache(maxsize=5) + invalidate_cache() per profile loader"
    - "Pattern S-6: datetime.now(UTC) obbligatorio (CI grep gate — no naive datetime)"
    - "Pattern P2: EmitterState frozen dataclass con dataclasses.replace mutation (IOT-03)"
    - "Pattern P1: asyncua Server setup con namespace per family (RESEARCH §Pattern 1)"

key-files:
  created:
    - "simulators/sim-textile/src/sim_textile/models.py — FaultProfile, FaultInjection, EmitterState"
    - "simulators/sim-textile/src/sim_textile/faults/nan.py — maybe_nan pure function"
    - "simulators/sim-textile/src/sim_textile/faults/drift.py — apply_drift pure function"
    - "simulators/sim-textile/src/sim_textile/faults/jitter.py — apply_jitter pure function"
    - "simulators/sim-textile/src/sim_textile/faults/burst.py — apply_burst pure function"
    - "simulators/sim-textile/src/sim_textile/faults/alarm_storm.py — check_alarm_storm pure function"
    - "simulators/sim-textile/src/sim_textile/profile_loader.py — load_profile/load_all_profiles con lru_cache"
    - "simulators/sim-textile/src/sim_textile/server.py — asyncua setup_server multi-namespace"
    - "simulators/sim-textile/src/sim_textile/emitter.py — asset_emitter asyncio task"
    - "simulators/sim-textile/src/sim_textile/metrics.py — Prometheus counters"
    - "simulators/sim-textile/src/sim_textile/main.py — asyncio.gather orchestration"
    - "simulators/sim-textile/src/sim_textile/cli.py — argparse CLI entry point"
    - "simulators/sim-textile/profiles/{loom,spinning,warping,dyeing,finishing}.yaml — 5 YAML profiles D-44"
    - "simulators/sim-textile/schemas/fault-profile.schema.json — JSON Schema Draft 2020-12"
    - "simulators/sim-textile/Dockerfile — multi-stage python:3.12-slim"
    - "simulators/sim-textile/tests/conftest.py — fixtures random_seed_42, frozen_time, sample_*"
    - "simulators/sim-textile/tests/test_faults.py — 18 test fault pure functions"
    - "simulators/sim-textile/tests/test_profile_loader.py — 11 test loader + cache"
    - "simulators/sim-textile/tests/test_profile_validation.py — 6 test schema validation"
    - "simulators/sim-textile/tests/test_emitter.py — 3 test emitter IOT-01/IOT-02/S-6"
    - "scripts/validate-fault-profiles.py — CLI validator Draft202012Validator + registry cross-check"
  modified:
    - "simulators/sim-textile/pyproject.toml — aggiunto asyncua/pydantic/structlog/prometheus-client/jsonschema/sft-assets deps"
    - "simulators/sim-textile/project.json — implicitDependencies sft-assets + target validate-profiles"
    - "simulators/sim-textile/src/sim_textile/__init__.py — barrel export FaultProfile/EmitterState/load_*"
    - "uv.lock — aggiornato con nuove dipendenze"

key-decisions:
  - "Fault functions pure su EmitterState frozen dataclass con replace-based mutation — testabili isolatamente (IOT-03)"
  - "asyncua set_writable(False) su ogni Variable node — protocol-level data-diode (T-03-03-opcua-write)"
  - "datetime.now(UTC) obbligatorio in emitter.py — CI grep gate previene naive datetime (Pattern S-6)"
  - "lru_cache(maxsize=5) per profile loader — idempotente, invalidate_cache() per test isolation"
  - "Dockerfile multi-stage: builder uv pip install, runtime copia site-packages + profiles"
  - "apply_burst usa decay lineare (non costante) per realismo: valore pieno a t=0, zero a t=duration"

patterns-established:
  - "Fault injection chain: drift → jitter → burst → nan → alarm_storm (in ordine nel loop emitter)"
  - "EmitterState frozen dataclass come accumulatore stato per pattern replace-based immutability"
  - "set_writable(False) su ogni OPC-UA Variable appena creata — mai dimenticare"
  - "profile_loader._PROFILES_DIR = Path(__file__).parent.parent.parent / 'profiles' — path resolution relativo al modulo"

requirements-completed:
  - IOT-01
  - IOT-02
  - IOT-03

duration: 28min
completed: "2026-05-18"
---

# Phase 3 Plan 03: sim-textile OPC-UA Simulator Summary

**Singolo processo asyncio sim-textile con asyncua Server multi-namespace, 5 fault profiles YAML calibrati D-44, pure function state machine IOT-03, Prometheus /metrics e Dockerfile multi-stage python:3.12-slim**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-05-18T12:30:00Z
- **Completed:** 2026-05-18T13:00:00Z
- **Tasks:** 2 (Task 1: fault state machine + profiles; Task 2: OPC-UA server + emitter + Dockerfile)
- **Files created/modified:** 26

## Accomplishments

- 5 pure fault functions (maybe_nan, apply_drift, apply_jitter, apply_burst, check_alarm_storm) con EmitterState frozen dataclass replace-based — IOT-03
- asyncua Server multi-namespace `urn:mantis:<family>` con `set_writable(False)` su ogni Variable — protocol-level data-diode IOT-02
- 5 YAML fault profiles (loom/spinning/warping/dyeing/finishing) conformi D-44 + JSON Schema Draft 2020-12 + validator CLI
- Prometheus endpoint /metrics con counters asset_family/asset_id/tag_id e gauge rate
- CLI argparse con env fallback SIM_PROFILES/SIM_TIME_SCALE/METRICS_PORT + --dry-run
- 38 test verdi (inclusi 13 comportamentali da spec + coverage extra)

## Task Commits

1. **Task 1: Fault state machine + Pydantic models + 5 YAML profiles + schema + validator** — `63086a4` (feat)
2. **Task 2: asyncua server multi-namespace + emitter + Prometheus + CLI + Dockerfile** — `3c87717` (feat)

## Files Created/Modified

- `simulators/sim-textile/src/sim_textile/models.py` — FaultProfile, FaultInjection, EmitterState Pydantic v2 frozen
- `simulators/sim-textile/src/sim_textile/faults/{nan,drift,jitter,burst,alarm_storm}.py` — 5 pure fault functions
- `simulators/sim-textile/src/sim_textile/profile_loader.py` — lru_cache(maxsize=5) + yaml.safe_load
- `simulators/sim-textile/src/sim_textile/server.py` — asyncua setup_server + set_writable(False) per ogni Variable
- `simulators/sim-textile/src/sim_textile/emitter.py` — asset_emitter asyncio task, datetime.now(UTC)
- `simulators/sim-textile/src/sim_textile/metrics.py` — Prometheus Counter + Gauge
- `simulators/sim-textile/src/sim_textile/main.py` — asyncio.gather orchestration
- `simulators/sim-textile/src/sim_textile/cli.py` — argparse + --dry-run + env fallback
- `simulators/sim-textile/profiles/{loom,spinning,warping,dyeing,finishing}.yaml` — 5 YAML profiles D-44
- `simulators/sim-textile/schemas/fault-profile.schema.json` — JSON Schema Draft 2020-12
- `simulators/sim-textile/Dockerfile` — multi-stage python:3.12-slim, USER 1000:1000
- `simulators/sim-textile/tests/test_faults.py` — 18 test (includes 7 spec + extra)
- `simulators/sim-textile/tests/test_profile_loader.py` — 11 test loader + cache
- `simulators/sim-textile/tests/test_profile_validation.py` — 6 test schema + tag registry
- `simulators/sim-textile/tests/test_emitter.py` — 3 test (tz-aware, CLI dry-run, IOT-01 all families)
- `scripts/validate-fault-profiles.py` — CLI validator schema + registry cross-check
- `simulators/sim-textile/pyproject.toml` — deps asyncua/pydantic/structlog/prometheus-client/jsonschema/sft-assets
- `simulators/sim-textile/project.json` — validate-profiles target + sft-assets implicit dep

## Decisions Made

- **apply_burst decay lineare**: implementato decay lineare (valore pieno a t=0, zero a t=duration_s) invece di costante per maggiore realismo fisica
- **Tag registry cross-check in validator**: profiles referenziano solo tag_id presenti in sft-assets registry.yaml — cross-check sia in script CLI che in test_profile_validation
- **set_writable(False) 5 volte in server.py**: il grep count di 5 include docstring/commenti + 1 chiamata effettiva nel loop per ogni Variable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fix test CLI subprocess path**
- **Found during:** Task 2 (test_emitter.py - TestCliDryRun)
- **Issue:** test inizialmente usava `sys.executable -m sim_textile.cli` via subprocess, ma PYTHONPATH non era risolto correttamente e il comando falliva con output vuoto
- **Fix:** Cambiato a `uv run --project simulators/sim-textile sim-textile --dry-run` — usa l'entrypoint installato correttamente
- **Files modified:** `simulators/sim-textile/tests/test_emitter.py`
- **Committed in:** `3c87717` (part of Task 2 commit)

**2. [Rule 1 - Bug] Fix Prometheus _metrics labels access**
- **Found during:** Task 2 (test_emitter.py - TestAllFamiliesEmit)
- **Issue:** Il test accedeva `sim_events_emitted_total._metrics` con `labels["asset_family"]` ma le chiavi interne di prometheus_client Counter._metrics sono tuple (non dict)
- **Fix:** Cambiato accesso a `label_key[0]` dove index 0 è asset_family (primo label)
- **Files modified:** `simulators/sim-textile/tests/test_emitter.py`
- **Committed in:** `3c87717` (part of Task 2 commit)

**3. [Rule 1 - Bug] Fix naive datetime in docstring/comments causava falso positivo CI gate**
- **Found during:** Task 2 (verifica `grep -rE "datetime\.now\(\)" simulators/sim-textile/src/`)
- **Issue:** Commenti e docstring in emitter.py contenevano il pattern `datetime.now()` (incluso come esempio di pattern vietato) — il CI grep gate trovava match
- **Fix:** Riscritto i commenti per evitare il pattern: `datetime.now()` → `naive datetime senza tz` / `naive (Pitfall 7)`
- **Files modified:** `simulators/sim-textile/src/sim_textile/emitter.py`
- **Committed in:** `3c87717` (part of Task 2 commit)

---

**Total deviations:** 3 auto-fixed (tutti Rule 1 — bug test/false positive)
**Impact on plan:** Nessun cambio di scope. Fix necessari per correttezza test e CI gate.

## Issues Encountered

- Merge da master necessario per ottenere sft-assets (Plan 03-01) non ancora presente nel worktree — fast-forward merge eseguito senza conflitti
- asyncua installazione: asyncua>=1.1.8 richiede cryptography e pyopenssl — installati automaticamente

## Known Stubs

Nessuno — tutti i moduli sono implementati con logica reale, non placeholder.

## Threat Flags

Nessuna nuova superficie di sicurezza non prevista nel threat_model del plan.

## Self-Check: PASSED

**Files verificati:**
- `simulators/sim-textile/src/sim_textile/models.py` — FOUND
- `simulators/sim-textile/src/sim_textile/server.py` — FOUND (contiene `set_writable(False)`)
- `simulators/sim-textile/src/sim_textile/emitter.py` — FOUND (contiene `datetime.now(UTC)`)
- `simulators/sim-textile/profiles/loom.yaml` — FOUND (asset_family: loom)
- `simulators/sim-textile/schemas/fault-profile.schema.json` — FOUND (contiene `$schema`)
- `simulators/sim-textile/Dockerfile` — FOUND (2x `FROM python:3.12-slim`)
- `scripts/validate-fault-profiles.py` — FOUND (contiene `Draft202012Validator`)

**Commits verificati:**
- `63086a4` feat(03-03-fault-profiles) — FOUND
- `3c87717` feat(03-03-opcua-server) — FOUND

**Test suite:** 38/38 passed
**validate-fault-profiles.py:** 5/5 profiles OK, exit 0
**CLI dry-run:** exit 0, output "Resolved config: profiles=..."
**grep gate naive datetime:** exit 1 (no match)
**grep gate yaml.load:** exit 1 (no match)

## Next Phase Readiness

- **03-04 (ot-bridge)**: pronto — server OPC-UA esposto su 4840 con Variable nodes navigabili; asyncua client può connettersi e sottoscriversi
- **03-06 (compose)**: pronto — Dockerfile multi-stage presente, ENV configurati; sim.yml placeholder può essere sostituito
- **Phase 4+ agents**: IOT-01/02/03 chiusi — stream sensore realistico con fault calibrati disponibile

---
*Phase: 03-it-ot-simulation-layer*
*Completed: 2026-05-18*
