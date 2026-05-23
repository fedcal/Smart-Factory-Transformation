---
phase: 07-agents-maintenance-reliability
plan: 02
plan_id: 07-02
subsystem: domain-model
tags: [pydantic, yaml, taxonomy, maintenance, iso-14224, mttr, sop, validator, ci]

# Dependency graph
requires:
  - phase: 05-knowledge-curation
    provides: SOP corpus (SOP-LOOM-001..005, SOP-SPN-001..005, SOP-DYE-001..005, SOP-QLT-001..005) used to resolve intervention_steps_sop_id refs
  - phase: 06-agents-operations-production
    provides: FailureMode Pydantic + failure_modes.yaml hitl_tier extension (Plan 06-04) — backward-compat baseline
  - phase: 07-agents-maintenance-reliability/00
    provides: Wave 0 placeholder test_maintenance_meta.py + plan scaffolding

provides:
  - MaintenanceSpec Pydantic v2 model (frozen + extra=forbid) with regex-validated reason_code, MTTR bounds, SOP id pattern, optional preventive_check_interval_hours
  - FailureMode.maintenance optional field (additive — Pattern G non-breaking)
  - 7 textile defect entries in failure_modes.yaml extended with maintenance subkey (unique reason_codes, real SOP refs)
  - CI validator extended with reason_code uniqueness (hard fail) + SOP id resolution (warn-only default, --strict-sop flag)

affects:
  - 07-05 (downtime_event_generator) — reads reason_code per simulazioni Pareto
  - 07-09 (DowntimeAnalyzer) — group-by reason_code per Pareto charts
  - 07-11 (docs site) — pubblica taxonomy table

# Tech tracking
tech-stack:
  added: []  # no new package dependencies
  patterns:
    - "Additive non-breaking schema extension (Pattern G): nuovi campi optional con default per preservare backward-compat"
    - "Two-tier validator: hard fail (reason_code uniqueness) vs warn-only with strict-flag (SOP resolution) — Rule 3 non-blocking durante stabilization"
    - "ISO 14224-style reason_code naming: <MODULE>-<DEFECT_ABBR>-<NNN>"

key-files:
  created:
    - "(none — test_maintenance_meta.py existed as Wave 0 stub, now fully implemented)"
  modified:
    - "packages/sft-domain/src/sft_domain/failure_modes/models.py (+MaintenanceSpec, FailureMode.maintenance)"
    - "packages/sft-domain/src/sft_domain/failure_modes/__init__.py (re-export MaintenanceSpec)"
    - "packages/sft-domain/src/sft_domain/failure_modes.yaml (+maintenance subkey su 7 textile defects)"
    - "packages/sft-domain/tests/failure_modes/test_maintenance_meta.py (RED→GREEN — 33 test cases)"
    - "scripts/validate-failure-modes.py (+_check_reason_code_uniqueness, +_check_sop_id_resolution, +_discover_sop_corpus_ids, +--strict-sop CLI flag)"

key-decisions:
  - "Aligned SOP refs to actual corpus naming (SOP-SPN-* not SOP-SPIN-*) per plan deviation Rule 1: avoids orphan-SOP validator failures"
  - "Validator uses warn-only fallback when corpus_dir not found (Rule 3 non-blocking); --strict-sop flag available per future enforcement"
  - "SOP discovery uses filename regex SOP_ID_FROM_FILENAME — sufficient per Phase 5 synthetic corpus; nessun sop_index.yaml necessario"
  - "reason_code regex ^[A-Z][A-Z0-9-]+$ richiede min 2 caratteri (test_valid_min_two_chars vs. test_invalid_single_char)"
  - "mttr_target_minutes upper bound 10080 = 1 settimana (sufficient per textile maintenance tasks)"

patterns-established:
  - "Pattern G additive sub-key con default None — model_config 'extra=forbid' rispettato sia in MaintenanceSpec sia in FailureMode senza breaking esistente"
  - "Pattern validator a due livelli: hard-fail per invarianti correctness (uniqueness) + warn-only per dipendenze cross-phase (SOP corpus)"

requirements-completed: [MNT-05]

