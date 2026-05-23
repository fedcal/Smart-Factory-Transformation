---
phase: 07-agents-maintenance-reliability
plan: 00
plan_id: 07-00
subsystem: testing-scaffold
tags: [wave-0, test-stubs, fixtures, mock-llm, maintenance-agents]
requires: []
provides:
  - pytest-discoverable test stubs for plans 07-01..07-12
  - shared fixtures `mock_llm_backend` and `mnt_scenario` for maintenance e2e
  - 12 scenario YAML skeletons (4 agents × 3 scenarios)
  - 6 mock LLM JSONL skeletons (rca-specialist × 3 + maintenance-coach × 3 — PM + DA are LLM-free)
affects: []
tech-stack:
  added: []
  patterns:
    - "Per-package pytest stubs with module docstring → implementing plan ID mapping (mirrors Phase 6 06-00)"
    - "yaml.safe_load enforcement on all fixture loaders (T-V7-W0-yaml-injection mitigation)"
    - "JSONL record/replay schema: prompt_hash + response{content,tool_calls,usage_metadata}"
    - "Indirect parametrize key '<agent>/<scenario>' for mnt_scenario / mock_llm_backend fixtures"
    - "Selective JSONL trace wiring — mock_llm_backend only sets MOCK_LLM_FIXTURE for rca-specialist + maintenance-coach (PM + DA are deterministic, LLM-free)"
key-files:
  created:
    - packages/sft-ml/tests/__init__.py
    - packages/sft-ml/tests/test_feature_map.py
    - packages/sft-ml/tests/test_model_smoke.py
    - packages/sft-ml/tests/test_training.py
    - packages/sft-agents/tests/runtime/test_clusters_maintenance.py
    - packages/sft-agents/tests/tools/test_request_help.py
    - packages/sft-domain/tests/failure_modes/__init__.py
    - packages/sft-domain/tests/failure_modes/test_maintenance_meta.py
    - infra/migrations/timescale/tests/test_migration_008.py
    - infra/migrations/timescale/tests/test_migration_009.py
    - apps/agents/maintenance/predictive-maintenance/tests/__init__.py
    - apps/agents/maintenance/predictive-maintenance/tests/conftest.py
    - apps/agents/maintenance/predictive-maintenance/tests/test_inference.py
    - apps/agents/maintenance/predictive-maintenance/tests/test_consumer.py
    - apps/agents/maintenance/predictive-maintenance/tests/test_evidence_panel.py
    - apps/agents/maintenance/rca-specialist/tests/__init__.py
    - apps/agents/maintenance/rca-specialist/tests/conftest.py
    - apps/agents/maintenance/rca-specialist/tests/test_models.py
    - apps/agents/maintenance/rca-specialist/tests/test_validators.py
    - apps/agents/maintenance/rca-specialist/tests/test_evidence_panel.py
    - apps/agents/maintenance/maintenance-coach/tests/__init__.py
    - apps/agents/maintenance/maintenance-coach/tests/conftest.py
    - apps/agents/maintenance/maintenance-coach/tests/test_checkpoint_resume.py
    - apps/agents/maintenance/maintenance-coach/tests/test_mttr.py
    - apps/agents/maintenance/maintenance-coach/tests/test_evidence_panel.py
    - apps/agents/maintenance/downtime-analyzer/tests/__init__.py
    - apps/agents/maintenance/downtime-analyzer/tests/conftest.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_oee.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_pareto.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_consumer.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_repository.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_evidence_panel.py
    - simulators/sim-textile/tests/test_downtime_generator.py
    - apps/api-gateway/tests/test_maintenance_endpoints.py
    - tests/e2e/maintenance/__init__.py
    - tests/e2e/maintenance/conftest.py
    - tests/e2e/maintenance/test_predictive_maintenance_scenarios.py
    - tests/e2e/maintenance/test_rca_specialist_scenarios.py
    - tests/e2e/maintenance/test_maintenance_coach_scenarios.py
    - tests/e2e/maintenance/test_downtime_analyzer_scenarios.py
    - tests/fixtures/mnt_scenarios/predictive-maintenance/happy.yaml
    - tests/fixtures/mnt_scenarios/predictive-maintenance/degraded.yaml
    - tests/fixtures/mnt_scenarios/predictive-maintenance/failure.yaml
    - tests/fixtures/mnt_scenarios/rca-specialist/happy.yaml
    - tests/fixtures/mnt_scenarios/rca-specialist/degraded.yaml
    - tests/fixtures/mnt_scenarios/rca-specialist/failure.yaml
    - tests/fixtures/mnt_scenarios/maintenance-coach/happy.yaml
    - tests/fixtures/mnt_scenarios/maintenance-coach/degraded.yaml
    - tests/fixtures/mnt_scenarios/maintenance-coach/failure.yaml
    - tests/fixtures/mnt_scenarios/downtime-analyzer/happy.yaml
    - tests/fixtures/mnt_scenarios/downtime-analyzer/degraded.yaml
    - tests/fixtures/mnt_scenarios/downtime-analyzer/failure.yaml
    - tests/fixtures/llm_responses/rca-specialist/happy.jsonl
    - tests/fixtures/llm_responses/rca-specialist/degraded.jsonl
    - tests/fixtures/llm_responses/rca-specialist/failure.jsonl
    - tests/fixtures/llm_responses/maintenance-coach/happy.jsonl
    - tests/fixtures/llm_responses/maintenance-coach/degraded.jsonl
    - tests/fixtures/llm_responses/maintenance-coach/failure.jsonl
  modified: []
