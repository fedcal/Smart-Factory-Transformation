---
lang: en
agent: event-taxonomy
requirements:
  - MNT-05
tags:
  - agents
  - maintenance
  - MNT-05
  - taxonomy
---

# Maintenance Event Taxonomy

This page documents the maintenance event taxonomy (`reason_code`) used by
the maintenance cluster of **Mantis Textile Group**.

The canonical source is
`packages/sft-domain/src/sft_domain/failure_modes.yaml`
(07-02 extension D-MNT-TAX); the CI validator
`scripts/validate-failure-modes.py` enforces:

- uniqueness of `reason_code` across the entire registry;
- resolution of `intervention_steps_sop_id` against the Phase 5 SOP corpus;
- consistency of `mttr_target_minutes` and `severity` fields.

## Naming Convention

`reason_code` values follow the convention inspired by the spirit of ISO 14224:

```
<MODULE>-<DEFECT_ABBREVIATION>-<NNN>
```

Examples:

| Code | Module | Defect | Number |
|------|--------|--------|--------|
| `WEAVING-BE-001` | Weaving | Broken End | 001 |
| `WEAVING-MP-002` | Weaving | Mispick | 002 |
| `SPINNING-SL-001` | Spinning | Slub | 001 |
| `DYEING-SD-001` | Dyeing | Shade Deviation | 001 |

Recognised modules are: `WEAVING`, `SPINNING`, `DYEING`.
Numbers are assigned in registration order and are never reused after
deprecation.

## reason_code Registry

The table below mirrors the current content of `failure_modes.yaml` for the
failure modes that have a `maintenance:` block with a defined `reason_code`.

| reason_code | Italian Name | English Name | Asset families | MTTR target (min) | SOP ID | Check interval (h) | Severity |
|---|---|---|---|---|---|---|---|
| `WEAVING-BE-001` | rottura filo ordito | broken end | weaving | 30 | SOP-LOOM-001 | 168 | medium |
| `WEAVING-MP-002` | trama mancata | mispick | weaving, quality_grading | 15 | SOP-LOOM-002 | — | medium |
| `WEAVING-SF-003` | difetto cimosa | selvage fault | weaving | 45 | SOP-LOOM-004 | 336 | low |
| `SPINNING-SL-001` | ingrossamento filato | slub | spinning, quality_grading | 20 | SOP-SPN-004 | — | medium |
| `SPINNING-NP-002` | filato neppy | neppy yarn | spinning, quality_grading | 25 | SOP-SPN-002 | — | medium |
| `DYEING-SD-001` | deviazione cromatica | shade deviation | dyeing, quality_grading | 60 | SOP-DYE-003 | — | medium |
| `DYEING-UD-002` | tintura non uniforme | unlevel dyeing | dyeing, quality_grading | 90 | SOP-DYE-001 | 720 | medium |

**Total documented reason_codes: 7** (matching the 7 failure modes with a
`maintenance:` block in the D-65 registry).

## Cross-agent Usage

| Agent | Usage of reason_code |
|-------|----------------------|
| `PredictiveMaintenance` | Does not use `reason_code` directly; operates on `health_index` computed from sensors. The `reason_code` is included as optional context in the NATS trigger payload from `AnomalyDetector`. |
| `RCASpecialist` | `problem_statement` often includes the triggering event's `reason_code`; `rag_search` uses the code to filter relevant SOPs. |
| `MaintenanceCoach` | `reason_code` in input selects the correct SOP corpus (`rag_search`) and the Coach thread is started with the code as primary context. |
| `DowntimeAnalyzer` | Persists `reason_code` in every `maintenance.downtime_events` row; the `top_5_downtime_reason_codes` Pareto analysis aggregates by this field. |

## Adding a New reason_code

1. **Add the entry to the registry**:
   Edit `packages/sft-domain/src/sft_domain/failure_modes.yaml` adding an
   entry with a `maintenance:` block containing at minimum:
   ```yaml
   maintenance:
     reason_code: <MODULE>-<ABBR>-<NNN>
     mttr_target_minutes: <int>
     intervention_steps_sop_id: <SOP-ID>
   ```

2. **Add the corresponding SOP**:
   The SOP file referenced by `intervention_steps_sop_id` must exist in the
   `simulators/synthetic-corpus/` corpus before the CI validator accepts the PR.

3. **Run the validator**:
   ```bash
   python scripts/validate-failure-modes.py
   ```
   The validator checks: uniqueness of `reason_code`, existence of `sop_id`
   in the corpus, consistency of `severity` with other defects in the module.

4. **Update this page**:
   Add the new row to the "reason_code Registry" table above and increment
   the "Total documented reason_codes" counter.

5. **PR review**:
   The reviewer must verify that the `reason_code` follows the naming convention
   (ISO 14224 spirit) and that `mttr_target_minutes` is based on historical
   data or documented engineering estimates.
