---
phase: 06-agents-operations-production
plan: 04
subsystem: ops-domain
tags: [pydantic, scheduling, yaml-seeds, ops-models, tdd]
requires:
  - 06-00 (Wave 0 test scaffolding)
provides:
  - sft_domain.ops (Anomaly, AnomalyBaseline, QualityEvent, QualityVerdict,
    OrderSpec, AssetCapacity, ScheduleDraft, ScheduleDraftItem, OpsState,
    RagCitation, load_orders, load_asset_capacity, load_anomaly_baselines)
  - sft_domain.scheduling (schedule_spt, schedule_edd — deterministic pure fn)
  - failure_modes.yaml extension (hitl_tier, setup_minutes, severity_band on
    all 32 entries; 7-textile-defect taxonomy complete with `neppy` +
    `unlevel_dyeing` added)
  - orders.yaml (20 synthetic Mantis Textile orders)
  - asset_capacity.yaml (30 entries, one per registry asset)
  - anomaly_baselines.yaml (11 baselines × 5 asset families)
affects:
  - packages/sft-domain (foundation for all 4 OPS agents in Wave 2: 06-06/07/08/09)
  - sft-agents (RagCitation is now canonically in sft-domain; sft-agents should
    re-export in a follow-up to avoid duplicate definitions)
tech-stack:
  added:
    - hashlib (stdlib) — deterministic UUID derivation for schedule_id
  patterns:
    - Pydantic v2 frozen + extra=forbid
    - tz-aware datetime via field_validator (Pitfall 7)
    - lru_cache(maxsize=1) + yaml.safe_load loaders (T-V6-yaml-injection)
    - Pure-function scheduling heuristics with deterministic tie-breaking
key-files:
  created:
    - packages/sft-domain/src/sft_domain/ops/__init__.py (55 lines)
    - packages/sft-domain/src/sft_domain/ops/anomaly.py (172 lines)
    - packages/sft-domain/src/sft_domain/ops/citation.py (52 lines)
    - packages/sft-domain/src/sft_domain/ops/quality.py (83 lines)
    - packages/sft-domain/src/sft_domain/ops/schedule.py (217 lines)
    - packages/sft-domain/src/sft_domain/ops/state.py (79 lines)
    - packages/sft-domain/src/sft_domain/ops/_validators.py (19 lines)
    - packages/sft-domain/src/sft_domain/scheduling/__init__.py (14 lines)
    - packages/sft-domain/src/sft_domain/scheduling/heuristic.py (142 lines)
    - packages/sft-domain/src/sft_domain/scheduling/constraints.py (65 lines)
    - packages/sft-domain/orders.yaml (20 orders, 213 lines)
    - packages/sft-domain/asset_capacity.yaml (30 entries, 234 lines)
    - packages/sft-domain/anomaly_baselines.yaml (11 baselines, 137 lines)
  modified:
    - packages/sft-domain/src/sft_domain/failure_modes/models.py (added
      hitl_tier, setup_minutes, severity_band fields — backward-compatible)
    - packages/sft-domain/src/sft_domain/failure_modes.yaml (added `neppy` +
      `unlevel_dyeing`; annotated 7 textile defects with hitl_tier mapping)
    - packages/sft-domain/tests/test_ops_models.py (500 lines, replaced Wave 0 stub)
    - packages/sft-domain/tests/test_failure_modes_hitl_tier.py (132 lines,
      replaced Wave 0 stub)
    - packages/sft-domain/tests/test_scheduling.py (279 lines, replaced Wave 0 stub)
    - packages/sft-domain/tests/test_yaml_validators.py (149 lines, replaced
      Wave 0 stub)
