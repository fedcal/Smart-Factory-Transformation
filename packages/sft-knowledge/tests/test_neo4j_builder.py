# Covers KNW-08 SC#4 (graph CI validator) + Plan 05-08 Neo4jGraphBuilder per 05-VALIDATION.md
"""Plan 05-05 (bootstrap + APOC) + Plan 05-08 (Neo4jGraphBuilder) integration tests.

Integration tests require Docker (testcontainers) and are gated by
``@pytest.mark.integration``. The static source-scan test
``test_cypher_no_data_fstring`` is a unit test (no Docker).
"""

from __future__ import annotations

import pathlib
import re
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


def _connection_params(
    request: pytest.FixtureRequest,
) -> tuple[str, tuple[str, str]]:
    """Recupera URI + auth dal testcontainer Neo4j (stashed da conftest fixture)."""
    uri = getattr(request.config, "_neo4j_uri", None)
    user = getattr(request.config, "_neo4j_user", None)
    password = getattr(request.config, "_neo4j_password", None)
    if not uri or not user or not password:
        pytest.fail(
            "neo4j_driver fixture did not publish _neo4j_uri/_user/_password "
            "on request.config — conftest fixture broken"
        )
    return uri, (user, password)


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


async def _wipe_graph(driver) -> None:
    """Cancella tutti i nodi/relazioni — usato prima di ogni integration test."""
    async with driver.session(database="neo4j") as session:
        await session.run("MATCH (n) DETACH DELETE n")


# ---------------------------------------------------------------------------
# Plan 05-05 bootstrap + APOC tests (unchanged).
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_constraints_idempotent(
    neo4j_driver, request: pytest.FixtureRequest
) -> None:
    """KNW-08: bootstrap crea 4 unique constraints + 1 index, idempotente."""
    uri, auth = _connection_params(request)

    first = _run_bootstrap(uri, auth)
    assert first.returncode == 0, (
        f"bootstrap first run failed: stdout={first.stdout!r} "
        f"stderr={first.stderr!r}"
    )

    async with neo4j_driver.session(database="neo4j") as session:
        result = await session.run("SHOW CONSTRAINTS")
        records = [r async for r in result]

    names = {r["name"] for r in records}
    missing = EXPECTED_CONSTRAINTS - names
    assert not missing, (
        f"missing constraints after first bootstrap: {missing} (present: {names})"
    )

    async with neo4j_driver.session(database="neo4j") as session:
        result = await session.run(
            "SHOW INDEXES YIELD name WHERE name = $name RETURN name",
            name=EXPECTED_INDEX,
        )
        idx_records = [r async for r in result]
    assert len(idx_records) == 1, (
        f"expected exactly 1 index named {EXPECTED_INDEX}, got {idx_records!r}"
    )

    constraints_before = len(names & EXPECTED_CONSTRAINTS)

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
@pytest.mark.asyncio(loop_scope="session")
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
# Plan 05-08 Task 2 — Neo4jGraphBuilder unit test (no Docker).
# ---------------------------------------------------------------------------


def test_cypher_no_data_fstring() -> None:
    """T-05-08-01 mitigation: no f-string interpolates data property values.

    Le label (Machine, Part, FailureMode, SOP) sono costanti modulo: ammettiamo
    le come stringhe fisse nelle Cypher constants. Vietato qualsiasi
    `f"... {var} ..."` dove `var` è un argomento (sop_id, source_uri, version,
    chunk_idx, ecc.).
    """
    src = (
        WORKSPACE_ROOT
        / "packages"
        / "sft-knowledge"
        / "src"
        / "sft_knowledge"
        / "stores"
        / "neo4j.py"
    ).read_text(encoding="utf-8")

    forbidden = re.compile(
        r'f"[^"]*\{(sop_id|source_uri|version|chunk_idx|content_hash|name_it|name_en|severity|id)\}'
    )
    matches = forbidden.findall(src)
    assert not matches, (
        f"data-value f-string found in stores/neo4j.py (Cypher injection risk): {matches!r}"
    )

    # Triple-quoted Cypher constants devono essere stringhe normali ("\"\"\"" o "'''"),
    # NON f-string: verifichiamo che NON ci sia un f-string multi-line.
    f_triple = re.compile(r'f"""', re.MULTILINE)
    assert not f_triple.search(src), (
        "f-string triple-quote rilevata in stores/neo4j.py — Cypher constants "
        "non devono usare f-string"
    )


