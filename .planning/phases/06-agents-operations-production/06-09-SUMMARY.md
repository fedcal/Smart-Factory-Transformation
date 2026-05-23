---
phase: 06-agents-operations-production
plan: 09
plan_id: 06-09
subsystem: sim-textile
tags: [simulator, quality, nats, dye-lot, tdd, ops-03, d-qi-04]
requires:
  - 06-00  # phase context
  - 06-04  # QualityEvent Pydantic model + dye_lot_id regex
provides:
  - sim_textile.production_state.ProductionState
  - sim_textile.quality_event_generator.quality_event_emitter
  - sim_textile.quality_event_generator.start_quality_event_tasks
affects:
  - simulators/sim-textile  # nuova superficie publish NATS quality.events.*
  - QualityInspector (06-07)  # consumer dei messaggi quality.events.*
tech-stack:
  added:
    - sft-domain (workspace dep — QualityEvent model)
  patterns:
    - "asyncio task per-asset (analogo a asset_emitter)"
    - "tz-aware datetime.now(UTC) — Pattern S-6"
    - "secrets.token_hex(2) CSPRNG per seq dye_lot_id"
    - "per-asset random.Random(asset_id) seed — no global random.seed pollution"
    - "Bernoulli per-tick emit con rate clamp (10/min nominal, 30/min faulted)"
key-files:
  created:
    - simulators/sim-textile/src/sim_textile/production_state.py
    - simulators/sim-textile/src/sim_textile/quality_event_generator.py
  modified:
    - simulators/sim-textile/tests/test_production_state.py
    - simulators/sim-textile/tests/test_quality_generator.py
    - simulators/sim-textile/pyproject.toml
    - uv.lock
decisions:
  - "ProductionState NOT frozen: stato vivo per-asset incapsulato dietro maybe_rotate(); immutabilita' globale (coding-style.md) resta enforced sui modelli condivisi (QualityEvent frozen=True)."
  - "Bias defect_type via dict family -> tuple[DefectType]: 90% massa sui defect 'naturali', 10% uniforme sugli altri. Loom -> broken_end/mispick/selvage_fault; spinning -> slub/neppy; dyeing -> shade_deviation/unlevel_dyeing; warping -> broken_end/selvage_fault; finishing -> shade_deviation/selvage_fault."
  - "Rate limit calcolato come Bernoulli per-tick: p = rate_per_min / ticks_per_min con clamp [0,1] (T-V6-dos-event-flood)."
  - "Per-asset random.Random(asset_id) seed garantisce determinismo dei test senza inquinare random.seed globale (preferito su 'random' module-level)."
  - "emitter.py NON modificato: il plan dichiara 'entrypoint wiring optional — full hook deferred until QualityInspector E2E in 06-13'. Esportata invece la factory start_quality_event_tasks() che il main entrypoint potra' chiamare in 06-13."
  - "Test usa AsyncMock invece di testcontainer NATS: tempi <1s e nessuna dipendenza docker. Test integration con broker reale rinviati a 06-13 (E2E QualityInspector)."
metrics:
  duration_minutes: 18
  date_completed: 2026-05-23
  tasks_completed: 2  # Task 1 (RED) + Task 2 (GREEN)
  files_created: 2
  files_modified: 4
  tests_added: 12  # 6 production_state + 6 quality_generator
  tests_passing: 50  # full sim-textile suite
---

# Phase 6 Plan 9: sim-textile QC Event Generator Summary

**One-liner:** `ProductionState` dye_lot rotation (60 min/asset, D-QI-04) + async `quality_event_emitter` che pubblica `QualityEvent` rate-limitati (10/min nominal, 30/min faulted) su `quality.events.<asset_id>` con defect_type biased per family.

## What Was Built

### `simulators/sim-textile/src/sim_textile/production_state.py`
- Dataclass `ProductionState(asset_id, current_dye_lot_id, rotation_interval=60min, _last_rotation)`.
- `ProductionState.bootstrap(asset_id, now=None)` classmethod -> initial dye_lot_id `DL-<asset>-<YYYYMMDD>-<hex4>` matching D-QI-04 regex.
- `ProductionState.maybe_rotate(now) -> bool` rotates when `(now - _last_rotation) >= rotation_interval`; uses `secrets.token_hex(2)` for CSPRNG seq.
- All `datetime` valori tz-aware UTC (Pattern S-6, T-V6-naive-datetime).