decisions:
  - "Adopted the same `def test_placeholder(): pytest.skip(...)` body convention used in Phase 6 06-00 (predictable per-test reporting, avoids module-level skip surprises)"
  - "`mock_llm_backend` selectively sets `MOCK_LLM_FIXTURE` only for rca-specialist + maintenance-coach (PM + DA are LLM-free per 07-VALIDATION.md L91-95) — forces clear KeyError if a future test mistakenly tries to instantiate an LLM backend for the deterministic agents"
  - "Per-agent conftest.py stubs are docstring-only (no fixtures) — real fixtures land in the implementing plan; keeps Wave 0 surface minimal and avoids premature coupling"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-23"
  tasks_total: 3
  tasks_completed: 3
  files_created: 58
  files_modified: 0
---

# Phase 07 Plan 00: Wave 0 Test Scaffolding Summary

**One-liner:** Wave 0 test scaffold for Phase 7 maintenance agents — 58 pytest stub files, 12 scenario YAML + 6 mock LLM JSONL fixtures, shared `mock_llm_backend`/`mnt_scenario` fixtures — all skips, zero business logic, so Wave 1+ tasks always have an `<automated>` target to point at.

## What Was Built

- **10 stub test modules + 2 `__init__.py`** for sft-ml, sft-agents (`runtime/clusters_maintenance`, `tools/request_help`), sft-domain (`failure_modes/maintenance_meta`), and timescale migrations 008/009 — covering future plans 07-01..07-05.
- **22 stub test modules + 4 `__init__.py` + 4 `conftest.py`** for the 4 maintenance agents (predictive-maintenance, rca-specialist, maintenance-coach, downtime-analyzer), sim-textile downtime generator extension, and api-gateway maintenance endpoints — covering future plans 07-05..07-11.
- **4 e2e scenario modules + 1 `conftest.py` + 1 `__init__.py`** under `tests/e2e/maintenance/` — 12 parameterized stub tests (4 agents × 3 scenarios) all gated by `@pytest.mark.e2e`.
- **Shared fixtures** `mnt_scenario` (yaml.safe_load loader) and `mock_llm_backend` (env-var wiring for MockReplayChatModel — only for rca-specialist + maintenance-coach) in `tests/e2e/maintenance/conftest.py`.
- **12 scenario YAML skeletons** under `tests/fixtures/mnt_scenarios/` — all valid `yaml.safe_load` with `{scenario: {name, note}}` shape.
- **6 mock LLM JSONL skeletons** under `tests/fixtures/llm_responses/{rca-specialist,maintenance-coach}/` — each one valid single-line JSON with `prompt_hash` + `response.{content,tool_calls,usage_metadata}` shape.

