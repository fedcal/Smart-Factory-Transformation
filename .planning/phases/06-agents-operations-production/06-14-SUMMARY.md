---
phase: 06-agents-operations-production
plan: 14
plan_id: 06-14
subsystem: docs+ops-agents
requirements: [OPS-05]
status: complete
wave: 5
tags:
  - docs
  - mkdocs
  - i18n
  - agents
  - operations
  - OPS-05
  - TDD
dependency_graph:
  requires: ["06-00", "06-06", "06-07", "06-08", "06-10"]
  provides: ["bilingual-docs-ops-agents", "ops05-evidence-declaration"]
  affects:
    - docs/mkdocs.yml
    - apps/agents/ops/anomaly-detector
    - apps/agents/ops/quality-inspector
    - apps/agents/ops/production-planner
    - apps/agents/ops/operator-assistant
tech_stack:
  added:
    - mkdocs-static-i18n (folder structure, already configured)
  patterns:
    - "single-source-of-truth: metadata.py module constants mirror MkDocs page"
    - "OPS-05 declaration helper: build_ops05_evidence_panel(hitl_tier=..., extra=...)"
key_files:
  created:
    - docs/docs/agents/operations/operator-assistant.md
    - docs/docs/agents/operations/production-planner.md
    - docs/docs/agents/operations/quality-inspector.md
    - docs/docs/agents/operations/anomaly-detector.md
    - docs/docs/en/agents/operations/operator-assistant.md
    - docs/docs/en/agents/operations/production-planner.md
    - docs/docs/en/agents/operations/quality-inspector.md
    - docs/docs/en/agents/operations/anomaly-detector.md
    - apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/metadata.py
    - apps/agents/ops/quality-inspector/src/ops_quality_inspector/metadata.py
    - apps/agents/ops/production-planner/src/ops_production_planner/metadata.py
    - apps/agents/ops/operator-assistant/src/ops_operator_assistant/metadata.py
  modified:
    - docs/mkdocs.yml
    - apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/__init__.py
    - apps/agents/ops/quality-inspector/src/ops_quality_inspector/__init__.py
    - apps/agents/ops/production-planner/src/ops_production_planner/__init__.py
    - apps/agents/ops/operator-assistant/src/ops_operator_assistant/__init__.py
    - apps/agents/ops/anomaly-detector/tests/test_evidence_panel.py
    - apps/agents/ops/quality-inspector/tests/test_evidence_panel.py
    - apps/agents/ops/production-planner/tests/test_evidence_panel.py
    - apps/agents/ops/operator-assistant/tests/test_evidence_panel.py
decisions:
  - "Used existing mkdocs-static-i18n folder structure (docs/docs/<page>.md + docs/docs/en/<page>.md) rather than .it.md/.en.md suffix pattern from PLAN — reconciliation with actual i18n plugin config"
  - "Added metadata.py module per agent (single source of truth) instead of polluting sft_agents.models.evidence.EvidencePanel (which has extra='forbid' and cannot be extended without breaking Phase 4 schema)"
  - "build_ops05_evidence_panel returns dict (not Pydantic model) for JSON-serialisation parity and to avoid forcing every downstream consumer to import the helper class"
  - "Extras parameter never overwrites the 5 required OPS-05 keys (defensive — callers cannot accidentally redefine agent_id or tool_inventory)"
  - "Default HITL tier per agent encodes the modal interaction: AnomalyDetector=none (fully auto), QualityInspector=supervisor (modal major branch), ProductionPlanner=supervisor (always), OperatorAssistant=none (read-only Q&A)"
metrics:
  duration_minutes: 30
  completed_at: 2026-05-23
  tasks_completed: 2
  files_created: 12
  files_modified: 9
  tests_added: 36
  tests_passing: 36
  pre_existing_tests_passing: 119
---

# Phase 06 Plan 14: Bilingual OPS Docs + OPS-05 Evidence Panel Summary

Shipped 8 MkDocs bilingual agent pages (IT + EN) under `docs/docs/agents/operations/` and the matching `metadata.py` module per OPS agent exposing the OPS-05 declaration (`tool_inventory`, `data_sources`, `hitl_tier`, `kpis_impacted`, `agent_id`) — single source of truth shared between code and docs.

## Tasks Executed

| # | Name | Commit | Verification |
|---|------|--------|--------------|
| 1 | 8 MkDocs bilingual pages + mkdocs.yml nav | `8074679` | `mkdocs build --strict` green; 8/8 pages built; 0 broken links; 0 Accenture hits |
| 2 (RED) | Un-skip 4 `test_evidence_panel.py` with failing OPS-05 contract | `34973cb` | All 4 tests fail with `ImportError: cannot import name 'metadata'` |
| 2 (GREEN) | Add `metadata.py` per agent + re-export from `__init__.py` | `abd0af5` | 36/36 new tests green; 119/119 pre-existing OPS tests green |

## OPS-05 Declaration Schema (single shape, 4 agents)

```python
from ops_<agent> import build_ops05_evidence_panel
panel = build_ops05_evidence_panel(hitl_tier="supervisor")  # optional override
# {
#   "agent_id": "<agent-slug>",
#   "tool_inventory": ["tool1", ...],
#   "data_sources": ["TimescaleDB ...", "Qdrant ...", ...],
#   "hitl_tier": "supervisor",  # or default per agent
#   "kpis_impacted": ["kpi1", ...],
# }
```