decisions:
  - D-06-04-01 — RagCitation moved canonically into sft-domain (ops/citation.py)
    to break the latent sft-domain → sft-agents circular dependency that the
    plan's literal instruction would have created. sft-agents declares
    sft-domain as runtime dep (pyproject), so the citation type belongs in the
    domain layer. sft-agents.models.evidence.RagCitation will be migrated to
    a re-export in a follow-up plan (zero-impact today — no caller imports
    citations from sft-agents yet).
  - D-06-04-02 — schedule_id derived from sha256("strategy|horizon_start_iso|
    sorted(order_ids)")[:32] for reproducibility (planner pass T1 truth).
    `created_at` is fixed to `horizon_start` (not datetime.now(UTC)) so the
    same inputs produce identical ScheduleDraft frames — required by
    test_determinism_items_identical + test_deterministic_schedule_id.
  - D-06-04-03 — earliest_slot is "append-last + setup" rather than the
    full-gap-search of RESEARCH §Pattern 5 pseudocode. The pure append model
    is sufficient for SPT/EDD (orders are sorted up front; the timeline grows
    monotonically), keeps the function O(n) per asset, and produces the
    invariants tested (no-overlap, dye-lot changeover, setup gap).
metrics:
  duration_minutes: 35
  files_created: 13
  files_modified: 6
  tests_total: 157
  tests_added_this_plan: 81
  tests_passing: 157
  tests_failing: 0
  loc_added: 2542
  completed_date: 2026-05-23
---

# Phase 6 Plan 04: Ops Domain Models Summary

OPS domain layer foundation for all 4 Wave 2 agents (AnomalyDetector,
OperatorAssistant, QualityInspector, ProductionPlanner): 10 Pydantic v2
frozen models (anomaly/quality/schedule/state) + 3 YAML seed files (orders,
asset_capacity, anomaly_baselines) + deterministic SPT/EDD pure-function
heuristics, all delivered TDD with 81 new tests and zero regressions on the
76 pre-existing sft-domain tests.

## What Shipped

### Pydantic Models (sft-domain/ops)

| Module        | Models / Exports                                                                                          |
| ------------- | --------------------------------------------------------------------------------------------------------- |
| `anomaly.py`  | `Anomaly`, `AnomalyBaseline`, `Severity`, `load_anomaly_baselines`, `invalidate_anomaly_baselines_cache`  |
| `quality.py`  | `QualityEvent`, `QualityVerdict`, `DefectType` (7-defect Literal), `Severity`                             |
| `schedule.py` | `OrderSpec`, `AssetCapacity`, `ScheduleDraftItem`, `ScheduleDraft`, `load_orders`, `load_asset_capacity`  |
| `state.py`    | `OpsState` (TypedDict, total=False, 15 fields for LangGraph subgraph)                                     |
| `citation.py` | `RagCitation` (moved from sft-agents to break circular dep — see D-06-04-01)                              |

All models: `frozen=True`, `extra="forbid"`, tz-aware datetime via
`field_validator` (Pitfall 7). `QualityEvent.dye_lot_id` enforces the D-QI-04
regex `^DL-[A-Z0-9-]+-\d{8}-[0-9a-f]+$`; `QualityVerdict.score` is
constrained to `[0..4]` (T-V6-injection-score). `ScheduleDraftItem` enforces
`end_at > start_at` via `model_validator`.

### Scheduling (sft-domain/scheduling)

- `schedule_spt(orders, capacity, failure_modes, horizon_start, horizon_end)`
  — Shortest Processing Time first; tie-break stable on `order_id`.
- `schedule_edd(...)` — Earliest Due Date first; same tie-break.
- Helper `earliest_slot` + `setup_minutes_for_transition` (constraints.py)
  honor dye-lot changeover AND `FailureMode.setup_minutes`.
- **Determinism:** same inputs → identical `items` AND identical `schedule_id`
  (sha256-derived UUID). `created_at = horizon_start` (not `now(UTC)`).

### YAML Seed Files

| File                     | Top-level key       | Entries | Notes                                                                                                |
| ------------------------ | ------------------- | ------- | ---------------------------------------------------------------------------------------------------- |
| `orders.yaml`            | `orders:`           | 20      | 4 SKU families × 5 process families (cotton, poly-blend, denim, technical, warping, dyeing, finish)  |
| `asset_capacity.yaml`    | `asset_capacity:`   | 30      | One per registry asset; capacity calibrated per family (loom 260-320 m/h, dye 50-60 m/h, etc.)       |
| `anomaly_baselines.yaml` | `anomaly_baselines:`| 11      | Coverage of 5 asset_family × representative sensors (warp_tension, spindle_rpm, dyer_temperature...) |

### FailureMode Extension (backward-compat)

`packages/sft-domain/src/sft_domain/failure_modes/models.py` gained 3 optional
fields (`hitl_tier: Literal["auto-log","supervisor","manager+safety"] =
"supervisor"`, `setup_minutes: int = 0`, `severity_band: dict[str, Any] = {}`)
with defaults so all 30 existing entries continue to parse. The YAML gained
`neppy` + `unlevel_dyeing` to complete the 7-defect textile taxonomy
(broken_end, mispick, slub, neppy, selvage_fault, shade_deviation,
unlevel_dyeing). All 7 carry a non-default `hitl_tier` mapping per
RESEARCH §Pattern 6.

## Test Results

```
$ pytest packages/sft-domain/tests/
================== 157 passed in 3.47s ==================
```

Breakdown (157 total, 81 new this plan, 76 baseline preserved):
- test_ops_models.py: 46 (new) — frozen, extra=forbid, tz-aware, score range,
  dye_lot_id regex, OpsState keys
- test_failure_modes_hitl_tier.py: 13 (new) — Literal validation, defaults,
  backward-compat, 7-textile-defect coverage
- test_scheduling.py: 13 (new) — SPT/EDD ordering, no-overlap, dye-lot
  changeover, setup_minutes from failure mode, unscheduled overflow,
  determinism (items + schedule_id), SPT≠EDD divergence
- test_yaml_validators.py: 9 (new) — loader smoke, cross-refs orders.compatible
  ⊆ capacity.family, capacity.asset_id ⊆ registry, anomaly families ⊆ registry,
  yaml.safe_load enforcement
- test_failure_modes_loader.py: 23 (preserved, unchanged)
- test_glossary_*.py: 53 (preserved, unchanged)

## TDD Gate Compliance

Each task followed RED → GREEN:
- Task 1 (RED): commit `d244a00` — failing tests for ops models + failure_modes
  extension; verified `ModuleNotFoundError: sft_domain.ops`.
- Task 2 (GREEN): commit `1c535fd` — implementation + failure_modes.yaml
  extension. All 82 tests green; zero regressions on existing 23 failure_modes
  loader tests.
- Task 3 (RED): commit `dcd1140` — failing tests for scheduling + YAML
  validators; verified `ModuleNotFoundError: sft_domain.scheduling`.
- Task 4 (GREEN): commit `5a8a57f` — scheduling implementation + 3 YAML seeds.
  All 157 tests green.

Plan-level `type: tdd` gate satisfied: every behavior-adding commit
(`feat(...)`) is preceded by a `test(...)` commit on the same surface.

## Commits

| Hash      | Type | Subject                                                                       |
| --------- | ---- | ----------------------------------------------------------------------------- |
| `d244a00` | test | add failing tests for ops models and failure_modes hitl_tier extension        |
| `1c535fd` | feat | implement ops domain models and extend FailureMode                            |
| `dcd1140` | test | add failing tests for SPT/EDD heuristics and YAML cross-refs                  |
| `5a8a57f` | feat | implement SPT/EDD heuristics and ship 3 YAML seed files                       |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 - Architectural] RagCitation lives in sft-domain, not sft-agents**

