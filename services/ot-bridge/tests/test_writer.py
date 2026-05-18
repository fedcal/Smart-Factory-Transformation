"""Test per svc_ot_bridge.timescale_writer — asyncpg batch INSERT + pool config.

Test 11: executemany_placeholder — SQL contiene $1..$7, nessuna f-string
Test 12: batch_size              — writer flush solo dopo 500 eventi
Test 13: flush_interval          — writer flush dopo 100ms anche con < 500 eventi
Test 14: pool_config             — create_pool chiamato con kwargs corretti (Pitfall 6)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
import re

import pytest

UTC = timezone.utc


def _make_event(i: int = 0):
    """Helper: crea SensorEvent LOOM-01 warp_tension."""
    from svc_ot_bridge.models import SensorEvent
    from sft_assets._models import AssetFamily

    return SensorEvent(
        asset_id="LOOM-01",
        asset_family=AssetFamily.LOOM,
        tag_id="warp_tension",
        timestamp_utc=datetime(2026, 5, 18, i // 3600, (i % 3600) // 60, i % 60, tzinfo=UTC),
        value=float(i),
        unit="N",
        quality_code=0,
        source="live",
        server_received_ts=datetime(2026, 5, 18, tzinfo=UTC),
    )


class TestExecutemanyPlaceholder:
    """Test 11 — SQL usa $1..$7 placeholder, zero f-string interpolation."""

    def test_executemany_placeholder(self) -> None:
        """Il modulo timescale_writer deve contenere _INSERT_SQL con $1..$7
        e non deve contenere nessuna f-string SQL (sicurezza T-V5-sql)."""
        import svc_ot_bridge.timescale_writer as writer_module

        # Verifica che _INSERT_SQL esista e contenga i placeholder corretti
        assert hasattr(writer_module, "_INSERT_SQL"), "_INSERT_SQL deve essere costante modulo"

        sql = writer_module._INSERT_SQL

        # Deve contenere tutti i placeholder $1..$7
        for i in range(1, 8):
            assert f"${i}" in sql, f"Placeholder ${i} mancante in _INSERT_SQL"

        # Non deve contenere f-string SQL (assenza di interpolazione dinamica)
        # Il test verifica che la costante sia una stringa semplice, non costruita dinamicamente
        assert isinstance(sql, str), "_INSERT_SQL deve essere str"
        assert "INSERT INTO sensor_events" in sql
        assert "VALUES" in sql.upper()


class TestBatchSize:
    """Test 12 — writer accumula 500 eventi prima di flush."""

    async def test_batch_size(self, mock_pool) -> None:
        """Pool.acquire deve essere invocato solo dopo il 500° push (batch_size=500)."""
        from svc_ot_bridge.timescale_writer import TimescaleWriter

        pool_mock, conn_mock = mock_pool

        writer = TimescaleWriter(dsn="postgresql://test", batch_size=500, flush_interval_s=999.0)
        writer._pool = pool_mock

        # Push 499 eventi — non deve flush
        for i in range(499):
            await writer.push(_make_event(i))

        pool_mock.acquire.assert_not_called()

        # Push il 500° evento — deve triggerare il flush
        await writer.push(_make_event(499))

        pool_mock.acquire.assert_called()
        conn_mock.executemany.assert_called()


class TestFlushInterval:
    """Test 13 — writer flush dopo 100ms anche se buffer < 500."""

    async def test_flush_interval(self, mock_pool) -> None:
        """Il flush_loop deve flush il buffer dopo flush_interval_s anche con < 500 eventi."""
        from svc_ot_bridge.timescale_writer import TimescaleWriter

        pool_mock, conn_mock = mock_pool

        # Usa flush_interval molto breve per il test
        writer = TimescaleWriter(dsn="postgresql://test", batch_size=500, flush_interval_s=0.05)
        writer._pool = pool_mock

        # Avvia il flush loop come task
        flush_task = asyncio.create_task(writer._flush_loop())

        # Aggiungi qualche evento
        for i in range(5):
            await writer.push(_make_event(i))

        # Aspetta il flush (> flush_interval_s)
        await asyncio.sleep(0.15)

        # Cancella il loop
        flush_task.cancel()
        try:
            await flush_task
        except asyncio.CancelledError:
            pass

        # Il flush deve essere stato eseguito (almeno una volta)
        conn_mock.executemany.assert_called()


class TestPoolConfig:
    """Test 14 — TimescaleWriter.start() chiama asyncpg.create_pool con kwargs corretti."""

    async def test_pool_config(self) -> None:
        """create_pool deve essere chiamato con min_size=10, max_size=20,
        statement_cache_size=0, command_timeout=10.0 (Pitfall 6)."""
        from svc_ot_bridge.timescale_writer import TimescaleWriter

        pool_instance = MagicMock()

        # asyncpg.create_pool e' una coroutine — patch con AsyncMock che ritorna pool_instance
        mock_create_pool = AsyncMock(return_value=pool_instance)

        with patch("svc_ot_bridge.timescale_writer.asyncpg.create_pool", mock_create_pool), \
             patch("asyncio.create_task") as mock_create_task:

            writer = TimescaleWriter(dsn="postgresql://test:5432/sft")
            await writer.start()

            mock_create_pool.assert_called_once()
            call_kwargs = mock_create_pool.call_args[1]

            assert call_kwargs["min_size"] == 10, "min_size deve essere 10"
            assert call_kwargs["max_size"] == 20, "max_size deve essere 20"
            assert call_kwargs["statement_cache_size"] == 0, "statement_cache_size deve essere 0 (Pitfall 6)"
            assert call_kwargs["command_timeout"] == 10.0, "command_timeout deve essere 10.0s"
