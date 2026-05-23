---
phase: 07-agents-maintenance-reliability
plan: 11
plan_id: 07-11
subsystem: docs + tests
tags: [docs, maintenance, mnt-05, evidence-panel, mkdocs, bilingual]
dependency_graph:
  requires: [07-06, 07-07, 07-08, 07-09]
  provides: [MNT-05-docs, evidence-panel-lockstep-tests]
  affects: [docs/mkdocs.yml, docs/docs/agents/maintenance/, docs/docs/en/agents/maintenance/]
tech_stack:
  added: []
  patterns: [06-14 doc page template, OPS-05 evidence panel lockstep test pattern]
key_files:
  created:
    - docs/docs/agents/maintenance/predictive-maintenance.md
    - docs/docs/agents/maintenance/rca-specialist.md
    - docs/docs/agents/maintenance/maintenance-coach.md
    - docs/docs/agents/maintenance/downtime-analyzer.md
    - docs/docs/agents/maintenance/event-taxonomy.md
    - docs/docs/en/agents/maintenance/predictive-maintenance.md
    - docs/docs/en/agents/maintenance/rca-specialist.md
    - docs/docs/en/agents/maintenance/maintenance-coach.md
    - docs/docs/en/agents/maintenance/downtime-analyzer.md
    - docs/docs/en/agents/maintenance/event-taxonomy.md
    - apps/agents/maintenance/predictive-maintenance/tests/test_evidence_panel.py
    - apps/agents/maintenance/rca-specialist/tests/test_evidence_panel.py
    - apps/agents/maintenance/maintenance-coach/tests/test_evidence_panel.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_evidence_panel.py
  modified:
    - docs/mkdocs.yml
decisions:
  - "mkdocs i18n convention: docs_structure=folder (IT default, EN under en/ folder); single nav block with nav_translations. No separate EN nav block needed."
  - "build_ops05_evidence_panel signature varies: PM/Coach/DA accept (hitl_tier, extra) kwargs; RCA requires positional args (input_summary, model_version, tool_calls, decision, prompt_hash). Tests aligned to each agent's actual signature."
  - "RCA HITL_TIER_DEFAULT='supervisor' is hardcoded and cannot be overridden via extra dict — D-RCA-02 literal. Test asserts this invariant explicitly."
  - "Coach HITL_TIER_DEFAULT='supervisor' reflects escalation posture; normal steps use hitl_tier='auto' override per-call."
  - "event-taxonomy.md references 7 reason_codes from failure_modes.yaml that have maintenance: blocks; 4 failure modes (rottura_filo, shuttle_jam, warp_tension_drift, difetto_*) have no maintenance block and are not enumerated."
metrics:
  duration: 45min
  completed_date: "2026-05-23"
  tasks_completed: 2
  files_created: 14
  files_modified: 1
  tests_added: 67
---

# Phase 7 Plan 11: MkDocs Maintenance Agent Docs + Evidence Panel Lockstep Tests Summary

MNT-05 deliverable: 10 bilingual MkDocs pages (8 agent + 2 event-taxonomy) + 4 test_evidence_panel.py un-stubbed enforcing docs-to-code lockstep for all 4 maintenance cluster agents.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Author 8 agent pages IT+EN + 2 taxonomy pages + mkdocs.yml nav | 80aa44a + 1c684c9 + 9574a16 | 10 md + 1 yml |
| 2 | Un-stub 4 test_evidence_panel.py (docs ↔ code lockstep) | f78e193 | 4 test files |

## Commits

- `80aa44a` — `docs(07-11): 4 maintenance agent pages IT + EN (MNT-01/02/03/04)` (8 files)
- `1c684c9` — `docs(07-11): event-taxonomy.md IT + EN (MNT-05 explicit deliverable)` (2 files)
- `9574a16` — `docs(07-11): mkdocs.yml nav extension for Maintenance cluster` (1 file)
- `f78e193` — `test(07-11): un-stub 4 test_evidence_panel.py -- docs <> code lockstep (mirror 06-14)` (4 files)

## What Was Shipped

### Task 1: 10 Bilingual MkDocs Pages

**4 Agent pages × 2 languages = 8 pages:**

| Agent | Slug | Requirements | HITL Tier |
|-------|------|-------------|-----------|
| PredictiveMaintenance | predictive-maintenance | MNT-01, MNT-05 | AUTO (health≥0.3) / SUPERVISOR (health<0.3) |
| RCASpecialist | rca-specialist | MNT-02, MNT-05 | ALWAYS SUPERVISOR (D-RCA-02 literal) |
| MaintenanceCoach | maintenance-coach | MNT-03, MNT-05 | AUTO (normal step) / SUPERVISOR (request_help) |
| DowntimeAnalyzer | downtime-analyzer | MNT-04, MNT-05 | none — fully autonomous analytics |

Each page follows the 06-14 frontmatter convention (`lang`, `agent`, `requirements`, `tags`) and includes all required sections: Panoramica/Overview, Strumenti Utilizzati/Tools Used, Fonti Dati/Data Sources, HITL Tier (3-col table), KPI Impattati/KPIs Impacted, Invocazione/Invocation, Audit Footprint.