- **Found during:** Task 2 (implementing `QualityVerdict.citations`)
- **Issue:** The plan instructs `from sft_agents.models.evidence import
  RagCitation` inside `sft-domain`. `sft-agents/pyproject.toml` already
  declares `sft-domain` as a runtime dependency; importing the reverse
  direction would create a hard circular dependency at install time
  (`pip install` would fail) and at import time (`ImportError` from cycle).
- **Fix:** Created `sft_domain/ops/citation.py` containing an identical
  `RagCitation` (same schema, same validator). Exported via `sft_domain.ops`.
  The existing `sft_agents.models.evidence.RagCitation` was left untouched
  (no callers were importing citations across the boundary yet) and will be
  migrated to a re-export of the new canonical home in a follow-up plan.
  Document references this in `ops/citation.py` docstring.
- **Files modified:** `packages/sft-domain/src/sft_domain/ops/citation.py`,
  `packages/sft-domain/src/sft_domain/ops/__init__.py`,
  `packages/sft-domain/src/sft_domain/ops/quality.py`,
  `packages/sft-domain/src/sft_domain/ops/schedule.py`
- **Commit:** `1c535fd`
- **Why "Rule 4" not "Rule 3":** This is architectural — choosing where a
  shared model canonically lives. The decision affects multiple packages.

**2. [Rule 1 - Bug] `created_at` must be deterministic for `test_determinism`**

- **Found during:** Task 4 (implementing `schedule_spt`)
- **Issue:** Plan's `ScheduleDraft.created_at` default is
  `datetime.now(UTC)`. Two consecutive `schedule_spt(...)` calls would
  therefore produce different `created_at` values, breaking the determinism
  invariant tested by `test_determinism_items_identical` and required by the
  plan's first truth ("`schedule_spt(...)` produces deterministic output
  given identical inputs").
