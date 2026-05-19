# Covers KNW-08 SC#4 (graph CI validator) per 05-VALIDATION.md
"""Plan 05-05 integration tests for Neo4j bootstrap script + APOC plugin.

Plan 05-08 will add Neo4jGraphBuilder.merge_sop + graph CI validator tests
(test_graph_ci_validator and test_merge_sop_idempotent are left as stubs).

These tests require Docker (testcontainers) and are gated by
``@pytest.mark.integration``; they are excluded from the quick CI lane and run
only when the integration suite is invoked.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

# Workspace root = .../<repo>/  (this file lives at packages/sft-knowledge/tests/)
WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[3]
BOOTSTRAP_SCRIPT = WORKSPACE_ROOT / "scripts" / "neo4j-bootstrap.py"

# D-65 LOCKED — 4 unique constraints + 1 index
EXPECTED_CONSTRAINTS = {
    "machine_id_unique",
    "part_id_unique",
    "failure_mode_id_unique",
    "sop_id_unique",
}
EXPECTED_INDEX = "sop_version"


def _driver_uri_and_auth(neo4j_driver) -> tuple[str, tuple[str, str]]:
    """Estrae URI + auth dal driver fixture per costruire la CLI subprocess.

    Il driver neo4j-python espone l'URI sotto `_pool.address` o tramite metadata.
    Per robustezza usiamo il container URL pubblicato dalla fixture session
    (vedi conftest); preferiamo però una via diretta:
    leggiamo dall'env esposto dal testcontainer (NEO4J_ADMIN_PASSWORD costante)
    e dall'URI risolto dal driver stesso.
    """
    # neo4j.AsyncDriver expose `.uri` su versioni recenti; fallback su address pool.
    uri = getattr(neo4j_driver, "uri", None) or f"bolt://{neo4j_driver._pool.address.host}:{neo4j_driver._pool.address.port}"  # type: ignore[attr-defined]
    # Recupera password dal driver auth provider (statico in testcontainer).
    # Testcontainers Neo4jContainer espone NEO4J_ADMIN_PASSWORD; lo riusiamo qui.
    from testcontainers.neo4j import Neo4jContainer

    password = getattr(Neo4jContainer, "NEO4J_ADMIN_PASSWORD", "neo4j")
    return uri, ("neo4j", password)


def _run_bootstrap(uri: str, auth: tuple[str, str]) -> subprocess.CompletedProcess[str]:
    """Esegue lo script bootstrap come subprocess (parallelo al pattern qdrant)."""
    return subprocess.run(
        [
            sys.executable,
            str(BOOTSTRAP_SCRIPT),
            "--neo4j-uri",
            uri,
            "--neo4j-auth",
            f"{auth[0]}/{auth[1]}",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_ROOT),
    )


@pytest.mark.integration
async def test_constraints_idempotent(neo4j_driver) -> None:
    """KNW-08: bootstrap crea 4 unique constraints + 1 index, idempotente."""
    uri, auth = _driver_uri_and_auth(neo4j_driver)

    # Primo run — crea tutto.
    first = _run_bootstrap(uri, auth)
    assert first.returncode == 0, (
        f"bootstrap first run failed: stdout={first.stdout!r} "
        f"stderr={first.stderr!r}"
    )

    # Verifica constraint via SHOW CONSTRAINTS.
    async with neo4j_driver.session(database="neo4j") as session:
        result = await session.run("SHOW CONSTRAINTS")
        records = [r async for r in result]

    names = {r["name"] for r in records}
    missing = EXPECTED_CONSTRAINTS - names
    assert not missing, (
        f"missing constraints after first bootstrap: {missing} (present: {names})"
    )

    # Verifica index via SHOW INDEXES.
    async with neo4j_driver.session(database="neo4j") as session:
        result = await session.run(
            "SHOW INDEXES YIELD name WHERE name = $name RETURN name",
            name=EXPECTED_INDEX,
        )
        idx_records = [r async for r in result]
    assert len(idx_records) == 1, (
        f"expected exactly 1 index named {EXPECTED_INDEX}, got {idx_records!r}"
    )

    # Conta i constraint prima del secondo run.
    constraints_before = len(names & EXPECTED_CONSTRAINTS)

    # Secondo run — idempotenza: nessuna eccezione, nessun cambio.
    second = _run_bootstrap(uri, auth)
    assert second.returncode == 0, (
        f"bootstrap second run failed: stdout={second.stdout!r} "
        f"stderr={second.stderr!r}"
    )

    async with neo4j_driver.session(database="neo4j") as session:
        result = await session.run("SHOW CONSTRAINTS")
        records_after = [r async for r in result]
    names_after = {r["name"] for r in records_after}
    constraints_after = len(names_after & EXPECTED_CONSTRAINTS)

    assert constraints_after == constraints_before, (
        f"constraint count changed across runs: "
        f"before={constraints_before} after={constraints_after}"
    )


@pytest.mark.integration
async def test_apoc_available(neo4j_driver) -> None:
    """KNW-08: APOC plugin callable on the testcontainer Neo4j 5.24."""
    async with neo4j_driver.session(database="neo4j") as session:
        result = await session.run(
            "CALL apoc.help('apoc') YIELD core RETURN count(*) AS n"
        )
        record = await result.single()

    assert record is not None, "apoc.help returned no rows"
    assert record["n"] > 0, (
        f"APOC unavailable: apoc.help returned n={record['n']} "
        "(check NEO4J_PLUGINS env in compose/testcontainer)"
    )


# ---------------------------------------------------------------------------
# Plan 05-08 stubs — Neo4jGraphBuilder + graph CI validator.
# ---------------------------------------------------------------------------


def test_graph_ci_validator() -> None:
    """KNW-08 SC#4 stub — implemented in Plan 05-08 (graph schema validator)."""
    pytest.skip("Implemented in Plan 05-08")


def test_merge_sop_idempotent() -> None:
    """KNW-08 stub — implemented in Plan 05-08 (Neo4jGraphBuilder.merge_sop)."""
    pytest.skip("Implemented in Plan 05-08")
