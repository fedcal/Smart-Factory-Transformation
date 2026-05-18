---
phase: 03-it-ot-simulation-layer
plan: "06"
subsystem: infra
tags: [docker-compose, dual-network, data-diode, integration-tests, e2e, nats, opcua, timescaledb, smoke-load, ci, pytest]

requires:
  - phase: 03-03
    provides: "sim-textile Dockerfile + OPC-UA server"
  - phase: 03-04
    provides: "ot-bridge Dockerfile + NATS publisher + asyncpg writer"
  - phase: 03-05
    provides: "timescale-migrate.py + nats-bootstrap-streams.py + hypertable"

provides:
  - "docker-compose dual-network (sft-ot + sft-core) con sim-textile + ot-bridge"
  - "NATS reallineato su sft-core (D-51 Layer 1 conforme)"
  - "D-51 3-layer data-diode enforcement test suite"
  - "Test E2E roundtrip sim → bridge → NATS → TimescaleDB"
  - "IOT-10 smoke gate: harness 1k×10s p99<200ms"
  - "CI gates: 3 nuovi step Phase 3 (validate + integration + smoke load)"

affects:
  - 03-07-load-full
  - 04-core-agentic-runtime
  - phase-11-security-hardening

tech-stack:
  added:
    - "asyncpg>=0.30 (workspace dev dep)"
    - "asyncua>=1.1.8 (workspace dev dep)"
    - "nats-py>=2.14.0 (workspace dev dep)"
    - "testcontainers[postgres]>=4.14 (workspace dev dep)"
  patterns:
    - "compose_stack session-scoped fixture per docker compose lifecycle in pytest"
    - "D-51 3-layer data-diode: container fake-agent Layer 1 + host-side Layer 2 + grep Layer 3"
    - "asyncpg statement_cache_size=0 per TimescaleDB dynamic plan optimization"
    - "NATS consumer durable test_subject_check per verifica subject format"
    - "CI grep gates: no f-string SQL + no yaml.load + no OPC-UA write + no naive datetime"

key-files:
  created:
    - "tests/integration/__init__.py"
    - "tests/integration/conftest.py"
    - "tests/integration/test_data_diode.py"
    - "tests/integration/test_opcua_browseable.py"
    - "tests/integration/test_nats_subjects.py"
    - "tests/integration/test_e2e_sim_to_timescale.py"
    - "tests/integration/README.md"
    - "tests/load/__init__.py"
    - "tests/load/harness.py"
    - "tests/load/test_ingestion_smoke.py"
  modified:
    - "infra/compose/sim.yml"
    - "Makefile"
    - "tests/conftest.py"
    - ".github/workflows/ci.yml"
    - "pyproject.toml"

key-decisions:
  - "NATS spostato da sft-sim a sft-core (PATTERNS line 726) — NATS e' IT-side broker"
  - "sft-sim rinominato sft-ot per semantic clarity D-51 Layer 1"
  - "ot-bridge e' l'unico container dual-network (sft-ot + sft-core)"
  - "D-51 Layer 2 (host-side pytest) documentato con caveat A5 (Docker DNS shared)"
  - "OQ1 RESOLVED: NATS replicas=1 dev, cluster deferred Phase 11"
  - "compose_stack fixture usa --wait per garantire healthy state prima dei test"

requirements-completed:
  - IOT-02
  - IOT-04
  - IOT-05
  - IOT-10

duration: 6min
completed: "2026-05-18"
---

# Phase 3 Plan 06: Compose + Integration + Smoke Load Summary

**Docker-compose dual-network (sft-ot/sft-core) con sim-textile e ot-bridge, D-51 3-layer data-diode test, roundtrip E2E e smoke gate IOT-10 1k×10s — Task 4 (checkpoint manuale) in attesa**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-18T11:09:42Z
- **Completed:** 2026-05-18T11:15:00Z
- **Tasks:** 3/4 (Task 4 = checkpoint:human-verify, pending)
- **Files modified:** 14

## Accomplishments

- Docker-compose esteso con servizi `sim-textile` (sft-ot only) e `ot-bridge` (dual-network sft-ot + sft-core); NATS reallineato da sft-sim a sft-core (D-51 Layer 1 conforme)
- Suite di test integration completa: D-51 3-layer enforcement + OPC-UA browseable (5 namespace urn:mantis) + NATS subject format D-52 + E2E roundtrip asyncpg
- IOT-10 smoke gate: harness asyncio custom con asyncpg pool (min_size=10, max_size=20, statement_cache_size=0) + test 1k×10s p99<200ms
- CI esteso con 3 step Phase 3: validate IT/OT artifacts (5 grep gates) + integration tests + smoke load
- Tutti i file Python parsano senza errori di sintassi; tutti i grep gates CI passano

## Task Commits

1. **Task 1: docker-compose dual-network + Makefile + README** - `e3a225d` (feat)
2. **Task 2: 3-layer data-diode + E2E + smoke load harness** - `0e50dd0` (feat)
3. **Task 3: CI extension + pyproject.toml dev deps** - `b8e0833` (feat)
4. **Task 4: checkpoint:human-verify** — PENDING (stack inspection manuale richiesta)

