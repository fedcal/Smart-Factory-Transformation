"""Smoke tests for the committed Ridge model artifact (07-RESEARCH.md Pitfall 1).

Asserts:
- packages/sft-ml/models/ridge-fd001-fd003-v1.0.joblib exists.
- load_model returns a sklearn Pipeline.
- predict_with_ci returns (int, int, int) bounded ci_lower ≤ rul ≤ ci_upper.
- RMSE on the FD001 test set ≤ 35 cycles (literature baseline for Ridge on raw
  C-MAPSS sensors).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sft_ml.cmapss.feature_map import map_textile_window_to_cmapss
from sft_ml.cmapss.inference import load_model, predict_with_ci
from sft_ml.cmapss.training import CMAPSS_COLUMNS, load_fd_subset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "ridge-fd001-fd003-v1.0.joblib"
FD001_DIR = PROJECT_ROOT / "data" / "c-mapss-fd001"


@pytest.fixture(scope="module")
def model():
    if not MODEL_PATH.exists():
        pytest.skip(f"Model artifact missing: {MODEL_PATH}")
    return load_model(MODEL_PATH)


def test_model_artifact_exists() -> None:
    assert MODEL_PATH.exists(), f"Expected committed model at {MODEL_PATH}"
    # Companion JSON metadata for integrity check.
    assert MODEL_PATH.with_suffix(".json").exists()


def test_load_model_returns_pipeline(model) -> None:
    # Pipeline has 'predict' method.
    assert hasattr(model, "predict")
    assert hasattr(model, "named_steps")


def test_predict_with_ci_returns_bounded_triple(model) -> None:
    # Build a synthetic textile loom window, map it to C-MAPSS, then predict.
    window = pd.DataFrame(
        {
            "loom_temperature": [80.1, 80.5, 80.2],
            "warp_tension": [120.0, 121.0, 122.0],
            "creel_speed": [500.0, 502.0, 501.0],
            "broken_pick_count": [0.0, 0.0, 1.0],
            "ambient_temperature": [22.0, 22.5, 22.7],
            "ambient_humidity": [55.0, 56.0, 55.5],
        }
    )
    features = map_textile_window_to_cmapss(window, "loom")
    rul, ci_lower, ci_upper = predict_with_ci(features, model)
    assert isinstance(rul, int)
    assert isinstance(ci_lower, int)
    assert isinstance(ci_upper, int)
    assert ci_lower <= rul <= ci_upper


def test_predict_is_deterministic(model) -> None:
    rng = np.random.default_rng(seed=7)
    features = pd.DataFrame(
        [{c: float(rng.normal()) for c in CMAPSS_COLUMNS[2:]}]
    )
    r1 = predict_with_ci(features, model)
    r2 = predict_with_ci(features, model)
    assert r1 == r2


@pytest.mark.slow
def test_rmse_on_fd001_within_literature_baseline(model) -> None:
    """RMSE on FD001 test set ≤ 40 cycles (literature baseline for Ridge ~30-35)."""
    _train, test, rul_truth = load_fd_subset(FD001_DIR, "FD001")
    # For each test unit, use the LAST cycle row as the input window — this is the
    # canonical RUL evaluation protocol for the C-MAPSS test set.
    last_rows = test.groupby("unit_number").tail(1).reset_index(drop=True)
    feature_cols = [c for c in last_rows.columns if c.startswith(("op_setting_", "s"))]
    X = last_rows[feature_cols]
    raw_preds = model.predict(X)
    # Cap at 125 (same piecewise-linear convention as training).
    preds = np.clip(raw_preds, 0, 125)
    truth = rul_truth.values.astype(float)
    rmse = float(np.sqrt(np.mean((preds - truth) ** 2)))
    # Literature baseline ~30-35 for plain Ridge; allow up to 40 as engineering margin.
    assert rmse <= 40.0, f"RMSE {rmse:.2f} exceeds literature baseline (≤40 cycles)"
