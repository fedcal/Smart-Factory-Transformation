"""Shared pytest fixtures per i test di svc-ot-bridge.

Fornisce:
    sample_sensor_event     — SensorEvent LOOM-01 warp_tension valid
    mock_pool               — AsyncMock di asyncpg.Pool con acquire() context manager
    mock_jetstream_ctx      — AsyncMock di JetStreamContext con .publish capturable
    frozen_utc_now          — datetime fisso UTC
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

UTC = timezone.utc


@pytest.fixture
def frozen_utc_now() -> datetime:
    """Restituisce un datetime fisso UTC per test deterministici."""
    return datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def sample_sensor_event(frozen_utc_now: datetime):
    """Restituisce un SensorEvent LOOM-01 warp_tension valido.

    Questo fixture richiede che models.py e normalizer.py siano gia' implementati
    (GREEN phase). Durante il RED phase il test che lo usa fallira' su ImportError.
    """
    from svc_ot_bridge.models import SensorEvent
    from sft_assets._models import AssetFamily

    return SensorEvent(
        asset_id="LOOM-01",
        asset_family=AssetFamily.LOOM,
        tag_id="warp_tension",
        timestamp_utc=frozen_utc_now,
        value=25.3,
        unit="N",
        quality_code=0,
        source="live",
        server_received_ts=frozen_utc_now,
    )


@pytest.fixture
def mock_pool():
    """Mock di asyncpg.Pool con acquire() context manager che ritorna mock conn."""
    conn = AsyncMock()
    conn.executemany = AsyncMock(return_value=None)

    # Crea un context manager asincrono per pool.acquire()
    acquire_ctx = MagicMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)

    pool = AsyncMock()
    # pool.acquire() deve ritornare il context manager (non una coroutine)
    pool.acquire = MagicMock(return_value=acquire_ctx)

    return pool, conn


@pytest.fixture
def mock_jetstream_ctx():
    """Mock di JetStreamContext con .publish capturable."""
    js = AsyncMock()
    js.publish = AsyncMock(return_value=None)
    return js