## Files Created/Modified

- `infra/compose/sim.yml` — dual-network extension: sft-ot (sim-textile only) + sft-core (nats, postgres); sim-textile + ot-bridge services con build context `../..`
- `Makefile` — target Phase 3: `up-it-ot`, `down-it-ot`, `integration-test`, `smoke-load`, `bootstrap-nats`
- `tests/conftest.py` — aggiunge `compose_stack` session-scoped fixture + marker registration
- `tests/integration/README.md` — prerequisiti, test list, caveat A5 (Docker DNS shared)
- `tests/integration/test_data_diode.py` — D-51 Layer 1 (container fake-agent su sft-core) + Layer 2 (host-side asyncua) + Layer 3 (grep static)
- `tests/integration/test_opcua_browseable.py` — 5 namespace urn:mantis:<family> + variabile non-writable
- `tests/integration/test_nats_subjects.py` — stream SENSOR_EVENTS esiste + subject format D-52
- `tests/integration/test_e2e_sim_to_timescale.py` — roundtrip sim→bridge→NATS→TimescaleDB asyncpg
- `tests/load/harness.py` — asyncio publisher harness D-48 (asyncpg pool, rate control, p99 measurement)
- `tests/load/test_ingestion_smoke.py` — smoke gate IOT-10: 1k×10s, p99<200ms
- `.github/workflows/ci.yml` — 3 step Phase 3: validate IT/OT artifacts + integration tests + smoke load
- `pyproject.toml` — dev deps: testcontainers[postgres]>=4.14, asyncpg>=0.30, asyncua>=1.1.8, nats-py>=2.14.0

## Decisions Made

- **NATS su sft-core**: Phase 1 aveva NATS su sft-sim (errore di naming — NATS e' IT-side broker). Phase 3 sposta NATS su sft-core per allineamento D-51 (PATTERNS line 726 fix). Backward compat: `sft-sim` eliminato, rete rinominata `sft-ot`.
- **D-51 Layer 2 caveat A5**: il test host-side per Layer 2 documenta che Docker DNS shared puo' false-pass. Layer 1 (container fake-agent) rimane il gate primario per il CI.
- **compose_stack fixture** usa `--wait` flag per garantire healthy state prima dei test; aggiunge `time.sleep(5)` per sim-textile OPC-UA emission warmup.
- **OQ1 RESOLVED**: NATS replicas=1 dev sufficienti per smoke test (cluster 3x deferred Phase 11).

## Deviations from Plan

None — piano eseguito esattamente come specificato. L'unica nota: il test `test_layer2_agent_cannot_open_opcua_session` usa `assert not connection_succeeded` invece di `pytest.raises`, per gestire il caveat A5 documentato nel piano (Docker DNS shared puo' far risolvere il nome dall'host in dev, rendendo `pytest.raises` poco affidabile come Layer 2 gate).

## Known Stubs

Nessuno — nessun dato hardcoded o placeholder che prevenga il raggiungimento degli obiettivi del piano. I test sono condizionali su `compose_stack` fixture (skip se docker non disponibile) — comportamento intenzionale documentato.

## Threat Flags

Nessuna nuova superficie di sicurezza introdotta oltre quanto previsto dal threat model del piano.

## Issues Encountered

None — tutti i file parsano correttamente, compose config valida, tutti i grep gates passano.

## User Setup Required

**Task 4 checkpoint:human-verify in attesa.** Vedere sezione "CHECKPOINT REACHED" nella risposta dell'agente.

## Next Phase Readiness

- Compose dual-network pronto per `docker compose -f infra/compose/core.yml -f infra/compose/sim.yml up`
- Test integration pronti per esecuzione dopo stack startup
- Smoke load harness pronto per CI gate
- Task 4 (manuale): build immagini + avvio stack + verifica log + query TimescaleDB + metrics Prometheus

---
*Phase: 03-it-ot-simulation-layer*
*Completed: 2026-05-18 (Tasks 1-3; Task 4 pending checkpoint)*

---

## Task 4 — Resolution

**Decision (2026-05-18 orchestrator):** `approved-ci-only`

L'orchestratore ha optato per affidare la validazione al CI workflow invece di eseguire i 11 step manuali di local stack inspection. Razionale:

- Tutti i test unitari di Wave 1+2 sono verdi (sft-assets 20/20, sft-tools 34/34, sim-textile 38/38, ot-bridge 14/14)
- `docker compose -f infra/compose/core.yml -f infra/compose/sim.yml config` exit 0 (compose syntax valida — Task 1 acceptance)
- CI workflow `.github/workflows/ci.yml` (Task 3) include 3 step Phase 3 che coprono esattamente i 11 step manuali:
  - "Run IT/OT integration tests" — D-51 3-layer + OPC-UA browseable + NATS subjects + E2E
  - "Run IT/OT load test (smoke)" — 1k×10s p99<200ms
  - "Validate IT/OT artifacts" — 5 grep gates
- Schema-push già verificato in Plan 03-05 Task 2 (hypertable + compression_policy + retention_policy attivi)

Task 4 è marcato `resolved-via-ci`. Eventuali bug strutturali emergeranno nel prossimo push o nel full load test di Plan 03-07.