## Plan → Test File Mapping

Each stub's module docstring records the implementing plan ID for downstream agents:

| Plan | Stub Files |
|------|------------|
| 07-01 audit-actiontype-extension | `infra/migrations/timescale/tests/test_migration_009.py` |
| 07-02 taxonomy-extension | `packages/sft-domain/tests/failure_modes/test_maintenance_meta.py` |
| 07-03 sft-ml-scaffold | `packages/sft-ml/tests/test_feature_map.py`, `test_model_smoke.py`, `test_training.py` |
| 07-04 maintenance-cluster-routing + shared tools | `packages/sft-agents/tests/runtime/test_clusters_maintenance.py`, `packages/sft-agents/tests/tools/test_request_help.py` |
| 07-05 timescale-migration-008 + sim-textile ext | `infra/migrations/timescale/tests/test_migration_008.py`, `simulators/sim-textile/tests/test_downtime_generator.py` |
| 07-06 predictive-maintenance | `apps/agents/maintenance/predictive-maintenance/tests/test_inference.py`, `test_consumer.py` |
| 07-07 rca-specialist | `apps/agents/maintenance/rca-specialist/tests/test_models.py`, `test_validators.py` |
| 07-08 maintenance-coach | `apps/agents/maintenance/maintenance-coach/tests/test_checkpoint_resume.py`, `test_mttr.py` |
| 07-09 downtime-analyzer | `apps/agents/maintenance/downtime-analyzer/tests/test_oee.py`, `test_pareto.py`, `test_consumer.py`, `test_repository.py` |
| 07-10 api-gateway-maintenance-endpoints | `apps/api-gateway/tests/test_maintenance_endpoints.py` |
| 07-11 docs+evidence-panel | `apps/agents/maintenance/{4-agents}/tests/test_evidence_panel.py` |
| 07-12 e2e-scenarios | `tests/e2e/maintenance/test_*_scenarios.py` (4 modules) + `tests/e2e/maintenance/conftest.py` + 12 YAML + 6 JSONL fixtures |

## Verification Performed

| Check | Command | Result |
|-------|---------|--------|
| sft-ml stubs collect | `(cd packages/sft-ml && pytest tests/ --collect-only -q)` | 3 placeholders collected |
| sft-agents new stubs collect | `(cd packages/sft-agents && pytest tests/runtime/test_clusters_maintenance.py tests/tools/test_request_help.py --collect-only -q)` | 2 placeholders |
| sft-domain new stub collect | `(cd packages/sft-domain && pytest tests/failure_modes/test_maintenance_meta.py --collect-only -q)` | 1 placeholder |
| predictive-maintenance stubs | `(cd apps/agents/maintenance/predictive-maintenance && pytest tests/ --collect-only -q)` | 3 placeholders |
| rca-specialist stubs | `(cd apps/agents/maintenance/rca-specialist && pytest tests/ --collect-only -q)` | 3 placeholders |
| maintenance-coach stubs | `(cd apps/agents/maintenance/maintenance-coach && pytest tests/ --collect-only -q)` | 3 placeholders |
| downtime-analyzer stubs | `(cd apps/agents/maintenance/downtime-analyzer && pytest tests/ --collect-only -q)` | 5 placeholders |
| sim-textile new stub | `(cd simulators/sim-textile && pytest tests/test_downtime_generator.py --collect-only -q)` | 1 placeholder |
| api-gateway maintenance stub | `(cd apps/api-gateway && pytest tests/test_maintenance_endpoints.py --collect-only -q)` | 1 placeholder |
| e2e maintenance collection (`-m e2e`) | `pytest tests/e2e/maintenance/ --collect-only -q -m "e2e"` | 12 parameterized tests collected |
| 12 YAML stubs `yaml.safe_load` | `python3 -c "import yaml, pathlib; [yaml.safe_load(p.read_text()) for p in pathlib.Path('tests/fixtures/mnt_scenarios').rglob('*.yaml')]"` | 12 files load, all `dict` with `scenario` key |
| 6 JSONL stubs `json.loads` | `python3 -c "import json, pathlib; [json.loads(line) for p in pathlib.Path('tests/fixtures/llm_responses').rglob('*.jsonl') if 'rca-specialist' in str(p) or 'maintenance-coach' in str(p) for line in p.read_text().splitlines() if line.strip()]"` | 6 files valid; each has `prompt_hash` + `response` |