# ---------------------------------------------------------------------------
# Plan 05-08 Task 2 — Neo4jGraphBuilder integration tests.
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_merge_machines_idempotent(
    neo4j_driver, request: pytest.FixtureRequest
) -> None:
    """D-65: merge_machines_from_assets eseguito due volte → nessun duplicato."""
    from sft_assets import load_assets

    from sft_knowledge.stores.neo4j import Neo4jGraphBuilder

    uri, auth = _connection_params(request)
    boot = _run_bootstrap(uri, auth)
    assert boot.returncode == 0, f"bootstrap failed: {boot.stderr!r}"

    await _wipe_graph(neo4j_driver)

    assets = load_assets()
    expected_count = len(assets)
    builder = Neo4jGraphBuilder(driver=neo4j_driver)

    await builder.merge_machines_from_assets(assets)
    async with neo4j_driver.session(database="neo4j") as session:
        r = await session.run("MATCH (m:Machine) RETURN count(m) AS n")
        n1 = (await r.single())["n"]
    assert n1 == expected_count, (
        f"prima MERGE: attesi {expected_count} Machine, trovati {n1}"
    )

    # Re-MERGE → idempotenza.
    await builder.merge_machines_from_assets(assets)
    async with neo4j_driver.session(database="neo4j") as session:
        r = await session.run("MATCH (m:Machine) RETURN count(m) AS n")
        n2 = (await r.single())["n"]
    assert n2 == n1, f"re-MERGE non idempotente: prima={n1} dopo={n2}"


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_merge_failure_modes_idempotent(
    neo4j_driver, request: pytest.FixtureRequest
) -> None:
    """D-65: merge_failure_modes due volte → nessun duplicato di node/edge."""
    from sft_domain.failure_modes._loader import load_failure_modes

    from sft_knowledge.stores.neo4j import Neo4jGraphBuilder

    uri, auth = _connection_params(request)
    boot = _run_bootstrap(uri, auth)
    assert boot.returncode == 0

    await _wipe_graph(neo4j_driver)

    fms = load_failure_modes()
    expected_count = len(fms)
    builder = Neo4jGraphBuilder(driver=neo4j_driver)

    await builder.merge_failure_modes(fms)
    async with neo4j_driver.session(database="neo4j") as session:
        r = await session.run("MATCH (f:FailureMode) RETURN count(f) AS n")
        n1 = (await r.single())["n"]
        r = await session.run("MATCH (p:Part) RETURN count(p) AS n")
        p1 = (await r.single())["n"]
        r = await session.run(
            "MATCH (:Part)-[h:HAS_FAILURE_MODE]->(:FailureMode) RETURN count(h) AS n"
        )
        e1 = (await r.single())["n"]
    assert n1 == expected_count, (
        f"prima MERGE: attesi {expected_count} FailureMode, trovati {n1}"
    )
    assert p1 > 0, "no Part nodes created"
    assert e1 > 0, "no HAS_FAILURE_MODE edges created"

    await builder.merge_failure_modes(fms)
    async with neo4j_driver.session(database="neo4j") as session:
        r = await session.run("MATCH (f:FailureMode) RETURN count(f) AS n")
        n2 = (await r.single())["n"]
        r = await session.run("MATCH (p:Part) RETURN count(p) AS n")
        p2 = (await r.single())["n"]
        r = await session.run(
            "MATCH (:Part)-[h:HAS_FAILURE_MODE]->(:FailureMode) RETURN count(h) AS n"
        )
        e2 = (await r.single())["n"]
    assert (n2, p2, e2) == (n1, p1, e1), (
        f"re-MERGE non idempotente: prima=({n1},{p1},{e1}) dopo=({n2},{p2},{e2})"
    )


