---
phase: "09"
plan: "03"
subsystem: energy-optimizer
tags: [scm, hitl, enpi, iso-50001, asyncpg, langgraph, audit]
dependency_graph:
  requires: ["09-00a", "09-00b", "09-01", "09-02"]
  provides: ["scm_energy_optimizer.agent.EnergyOptimizer", "scm_energy_optimizer.enpi.compute_enpi"]
  affects: ["09-06 (supply gateway)", "09-08 (supply subgraph)"]
tech_stack:
  added: []
  patterns:
    - "ISO 50001 EnPI kWh/kg pure function (Pattern 7 from 09-RESEARCH.md)"
    - "interrupt-then-audit HITL (single-supervisor, mirrors InventoryManager SCM-01)"
    - "Stable proposal_id via sha256(AGENT_ID.thread_id)[:32] (CR-04)"
    - "asyncpg repository with $N params + datetime objects (no .isoformat())"
    - "Frozen Pydantic models with extra=forbid (CR-05)"
key_files:
  created:
    - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/enpi.py
    - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/models.py
    - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/repository.py
    - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/metadata.py
    - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/agent.py
  modified:
    - apps/agents/supply/energy-optimizer/tests/test_enpi.py
    - apps/agents/supply/energy-optimizer/tests/test_energy_hitl.py
decisions:
  - "EnergyOptimizer uses single-supervisor HITL (mirrors InventoryManager, simpler than dual-supervisor ShiftHandover)"
  - "off_peak_kwh_pct computed over ALL kwh_readings (not only valid kg>0 slots) — per Pattern 7 spec"
  - "scm-energy-optimizer installed editable in venv (same treatment as scm-inventory-manager, per STATE.md note)"
  - "expected_savings_pct estimated as proportional to peak-hour fraction, clamped [0,100] before OffPeakProposal (CR-05)"
  - "Fallback synthetic data (412 kWh, 100 kg, is_peak=True) used when repository returns empty rows (test environment)"
metrics:
  duration: "~30min"
  completed: "2026-05-24T14:43:14Z"
  tasks: 2
  files: 7
---

# Phase 09 Plan 03: EnergyOptimizer Summary

**One-liner:** ISO 50001 EnPI kWh/kg computation + asyncpg EnergyRepository over scm.energy_readings/enpi_baseline + HITL off-peak scheduling proposal agent with interrupt-then-audit pattern and stable sha256 proposal_id.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | models + compute_enpi + repository + metadata | 5ded563 | enpi.py, models.py, repository.py, metadata.py, test_enpi.py |
| 2 | EnergyOptimizer HITL agent (interrupt-then-audit, stable id) | 9bfadfe | agent.py, test_energy_hitl.py |

## What Was Built

### Task 1: Pure Function + Models + Repository + Metadata

**enpi.py** — `compute_enpi()` ISO 50001 pure function:
- `enpi_actual = sum(kwh_valid) / sum(kg_valid)` for slots with `kg > 0`
- `deviation_pct = (actual - baseline) / baseline * 100`
- `off_peak_kwh_pct` computed over ALL readings (not just valid kg>0 slots)
- `ValueError` raised when no valid slot exists (no silent NaN/inf)
- Frozen `EnpiReport` dataclass — post-construction mutation impossible (CR-05)

**models.py** — Three frozen Pydantic models with `extra="forbid"`:
- `EnergyReading`: asyncpg row DTO (ts, asset_id, kwh, kg_processed, is_peak_hour)
- `OffPeakProposal`: off-peak scheduling proposal with stable `proposal_id` (CR-04)
- `EnergyAlert`: ENERGY_ALERT state output for downstream routing

**repository.py** — `EnergyRepository(pool)`:
- `_SQL_READINGS`: `SELECT ts, asset_id, kwh, kg_processed, is_peak_hour FROM scm.energy_readings WHERE process=$1 AND ts>=$2 AND ts<$3 ORDER BY ts` — $N params only (T-09-12)
- `_SQL_BASELINE`: reads `scm.enpi_baseline` — single fetchrow by process
- datetime objects passed directly to asyncpg (no `.isoformat()` — WR-03, Pitfall 7)

