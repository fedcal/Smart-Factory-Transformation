"""Inference helper for PredictiveMaintenance agent (D-PM-04 / MNT-01).

Responsibilities:
1. ``load_pretrained_model(path)`` — thin wrapper around ``sft_ml.cmapss.load_model``;
   raises descriptive error on FileNotFoundError pointing at 07-03 setup.
2. ``compute_health_index(rul_cycles)`` — deterministic clamp(rul_cycles / 125.0, 0.0, 1.0).
3. ``predict_rul(pipeline, features)`` — delegates to ``sft_ml.cmapss.predict_with_ci``
   then adds health_index. Returns (rul_cycles, ci_low, ci_high, health_index).

Model path: repo-relative ``packages/sft-ml/models/ridge-fd001-fd003-v1.0.joblib``.
Override via env var ``SFT_ML_MODEL_PATH`` for testing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd

from sft_ml.cmapss import load_model, predict_with_ci

#: Piecewise-linear RUL cap matching C-MAPSS training convention (07-03 sft-ml).
RUL_MAX_CYCLES: int = 125

#: Default model path: repo-relative packages/sft-ml/models/ridge-fd001-fd003-v1.0.joblib
#: parents[0]=mnt_predictive_maintenance, [1]=src, [2]=predictive-maintenance,
#: [3]=maintenance, [4]=agents, [5]=apps, [6]=repo_root
_MODEL_PATH: Path = (
    Path(__file__).resolve().parents[6]
    / "packages"
    / "sft-ml"
    / "models"
    / "ridge-fd001-fd003-v1.0.joblib"
)


def load_pretrained_model(path: Path | None = None) -> Any:
    """Load the committed Ridge C-MAPSS joblib model.

    Args:
        path: Override path. When None, uses ``SFT_ML_MODEL_PATH`` env var,
              falling back to the repo-relative default ``_MODEL_PATH``.

    Returns:
        sklearn Pipeline (Ridge + scaler) loaded from joblib.

    Raises:
        FileNotFoundError: with a descriptive message pointing at 07-03 setup
            when the model file is not found.
        RuntimeError: if sklearn version is below the model's sklearn_min
            (propagated from sft_ml.cmapss.load_model).
    """
    if path is not None:
        resolved = Path(path)
    elif (env_path := os.environ.get("SFT_ML_MODEL_PATH")):
        resolved = Path(env_path)
    else:
        resolved = _MODEL_PATH

    if not resolved.exists():
        raise FileNotFoundError(
            f"PredictiveMaintenance model file not found: {resolved}. "
            "Run plan 07-03 (sft-ml package + model training) to generate the model. "
            "Expected path: packages/sft-ml/models/ridge-fd001-fd003-v1.0.joblib"
        )

    return load_model(resolved)


def compute_health_index(rul_cycles: int) -> float:
    """Derive health_index from rul_cycles deterministically.

    Formula: clamp(rul_cycles / RUL_MAX_CYCLES, 0.0, 1.0)

    Args:
        rul_cycles: Predicted remaining useful cycles (any int).

    Returns:
        float in [0.0, 1.0]. Values < 0.3 trigger the HITL supervisor gate.
    """
    return min(max(rul_cycles / RUL_MAX_CYCLES, 0.0), 1.0)


def predict_rul(
    pipeline: Any,
    features: pd.DataFrame,
) -> tuple[int, int, int, float]:
    """Run RUL inference and return (rul_cycles, ci_lower, ci_upper, health_index).

    Delegates to ``sft_ml.cmapss.predict_with_ci`` for the point estimate + CI,
    then derives health_index via ``compute_health_index``.

    Args:
        pipeline: sklearn Pipeline returned by ``load_pretrained_model``.
        features: Single-row DataFrame with 24 columns (op_setting_1/2/3 + s1..s21).
                  Multi-row input uses only the first row.

    Returns:
        ``(rul_cycles, ci_lower, ci_upper, health_index)`` as (int, int, int, float).
    """
    rul_cycles, ci_lower, ci_upper = predict_with_ci(features, pipeline)
    health_index = compute_health_index(rul_cycles)
    return rul_cycles, ci_lower, ci_upper, health_index


__all__ = [
    "RUL_MAX_CYCLES",
    "load_pretrained_model",
    "compute_health_index",
    "predict_rul",
]