def _build_parsed_doc():
    """Costruisce un ParsedDoc minimale per i test SOP."""
    from sft_knowledge.parsers.base import ParsedDoc, ParsedSection

    return ParsedDoc(
        source_uri="file://sop/SOP-LOOM-001-v1.md",
        frontmatter={
            "id": "SOP-LOOM-001",
            "title": "Risoluzione rottura filo ordito",
            "acl_level": "public",
            "asset_family": "weaving",
        },
        sections=[
            ParsedSection(heading_path=["Procedura"], text="step1"),
        ],
        version="1.0",
        lang="it",
    )


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_merge_sop_creates_documented_by_edge(
    neo4j_driver, request: pytest.FixtureRequest
) -> None:
    """D-65 + KNW-08 SC#4: merge_sop crea SOP + DOCUMENTED_BY edge."""
    from sft_domain.failure_modes._loader import load_failure_modes

    from sft_knowledge.stores.neo4j import Neo4jGraphBuilder

    uri, auth = _connection_params(request)
    boot = _run_bootstrap(uri, auth)
    assert boot.returncode == 0

    await _wipe_graph(neo4j_driver)

    builder = Neo4jGraphBuilder(driver=neo4j_driver)
    # Prerequisito: FailureMode broken_end deve esistere prima di linkare.
    await builder.merge_failure_modes(load_failure_modes())

    parsed = _build_parsed_doc()
    n_links = await builder.merge_sop(parsed, failure_mode_ids=["broken_end"])
    assert n_links >= 1, "merge_sop non ha riportato edge creati"

    async with neo4j_driver.session(database="neo4j") as session:
        r = await session.run(
            "MATCH (f:FailureMode {id:'broken_end'})-[:DOCUMENTED_BY]->(s:SOP) "
            "RETURN count(s) AS n, collect(s.id)[0] AS sid"
        )
        rec = await r.single()
    assert rec["n"] >= 1, "nessuna edge DOCUMENTED_BY trovata"


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_sop_id_includes_version(
    neo4j_driver, request: pytest.FixtureRequest
) -> None:
    """D-69 multi-version: SOP.id = '{frontmatter.id}@{version}'."""
    from sft_knowledge.stores.neo4j import Neo4jGraphBuilder

    uri, auth = _connection_params(request)
    boot = _run_bootstrap(uri, auth)
    assert boot.returncode == 0

    await _wipe_graph(neo4j_driver)

    builder = Neo4jGraphBuilder(driver=neo4j_driver)
    parsed = _build_parsed_doc()
    await builder.merge_sop(parsed, failure_mode_ids=[])

    async with neo4j_driver.session(database="neo4j") as session:
        r = await session.run("MATCH (s:SOP) RETURN s.id AS sid")
        rec = await r.single()
    assert rec is not None, "no SOP node created"
    pattern = re.compile(r".+@\d+(\.\d+)*$")
    assert pattern.match(rec["sid"]), (
        f"SOP.id non in formato '<id>@<version>': {rec['sid']!r}"
    )


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_graph_ci_validator(
    neo4j_driver, request: pytest.FixtureRequest
) -> None:
    """KNW-08 SC#4: ogni FailureMode coperto ha ≥1 DOCUMENTED_BY edge a SOP.

    Pre-popola Machine + FailureMode, poi merge un set di SOP simulate
    (una per ciascun id failure mode). Esegue il validator:
        MATCH (f:FailureMode) WHERE NOT (f)-[:DOCUMENTED_BY]->(:SOP)
        RETURN f.id AS orphan
    → deve essere vuoto.
    """
    from sft_assets import load_assets
    from sft_domain.failure_modes._loader import load_failure_modes

    from sft_knowledge.parsers.base import ParsedDoc, ParsedSection
    from sft_knowledge.stores.neo4j import Neo4jGraphBuilder

    uri, auth = _connection_params(request)
    boot = _run_bootstrap(uri, auth)
    assert boot.returncode == 0

    await _wipe_graph(neo4j_driver)

    builder = Neo4jGraphBuilder(driver=neo4j_driver)
    await builder.merge_machines_from_assets(load_assets())
    fms = load_failure_modes()
    await builder.merge_failure_modes(fms)

    # Crea una SOP simulata per ciascun FailureMode.
    for fm in fms:
        parsed = ParsedDoc(
            source_uri=f"file://sop/SOP-{fm.id}.md",
            frontmatter={
                "id": f"SOP-{fm.id}",
                "title": f"Procedura {fm.name_it}",
                "acl_level": "public",
            },
            sections=[ParsedSection(heading_path=["X"], text="body")],
            version="1.0",
            lang="it",
        )
        await builder.merge_sop(parsed, failure_mode_ids=[fm.id])

    async with neo4j_driver.session(database="neo4j") as session:
        r = await session.run(
            "MATCH (f:FailureMode) "
            "WHERE NOT (f)-[:DOCUMENTED_BY]->(:SOP) "
            "RETURN collect(f.id) AS orphans"
        )
        rec = await r.single()
    orphans = rec["orphans"] if rec else []
    assert not orphans, (
        f"KNW-08 SC#4 violato: FailureMode orfani (no SOP): {orphans}"
    )


