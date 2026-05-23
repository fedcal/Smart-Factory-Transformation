# Model Card — `ridge-fd001-fd003-v1.0`

Format inspired by Mitchell et al. (2018), [Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993).

## Model Details

| Field                  | Value                                                                          |
| ---------------------- | ------------------------------------------------------------------------------ |
| **Name**               | `ridge-fd001-fd003-v1.0`                                                       |
| **Version**            | v1.0                                                                           |
| **Training date**      | 2026-05-23                                                                     |
| **Framework**          | scikit-learn ≥1.7.0,<1.9.0 (trained on 1.8.0)                                  |
| **Architecture**       | `Pipeline(StandardScaler → Ridge(alpha=1.0, random_state=42))`                 |
| **Artifact path**      | `packages/sft-ml/models/ridge-fd001-fd003-v1.0.joblib`                         |
| **File size**          | ~1.5 KB (gzip-3 compressed, Ridge is a tiny linear model)                      |
| **Companion metadata** | `ridge-fd001-fd003-v1.0.json` (sklearn_min, python_min, RANDOM_STATE, rul_cap) |
| **SHA256 (joblib)**    | `8600003410e0f9edb7906ad4cdb1212d186be2f2dcbd7135bf5a57f1ccdc7a75`             |

## Intended Use

**Primary use case:** PoC textile-manufacturing Remaining Useful Life (RUL) estimation, consumed by the
`PredictiveMaintenance` agent (plan 07-06, Phase 7 MNT-01). Asset families covered by the textile
feature map:

- `loom`     — loom_temperature, warp_tension, creel_speed, broken_pick_count
- `spinning` — spindle_vibration, spindle_temperature, ring_position
- `dyeing`   — bath_temperature, ph_level, agitator_rpm
- `warping`  — drum_rpm, yarn_tension, drum_temperature

**Out of scope:** safety-critical / regulatory decisions, real-time control loops, billing or
contractual SLAs. The model output is subordinate to the HITL supervisor when `health_index < 0.3`
(Phase 7 maintenance approval policy).

## Training Data

- **Dataset:** NASA C-MAPSS Turbofan Engine Degradation Simulation Data Set,
  sub-datasets **FD001** + **FD003** (joint training).
- **Citation:** Saxena, A., Goebel, K., Simon, D., Eklund, N. (2008).
  *Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation.*
  International Conference on Prognostics and Health Management (PHM 2008).
- **License:** US Government public-domain (NASA Prognostics CoE).
- **Source / mirror:** https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ ;
  reproducible mirror used for this commit: https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip
- **Subset rationale (D-PM-02):**
  - **FD001** — single fault mode, single operating condition; baseline (mechanical wear analog →
    textile loom mechanical degradation).
  - **FD003** — HPC + Fan degradation, multi-fault; covers a second textile fault family
    (chemical / contamination degradation → dyeing).
- **Schema:** 26 columns — `unit_number, time_cycles, op_setting_1, op_setting_2, op_setting_3,
  s1..s21` (see `cmapss/training.py::CMAPSS_COLUMNS`). Canonical reference:
  https://github.com/makinarocks/awesome-industrial-machine-datasets/blob/master/data-explanation/C-MAPSS/README.md
- **Training rows:** 45 351 joint (FD001: 20 631 + FD003: 24 720, across 200 simulated units).
- **RUL target:** piecewise-linear `max_cycle_per_unit - current_cycle`, capped at 125
  (literature standard, Heimes 2008).

## Cross-Domain Mapping Caveat (CRITICAL)

The textile sensors are mapped to C-MAPSS turbofan sensor proxies via a **best-guess semantic
mapping** in `cmapss/feature_map.py` (e.g., `loom_temperature → s8` = LPT outlet temperature analog,
`spindle_vibration → s9` = fan vibration analog). **This is NOT domain-adapted retraining.**

The literature on NASA→manufacturing domain transfer demonstrates that such mappings work
**qualitatively** (the model captures degradation trend direction) but suffer significant
**`domain shift`** — the absolute RUL cycle values should be treated as ordinal, not calibrated.

