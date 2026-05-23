"""C-MAPSS RUL pipeline + textile cross-domain feature mapping.

Submodules (concrete implementations land in plan 07-03, Task 3):
    feature_map — TEXTILE_TO_CMAPSS_FEATURE_MAP, OP_SETTING_MAP, map_textile_window_to_cmapss
    training    — CMAPSS_COLUMNS, RANDOM_STATE, load_fd_subset, compute_train_rul,
                  train_ridge, train_random_forest, save_model
    inference   — load_model, predict_with_ci
    schema      — CMAPSSRecord (frozen Pydantic v2)

Re-exports are intentionally deferred to submodule import sites to avoid
forcing the import of training (which pulls scikit-learn) when callers only
need the lightweight schema. Recommended import:

    >>> from sft_ml.cmapss.training import train_ridge, RANDOM_STATE
    >>> from sft_ml.cmapss.feature_map import map_textile_window_to_cmapss
    >>> from sft_ml.cmapss.inference import load_model, predict_with_ci
    >>> from sft_ml.cmapss.schema import CMAPSSRecord
"""
