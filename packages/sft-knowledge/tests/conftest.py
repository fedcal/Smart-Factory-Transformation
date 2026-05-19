"""Shared pytest fixtures + marker registration for sft-knowledge (Plan 05-01 Task 4).

Provides:
    pytest markers      — `integration` (testcontainers Qdrant/Neo4j) + `gpu` (CUDA-only)
    qdrant_client       — async testcontainer Qdrant 1.16.1 (Plan 05-04 + 05-08 consumer)
    neo4j_driver        — async testcontainer Neo4j 5.24-community (Plan 05-05 + 05-08)
    bge_m3_embedder     — lazy singleton BGE-M3 (Plan 05-07 consumer); skips if module
                          not yet present.

All testcontainer fixtures are session-scoped to amortize container startup; they are
imported lazily inside the fixture body so this conftest can be collected even when
testcontainers / qdrant-client / neo4j drivers are not yet installed (some Wave-0 tests
are skipped — we should not hard-fail collection).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio


def pytest_configure(config: pytest.Config) -> None:
    """Register sft-knowledge custom pytest markers per Shared Pattern 10."""
    config.addinivalue_line(
        "markers",
        "integration: requires docker / testcontainers (Qdrant, Neo4j, Postgres)",
    )
    config.addinivalue_line(
        "markers",
        "gpu: requires CUDA GPU — skipped on CI CPU runner",
    )


# ---------------------------------------------------------------------------
# Qdrant testcontainer (consumed by Plans 05-04 + 05-08 integration tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def qdrant_client(request: pytest.FixtureRequest) -> AsyncIterator[Any]:
    """Async Qdrant client backed by a session-scoped testcontainer.

    Lazy import: testcontainers + qdrant-client may not be installed in every
    dev environment; only `@pytest.mark.integration` tests should depend on
    this fixture.

    Esposes the underlying container URL (rest scheme) via ``request.config.stash``
    under key ``qdrant_url`` so integration tests that need to spawn external
    processes (e.g. Plan 05-04 bootstrap subprocess) can recover it without
    poking at private client internals.
    """
    try:
        from qdrant_client import AsyncQdrantClient
        from testcontainers.qdrant import QdrantContainer
    except ImportError as exc:  # pragma: no cover - exercised when deps missing
        pytest.skip(f"qdrant testcontainer deps unavailable: {exc}")

    # testcontainers 4.x does not expose `get_client_url()`; build the URL from
    # the exposed REST port + host IP. `_rest_port` is the documented default
    # (6333) used by `QdrantContainer.__init__`.
    with QdrantContainer("qdrant/qdrant:v1.16.1") as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(container._rest_port)  # noqa: SLF001
        url = f"http://{host}:{port}"

        client = AsyncQdrantClient(url=url)
        # Make the URL discoverable by tests (see docstring).
        request.config._qdrant_url = url  # type: ignore[attr-defined]
        try:
            yield client
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# Neo4j testcontainer (consumed by Plans 05-05 + 05-08 integration tests)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def neo4j_driver(request: pytest.FixtureRequest) -> AsyncIterator[Any]:
    """Async Neo4j driver backed by a session-scoped testcontainer (5.24-community).

    Lazy import (see `qdrant_client` rationale).

    Pubblica su ``request.config`` (Pattern 05-04 _qdrant_url):
        _neo4j_uri      — Bolt URI esposto dal container
        _neo4j_user     — username (di norma "neo4j")
        _neo4j_password — password sincronizzata col container env NEO4J_AUTH
    Le integration test che lanciano subprocess CLI (es. neo4j-bootstrap.py)
    leggono questi attributi per ricostruire le credenziali senza ispezionare
    membri privati del driver.

    Il container abilita APOC via env NEO4J_PLUGINS=["apoc"] (RESEARCH §5 OQ-3
    mitigation) — richiesto da Plan 05-05 test_apoc_available.
    """
    try:
        from neo4j import AsyncGraphDatabase
        from testcontainers.neo4j import Neo4jContainer
    except ImportError as exc:  # pragma: no cover
        pytest.skip(f"neo4j testcontainer deps unavailable: {exc}")

    container = Neo4jContainer("neo4j:5.24-community").with_env(
        "NEO4J_PLUGINS", '["apoc"]'
    )
    with container as running:
        uri = running.get_connection_url()
        user = running.username
        password = running.password

        # Stash su request.config per il subprocess delle integration test.
        request.config._neo4j_uri = uri  # type: ignore[attr-defined]
        request.config._neo4j_user = user  # type: ignore[attr-defined]
        request.config._neo4j_password = password  # type: ignore[attr-defined]

        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        try:
            yield driver
        finally:
            await driver.close()


# ---------------------------------------------------------------------------
# BGE-M3 embedder (consumed by Plan 05-07)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def bge_m3_embedder() -> Any:
    """Lazy singleton BGE-M3 embedder.

    Skips automatically when `sft_knowledge.embedding.bge_m3` is not yet created
    (Plan 05-07 introduces it).
    """
    try:
        from sft_knowledge.embedding.bge_m3 import BgeM3Embedder  # type: ignore[import-not-found]
    except ImportError:
        pytest.skip("BgeM3Embedder not yet implemented (Plan 05-07)")
    return BgeM3Embedder()