### `simulators/sim-textile/src/sim_textile/quality_event_generator.py`
- `async quality_event_emitter(asset, profile, production_state, nc, *, time_scale=1.0, emit_probability=None)`:
  per-tick loop con `datetime.now(UTC)`, `production_state.maybe_rotate(now)`, Bernoulli emit, build `QualityEvent`, `await nc.publish(f"quality.events.{asset_id}", payload)`.
- `start_quality_event_tasks(assets, profiles, nc, production_states, *, time_scale)` factory che crea un task per asset (entrypoint wiring deferred a 06-13).
- Rate clamp: `_RATE_NOMINAL_PER_MIN=10`, `_RATE_FAULTED_PER_MIN=30`. Profilo "faulted" = qualsiasi `fault_injection.*.enabled` o `nan_probability > 0`.
- Bias defect_type 90% sui defect naturali della family (vedi tabella sotto).
- `full_width = rng.random() < 0.05` (5%).
- `defect_length_inches` lognormal con mean variabile per defect (broken_end 6", shade_deviation 12", unlevel_dyeing 24").
- Per-asset `random.Random(asset.asset_id)` seed -> determinismo riproducibile nei test.

### Defect Type Bias per Family

| Asset Family | Biased Defects (90% massa) | Note |
|--------------|----------------------------|------|
| `loom`       | `broken_end`, `mispick`, `selvage_fault` | Difetti tessitura |
| `spinning`   | `slub`, `neppy` | Difetti filatura |
| `warping`    | `broken_end`, `selvage_fault` | Difetti orditura |
| `dyeing`     | `shade_deviation`, `unlevel_dyeing` | Difetti tintura |
| `finishing`  | `shade_deviation`, `selvage_fault` | Difetti finissaggio |

Il 10% rimanente si distribuisce uniforme sui defect "non naturali" per quella family, per generare un mix realistico.

### Rate Limit Constants

| Profile | Cap | Calcolo per-tick (sample_rate=10Hz, ticks/min=600) |
|---------|-----|---------------------------------------------------|
| Nominal | 10 events/min/asset | p = 10/600 ≈ 0.0166 Bernoulli per tick |
| Faulted | 30 events/min/asset | p = 30/600 ≈ 0.05 Bernoulli per tick |

Override esplicito via parametro `emit_probability` (clamp [0,1]) — utile nei test deterministici.

## Tests

| File | Test Count | Strategy |
|------|------------|----------|
| `tests/test_production_state.py` | 6 | dataclass unit tests + deterministic time injection |
| `tests/test_quality_generator.py` | 6 | AsyncMock NATS client (`nc.publish` AsyncMock); no testcontainer |

**12/12 nuovi test passano; suite completa sim-textile: 50/50 green.**

I 12 test coprono:
- ProductionState: formato iniziale, no-rotate prima dell'intervallo, rotate dopo intervallo, idempotenza post-rotation, token hex 4-char variability, attraversamento mezzanotte.
- quality_event_generator: subject NATS corretto, payload valido QualityEvent JSON, dye_lot_id propagato, rate limit nominal, bias dyer >=70% shade_deviation/unlevel_dyeing, presenza `full_width`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Build/env] Workspace venv missing pytest**
- **Found during:** Task 1 RED phase (running `uv run pytest`)
- **Issue:** `.venv/bin/python -m pytest` riportava "No module named pytest"; il default `uv run` invocava il system python 3.13 invece del venv 3.12.
- **Fix:** Eseguito `uv sync --all-packages --all-extras` dal root del workspace; risolto installando le dev-deps (pytest 9.0.3, pytest-asyncio 1.3.0) nel `.venv` 3.12 condiviso.
- **Files modified:** none (solo `uv.lock`, gia' incluso nel commit feat)
- **Commit:** N/A (effetto laterale di `uv sync`, snapshot in `uv.lock`)

**2. [Rule 2 - Missing critical functionality] Aggiunto sft-domain a sim-textile pyproject**
- **Found during:** Task 2 GREEN (import `from sft_domain.ops.quality import QualityEvent`)
- **Issue:** `simulators/sim-textile/pyproject.toml` non dichiarava `sft-domain` come dependency; l'import sarebbe rotto in installazione isolata.
- **Fix:** Aggiunto `sft-domain` ai `dependencies` + `[tool.uv.sources]` workspace=true.
- **Files modified:** `simulators/sim-textile/pyproject.toml`, `uv.lock`
- **Commit:** `abd6686` (incluso nel GREEN commit)

### Intentional Scope Deviations

**3. emitter.py NOT modified (vs. plan files_modified list)**
- **Plan diceva:** modificare `simulators/sim-textile/src/sim_textile/emitter.py`.
- **Plan stesso clarification (Task 2 done criterion):** "entrypoint wiring optional — full hook deferred until QualityInspector E2E in 06-13".
- **Decisione:** esportata factory `start_quality_event_tasks()` in `quality_event_generator.py` (callable dal main del simulator), senza toccare `asset_emitter`. Razionale: il loop `asset_emitter` esistente scrive su OPC-UA (non NATS), mentre i quality events vanno direttamente su NATS — sono task paralleli per natura, non fault-chain step. Restructure di `asset_emitter` violerebbe SRP.
- **Impact:** zero rischio regressione su test esistenti (`test_emitter.py` 3/3 green); il wiring entrypoint verra' fatto in 06-13 quando il simulator avra' bisogno di una connection NATS condivisa.

## Verification

- [x] `pytest simulators/sim-textile/tests/` -> 50/50 PASSED
- [x] `python -c "from sim_textile.production_state import ProductionState; from sim_textile.quality_event_generator import quality_event_emitter; print('OK')"` -> OK
- [x] `ruff check simulators/sim-textile/src/sim_textile/production_state.py simulators/sim-textile/src/sim_textile/quality_event_generator.py` -> All checks passed
- [x] dye_lot_id rotation 60 min sim-time per asset (test `test_maybe_rotate_rotation_after_interval` + `test_rotation_idempotent_within_interval_after_rotation`)
- [x] Rate clamp <=10/min nominal (test `test_rate_limited_under_nominal`)
- [x] Bias dyer >=70% shade_deviation/unlevel_dyeing (test `test_defect_type_biased_by_fault_profile`)

## Success Criteria

- [x] `dye_lot_id` rotates every ~60 min sim-time per asset
- [x] All emitted events validate as `QualityEvent`
- [x] Rate limit prevents flood (≤10/min nominal, ≤30/min faulted)
- [x] No new top-level deps (uses `nats-py` only via test mock; `sft-domain` workspace-only)

## Threat Model Compliance

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-V6-dos-event-flood | Bernoulli rate clamp 10/30 per min | OK |
| T-V6-injection | Payload sempre `QualityEvent.model_dump_json()` | OK |
| T-V6-naive-datetime | `datetime.now(UTC)` enforced ovunque | OK |
| T-V6-replay | N/A (accept — sim-only) | accept |

No new threat surface introduced beyond plan threat_model. No `## Threat Flags` section needed.

## Known Stubs

None. ProductionState e quality_event_generator sono completamente operativi; lo wiring entrypoint nel simulator main e' un'operazione separata gia' tracciata per 06-13 (QualityInspector E2E).

## Commits

| Hash | Type | Message |
|------|------|---------|
| `b74d7b0` | test | add failing tests for ProductionState + quality_event_generator (RED) |
| `abd6686` | feat | implement ProductionState + quality_event_generator (GREEN) |

## TDD Gate Compliance

- [x] RED gate: commit `b74d7b0` (`test(06-09): ...`) created with 12 failing tests
- [x] GREEN gate: commit `abd6686` (`feat(06-09): ...`) created after RED, brings 12/12 to pass
- [ ] REFACTOR: not needed (codice <300 lines totale, ruff clean, nessun smell evidente)

## Self-Check: PASSED

- `simulators/sim-textile/src/sim_textile/production_state.py` -> FOUND
- `simulators/sim-textile/src/sim_textile/quality_event_generator.py` -> FOUND
- commit `b74d7b0` -> FOUND
- commit `abd6686` -> FOUND
- All 50 sim-textile tests -> PASSED
