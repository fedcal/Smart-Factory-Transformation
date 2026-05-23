---
phase: 06-agents-operations-production
plan: 00
plan_id: 06-00
subsystem: testing-scaffold
tags: [wave-0, test-stubs, fixtures, mock-llm, ops-agents]
requires: []
provides:
  - pytest-discoverable test stubs for plans 06-01..06-13
  - shared fixtures `mock_llm_backend` and `ops_scenario` for ops e2e
  - 12 scenario YAML skeletons (4 agents × 3 scenarios)
  - 12 mock LLM JSONL skeletons (record/replay schema)
  - `real-llm` pytest marker (opt-in Qwen2.5 smoke gate)
affects:
  - tests/conftest.py (added real-llm marker)
tech-stack:
  added: []
  patterns:
    - "Per-package pytest stubs with module docstring → implementing plan ID mapping"
    - "yaml.safe_load enforcement on all fixture loaders (T-V6-W0-yaml-injection mitigation)"
    - "JSONL record/replay schema: prompt_hash + response{content,tool_calls,usage_metadata}"
    - "Indirect parametrize key '<agent>/<scenario>' for ops_scenario / mock_llm_backend fixtures"
key-files:
  created:
    - packages/sft-agents/tests/llm/__init__.py
    - packages/sft-agents/tests/llm/test_mock_backend.py
    - packages/sft-agents/tests/runtime/__init__.py
    - packages/sft-agents/tests/runtime/test_rate_limiter.py
    - packages/sft-agents/tests/runtime/test_clusters_ops.py
    - packages/sft-agents/tests/tools/__init__.py
    - packages/sft-agents/tests/tools/test_escalate_tool.py
    - packages/sft-agents/tests/tools/test_log_event_tool.py
    - packages/sft-domain/tests/test_ops_models.py
    - packages/sft-domain/tests/test_scheduling.py
    - packages/sft-domain/tests/test_yaml_validators.py
    - packages/sft-domain/tests/test_failure_modes_hitl_tier.py
    - apps/agents/ops/anomaly-detector/tests/__init__.py
    - apps/agents/ops/anomaly-detector/tests/test_anomaly_detector.py
    - apps/agents/ops/anomaly-detector/tests/test_rate_limit.py
    - apps/agents/ops/anomaly-detector/tests/test_evidence_panel.py
    - apps/agents/ops/quality-inspector/tests/__init__.py
    - apps/agents/ops/quality-inspector/tests/test_quality_inspector.py
    - apps/agents/ops/quality-inspector/tests/test_nats_consumer.py
    - apps/agents/ops/quality-inspector/tests/test_evidence_panel.py
    - apps/agents/ops/production-planner/tests/__init__.py
    - apps/agents/ops/production-planner/tests/test_production_planner.py
    - apps/agents/ops/production-planner/tests/test_evidence_panel.py
    - apps/agents/ops/operator-assistant/tests/__init__.py
    - apps/agents/ops/operator-assistant/tests/test_operator_assistant.py
    - apps/agents/ops/operator-assistant/tests/test_validators.py
    - apps/agents/ops/operator-assistant/tests/test_evidence_panel.py
    - simulators/sim-textile/tests/test_quality_generator.py
    - simulators/sim-textile/tests/test_production_state.py
    - services/agents-scheduler/tests/__init__.py
    - services/agents-scheduler/tests/test_scheduler.py
    - apps/api-gateway/tests/test_ops_endpoints.py
    - tests/e2e/ops/__init__.py
    - tests/e2e/ops/conftest.py
    - tests/e2e/ops/test_operator_assistant_scenarios.py
    - tests/e2e/ops/test_production_planner_scenarios.py
    - tests/e2e/ops/test_quality_inspector_scenarios.py
    - tests/e2e/ops/test_anomaly_detector_scenarios.py
    - tests/fixtures/ops_scenarios/operator-assistant/happy.yaml
    - tests/fixtures/ops_scenarios/operator-assistant/degraded.yaml
    - tests/fixtures/ops_scenarios/operator-assistant/failure.yaml
    - tests/fixtures/ops_scenarios/production-planner/happy.yaml
    - tests/fixtures/ops_scenarios/production-planner/degraded.yaml
    - tests/fixtures/ops_scenarios/production-planner/failure.yaml
    - tests/fixtures/ops_scenarios/quality-inspector/happy.yaml
    - tests/fixtures/ops_scenarios/quality-inspector/degraded.yaml
    - tests/fixtures/ops_scenarios/quality-inspector/failure.yaml
    - tests/fixtures/ops_scenarios/anomaly-detector/happy.yaml
    - tests/fixtures/ops_scenarios/anomaly-detector/degraded.yaml
    - tests/fixtures/ops_scenarios/anomaly-detector/failure.yaml
    - tests/fixtures/llm_responses/operator-assistant/happy.jsonl
    - tests/fixtures/llm_responses/operator-assistant/degraded.jsonl
    - tests/fixtures/llm_responses/operator-assistant/failure.jsonl
    - tests/fixtures/llm_responses/production-planner/happy.jsonl
    - tests/fixtures/llm_responses/production-planner/degraded.jsonl
    - tests/fixtures/llm_responses/production-planner/failure.jsonl
    - tests/fixtures/llm_responses/quality-inspector/happy.jsonl
    - tests/fixtures/llm_responses/quality-inspector/degraded.jsonl
    - tests/fixtures/llm_responses/quality-inspector/failure.jsonl
    - tests/fixtures/llm_responses/anomaly-detector/happy.jsonl
    - tests/fixtures/llm_responses/anomaly-detector/degraded.jsonl
    - tests/fixtures/llm_responses/anomaly-detector/failure.jsonl
  modified:
    - tests/conftest.py