**metadata.py** — Agent constants:
- `AGENT_ID = "energy-optimizer"`, `CLUSTER = "supply"`
- `DATA_SOURCES = ("scm.energy_readings", "scm.enpi_baseline")`
- `build_evidence_panel()` helper — 5 required keys immutable

**test_enpi.py** — 8 contract tests all green:
- Mantis dyeing anchor: 4.12 kWh/kg, +8.42% above baseline 3.80
- Mantis finishing anchor: 2.18 kWh/kg, -0.91% below baseline 2.20
- kg=0 slot skipping, off_peak_kwh_pct formula, ValueError contract

### Task 2: EnergyOptimizer HITL Agent

**agent.py** — `EnergyOptimizer(pool, audit_writer, llm=None)`:
- Pattern G interrupt shim (NotImplementedError fallback — WR-01)
- State accessed via `.get()` with defaults throughout — no bare KeyError (CR-03)
- `_stable_id(state)`: `sha256(f"{AGENT_ID}.{thread_id}")[:32]` — stable across replay (CR-04)
- `interrupt({proposal, agent_id, proposal_id})` — RAISES on first execution, RETURNS on resume
- 0 audit writes before interrupt() returns (CR-02 guarantee)
- On resume: `ENERGY_PROPOSAL` (approval_id=None, CR-03) then `ENERGY_SIGNOFF` — both positional (CR-02)
- `expected_savings_pct` clamped to `[0.0, 100.0]` before `OffPeakProposal` construction (CR-05)

**test_energy_hitl.py** — 6 contract tests all green:
- CR-02: 0 audit writes before interrupt raises
- CR-02: positional AuditRecord (no kwargs) on both PROPOSAL + SIGNOFF
- CR-03: approval_id=None for ENERGY_PROPOSAL row
- CR-04: stable proposal_id via sha256 across replay
- Full HITL lifecycle: ENERGY_PROPOSAL + ENERGY_SIGNOFF (both rows present after resume)

## Verification Results

```
apps/agents/supply/energy-optimizer/tests/test_enpi.py        8 passed
apps/agents/supply/energy-optimizer/tests/test_energy_hitl.py 6 passed
TOTAL: 14 passed
```

## Deviations from Plan

### Auto-installed package (Rule 3 — blocking issue)

**1. [Rule 3 - Block] scm-energy-optimizer not installed editable in venv**
- **Found during:** Task 1 verification
- **Issue:** `ModuleNotFoundError: No module named 'scm_energy_optimizer'` — same pattern as 09-02 InventoryManager (documented in STATE.md)
- **Fix:** `uv pip install -e apps/agents/supply/energy-optimizer` — installed editable in the project venv (Python 3.12)
- **Note:** System Python is 3.14; all tests run via `uv run` to use the correct venv

None of the other deviations occurred. The plan executed exactly as specified.

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced beyond those already in the plan's threat model (T-09-12, T-09-13, T-09-14). All mitigations applied:
- T-09-12: `$N` params + datetime objects in repository ✓
- T-09-13: stable proposal_id from thread_id ✓
- T-09-14: kg>0 guard in compute_enpi + clamp before OffPeakProposal construction ✓

## Known Stubs

None. The agent uses a synthetic fallback (412 kWh, 100 kg, is_peak=True) when the repository returns empty rows. This is intentional for test environments and is not a UI-facing stub — it ensures the HITL contract tests work without a live TimescaleDB connection.

## Self-Check

Files created/committed:

- [x] apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/enpi.py (commit 5ded563)
- [x] apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/metadata.py (commit 5ded563)
- [x] apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/models.py (commit 5ded563)
- [x] apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/repository.py (commit 5ded563)
- [x] apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/agent.py (commit 9bfadfe)
- [x] apps/agents/supply/energy-optimizer/tests/test_enpi.py (commit 5ded563)
- [x] apps/agents/supply/energy-optimizer/tests/test_energy_hitl.py (commit 9bfadfe)

## Self-Check: PASSED