**Total placeholder tests collected across all stub modules:** 22 unit/module-level + 12 e2e parameterized = **34 skipped stubs**.

## Deviations from Plan

None — plan executed exactly as written. The plan asked for "~50" files; final count is 58 (10 + 24 + 24) which falls inside the explicit counts the plan enumerates per task.

### Auth Gates

None encountered.

### Pre-existing Test-Collection Constraint (Observation, Not Deviation)

The migration stubs (`infra/migrations/timescale/tests/test_migration_008.py` and `test_migration_009.py`) cannot be collected stand-alone via `pytest` because the existing `infra/migrations/timescale/tests/conftest.py` (added in earlier phases) imports `testcontainers.postgres.PostgresContainer`, and the `testcontainers` package is not installed in the current Python environment. The same constraint applies to the pre-existing `test_migration_007.py` and `test_migration_idempotent.py`; it is **not** a regression introduced by Wave 0. The stubs themselves contain only `import pytest` + `def test_placeholder(): pytest.skip(...)` and will collect cleanly once 07-05 / 07-01 add `testcontainers` to the project deps (same pattern as Phase 6 testcontainers wiring). The plan's `<automated>` verify command uses `grep -c "test_placeholder"` accepting 8-10 results — 6 placeholders collect from the non-blocked modules, and the 2 migration files exist on disk per `[ -f ]` check.

## Threat Model Compliance

| Threat ID | Disposition | Status |
|-----------|-------------|--------|
| T-V7-W0-fixture-tamper | accept | Wave 0 fixture content is benign placeholders; commit hashes recorded for future drift detection |
| T-V7-W0-yaml-injection | mitigate | `tests/e2e/maintenance/conftest.py::mnt_scenario` uses `yaml.safe_load` exclusively (`yaml.load` / `Loader` / `FullLoader` / `UnsafeLoader` never imported) |
| T-V7-W0-secret | mitigate | All 6 JSONL fixtures contain literal `"Wave 0 stub"` string and zeroed `prompt_hash`; no API keys, no PII, no real LLM traces |

## Known Stubs

This entire plan is intentional stubs (Wave 0 scaffold contract). Every test module skips and every fixture is a placeholder. The plan's success criterion **is** the stub set — they will be replaced by Wave 1-5 implementations. Resolution map is in the "Plan → Test File Mapping" table above.

## Commits

- `d4ffb46` — test(07-00): add Wave 0 stubs for sft-ml, sft-agents/runtime+tools, sft-domain failure_modes, migrations 008/009
- `90a90c6` — test(07-00): add Wave 0 stubs for 4 maintenance agents, sim-textile, api-gateway
- `8934f35` — test(07-00): add e2e/maintenance scaffold, scenario YAML+JSONL fixtures

## Self-Check: PASSED

Files: 58 created + 0 modified, all confirmed present on disk.
Commits: 3 task commits (metadata commit follows this file).
Verification: all `<automated>` checks per task passed (12 e2e tests collected, 12 YAML valid `safe_load`, 6 JSONL valid single-line JSON, 22 unit placeholders collected from non-blocked modules).
Nyquist gate: 07-VALIDATION.md `Wave 0 Requirements` checklist (L73-90) now fully satisfiable — `nyquist_compliant: true` can be set in the next sweep.