decisions:
  - "Added packages/sft-agents/tests/runtime/__init__.py (not listed in plan) for parity with llm/ and tools/ subpackages — required for clean pytest discovery"
  - "Used per-package pytest runs for verification (cd into package root) because the existing tests/__init__.py collision with packages/sft-agents/tests/conftest.py and packages/sft-domain/tests/conftest.py causes ImportPathMismatchError when collecting cross-package from repo root (pre-existing limitation, not Wave 0 regression)"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-23"
  tasks_total: 3
  tasks_completed: 3
  files_created: 61
  files_modified: 1
---

# Phase 06 Plan 00: Wave 0 Test Scaffolding Summary

**One-liner:** Wave 0 test scaffold for Phase 6 ops agents — 61 pytest stub files, 12 scenario YAML + 12 mock LLM JSONL fixtures, shared `mock_llm_backend`/`ops_scenario` fixtures, and `real-llm` marker — all skips, zero business logic, so Wave 1+ tasks always have an `<automated>` target to point at.

## What Was Built

- **11 stub test modules + 3 `__init__.py`** for sft-agents (`llm/`, `runtime/`, `tools/`) and sft-domain — covering future plans 06-01..06-08.
- **20 stub test modules + 4 `__init__.py`** for the 4 ops agents (anomaly-detector, quality-inspector, production-planner, operator-assistant), sim-textile extensions, agents-scheduler service, and api-gateway ops endpoints — covering future plans 06-06..06-13.
- **4 e2e scenario modules + 1 `conftest.py` + 1 `__init__.py`** under `tests/e2e/ops/` — 12 parameterized stub tests (4 agents × 3 scenarios) all gated by `@pytest.mark.e2e`.
- **Shared fixtures** `ops_scenario` (yaml.safe_load loader) and `mock_llm_backend` (env-var wiring for MockReplayChatModel) in `tests/e2e/ops/conftest.py`.
- **12 scenario YAML skeletons** under `tests/fixtures/ops_scenarios/` — all valid `yaml.safe_load`.
- **12 mock LLM JSONL skeletons** under `tests/fixtures/llm_responses/` — each one valid single-line JSON with `prompt_hash` + `response.{content,tool_calls,usage_metadata}` shape.
- **`real-llm` pytest marker** registered in root `tests/conftest.py`.

