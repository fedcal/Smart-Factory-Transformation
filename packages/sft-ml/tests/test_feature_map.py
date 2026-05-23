"""Tests for textile → C-MAPSS feature mapping (Pattern 2 of 07-RESEARCH.md).

Covers:
- TEXTILE_TO_CMAPSS_FEATURE_MAP shape (at minimum loom + spinning families).
- OP_SETTING_MAP for ambient T/H → op_setting_2/3.
- map_textile_window_to_cmapss output shape (single row, 21 sensors + 3 op).
- Unknown family raises KeyError.
- Empty DataFrame yields a zero-filled row (graceful default).
"""

from __future__ import annotations

import pandas as pd
import pytest

from sft_ml.cmapss.feature_map import (
    OP_SETTING_MAP,
    TEXTILE_TO_CMAPSS_FEATURE_MAP,
    map_textile_window_to_cmapss,
)


def test_feature_map_has_loom_and_spinning() -> None:
    assert "loom" in TEXTILE_TO_CMAPSS_FEATURE_MAP
    assert "spinning" in TEXTILE_TO_CMAPSS_FEATURE_MAP
    assert isinstance(TEXTILE_TO_CMAPSS_FEATURE_MAP["loom"], dict)
    assert isinstance(TEXTILE_TO_CMAPSS_FEATURE_MAP["spinning"], dict)
    # Loom family must contain at minimum the canonical mappings from Pattern 2.
    assert TEXTILE_TO_CMAPSS_FEATURE_MAP["loom"].get("loom_temperature") == "s8"
    assert TEXTILE_TO_CMAPSS_FEATURE_MAP["loom"].get("warp_tension") == "s11"


def test_op_setting_map_ambient_to_op_setting() -> None:
    assert OP_SETTING_MAP["ambient_temperature"] == "op_setting_2"
    assert OP_SETTING_MAP["ambient_humidity"] == "op_setting_3"


def test_map_loom_window_to_cmapss_shape() -> None:
    window = pd.DataFrame(
        {
            "loom_temperature": [80.1, 80.2, 80.3],
            "warp_tension": [120.0, 121.0, 122.0],
            "creel_speed": [500.0, 502.0, 501.0],
            "broken_pick_count": [0.0, 0.0, 1.0],
            "ambient_temperature": [22.0, 22.5, 22.7],
            "ambient_humidity": [55.0, 56.0, 55.5],
        }
    )
    row = map_textile_window_to_cmapss(window, "loom")
    # Single row output.
    assert row.shape[0] == 1
    # 24 columns: op_setting_1/2/3 + s1..s21.
    expected_cols = (
        ["op_setting_1", "op_setting_2", "op_setting_3"]
        + [f"s{i}" for i in range(1, 22)]
    )
    assert list(row.columns) == expected_cols
    # Mapped values: loom_temperature mean -> s8.
    assert row["s8"].iloc[0] == pytest.approx(80.2, rel=1e-3)
    # warp_tension mean -> s11.
    assert row["s11"].iloc[0] == pytest.approx(121.0, rel=1e-3)
    # ambient_temperature mean -> op_setting_2.
    assert row["op_setting_2"].iloc[0] == pytest.approx(22.4, rel=1e-2)
    # ambient_humidity mean -> op_setting_3.
    assert row["op_setting_3"].iloc[0] == pytest.approx(55.5, rel=1e-2)
    # op_setting_1 constant 0 (textile single-condition).
    assert row["op_setting_1"].iloc[0] == 0.0


def test_map_spinning_window_to_cmapss() -> None:
    window = pd.DataFrame(
        {
            "spindle_vibration": [0.5, 0.6, 0.55],
            "spindle_temperature": [78.0, 79.0, 78.5],
            "ring_position": [10.0, 11.0, 10.5],
        }
    )
    row = map_textile_window_to_cmapss(window, "spinning")
    assert row["s9"].iloc[0] == pytest.approx(0.55, rel=1e-3)
    assert row["s8"].iloc[0] == pytest.approx(78.5, rel=1e-3)
    assert row["s11"].iloc[0] == pytest.approx(10.5, rel=1e-3)


def test_unknown_asset_family_raises_keyerror() -> None:
    window = pd.DataFrame({"any_sensor": [1.0, 2.0]})
    with pytest.raises(KeyError):
        map_textile_window_to_cmapss(window, "unknown_family")


def test_empty_window_returns_zero_row() -> None:
    window = pd.DataFrame()
    row = map_textile_window_to_cmapss(window, "loom")
    assert row.shape[0] == 1
    # All sensor columns zero by default.
    for col in [f"s{i}" for i in range(1, 22)]:
        assert row[col].iloc[0] == 0.0
    assert row["op_setting_1"].iloc[0] == 0.0
    assert row["op_setting_2"].iloc[0] == 0.0
    assert row["op_setting_3"].iloc[0] == 0.0