### Per-agent constants (mirrors MkDocs pages)

| Agent | tool_inventory | hitl_tier_default | kpis_impacted |
|-------|---------------|--------------------|---------------|
| **anomaly-detector** | `query_timescale` | `none` (Decision.AUTO) | `mtbf`, `alert_fatigue_rate`, `sensor_coverage` |
| **quality-inspector** | `rag_search` | `supervisor` | `defect_rate_4pt`, `scrap_rate`, `dye_lot_deviation` |
| **production-planner** | `rag_search` | `supervisor` (always) | `on_time_delivery_rate`, `oee_availability`, `schedule_stability` |
| **operator-assistant** | `rag_search`, `traverse_graph`, `query_timescale`, `escalate_to_supervisor`, `log_event` | `none` (Q&A) | `mttr`, `first_time_fix_rate`, `knowledge_reuse_rate` |

## Deviations from Plan

### [Rule 3 — Blocking issue] Reconciled file paths with mkdocs-static-i18n

**Found during:** Task 1 setup.

**Issue:** The plan's `files_modified` listed paths like `docs/agents/operations/operator-assistant.it.md` and `…operator-assistant.en.md`. The actual i18n plugin (`mkdocs-static-i18n` 1.3.1, `docs_structure: folder`) requires the IT default at `docs/docs/<path>.md` and the EN translation at `docs/docs/en/<path>.md`. The plan's suffix-based paths would have failed `mkdocs build --strict`.

**Fix:** Used the existing project i18n convention. The set of 8 pages (4 agents × 2 languages) and content remains exactly as specified by the plan. The MkDocs build produced both `site/agents/operations/<agent>/` (IT) and `site/en/agents/operations/<agent>/` (EN) routes.

**Files moved:** none — wrote files directly to the correct paths.

**Commit:** `8074679`.

### [Rule 3 — Schema strictness] Returned dict from `build_ops05_evidence_panel`

**Found during:** Task 2 design.

**Issue:** Plan suggested extending `EvidencePanel`. The sft-agents `EvidencePanel` model (Phase 4 D-56) sets `model_config = {"frozen": True, "extra": "forbid"}` — adding `tool_inventory` etc. would either break Phase 4 schema or require a sibling model.

**Fix:** Built a plain `dict` return type. The helper is composable (callers attach the dict alongside or wrap into a custom envelope). Existing `EvidencePanel.tool_calls` continues to track *runtime* tool invocations; the new declaration tracks *agent capability declaration* — two distinct concerns.

**Commit:** `abd0af5`.

## TDD Gate Compliance

| Gate | Commit | Outcome |
|------|--------|---------|
| RED | `34973cb` | 4 test files fail with `ImportError` — proves test asserts genuinely new code path. |
| GREEN | `abd0af5` | All 36 tests pass; 119 pre-existing tests still pass. |
| REFACTOR | n/a | No refactor needed — code is already minimal. |

## Verification Output

```
$ mkdocs build --strict --config-file docs/mkdocs.yml
INFO  - mkdocs_static_i18n: Translated 30 navigation elements to 'en'
INFO  - Documentation built in 2.81 seconds   (0 broken links, 0 warnings other than unrelated Material team notice)

$ pytest apps/agents/ops/<agent>/tests/test_evidence_panel.py
4 × 9 tests = 36 passed

$ pytest apps/agents/ops/<agent>/tests/   # full suites
27 + 29 + 24 + 39 = 119 passed (no regression)

$ grep -ri "accenture" docs/docs/agents/ apps/agents/ops/
(no hits)
```

## Self-Check: PASSED

- [x] `docs/docs/agents/operations/operator-assistant.md` (IT) exists
- [x] `docs/docs/agents/operations/production-planner.md` (IT) exists
- [x] `docs/docs/agents/operations/quality-inspector.md` (IT) exists
- [x] `docs/docs/agents/operations/anomaly-detector.md` (IT) exists
- [x] `docs/docs/en/agents/operations/operator-assistant.md` (EN) exists
- [x] `docs/docs/en/agents/operations/production-planner.md` (EN) exists
- [x] `docs/docs/en/agents/operations/quality-inspector.md` (EN) exists
- [x] `docs/docs/en/agents/operations/anomaly-detector.md` (EN) exists
- [x] `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/metadata.py` exists
- [x] `apps/agents/ops/quality-inspector/src/ops_quality_inspector/metadata.py` exists
- [x] `apps/agents/ops/production-planner/src/ops_production_planner/metadata.py` exists
- [x] `apps/agents/ops/operator-assistant/src/ops_operator_assistant/metadata.py` exists
- [x] Commit `8074679` found in `git log`
- [x] Commit `34973cb` found in `git log`
- [x] Commit `abd0af5` found in `git log`
- [x] `mkdocs build --strict` succeeds with no broken links
- [x] 36/36 OPS-05 evidence panel tests pass
- [x] 119/119 pre-existing OPS agent tests pass (no regression)
- [x] Brand scrub: 0 "Accenture" hits in new files