## Plan → Test File Mapping

Each stub's module docstring records the implementing plan ID for downstream agents:

| Plan | Stub Files |
|------|------------|
| 06-01 mock-llm-backend | `packages/sft-agents/tests/llm/test_mock_backend.py` |
| 06-02 rate-limiter | `packages/sft-agents/tests/runtime/test_rate_limiter.py`, `apps/agents/ops/anomaly-detector/tests/test_rate_limit.py` |
| 06-03 ops-cluster-routing | `packages/sft-agents/tests/runtime/test_clusters_ops.py` |
| 06-04 ops-domain-models | `packages/sft-domain/tests/test_ops_models.py`, `test_yaml_validators.py`, `test_failure_modes_hitl_tier.py` |
| 06-05 ops-shared-tools | `packages/sft-agents/tests/tools/test_escalate_tool.py`, `test_log_event_tool.py` |
| 06-06 anomaly-detector | `apps/agents/ops/anomaly-detector/tests/test_anomaly_detector.py` |
| 06-07 quality-inspector | `apps/agents/ops/quality-inspector/tests/test_quality_inspector.py`, `test_nats_consumer.py` |
| 06-08 production-planner | `apps/agents/ops/production-planner/tests/test_production_planner.py`, `packages/sft-domain/tests/test_scheduling.py` |
| 06-09 operator-assistant + sim-textile | `apps/agents/ops/operator-assistant/tests/test_operator_assistant.py`, `test_validators.py`, `simulators/sim-textile/tests/test_quality_generator.py`, `test_production_state.py` |
| 06-10 agents-scheduler | `services/agents-scheduler/tests/test_scheduler.py` |
| 06-11 api-gateway-ops-endpoints | `apps/api-gateway/tests/test_ops_endpoints.py` |
| 06-12 e2e-scenarios | `tests/e2e/ops/test_*_scenarios.py` (4 modules) + `tests/e2e/ops/conftest.py` + 12 YAML + 12 JSONL fixtures |
| 06-13 EvidencePanel docs | `apps/agents/ops/{4-agents}/tests/test_evidence_panel.py` |

## Verification Performed

| Check | Command | Result |
|-------|---------|--------|
| sft-agents stubs collect | `(cd packages/sft-agents && pytest tests/llm/ tests/runtime/ tests/tools/ --collect-only -q)` | 5 placeholders collected |
| sft-domain stubs collect | `(cd packages/sft-domain && pytest tests/test_ops_models.py tests/test_scheduling.py tests/test_yaml_validators.py tests/test_failure_modes_hitl_tier.py --collect-only -q)` | 4 placeholders collected |
| anomaly-detector stubs | `(cd apps/agents/ops/anomaly-detector && pytest tests/ --collect-only -q)` | 3 placeholders |
| quality-inspector stubs | `(cd apps/agents/ops/quality-inspector && pytest tests/ --collect-only -q)` | 3 placeholders |
| production-planner stubs | `(cd apps/agents/ops/production-planner && pytest tests/ --collect-only -q)` | 2 placeholders |
| operator-assistant stubs | `(cd apps/agents/ops/operator-assistant && pytest tests/ --collect-only -q)` | 3 placeholders |
| sim-textile new stubs | `(cd simulators/sim-textile && pytest tests/test_quality_generator.py tests/test_production_state.py --collect-only -q)` | 2 placeholders |
| scheduler stub | `(cd services/agents-scheduler && pytest tests/ --collect-only -q)` | 1 placeholder |
| api-gateway ops stub | `(cd apps/api-gateway && pytest tests/test_ops_endpoints.py --collect-only -q)` | 1 placeholder |
| e2e ops collection (`-m e2e`) | `pytest tests/e2e/ops/ --collect-only -q -m "e2e"` | 12 parameterized tests collected |
| 12 YAML stubs `yaml.safe_load` | `python3 -c "import yaml, pathlib; [yaml.safe_load(p.read_text()) for p in pathlib.Path('tests/fixtures/ops_scenarios').rglob('*.yaml')]"` | 12 files load, all `dict` with `scenario` key |
| 12 JSONL stubs `json.loads` | `python3 -c "import json, pathlib; [json.loads(line) for p in pathlib.Path('tests/fixtures/llm_responses').rglob('*.jsonl') for line in p.read_text().splitlines() if line.strip()]"` | 12 files valid; each has `prompt_hash` + `response` |
| `real-llm` marker registered | `pytest --markers \| grep real-llm` | `@pytest.mark.real-llm: opt-in real Qwen2.5 smoke tests (skipped in CI default)` |