**2 Event-taxonomy pages (IT + EN):**

- MNT-05 explicit deliverable documenting 7 reason_codes from `failure_modes.yaml` D-65 registry
- ISO 14224 spirit naming convention documented: `<MODULE>-<ABBR>-<NNN>`
- Cross-agent usage table showing how each agent uses the reason_code
- Step-by-step guide for adding new reason_codes + CI validator reference

**mkdocs.yml nav extension:**

```yaml
- Agenti:
    - Operations: [... existing 4 pages ...]
    - Maintenance:
        - PredictiveMaintenance: agents/maintenance/predictive-maintenance.md
        - RCASpecialist: agents/maintenance/rca-specialist.md
        - MaintenanceCoach: agents/maintenance/maintenance-coach.md
        - DowntimeAnalyzer: agents/maintenance/downtime-analyzer.md
        - Tassonomia Eventi: agents/maintenance/event-taxonomy.md
```

Nav translations added: `Maintenance: Maintenance`, `Tassonomia Eventi: Event Taxonomy`.

### Task 2: 4 Evidence Panel Lockstep Tests

| Agent | Tests | Key Assertions |
|-------|-------|----------------|
| PredictiveMaintenance | 15 | TOOL_INVENTORY[3], timescale+ml data sources, HITL none→supervisor override |
| RCASpecialist | 16 | 4-tool inventory, HITL_TIER_DEFAULT='supervisor' (D-RCA-02 cannot be overridden) |
| MaintenanceCoach | 18 | request_help tier, HITL_TIER_DEFAULT='supervisor', auto override for normal steps |
| DowntimeAnalyzer | 18 | 2-tool deterministic inventory, HITL_TIER_DEFAULT='none', NATS + cross-cluster data sources |

**Total: 67 tests, all green.**

## Verification Results

- `mkdocs build --strict --config-file docs/mkdocs.yml`: SUCCESS (zero broken links, zero content warnings)
- IT docs count: 5 pages (4 agents + taxonomy)
- EN docs count: 5 pages (parallel mirror)
- Brand scrub (`Accenture` grep): CLEAN in all maintenance docs
- `WEAVING-BE-001`, `SPINNING-SL-001`, `DYEING-UD-002` enumerated in event-taxonomy.md
- All 67 test_evidence_panel.py assertions: PASSED via `.venv/bin/python3.12 -m pytest`

## Deviations from Plan

### Auto-noted Observations (Rule 4 capture per plan deviation_rules)

**1. mkdocs i18n plugin convention:**
The project uses `docs_structure: folder` with a single IT nav (default) and `nav_translations` for EN. No separate EN nav block is needed — the `en/` folder structure resolves pages automatically. This matches exactly the existing Phase 6 ops cluster pattern.

**2. build_ops05_evidence_panel() signature differences:**

| Agent | Signature style |
|-------|----------------|
| PM | `build_ops05_evidence_panel(*, hitl_tier=None, extra=None)` — kwargs only |
| RCA | `build_ops05_evidence_panel(input_summary, *, model_version, tool_calls, decision, prompt_hash, ...)` — required positionals |
| Coach | `build_ops05_evidence_panel(*, hitl_tier=None, extra=None)` — kwargs only |
| DA | `build_ops05_evidence_panel(*, hitl_tier=None, extra=None)` — kwargs only |

RCA has a richer signature because it wraps full audit metadata (prompt_hash, tool_calls, decision). Tests adapted accordingly — no metadata.py modifications needed.

**3. reason_code count:**
- Registry entries with `maintenance:` block: 7 (enumerated)
- Total failure mode entries in registry: ~37 (many lack `maintenance:` block — they are quality/operational events)
- Documented count exactly matches registry count of maintenance-tagged entries.

**4. Phase 12 brand-scrub pre-check:**
Zero matches for "Accenture" in all 10 maintenance docs pages. T-V7-brand-leak mitigated.

## Known Stubs

None — all 10 documentation pages are complete with substantive content sourced from metadata.py constants. The 4 test files are fully implemented with 67 assertions.

## Threat Flags

None — the plan's threat model (T-V7-doc-drift, T-V7-brand-leak, T-V7-taxonomy-doc-drift, T-V7-mkdocs-broken-link) was fully mitigated:
- T-V7-doc-drift: test_evidence_panel.py lockstep tests pass
- T-V7-brand-leak: grep gate clean
- T-V7-taxonomy-doc-drift: taxonomy references failure_modes.yaml as canonical; 7 reason_codes enumerated
- T-V7-mkdocs-broken-link: `--strict` build succeeds

## Self-Check: PASSED

All 15 files verified to exist on disk. All 4 commits verified in git log:
- 80aa44a (8 agent pages IT+EN)
- 1c684c9 (2 taxonomy pages)
- 9574a16 (mkdocs.yml nav)
- f78e193 (4 test files)
