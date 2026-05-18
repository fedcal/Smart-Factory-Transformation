"""Test 9: ReplayUCITool LangChain BaseTool.

Verifica:
    - Tool name, args_schema corretti
    - _run solleva NotImplementedError (async-only)
    - _arun su fixture ritorna DataFrame con schema unificato
"""

from __future__ import annotations

import pathlib
from unittest.mock import patch

import pandas as pd
import pytest

_FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "uci_production_sample.csv"

EXPECTED_COLUMNS = ["asset_id", "timestamp", "sensor_id", "value", "unit", "source_dataset", "source_unit"]


class TestReplayUCIToolMetadata:
    """Test 9a: Tool metadata."""

    def test_tool_name(self) -> None:
        """Test 9: name == 'replay_uci'."""
        from sft_tools.replay.uci import ReplayUCITool

        tool = ReplayUCITool()
        assert tool.name == "replay_uci"

    def test_tool_description_non_empty(self) -> None:
        """description non vuota."""
        from sft_tools.replay.uci import ReplayUCITool

        tool = ReplayUCITool()
        assert tool.description
        assert len(tool.description) > 20

    def test_tool_args_schema(self) -> None:
        """args_schema == ReplayUCIArgs."""
        from sft_tools.replay.uci import ReplayUCITool
        from sft_tools.replay.models import ReplayUCIArgs

        tool = ReplayUCITool()
        assert tool.args_schema is ReplayUCIArgs


class TestReplayUCIToolRun:
    """Test 9b: _run / _arun behavior."""

    def test_run_raises_not_implemented(self) -> None:
        """_run solleva NotImplementedError."""
        from sft_tools.replay.uci import ReplayUCITool

        tool = ReplayUCITool()
        with pytest.raises(NotImplementedError):
            tool._run(dataset="production", asset_id="LOOM-01")

    @pytest.mark.asyncio
    async def test_arun_returns_dataframe_with_schema(self) -> None:
        """Test 9: _arun su fixture ritorna DataFrame con schema unificato."""
        from sft_tools.replay.uci import ReplayUCITool

        tool = ReplayUCITool()
        with patch("sft_tools.replay.uci._get_uci_path", return_value=_FIXTURE_PATH):
            df = await tool._arun(dataset="production", asset_id="LOOM-01")

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == EXPECTED_COLUMNS

    @pytest.mark.asyncio
    async def test_arun_asset_id_applied(self) -> None:
        """asset_id nel DataFrame corrisponde a quello passato."""
        from sft_tools.replay.uci import ReplayUCITool

        tool = ReplayUCITool()
        with patch("sft_tools.replay.uci._get_uci_path", return_value=_FIXTURE_PATH):
            df = await tool._arun(dataset="production", asset_id="LOOM-01")

        assert (df["asset_id"] == "LOOM-01").all()

    @pytest.mark.asyncio
    async def test_arun_source_dataset_column(self) -> None:
        """source_dataset column deve essere 'uci'."""
        from sft_tools.replay.uci import ReplayUCITool

        tool = ReplayUCITool()
        with patch("sft_tools.replay.uci._get_uci_path", return_value=_FIXTURE_PATH):
            df = await tool._arun(dataset="production", asset_id="LOOM-01")

        assert (df["source_dataset"] == "uci").all()

    @pytest.mark.asyncio
    async def test_arun_timestamp_is_tz_aware(self) -> None:
        """Tutti i timestamp devono essere tz-aware UTC."""
        from sft_tools.replay.uci import ReplayUCITool

        tool = ReplayUCITool()
        with patch("sft_tools.replay.uci._get_uci_path", return_value=_FIXTURE_PATH):
            df = await tool._arun(dataset="production", asset_id="LOOM-01")

        for ts in df["timestamp"]:
            assert ts.tzinfo is not None, f"Timestamp non tz-aware: {ts}"
