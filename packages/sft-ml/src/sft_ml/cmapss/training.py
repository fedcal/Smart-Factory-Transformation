"""C-MAPSS RUL training pipeline (07-RESEARCH.md Pattern 1 + Pattern 3).

Deterministic Ridge + RandomForest baselines on NASA C-MAPSS FD001+FD003.
No PyTorch, no runtime download (data committed under packages/sft-ml/data/).

CLI entrypoint:

    cd packages/sft-ml
    uv run --project ../.. python -m sft_ml.cmapss.training

Produces ``models/ridge-fd001-fd003-v1.0.joblib`` + companion
``ridge-fd001-fd003-v1.0.json`` metadata.

Determinism contract: ``RANDOM_STATE = 42`` fissato. Same input data → same
fitted model coefficients → same predict output.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_STATE: int = 42

# Canonical NASA C-MAPSS column layout (26 cols).
CMAPSS_COLUMNS: list[str] = (
    ["unit_number", "time_cycles", "op_setting_1", "op_setting_2", "op_setting_3"]
    + [f"s{i}" for i in range(1, 22)]
)

# Piecewise-linear RUL cap (literature standard, Heimes 2008 / NASA convention).
RUL_CAP: int = 125


def load_fd_subset(
    data_dir: Path, subset: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """Load FD00x train/test/RUL truth files into DataFrames.

    Args:
        data_dir: directory containing ``train_{subset}.txt``,
            ``test_{subset}.txt``, ``RUL_{subset}.txt``.
        subset: e.g. ``"FD001"``, ``"FD003"``.

    Returns:
        (train_df, test_df, rul_series) — train/test follow CMAPSS_COLUMNS;
        rul is a 1-D Series with one entry per unit in test_df.
    """
    train = pd.read_csv(
        data_dir / f"train_{subset}.txt",
        sep=r"\s+",
        header=None,
        names=CMAPSS_COLUMNS,
        engine="python",
    )
    test = pd.read_csv(
        data_dir / f"test_{subset}.txt",
        sep=r"\s+",
        header=None,
        names=CMAPSS_COLUMNS,
        engine="python",
    )
    rul_truth = pd.read_csv(
        data_dir / f"RUL_{subset}.txt",
        sep=r"\s+",
        header=None,
        names=["rul"],
        engine="python",
    )["rul"]
    return train, test, rul_truth


def compute_train_rul(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``rul`` column: max_cycle_per_unit - current_cycle, capped at RUL_CAP."""
    max_per_unit = df.groupby("unit_number")["time_cycles"].transform("max")
    df = df.copy()
    df["rul"] = max_per_unit - df["time_cycles"]
    df["rul"] = np.minimum(df["rul"], RUL_CAP)
    return df


def _features_and_target(
    train_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    features = [c for c in train_df.columns if c.startswith(("op_setting_", "s"))]
    return train_df[features], train_df["rul"]


def train_ridge(train_df: pd.DataFrame) -> Pipeline:
    """Train deterministic Ridge regressor on engineered features.

    Pipeline = StandardScaler → Ridge(alpha=1.0, random_state=42).
    """
    X, y = _features_and_target(train_df)
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0, random_state=RANDOM_STATE)),
        ]
    )
    pipeline.fit(X, y)
    return pipeline


def train_random_forest(train_df: pd.DataFrame) -> Pipeline:
    """Train deterministic RandomForest (n_estimators=100, max_depth=10)."""
    X, y = _features_and_target(train_df)
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=RANDOM_STATE,
                    n_jobs=1,
                ),
            ),
        ]
    )
    pipeline.fit(X, y)
    return pipeline


def save_model(
    pipeline: Pipeline,
    out_path: Path,
    version: str = "v1.0",
    sklearn_min: str = "1.7.0",
    python_min: str = "3.12",
) -> None:
    """joblib serialize with gzip compression + companion JSON metadata.

    Metadata (separate .json file) allows integrity / version check WITHOUT
    unpickling the joblib (mitigates Pitfall 1 — sklearn major version skew).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, out_path, compress=("gzip", 3))
    meta = {
        "version": version,
        "sklearn_min": sklearn_min,
        "python_min": python_min,
        "random_state": RANDOM_STATE,
        "training_dataset": "NASA C-MAPSS FD001+FD003 (joint)",
        "rul_cap": RUL_CAP,
    }
    out_path.with_suffix(".json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n"
    )


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _train_and_save_joint_ridge() -> None:
    """Train Ridge on joint FD001+FD003 and save to models/ridge-fd001-fd003-v1.0.joblib."""
    pkg_root = Path(__file__).resolve().parents[3]
    fd001_dir = pkg_root / "data" / "c-mapss-fd001"
    fd003_dir = pkg_root / "data" / "c-mapss-fd003"
    out_path = pkg_root / "models" / "ridge-fd001-fd003-v1.0.joblib"

    print(f"Loading FD001 from {fd001_dir}")
    train_1, test_1, rul_1 = load_fd_subset(fd001_dir, "FD001")
    print(f"Loading FD003 from {fd003_dir}")
    train_3, test_3, rul_3 = load_fd_subset(fd003_dir, "FD003")

    print(f"FD001 train rows={len(train_1)} units={train_1['unit_number'].nunique()}")
    print(f"FD003 train rows={len(train_3)} units={train_3['unit_number'].nunique()}")

    train_1_rul = compute_train_rul(train_1)
    train_3_rul = compute_train_rul(train_3)

    # Joint training: simple concat is acceptable for Ridge baseline (no unit_number
    # collision because StandardScaler operates per-feature, not per-unit, and
    # unit_number is excluded from the feature set by _features_and_target).
    joint = pd.concat([train_1_rul, train_3_rul], ignore_index=True)
    print(f"Joint training rows={len(joint)}")

    pipeline = train_ridge(joint)
    print(f"Trained Ridge pipeline: {pipeline}")

    # Evaluate on each test set's last-cycle-per-unit (canonical RUL protocol).
    for label, test_df, rul_truth in [
        ("FD001", test_1, rul_1),
        ("FD003", test_3, rul_3),
    ]:
        last_rows = test_df.groupby("unit_number").tail(1).reset_index(drop=True)
        feature_cols = [
            c for c in last_rows.columns if c.startswith(("op_setting_", "s"))
        ]
        raw_preds = pipeline.predict(last_rows[feature_cols])
        preds = np.clip(raw_preds, 0, RUL_CAP)
        rmse = float(np.sqrt(np.mean((preds - rul_truth.values) ** 2)))
        print(f"{label} test RMSE (cycles): {rmse:.2f}")

    save_model(pipeline, out_path, version="v1.0")
    print(f"Saved model → {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")
    print(f"Saved metadata → {out_path.with_suffix('.json')}")


if __name__ == "__main__":
    _train_and_save_joint_ridge()
