"""C-MAPSS RUL pipeline + textile cross-domain feature mapping.

Re-exports the public surface consumed by PredictiveMaintenance agent (07-06):

    >>> from sft_ml.cmapss import (
    ...     CMAPSS_COLUMNS, RANDOM_STATE,
    ...     load_fd_subset, compute_train_rul,
    ...     train_ridge, train_random_forest, save_model,
    ...     load_model, predict_with_ci,
    ...     TEXTILE_TO_CMAPSS_FEATURE_MAP, OP_SETTING_MAP,
    ...     map_textile_window_to_cmapss,
    ...     CMAPSSRecord,
    ... )
"""

from sft_ml.cmapss.feature_map import (
    OP_SETTING_MAP,
    TEXTILE_TO_CMAPSS_FEATURE_MAP,
    map_textile_window_to_cmapss,
)
from sft_ml.cmapss.inference import load_model, predict_with_ci
from sft_ml.cmapss.schema import CMAPSSRecord
from sft_ml.cmapss.training import (
    CMAPSS_COLUMNS,
    RANDOM_STATE,
    compute_train_rul,
    load_fd_subset,
    save_model,
    train_random_forest,
    train_ridge,
)

__all__ = [
    "CMAPSS_COLUMNS",
    "RANDOM_STATE",
    "load_fd_subset",
    "compute_train_rul",
    "train_ridge",
    "train_random_forest",
    "save_model",
    "load_model",
    "predict_with_ci",
    "TEXTILE_TO_CMAPSS_FEATURE_MAP",
    "OP_SETTING_MAP",
    "map_textile_window_to_cmapss",
    "CMAPSSRecord",
]