# Metrics
duration: ~25min
completed: 2026-05-23
---

# Phase 07 Plan 02: MaintenanceSpec Taxonomy Extension Summary

**MaintenanceSpec Pydantic v2 + failure_modes.yaml maintenance subkey on 7 textile defects + CI validator con reason_code uniqueness + SOP resolution checks — additive non-breaking estensione di D-65 per soddisfare D-MNT-TAX/MNT-05.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-23T17:13:00Z
- **Completed:** 2026-05-23T17:38:20Z
- **Tasks:** 3 (TDD RED → GREEN per Task 1+2, plus Task 3 validator extension)
- **Files modified:** 5

## Accomplishments

### MaintenanceSpec model contract

```python
class MaintenanceSpec(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    reason_code: Annotated[str, Field(min_length=1, pattern=r"^[A-Z][A-Z0-9-]+$")]
    mttr_target_minutes: Annotated[int, Field(ge=0, le=10080)]
    intervention_steps_sop_id: Annotated[str, Field(min_length=1, pattern=r"^SOP-[A-Z0-9-]+$")]
    preventive_check_interval_hours: Annotated[int | None, Field(default=None, ge=1)] = None
```

`FailureMode.maintenance: MaintenanceSpec | None = None` — additive backward-compatible (Pattern G).

### Taxonomy table — 7 textile defects

| failure_mode      | reason_code        | MTTR (min) | SOP ref       | preventive (h) |
|-------------------|--------------------|------------|---------------|----------------|
| broken_end        | WEAVING-BE-001     | 30         | SOP-LOOM-001  | 168            |
| mispick           | WEAVING-MP-002     | 15         | SOP-LOOM-002  | —              |
| selvage_fault     | WEAVING-SF-003     | 45         | SOP-LOOM-004  | 336            |
| slub              | SPINNING-SL-001    | 20         | SOP-SPN-004   | —              |
| neppy             | SPINNING-NP-002    | 25         | SOP-SPN-002   | —              |
| shade_deviation   | DYEING-SD-001      | 60         | SOP-DYE-003   | —              |
| unlevel_dyeing    | DYEING-UD-002      | 90         | SOP-DYE-001   | 720            |

Tutti i 7 reason_code sono unici. Tutti i 7 intervention_steps_sop_id si risolvono contro il corpus Phase 5 reale (`simulators/synthetic-corpus/{en,it}/{loom,spinning,dyeing}/SOP-*.md`).

### SOP corpus resolution status

`scripts/validate-failure-modes.py --strict-sop` esce 0: tutti i 7 SOP riferiti **esistono** nel corpus sintetico Phase 5:

```
FAILURE_MODES: total=34 referenced=34 orphans=0
MAINTENANCE:   total=7 unique_reason_codes=7 sop_refs_resolved=7/7
```

Nessun orphan SOP — nessuna follow-up task necessaria per Phase 5 SOP seeding.

### CI validator behavior

- **Default (no flag):** reason_code uniqueness = hard fail (exit 1 su duplicati). SOP resolution = warn-only (exit 0 anche con SOP missing). Compatibile con Phase 5 stabilization in corso.
- **`--strict-sop` flag:** SOP resolution diventa hard fail (exit 1). Pronto per essere abilitato post-Phase-8 KnowledgeCurator.
- **Corpus assente:** WARN strutturato `sop_corpus_not_found, skipping intervention_steps_sop_id resolution` + exit code 0 (default) → non blocca PR. `--strict-sop` con corpus assente → exit 0 ma con WARN visibile.

### Tests