Mitigation references for future work (Phase 11+ scope, NOT addressed here):

- LAMA-Net — *Latent Alignment with Manifold Adaptation* for cross-domain RUL,
  https://arxiv.org/pdf/2208.08388
- *Deep Domain Adaptation for Turbofan RUL: A Survey* (2025),
  https://arxiv.org/html/2510.03604 — Bi-Discrepancy Network, contrastive feature alignment,
  adversarial alignment.

Phase 7 explicitly does NOT implement domain adaptation per D-PM-01 (PoC scope, lightweight stack).

## Metrics

Evaluation protocol: canonical C-MAPSS test protocol — for each test unit, use the **last cycle**
of the truncated trajectory as input; compare predicted RUL to the ground-truth `RUL_FDxxx.txt`
value. Predictions are clipped to `[0, 125]` to match the training piecewise-linear cap.

| Test set      | RMSE (cycles) | Literature baseline (Ridge / raw sensors) |
| ------------- | ------------- | ----------------------------------------- |
| FD001         | **21.57**     | ≤35                                       |
| FD003         | **22.57**     | ≤35                                       |

Both well under the literature baseline (~30-35 for plain Ridge on raw sensors). Note: textile
cross-domain RMSE is NOT measured here — Phase 7 has no labeled textile RUL ground truth; field
calibration deferred (D-PM-01 PoC scope).

## Limitations

1. **PoC scope** — no online retraining (deferred Phase 11 per D-PM-01 rejected list).
2. **No domain adaptation** — cross-domain transfer is semantic best-guess; absolute cycle values
   are not calibrated for textile (see Cross-Domain Mapping Caveat).
3. **Pickle / joblib serialization brittleness** — joblib artifacts are NOT forward-compatible
   across scikit-learn major versions. Mitigated by:
   - Version pin in `packages/sft-ml/pyproject.toml`: `scikit-learn>=1.7.0,<1.9.0`.
   - Companion `.json` metadata records `sklearn_min`; `inference.load_model` raises before
     unpickling if installed sklearn major < required (Pitfall 1 mitigation, V12 integrity gate).
4. **Confidence interval is heuristic** — for Ridge, `predict_with_ci(features, ci_pct=0.1)`
   returns a simple ±10% band of the point estimate (NOT a true statistical CI). A real
   per-tree std-dev CI is available for the `RandomForest` variant (`train_random_forest`) but
   not used in v1.0.
5. **Ambient `op_setting_1` constant** — set to 0 (textile single-condition baseline equivalent
   to FD001 sea-level). FD003 multi-condition is NOT modelled at the op_setting_1 axis.

## Reproduction

The model artifact is **byte-equal-reproducible** offline (no network, no random sampling without
seed) given the committed dataset:

```bash
cd packages/sft-ml
uv run --project ../.. python -m sft_ml.cmapss.training
# Writes models/ridge-fd001-fd003-v1.0.joblib + .json
```

Determinism contract:

- `RANDOM_STATE = 42` set in `Ridge(...)`.
- StandardScaler is closed-form (no randomness).
- `pd.read_csv(..., sep=r'\s+', engine='python')` is deterministic.
- Joint training uses `pd.concat([..], ignore_index=True)` — order-preserving.

The smoke test `tests/test_model_smoke.py::test_predict_is_deterministic` asserts that two
consecutive `predict_with_ci` calls on the same input return identical triples.

## Threat Surface Recap (links to 07-03-PLAN.md threat_model)

| Threat ID            | Mitigation                                                                             |
| -------------------- | -------------------------------------------------------------------------------------- |
| T-V7-pickle-deser    | Companion `.json` sklearn version gate in `inference.load_model` before `joblib.load`. |
| T-V7-data-tamper     | SHA256 checksums recorded in `data/README.md` ; PR review on any data change.          |
| T-V7-model-drift     | `RANDOM_STATE=42` fissato; smoke test asserts deterministic predict.                   |
| T-V7-version-skew    | Pinned `scikit-learn>=1.7.0,<1.9.0` in pyproject + runtime check in `load_model`.      |