# ---------------------------------------------------------------------------
# Plan 05-08 Task 3 — dual-write atomicity (Neo4j-first per Pattern 1).
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_dual_write_neo4j_first_atomicity(
    neo4j_driver, qdrant_client, request: pytest.FixtureRequest
) -> None:
    """PATTERNS Pattern 1: Neo4j-first MERGE, poi Qdrant upsert; FK consistency.

    1. merge_machines + merge_failure_modes + merge_sop su Neo4j.
    2. Costruisce Chunk per la stessa SOP con metadata sop_id == frontmatter.id
       (logical FK; il payload.sop_id Qdrant non include la version per
       compatibilità con i lookup, mentre SOP.id Neo4j include @{version}).
    3. Upsert Qdrant.
    4. Verifica che il payload.sop_id == parsed.frontmatter['id'] e che il
       SOP.id Neo4j inizia con la stessa stringa.
    """
    import numpy as np
    from qdrant_client.http.models import SparseVector

    from sft_domain.failure_modes._loader import load_failure_modes

    from sft_knowledge.chunking.semantic import Chunk
    from sft_knowledge.stores.neo4j import Neo4jGraphBuilder
    from sft_knowledge.stores.qdrant import QdrantIndexer

    # Bootstrap Qdrant (gli unit test possono averlo già fatto, ma idempotente).
    qdrant_url = getattr(request.config, "_qdrant_url", None)
    assert qdrant_url, "qdrant_client fixture missing _qdrant_url"
    qd_boot = subprocess.run(
        [sys.executable, str(WORKSPACE_ROOT / "scripts" / "qdrant-bootstrap.py"),
         "--qdrant-url", qdrant_url],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_ROOT),
    )
    assert qd_boot.returncode == 0

    uri, auth = _connection_params(request)
    neo_boot = _run_bootstrap(uri, auth)
    assert neo_boot.returncode == 0

    await _wipe_graph(neo4j_driver)

    # === FASE 1: Neo4j first ===
    builder = Neo4jGraphBuilder(driver=neo4j_driver)
    await builder.merge_failure_modes(load_failure_modes())
    parsed = _build_parsed_doc()
    await builder.merge_sop(parsed, failure_mode_ids=["broken_end"])

    async with neo4j_driver.session(database="neo4j") as session:
        r = await session.run(
            "MATCH (s:SOP) WHERE s.id STARTS WITH $prefix RETURN s.id AS sid",
            prefix=parsed.frontmatter["id"],
        )
        rec = await r.single()
    assert rec is not None, "SOP non creato in Neo4j"
    neo4j_sop_id = rec["sid"]

    # === FASE 2: Qdrant upsert ===
    # Reset collection sop.
    await qdrant_client.delete(
        collection_name="sop",
        points_selector={"filter": {"must": []}},
        wait=True,
    )

    indexer = QdrantIndexer(client=qdrant_client, collection="sop")
    chunks = [
        Chunk(
            text=section.text,
            chunk_idx=i,
            heading_path=list(section.heading_path),
            metadata={
                "source_uri": parsed.source_uri,
                "version": parsed.version,
                "lang": parsed.lang,
                "acl_level": parsed.frontmatter["acl_level"],
                "asset_family": parsed.frontmatter["asset_family"],
                "sop_id": parsed.frontmatter["id"],
            },
        )
        for i, section in enumerate(parsed.sections)
    ]
    dense = [np.zeros(1024) for _ in chunks]
    sparse = [SparseVector(indices=[0], values=[0.0]) for _ in chunks]
    await indexer.upsert_batch(chunks, dense, sparse)

    # === FASE 3: verifica FK consistency Qdrant.sop_id ↔ Neo4j SOP.id prefix ===
    points, _ = await qdrant_client.scroll(
        collection_name="sop",
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    assert points, "no Qdrant points after upsert"
    payload = points[0].payload or {}
    assert payload["sop_id"] == parsed.frontmatter["id"]
    assert neo4j_sop_id.startswith(parsed.frontmatter["id"]), (
        f"FK divergente: Neo4j {neo4j_sop_id!r} non inizia con "
        f"Qdrant.sop_id {parsed.frontmatter['id']!r}"
    )
