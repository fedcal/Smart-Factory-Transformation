"""
infra/migrations/timescale/tests/conftest.py

Session-scoped testcontainers fixture providing an isolated TimescaleDB instance.

Uses the same image version as infra/compose/core.yml: timescale/timescaledb:2.18.0-pg16.
The fixture starts the container once per test session and tears it down after all tests.

Requires Docker to be available.  Tests marked with @pytest.mark.testcontainers are
skipped automatically when Docker is not accessible (see pytest.ini_options markers).
"""
from __future__ import annotations

from collections.abc import Generator

import pytest
from testcontainers.postgres import PostgresContainer

_TIMESCALE_IMAGE = "timescale/timescaledb:2.18.0-pg16"
_DB_USER = "sft"
_DB_PASS = "sft_dev_pass"
_DB_NAME = "sft"


@pytest.fixture(scope="session")
def timescale_dsn() -> Generator[str, None, None]:
    """Yield a DSN for a fresh session-scoped TimescaleDB testcontainer."""
    with PostgresContainer(
        image=_TIMESCALE_IMAGE,
        username=_DB_USER,
        password=_DB_PASS,
        dbname=_DB_NAME,
    ) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        dsn = f"postgresql://{_DB_USER}:{_DB_PASS}@{host}:{port}/{_DB_NAME}"
        yield dsn
