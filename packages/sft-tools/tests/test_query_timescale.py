"""Test 10-11: QueryTimescaleTool LangChain BaseTool.

Verifica:
    - Tool name, args_schema corretti
    - SQL usa placeholder $1, $2, $3 (no f-string SQL injection)
    - tags filtro usa ANY($N) con parameter binding
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

UTC = timezone.utc


class TestQueryTimescaleToolMetadata:
    """Test 10a: Tool metadata."""

    def test_tool_name(self) -> None:
        """Test 10: name == 'query_timescale'."""
        from sft_tools.timescale.query import QueryTimescaleTool

        tool = QueryTimescaleTool()
        assert tool.name == "query_timescale"

    def test_tool_description_non_empty(self) -> None:
        """description non vuota."""
        from sft_tools.timescale.query import QueryTimescaleTool

        tool = QueryTimescaleTool()
        assert tool.description
        assert len(tool.description) > 20

    def test_tool_args_schema(self) -> None:
        """args_schema == QueryTimescaleArgs."""
        from sft_tools.timescale.query import QueryTimescaleTool
        from sft_tools.replay.models import QueryTimescaleArgs

        tool = QueryTimescaleTool()
        assert tool.args_schema is QueryTimescaleArgs


class TestQueryTimescaleToolRun:
    """Test 10b: _run raises NotImplementedError."""

    def test_run_raises_not_implemented(self) -> None:
        """_run solleva NotImplementedError."""
        from sft_tools.timescale.query import QueryTimescaleTool

        tool = QueryTimescaleTool()
        with pytest.raises(NotImplementedError):
            tool._run(
                asset_id="LOOM-01",
                time_range=(
                    datetime(2026, 5, 18, 0, 0, 0, tzinfo=UTC),
                    datetime(2026, 5, 18, 1, 0, 0, tzinfo=UTC),
                ),
            )


class TestQueryTimescaleToolSQLPlaceholders:
    """Test 10c: SQL usa placeholder $1, $2, $3 — no f-string SQL injection."""

    @pytest.mark.asyncio
    async def test_arun_uses_dollar_placeholders(self, mock_asyncpg_conn) -> None:
        """Test 10: SQL costruito usa $1, $2, $3 — cattura args passati a conn.fetch."""
        from sft_tools.timescale.query import QueryTimescaleTool

        tool = QueryTimescaleTool()
        time_range = (
            datetime(2026, 5, 18, 0, 0, 0, tzinfo=UTC),
            datetime(2026, 5, 18, 1, 0, 0, tzinfo=UTC),
        )

        with (
            patch("sft_tools.timescale.query.asyncpg") as mock_asyncpg,
            patch.dict("os.environ", {"TIMESCALE_DSN": "postgresql://test:test@localhost/test"}),
        ):
            mock_asyncpg.connect = AsyncMock(return_value=mock_asyncpg_conn)
            mock_asyncpg_conn.__aenter__ = AsyncMock(return_value=mock_asyncpg_conn)
            mock_asyncpg_conn.__aexit__ = AsyncMock(return_value=False)

            await tool._arun(asset_id="LOOM-01", time_range=time_range)

        # Verifica che conn.fetch sia stato chiamato con SQL contenente $1, $2, $3
        assert mock_asyncpg_conn.fetch.called
        call_args = mock_asyncpg_conn.fetch.call_args
        sql_query = call_args[0][0]
        assert "$1" in sql_query, f"Expected $1 in SQL, got: {sql_query}"
        assert "$2" in sql_query, f"Expected $2 in SQL, got: {sql_query}"
        assert "$3" in sql_query, f"Expected $3 in SQL, got: {sql_query}"

    @pytest.mark.asyncio
    async def test_arun_statement_cache_size_zero(self) -> None:
        """Connessione asyncpg usa statement_cache_size=0 (Pitfall 6)."""
        from sft_tools.timescale.query import QueryTimescaleTool

        tool = QueryTimescaleTool()
        time_range = (
            datetime(2026, 5, 18, 0, 0, 0, tzinfo=UTC),
            datetime(2026, 5, 18, 1, 0, 0, tzinfo=UTC),
        )

        with (
            patch("sft_tools.timescale.query.asyncpg") as mock_asyncpg,
            patch.dict("os.environ", {"TIMESCALE_DSN": "postgresql://test:test@localhost/test"}),
        ):
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

            await tool._arun(asset_id="LOOM-01", time_range=time_range)

        # Verifica che asyncpg.connect sia chiamato con statement_cache_size=0
        connect_kwargs = mock_asyncpg.connect.call_args
        assert connect_kwargs is not None
        # Accetta sia kwargs diretti sia keyword args
        all_kwargs = connect_kwargs[1] if connect_kwargs[1] else {}
        assert all_kwargs.get("statement_cache_size") == 0, (
            f"Expected statement_cache_size=0, got: {all_kwargs}"
        )


class TestQueryTimescaleToolTagsFilter:
    """Test 11: tags filtro usa ANY($N) con parameter binding."""

    @pytest.mark.asyncio
    async def test_tags_filter_uses_any_placeholder(self, mock_asyncpg_conn) -> None:
        """Test 11: tags=['warp_tension','pick_density'] produce SQL con ANY($N)."""
        from sft_tools.timescale.query import QueryTimescaleTool

        tool = QueryTimescaleTool()
        time_range = (
            datetime(2026, 5, 18, 0, 0, 0, tzinfo=UTC),
            datetime(2026, 5, 18, 1, 0, 0, tzinfo=UTC),
        )
        tags = ["warp_tension", "pick_density"]

        with (
            patch("sft_tools.timescale.query.asyncpg") as mock_asyncpg,
            patch.dict("os.environ", {"TIMESCALE_DSN": "postgresql://test:test@localhost/test"}),
        ):
            mock_asyncpg.connect = AsyncMock(return_value=mock_asyncpg_conn)

            await tool._arun(asset_id="LOOM-01", time_range=time_range, tags=tags)

        # Verifica SQL contiene ANY($N) per il filtro tag
        assert mock_asyncpg_conn.fetch.called
        call_args = mock_asyncpg_conn.fetch.call_args
        sql_query = call_args[0][0]
        assert "ANY($" in sql_query, f"Expected ANY($N) in SQL, got: {sql_query}"

        # Verifica che tags sia passato come parametro (non interpolato)
        fetch_params = call_args[0][1:]  # parametri posizionali dopo la query
        assert any(param == tags or param == list(tags) for param in fetch_params), (
            f"Expected tags list in fetch params, got: {fetch_params}"
        )
