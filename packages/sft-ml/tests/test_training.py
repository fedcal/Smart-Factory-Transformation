"""Tests for the C-MAPSS training pipeline (Pattern 1 + 3 of 07-RESEARCH.md).

Covers:
- CMAPSS_COLUMNS has 26 entries.
- RANDOM_STATE == 42 (determinism contract).
- load_fd_subset loads (train, test, rul) shapes for FD001.
- compute_train_rul adds 'rul' column with max-per-unit semantics + cap=125.
- train_ridge returns a sklearn Pipeline producing deterministic predictions.
- save_model writes joblib + companion .json metadata.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sft_ml.cmapss.training import (
    CMAPSS_COLUMNS,
    RANDOM_STATE,
    compute_train_rul,
    load_fd_subset,
    save_model,
    train_ridge,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FD001_DIR = PROJECT_ROOT / "data" / "c-mapss-fd001"


def test_cmapss_columns_count() -> None:
    assert len(CMAPSS_COLUMNS) == 26
    assert CMAPSS_COLUMNS[0] == "unit_number"
    assert CMAPSS_COLUMNS[1] == "time_cycles"
    assert CMAPSS_COLUMNS[2:5] == ["op_setting_1", "op_setting_2", "op_setting_3"]
    assert CMAPSS_COLUMNS[5] == "s1"
    assert CMAPSS_COLUMNS[-1] == "s21"


def test_random_state_is_42() -> None:
    assert RANDOM_STATE == 42


def test_load_fd001_subset_shapes() -> None:
    train, test, rul = load_fd_subset(FD001_DIR, "FD001")
    assert list(train.columns) == CMAPSS_COLUMNS
    assert list(test.columns) == CMAPSS_COLUMNS
    # FD001 is the smallest subset: ~100 train units, ~100 test units, 100 RUL truths.
    assert train["unit_number"].nunique() == 100
    assert test["unit_number"].nunique() == 100
    assert len(rul) == 100
    assert train.shape[0] > 20_000  # ~20631 rows in canonical FD001 train
    assert test.shape[0] > 13_000  # ~13096 rows in canonical FD001 test


def test_compute_train_rul_max_per_unit_with_cap() -> None:
    # 2 units with known max cycles 50 and 200 → second unit will be capped at 125.
    df = pd.DataFrame(
        {
            "unit_number": [1, 1, 1, 2, 2, 2],
            "time_cycles": [1, 25, 50, 1, 100, 200],
        }
    )
    out = compute_train_rul(df)
    assert "rul" in out.columns
    # Unit 1: max=50, so RUL = 50-1=49, 50-25=25, 50-50=0.
    unit1 = out[out["unit_number"] == 1].sort_values("time_cycles")
    np.testing.assert_array_equal(unit1["rul"].values, [49, 25, 0])
    # Unit 2: max=200, but raw values (199, 100, 0) all <= 125 except 199 → cap to 125.
    unit2 = out[out["unit_number"] == 2].sort_values("time_cycles")
    np.testing.assert_array_equal(unit2["rul"].values, [125, 100, 0])


def test_train_ridge_deterministic() -> None:
    # Tiny synthetic dataset on the full schema to exercise the pipeline.
    rng = np.random.default_rng(seed=0)
    n = 50
    df = pd.DataFrame(
        {
            "unit_number": np.ones(n, dtype=int),
            "time_cycles": np.arange(1, n + 1),
            **{c: rng.normal(size=n) for c in CMAPSS_COLUMNS[2:]},
        }
    )
    df["rul"] = np.arange(n - 1, -1, -1).astype(float)
    p1 = train_ridge(df)
    p2 = train_ridge(df)
    features = [c for c in df.columns if c.startswith(("op_setting_", "s"))]
    pred1 = p1.predict(df[features])
    pred2 = p2.predict(df[features])
    np.testing.assert_array_equal(pred1, pred2)


def test_save_model_writes_joblib_and_metadata(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=1)
    n = 30
    df = pd.DataFrame(
        {
            "unit_number": np.ones(n, dtype=int),
            "time_cycles": np.arange(1, n + 1),
            **{c: rng.normal(size=n) for c in CMAPSS_COLUMNS[2:]},
        }
    )
    df["rul"] = np.arange(n - 1, -1, -1).astype(float)
    pipeline = train_ridge(df)
    out_path = tmp_path / "ridge-test-v0.joblib"
    save_model(pipeline, out_path, version="v0")
    assert out_path.exists()
    assert out_path.with_suffix(".json").exists()
    meta_text = out_path.with_suffix(".json").read_text()
    assert "v0" in meta_text
    assert "sklearn_min" in meta_text


@pytest.mark.slow
def test_compute_train_rul_on_real_fd001() -> None:
    train, _test, _rul = load_fd_subset(FD001_DIR, "FD001")
    out = compute_train_rul(train)
    # RUL is capped at 125 — no value should exceed 125.
    assert out["rul"].max() == 125
    # Min should be 0 (final cycle of failing unit).
    assert out["rul"].min() == 0
