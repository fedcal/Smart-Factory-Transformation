"""Shared pytest fixtures per i test di sft-tools.

Fornisce:
    sample_replay_record_dict   — dict valido per ReplayRecord
    frozen_utc_now              — datetime UTC fissa per test deterministici
    mock_asyncpg_conn           — AsyncMock per asyncpg connection
    cmapss_fixture_path         — path fissa al fixture C-MAPSS FD001
    uci_fixture_path            — path fissa al fixture UCI production
"""

from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

UTC = timezone.utc

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def sample_replay_record_dict() -> dict:
    """Restituisce un dizionario valido per un ReplayRecord."""
    return {
        "asset_id": "LOOM-01",
        "timestamp": datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        "sensor_id": "sensor_2",
        "value": 1.23,
        "unit": "raw",
        "source_dataset": "cmapss",
        "source_unit": "FD001#unit1#cycle1",
    }


@pytest.fixture(scope="module")
def frozen_utc_now() -> datetime:
    """Restituisce un datetime UTC fisso per test deterministici."""
    return datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_asyncpg_conn():
    """AsyncMock per asyncpg connection con .fetch che ritorna records sintetici."""
    conn = AsyncMock()
    # Simula records sintetici per sensor_events query
    mock_record_1 = MagicMock()
    mock_record_1.__getitem__ = MagicMock(side_effect=lambda k: {
        "asset_id": "LOOM-01",
        "tag_id": "warp_tension",
        "timestamp_utc": datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        "value": 25.3,
        "unit": "N",
    }[k])
    mock_record_1.keys = MagicMock(return_value=["asset_id", "tag_id", "timestamp_utc", "value", "unit"])
    mock_record_1._asdict = MagicMock(return_value={
        "asset_id": "LOOM-01",
        "tag_id": "warp_tension",
        "timestamp_utc": datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
        "value": 25.3,
        "unit": "N",
    })
    conn.fetch = AsyncMock(return_value=[mock_record_1])
    return conn


@pytest.fixture(scope="module")
def cmapss_fixture_path() -> pathlib.Path:
    """Path fissa al fixture C-MAPSS FD001 per test."""
    path = _FIXTURES_DIR / "cmapss_fd001_sample.txt"
    assert path.exists(), f"Fixture C-MAPSS non trovata: {path}"
    return path


@pytest.fixture(scope="module")
def uci_fixture_path() -> pathlib.Path:
    """Path fissa al fixture UCI production per test."""
    path = _FIXTURES_DIR / "uci_production_sample.csv"
    assert path.exists(), f"Fixture UCI non trovata: {path}"
    return path