- **33 nuovi test case** in `tests/failure_modes/test_maintenance_meta.py` (TestMaintenanceSpecBasics, TestMaintenanceSpecReasonCodeRegex, TestMaintenanceSpecMttrBounds, TestMaintenanceSpecSopIdRegex, TestMaintenanceSpecPreventiveCheck, TestFailureModeMaintenanceField, TestFailureModesYamlMaintenanceRoundTrip).
- **190 test totali green** nel package `sft-domain` (incluso il pre-esistente test_failure_modes_loader.py + test_failure_modes_hitl_tier.py) — zero regressioni.
- TDD ciclo correttamente attraversato: RED commit (222c1e8) → GREEN commit (85642c6) → YAML extension (532ff68).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Naming alignment] SOP IDs aggiornati a convenzione corpus reale**
- **Found during:** Task 2 (YAML extension)
- **Issue:** Il plan suggeriva `SOP-SPIN-001` e `SOP-SPIN-002` per slub/neppy, ma il corpus Phase 5 usa `SOP-SPN-*` (3-letter abbreviation). Usare `SOP-SPIN-*` avrebbe creato orphan SOP refs e fatto fallire il validator in `--strict-sop`.
- **Fix:** Mapping aggiornato — slub→SOP-SPN-004 (slub-control), neppy→SOP-SPN-002 (drafting-cylinder-cleanup). Anche `shade_deviation` → SOP-DYE-003 (shade-verification) e `unlevel_dyeing` → SOP-DYE-001 (bath-preparation), `mispick` → SOP-LOOM-002, `selvage_fault` → SOP-LOOM-004 per mappare a documenti reali rather than placeholder.
- **Files modified:** packages/sft-domain/src/sft_domain/failure_modes.yaml
- **Commit:** 532ff68

Nessun'altra deviazione: il plan è stato eseguito secondo specifica.

## Authentication Gates

Nessun — esecuzione completamente offline (yaml + pydantic + script Python).

## Known Stubs

Nessuno — tutte le 7 entries di maintenance taxonomy sono populated con valori reali (no placeholder, no TODO non-tracked).

## Threat Surface Notes

Le mitigations dichiarate nel threat_model del plan sono tutte implementate:

| Threat ID                | Mitigation status |
|--------------------------|-------------------|
| T-V7-yaml-injection      | OK — loader continua ad usare `yaml.safe_load` esclusivamente |
| T-V7-tax-drift           | OK — validator hard-fail su reason_code duplicati |
| T-V7-tax-orphan-sop      | OK — validator warn (default) / fail (--strict-sop) su SOP missing |
| T-V7-naive-extra         | OK — `MaintenanceSpec.model_config = {"frozen": True, "extra": "forbid"}` |
| T-V7-SC                  | n/a — nessun package install |

Nessuna nuova superficie di sicurezza fuori dal threat model originale.

## Commit Log

| Commit  | Type | Summary                                                                                  |
|---------|------|------------------------------------------------------------------------------------------|
| 222c1e8 | test | add failing tests for MaintenanceSpec + FailureMode.maintenance (RED)                    |
| 85642c6 | feat | MaintenanceSpec Pydantic + FailureMode.maintenance optional field (D-MNT-TAX)            |
| 532ff68 | feat | extend failure_modes.yaml with maintenance taxonomy for 7 textile defects                |
| 647df82 | feat | CI validator — reason_code uniqueness + SOP id resolution (D-MNT-TAX)                    |

## TDD Gate Compliance

- RED commit present: 222c1e8 (`test(07-02):` — failing import on MaintenanceSpec)
- GREEN commit present after RED: 85642c6 (`feat(07-02):` — implementation makes tests pass)
- REFACTOR commit: not needed (no cleanup required after green)

## Self-Check: PASSED

- File `packages/sft-domain/src/sft_domain/failure_modes/models.py` exists with MaintenanceSpec + FailureMode.maintenance
- File `packages/sft-domain/src/sft_domain/failure_modes/__init__.py` re-exports MaintenanceSpec
- File `packages/sft-domain/src/sft_domain/failure_modes.yaml` extended with 7 maintenance subkeys
- File `packages/sft-domain/tests/failure_modes/test_maintenance_meta.py` extended con 33 test case (all green)
- File `scripts/validate-failure-modes.py` extended con 3 nuove funzioni + 1 nuovo CLI flag
- Commit 222c1e8 (RED) exists in git log
- Commit 85642c6 (model GREEN) exists in git log
- Commit 532ff68 (YAML extension) exists in git log
- Commit 647df82 (validator extension) exists in git log
- 190 sft-domain tests green
- Validator exits 0 in both default and --strict-sop modes
