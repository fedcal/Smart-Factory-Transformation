"""Textile → C-MAPSS cross-domain sensor mapping (07-RESEARCH.md Pattern 2).

Maps best-guess semantic textile sensor tags (loom, spinning, ...) into the
C-MAPSS 21-sensor + 3-op-setting schema so that a Ridge model trained on
turbofan FD001+FD003 can produce a qualitative RUL signal on textile assets.

**Honest caveat** (replicated in MODEL_CARD.md): this is a *best-guess
semantic proxy*, NOT domain-adapted retraining. Cross-domain transfer suffers
significant `domain shift` per the LAMA-Net (arXiv:2208.08388) and
Bi-Discrepancy Network literature. Use for trend signal only; do not treat
absolute RUL cycle counts as calibrated.
"""

from __future__ import annotations

import pandas as pd

# Local copy of CMAPSS_COLUMNS layout — avoids circular import with training.py
# while keeping the column list authoritative there.
_OP_AND_SENSOR_COLS = ["op_setting_1", "op_setting_2", "op_setting_3"] + [
    f"s{i}" for i in range(1, 22)
]


# Per D-PM-03 + cross-reference C-MAPSS sensor descriptions:
# https://github.com/makinarocks/awesome-industrial-machine-datasets/blob/master/data-explanation/C-MAPSS/README.md
TEXTILE_TO_CMAPSS_FEATURE_MAP: dict[str, dict[str, str]] = {
    "loom": {
        "loom_temperature": "s8",      # LPT outlet temperature analog
        "warp_tension": "s11",         # Static pressure HPC outlet analog
        "creel_speed": "s9",           # Physical fan speed analog
        "broken_pick_count": "s14",    # Demanded core speed (proxy event rate)
    },
    "spinning": {
        "spindle_vibration": "s9",     # Fan vibration analog
        "spindle_temperature": "s8",   # LPT outlet temperature analog
        "ring_position": "s11",        # Static pressure HPC outlet analog
    },
    "dyeing": {
        "bath_temperature": "s8",      # LPT outlet temperature analog
        "ph_level": "s17",             # Bleed enthalpy proxy (chemical degradation)
        "agitator_rpm": "s9",          # Fan speed analog
    },
    "warping": {
        "drum_rpm": "s9",              # Fan speed analog
        "yarn_tension": "s11",         # Static pressure HPC outlet analog
        "drum_temperature": "s8",      # LPT outlet temperature analog
    },
}

OP_SETTING_MAP: dict[str, str] = {
    "ambient_temperature": "op_setting_2",
    "ambient_humidity": "op_setting_3",
    # op_setting_1 = "altitude" in C-MAPSS — set to constant 0 for textile
    # (single operating condition, equivalent to FD001 sea-level baseline).
}


def map_textile_window_to_cmapss(
    window_df: pd.DataFrame, asset_family: str
) -> pd.DataFrame:
    """Aggregate last-window textile sensors into a single C-MAPSS row.

    Args:
        window_df: rolling window of textile sensor readings (columns =
            textile sensor tags). Empty DataFrame is permitted and yields a
            zero-filled row (graceful default for warm-up windows).
        asset_family: one of ``TEXTILE_TO_CMAPSS_FEATURE_MAP`` keys. Raises
            ``KeyError`` if unknown.

    Returns:
        Single-row DataFrame with 24 columns (op_setting_1/2/3 + s1..s21),
        zero-filled where no textile mapping exists.
    """
    if asset_family not in TEXTILE_TO_CMAPSS_FEATURE_MAP:
        raise KeyError(
            f"Unknown asset_family={asset_family!r}; "
            f"known: {sorted(TEXTILE_TO_CMAPSS_FEATURE_MAP)}"
        )

    feature_map = TEXTILE_TO_CMAPSS_FEATURE_MAP[asset_family]
    out = pd.Series(0.0, index=_OP_AND_SENSOR_COLS)
    out["op_setting_1"] = 0.0  # explicit textile baseline constant

    # Empty window → return zero row (graceful default).
    if window_df.empty:
        return out.to_frame().T

    for textile_tag, cmapss_col in feature_map.items():
        if textile_tag in window_df.columns:
            out[cmapss_col] = float(window_df[textile_tag].mean())

    for ambient_tag, op_col in OP_SETTING_MAP.items():
        if ambient_tag in window_df.columns:
            out[op_col] = float(window_df[ambient_tag].mean())

    return out.to_frame().T