**Total placeholder tests collected across all stub modules:** 24 unit/module-level + 12 e2e parameterized = **36 skipped stubs**.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing `packages/sft-agents/tests/runtime/__init__.py`**
- **Found during:** Task 1
- **Issue:** The plan explicitly listed `__init__.py` for `llm/` and `tools/` subdirectories but omitted one for `runtime/`. Pytest collection of `tests/runtime/test_rate_limiter.py` and `tests/runtime/test_clusters_ops.py` works either way under `rootdir`-style discovery, but adding the `__init__.py` keeps the three new sub-packages structurally symmetric and avoids future namespace-package ambiguity inside `sft-agents`.
- **Fix:** Created empty `packages/sft-agents/tests/runtime/__init__.py`.
- **Commit:** `f7da9ef` (Task 1).

No other deviations — plan executed exactly as written.

### Auth Gates

None encountered.

### Pre-existing Test-Collection Constraint (Observation, Not Deviation)

When running `pytest` from the repo root across `packages/sft-agents/tests/` and `packages/sft-domain/tests/` simultaneously, pytest hits an `ImportPathMismatchError` because both packages contain a `tests/__init__.py` (resolving to the same module name `tests.conftest`). This is a **pre-existing** monorepo limitation independent of Wave 0; the canonical Phase 6 verification harness uses the per-package `nx run-many --target=test --projects=...` command (see `06-VALIDATION.md`) which avoids this collision. The plan's `<automated>` verify commands have been validated per-package and all pass.

## Threat Model Compliance

| Threat ID | Disposition | Status |
|-----------|-------------|--------|
| T-V6-W0-fixture-tamper | accept | Wave 0 fixture content is benign placeholders; commit hashes recorded for future drift detection |
| T-V6-W0-yaml-injection | mitigate | `tests/e2e/ops/conftest.py::ops_scenario` uses `yaml.safe_load` exclusively (`yaml.load` / `Loader` / `FullLoader` / `UnsafeLoader` never imported) |
| T-V6-secret | mitigate | All 12 JSONL fixtures contain literal `"Wave 0 stub"` string and zeroed `prompt_hash`; no API keys, no PII, no real LLM traces |

## Known Stubs

This entire plan is intentional stubs (Wave 0 scaffold contract). Every test module skips and every fixture is a placeholder. The plan's success criterion **is** the stub set — they will be replaced by Wave 1-3 implementations. Resolution map is in the "Plan → Test File Mapping" table above.

## Commits

- `f7da9ef` — test(06-00): add Wave 0 stubs for sft-agents and sft-domain ops tests
- `cf0a6c9` — test(06-00): add Wave 0 stubs for ops agents, sim-textile, scheduler, gateway
- `f587ad6` — test(06-00): add e2e/ops scaffold, scenario YAML+JSONL fixtures, real-llm marker

## Self-Check

Files: 61 created + 1 modified, all confirmed present on disk.
Commits: 3 task commits + final metadata commit.
Verification: all `<automated>` checks per task passed.
Nyquist gate: 06-VALIDATION.md `Wave 0 Requirements` checklist now fully satisfiable — `nyquist_compliant: true` can be set in the next sweep.
