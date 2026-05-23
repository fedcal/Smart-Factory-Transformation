"""sft-ml: ML layer for Smart Factory Transformation.

Phase 7 (MNT-01) — RUL estimation pipeline based on NASA C-MAPSS FD001+FD003
turbofan dataset, mapped via best-guess semantic feature proxy to textile asset
sensors (loom + spinning). Deterministic Ridge baseline (random_state=42).

Subpackages:
    cmapss — load_fd_subset, compute_train_rul, train_ridge, train_random_forest,
             save_model, load_model, predict_with_ci, map_textile_window_to_cmapss,
             TEXTILE_TO_CMAPSS_FEATURE_MAP, OP_SETTING_MAP, CMAPSS_COLUMNS,
             RANDOM_STATE, CMAPSSRecord

See packages/sft-ml/MODEL_CARD.md for cross-domain transfer caveats and
reproduction instructions.
"""
