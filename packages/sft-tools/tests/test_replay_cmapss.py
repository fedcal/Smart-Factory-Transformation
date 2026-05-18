"""Test 4-8: ReplayCMAPSSTool LangChain BaseTool.

Verifica:
    - Tool name, description, args_schema corretti
    - _run solleva NotImplementedError (async-only)
    - _arun ritorna DataFrame con schema unificato (7 colonne)
    - Deterministic hash mapping unit_id → asset_id
    - target_asset_id override funziona
    - sensor_subset filtra correttamente
"""

from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from unittest.mock import patch

import pandas as pd
import pytest

UTC = timezone.utc

_FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "cmapss_fd001_sample.txt"

EXPECTED_COLUMNS = ["asset_id", "timestamp", "sensor_id", "value", "unit", "source_dataset", "source_unit"]


class TestReplayCMAPSSToolMetadata:
    """Test 4: Tool metadata (name, description, args_schema)."""

    def test_tool_name(self) -> None:
        """Test 4: name == 'replay_cmapss'."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool
        from sft_tools.replay.models import ReplayCMAPSSArgs

        tool = ReplayCMAPSSTool()
        assert tool.name == "replay_cmapss"

    def test_tool_description_non_empty(self) -> None:
        """Test 4: description non vuota."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool

        tool = ReplayCMAPSSTool()
        assert tool.description
        assert len(tool.description) > 20

    def test_tool_args_schema(self) -> None:
        """Test 4: args_schema == ReplayCMAPSSArgs."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool
        from sft_tools.replay.models import ReplayCMAPSSArgs

        tool = ReplayCMAPSSTool()
        assert tool.args_schema is ReplayCMAPSSArgs


class TestReplayCMAPSSToolRun:
    """Test 5: _run / _arun behavior."""

    def test_run_raises_not_implemented(self) -> None:
        """Test 5: _run solleva NotImplementedError."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool

        tool = ReplayCMAPSSTool()
        with pytest.raises(NotImplementedError):
            tool._run(unit_id=1)

    @pytest.mark.asyncio
    async def test_arun_returns_dataframe_with_schema(self) -> None:
        """Test 5: _arun su fixture ritorna DataFrame con 7 colonne e >= 21 righe."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool

        tool = ReplayCMAPSSTool()
        with patch("sft_tools.replay.cmapss._get_cmapss_path", return_value=_FIXTURE_PATH):
            df = await tool._arun(unit_id=1, dataset="FD001")

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == EXPECTED_COLUMNS
        # 3 cycles × 21 sensors = 63 rows for unit_id=1
        assert len(df) >= 21, f"Expected >= 21 rows, got {len(df)}"

    @pytest.mark.asyncio
    async def test_arun_source_dataset_column(self) -> None:
        """source_dataset column deve essere 'cmapss'."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool

        tool = ReplayCMAPSSTool()
        with patch("sft_tools.replay.cmapss._get_cmapss_path", return_value=_FIXTURE_PATH):
            df = await tool._arun(unit_id=1, dataset="FD001")

        assert (df["source_dataset"] == "cmapss").all()

    @pytest.mark.asyncio
    async def test_arun_timestamp_is_tz_aware(self) -> None:
        """Tutti i timestamp devono essere tz-aware UTC."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool

        tool = ReplayCMAPSSTool()
        with patch("sft_tools.replay.cmapss._get_cmapss_path", return_value=_FIXTURE_PATH):
            df = await tool._arun(unit_id=1, dataset="FD001")

        for ts in df["timestamp"]:
            assert ts.tzinfo is not None, f"Timestamp non tz-aware: {ts}"


class TestReplayCMAPSSToolDeterministicHash:
    """Test 6: Deterministic hash unit_id → asset_id."""

    @pytest.mark.asyncio
    async def test_same_unit_id_returns_same_asset_id(self) -> None:
        """Test 6: Due chiamate con stesso unit_id ritornano stesso asset_id."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool

        tool = ReplayCMAPSSTool()
        with patch("sft_tools.replay.cmapss._get_cmapss_path", return_value=_FIXTURE_PATH):
            df1 = await tool._arun(unit_id=1, dataset="FD001")
            df2 = await tool._arun(unit_id=1, dataset="FD001")

        assert df1["asset_id"].iloc[0] == df2["asset_id"].iloc[0]


class TestReplayCMAPSSToolTargetAssetId:
    """Test 7: target_asset_id override."""

    @pytest.mark.asyncio
    async def test_explicit_target_asset_id_applied(self) -> None:
        """Test 7: target_asset_id='LOOM-05' → df['asset_id'].unique() == ['LOOM-05']."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool

        tool = ReplayCMAPSSTool()
        with patch("sft_tools.replay.cmapss._get_cmapss_path", return_value=_FIXTURE_PATH):
            df = await tool._arun(unit_id=1, dataset="FD001", target_asset_id="LOOM-05")

        unique_ids = df["asset_id"].unique().tolist()
        assert unique_ids == ["LOOM-05"], f"Expected ['LOOM-05'], got {unique_ids}"


class TestReplayCMAPSSToolSensorSubset:
    """Test 8: sensor_subset filtra correttamente."""

    @pytest.mark.asyncio
    async def test_sensor_subset_filters_sensors(self) -> None:
        """Test 8: sensor_subset=['sensor_2','sensor_7'] filtra correttamente."""
        from sft_tools.replay.cmapss import ReplayCMAPSSTool

        tool = ReplayCMAPSSTool()
        subset = ["sensor_2", "sensor_7"]
        with patch("sft_tools.replay.cmapss._get_cmapss_path", return_value=_FIXTURE_PATH):
            df = await tool._arun(unit_id=1, dataset="FD001", sensor_subset=subset)

        sensor_ids = df["sensor_id"].unique().tolist()
        assert set(sensor_ids) == set(subset), f"Expected {subset}, got {sensor_ids}"
