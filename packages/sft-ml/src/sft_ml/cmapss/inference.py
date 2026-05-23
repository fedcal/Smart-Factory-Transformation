"""Inference helper for the committed Ridge C-MAPSS model.

Two responsibilities:

1. ``load_model(path)`` — joblib.load with companion ``.json`` metadata
   integrity check (Pitfall 1 mitigation): rejects loading if the installed
   scikit-learn major version is below the value recorded at training time.

2. ``predict_with_ci(features, pipeline, ci_pct=0.1)`` — deterministic helper
   returning ``(rul_cycles, ci_lower, ci_upper)`` as integers. For Ridge the
   CI is computed as a simple ±``ci_pct`` percentage band of the point
   estimate. This is a **PoC simplification** — RandomForest variant could
   produce a real per-tree std-dev later (deferred, see MODEL_CARD.md).

Determinism: same ``features`` input → same triple output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import sklearn

# Piecewise-linear RUL cap matches training (see training.RUL_CAP).
_RUL_CAP: int = 125


def _check_sklearn_version(meta: dict[str, Any]) -> None:
    """Refuse to load when installed sklearn major is below the model's sklearn_min."""
    required = meta.get("sklearn_min")
    if not required:
        return
    installed = sklearn.__version__
    required_major = int(str(required).split(".")[0])
    installed_major = int(installed.split(".")[0])
    if installed_major < required_major:
        raise RuntimeError(
            f"sklearn version skew: model requires >={required}, "
            f"installed {installed}. Refuse to unpickle (Pitfall 1)."
        )


def load_model(path: Path | str) -> Any:
    """Load a joblib-serialized sklearn Pipeline with metadata integrity check."""
    path = Path(path)
    meta_path = path.with_suffix(".json")
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        _check_sklearn_version(meta)
    return joblib.load(path)


def predict_with_ci(
    features: pd.DataFrame,
    pipeline: Any,
    ci_pct: float = 0.10,
) -> tuple[int, int, int]:
    """Predict RUL with a simple ±ci_pct band.

    Args:
        features: single-row DataFrame matching the training feature columns
            (op_setting_1/2/3 + s1..s21). Multi-row input is supported but only
            the first row is returned in the triple.
        pipeline: sklearn Pipeline returned by ``train_ridge``/``train_random_forest``.
        ci_pct: half-width of the confidence band as a fraction of the point
            estimate (default 0.10 → ±10%).

    Returns:
        ``(rul_cycles, ci_lower, ci_upper)`` as ints. The point estimate is
        clipped to ``[0, 125]`` (training piecewise-linear cap).
    """
    raw = float(pipeline.predict(features)[0])
    # Clip to training cap; negative predictions floored at 0.
    point = max(0.0, min(_RUL_CAP, raw))
    band = abs(point * ci_pct)
    lower = max(0.0, point - band)
    upper = min(float(_RUL_CAP), point + band)
    return int(round(point)), int(round(lower)), int(round(upper))