- **Fix:** In `heuristic._schedule(...)`, explicitly pass `created_at=
  horizon_start` so the timestamp is derived from a stable input. The
  `ScheduleDraft` model retains its `default_factory=lambda: datetime.now(UTC)`
  for callers that don't pass `created_at` (e.g., LLM-generated drafts in
  follow-up plans), preserving the "default ergonomic" behavior the plan
  prescribed.
- **Files modified:** `packages/sft-domain/src/sft_domain/scheduling/heuristic.py`
- **Commit:** `5a8a57f`

**3. [Rule 1 - Bug] Plan listed `neppy` + `unlevel_dyeing` as required textile
defects but they were absent from failure_modes.yaml**

- **Found during:** Task 2 (running `test_failure_modes_hitl_tier`)
- **Issue:** The existing taxonomy used `neps` (not `neppy`) and
  `screziatura` (the IT word for unlevel dyeing) but did not carry an
  `unlevel_dyeing` id. Plan truth #10 requires all 7 textile defects covered.
- **Fix:** Added `neppy` and `unlevel_dyeing` entries to
  `failure_modes.yaml`. The pre-existing `neps`/`screziatura` entries remain
  (some legacy SOPs reference them by name); a follow-up plan may consolidate
  via aliasing if desired.
- **Files modified:** `packages/sft-domain/src/sft_domain/failure_modes.yaml`
- **Commit:** `1c535fd`

### Pre-existing FailureMode entries auto-extended

Once the FailureMode model gained `hitl_tier`/`setup_minutes`/`severity_band`
with defaults, all 30 pre-existing YAML entries became valid without YAML
edits (they receive default values). This is the desired backward-compat
behavior captured by `test_existing_entries_still_valid`.

## Authentication Gates

None encountered (all work was local Python + filesystem).

## Known Stubs

None. Every ops model and scheduling function ships with full implementation
and tests. The `rationale_md` field on `ScheduleDraft` defaults to empty
string (`""`) because the LLM-driven rationale generation is **out of scope**
for the pure-function heuristic and lives in the `production-planner` agent
plan (06-08 / 06-09 wave). This is documented in the heuristic.py docstring
and is not a stub — it is an intentional separation of concerns required by
the determinism invariant (LLM calls are non-deterministic).

## Threat Flags

None. All threats from the plan's `<threat_model>` (T-V6-yaml-injection,
T-V6-injection-dye-lot, T-V6-injection-score, T-V6-baseline, T-V6-naive-
datetime, T-V6-yaml-drift) are mitigated as planned:

- `yaml.safe_load` only — enforced by source-grep tests
  (`test_safe_load_used_in_anomaly_loader`, `test_safe_load_used_in_schedule_loader`).
- `dye_lot_id` regex enforced by Pydantic at model construction.
- `score` `ge=0, le=4` enforced by Pydantic.
- `anomaly_baselines.yaml` PR-reviewed; Pydantic schema validation on load;
  cross-ref to registry covered by
  `test_anomaly_baselines_asset_family_in_registry`.
- All datetime fields use the shared `_tz_aware` validator from
  `sft_domain.ops._validators`.
- YAML drift covered by `test_orders_compatible_families_subset_of_capacity_families`,
  `test_asset_capacity_asset_id_subset_of_registry`,
  `test_asset_capacity_family_matches_registry_for_each_asset`.

## Self-Check: PASSED

Verified files exist on disk:
- `packages/sft-domain/src/sft_domain/ops/{__init__,anomaly,quality,schedule,state,citation,_validators}.py` ✓
- `packages/sft-domain/src/sft_domain/scheduling/{__init__,heuristic,constraints}.py` ✓
- `packages/sft-domain/{orders,asset_capacity,anomaly_baselines}.yaml` ✓
- `packages/sft-domain/src/sft_domain/failure_modes/models.py` (extended) ✓
- `packages/sft-domain/src/sft_domain/failure_modes.yaml` (extended) ✓

Verified commits exist in `git log --oneline`: `d244a00`, `1c535fd`,
`dcd1140`, `5a8a57f` ✓

Verified test suite: `pytest packages/sft-domain/tests/` → 157 passed, 0 failed, 0 skipped ✓

Verified canonical import smoke: `from sft_domain.ops import *` and
`from sft_domain.scheduling import schedule_spt, schedule_edd` both succeed ✓
