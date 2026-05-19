# Covers KNW-01 (collection bootstrap) + KNW-05 (provenance fields) per 05-VALIDATION.md
"""Plan 05-04 + Plan 05-08 integration/unit tests for the Qdrant bootstrap +
QdrantIndexer (batch upsert, deterministic point.id, full provenance payload,
idempotency, delete-by-source).

These tests require Docker (testcontainers) for the integration markers; they
are excluded from the quick CI lane and run only when the integration suite is
invoked. Unit tests (`point_id_*`, `upsert_validates_*`, `batch_size_respected`)
run without Docker.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import pathlib
import re
import subprocess
import sys
from typing import Any
from unittest.mock import AsyncMock

import numpy as np
import pytest

# Workspace root = .../<repo>/  (this file lives at packages/sft-knowledge/tests/)
WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[3]
BOOTSTRAP_SCRIPT = WORKSPACE_ROOT / "scripts" / "qdrant-bootstrap.py"

EXPECTED_COLLECTIONS = {"sop", "manuals", "troubleshooting", "training"}
EXPECTED_PAYLOAD_INDEXES = {
    "source_uri",
    "acl_level",
    "lang",
    "category",
    "version",
    "asset_family",
    "sop_id",
}
EXPECTED_DENSE_DIM = 1024

# KNW-05 SC#5 — provenance fields obbligatori in ciascun payload upserted.
REQUIRED_PAYLOAD_FIELDS = {
    "text",
    "source_uri",
    "chunk_idx",
    "version",
    "lang",
    "acl_level",
    "asset_family",
    "sop_id",
    "category",
    "heading_path",
    "created_at",
}

UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _container_url(request: pytest.FixtureRequest) -> str:
    """Recupera l'URL del testcontainer Qdrant stashed dalla fixture conftest."""
    url = getattr(request.config, "_qdrant_url", None)
    if not url:
        pytest.fail(
            "qdrant_client fixture did not publish _qdrant_url on request.config "
            "— conftest fixture broken"
        )
    return url


def _run_bootstrap(url: str) -> subprocess.CompletedProcess[str]:
    """Esegue lo script bootstrap come subprocess (Approach A del PLAN)."""
    return subprocess.run(
        [sys.executable, str(BOOTSTRAP_SCRIPT), "--qdrant-url", url],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_ROOT),
    )


@pytest.mark.integration
async def test_collection_bootstrap_idempotent(
    qdrant_client, request: pytest.FixtureRequest
) -> None:
    """KNW-01: bootstrap crea le 4 collection al primo run, no-op ai run successivi."""
    url = _container_url(request)

    # Primo run — crea tutto.
    first = _run_bootstrap(url)
    assert first.returncode == 0, (
        f"bootstrap first run failed: stdout={first.stdout!r} "
        f"stderr={first.stderr!r}"
    )

    colls = {c.name for c in (await qdrant_client.get_collections()).collections}
    assert colls == EXPECTED_COLLECTIONS, (
        f"expected {EXPECTED_COLLECTIONS}, got {colls}"
    )

    # Verifica config della collection `sop` (rappresentativa — tutte usano lo
    # stesso template).
    from qdrant_client.http.models import Distance

    info = await qdrant_client.get_collection("sop")
    vectors_cfg = info.config.params.vectors
    assert "dense" in vectors_cfg, (
        f"named vector 'dense' missing from sop collection config: {vectors_cfg!r}"
    )
    dense_params = vectors_cfg["dense"]
    assert dense_params.size == EXPECTED_DENSE_DIM, (
        f"dense vector size: expected {EXPECTED_DENSE_DIM}, got {dense_params.size}"
    )
    assert dense_params.distance == Distance.COSINE, (
        f"dense vector distance: expected COSINE, got {dense_params.distance}"
    )

    sparse_cfg = info.config.params.sparse_vectors
    assert sparse_cfg and "sparse" in sparse_cfg, (
        f"named sparse vector 'sparse' missing from sop collection: {sparse_cfg!r}"
    )

    payload_schema = info.payload_schema or {}
    indexed_fields = set(payload_schema.keys())
    missing = EXPECTED_PAYLOAD_INDEXES - indexed_fields
    assert not missing, (
        f"missing payload indexes on sop collection: {missing} "
        f"(present: {indexed_fields})"
    )

    # Secondo run — idempotenza: nessuna eccezione, nessun cambio.
    second = _run_bootstrap(url)
    assert second.returncode == 0, (
        f"bootstrap second run failed: stdout={second.stdout!r} "
        f"stderr={second.stderr!r}"
    )

    colls_after = {
        c.name for c in (await qdrant_client.get_collections()).collections
    }
    assert colls_after == colls, (
        f"collection set changed between runs: before={colls} after={colls_after}"
    )

    for name in EXPECTED_COLLECTIONS:
        assert f"OK [{name}]: exists" in second.stdout, (
            f"second run did not log idempotency for {name}: stdout={second.stdout!r}"
        )


@pytest.mark.integration
async def test_payload_indexes_complete(
    qdrant_client, request: pytest.FixtureRequest
) -> None:
    """KNW-01: ogni payload index dichiarato è utilizzabile in una filter query."""
    url = _container_url(request)
    boot = _run_bootstrap(url)
    assert boot.returncode == 0, (
        f"bootstrap pre-step failed: stdout={boot.stdout!r} stderr={boot.stderr!r}"
    )

    from qdrant_client.http.models import FieldCondition, Filter, MatchValue

    for field in EXPECTED_PAYLOAD_INDEXES:
        flt = Filter(
            must=[FieldCondition(key=field, match=MatchValue(value="dummy"))],
        )
        result = await qdrant_client.query_points(
            collection_name="sop",
            query_filter=flt,
            limit=1,
        )
        assert hasattr(result, "points"), (
            f"query_points returned unexpected shape for field={field}: {result!r}"
        )


# ---------------------------------------------------------------------------
# Plan 05-08 — QdrantIndexer unit tests (no Docker)
# ---------------------------------------------------------------------------


def test_point_id_deterministic() -> None:
    """RESEARCH §9 Risk 6: stessi input → stesso point_id."""
    from sft_knowledge.stores.qdrant import point_id

    a = point_id("file://sop/x.md", 0, "hello world")
    b = point_id("file://sop/x.md", 0, "hello world")
    assert a == b, f"point_id non deterministico: {a!r} != {b!r}"

    # Input diversi → output diverso.
    c = point_id("file://sop/x.md", 1, "hello world")
    assert a != c, "chunk_idx diverso deve produrre point_id diverso"


def test_point_id_uuid_format() -> None:
    """RESEARCH §9 Risk 6: output deve avere formato UUID 8-4-4-4-12."""
    from sft_knowledge.stores.qdrant import point_id

    out = point_id("file://sop/x.md", 0, "hello world")
    assert UUID_REGEX.match(out), (
        f"point_id non in formato UUID 8-4-4-4-12: {out!r}"
    )


def test_upsert_validates_input_lengths() -> None:
    """ValueError se len(chunks) != len(dense_vecs) o != len(sparse_vecs)."""
    from qdrant_client.http.models import SparseVector

    from sft_knowledge.chunking.semantic import Chunk
    from sft_knowledge.stores.qdrant import QdrantIndexer

    indexer = QdrantIndexer(client=AsyncMock(), collection="sop")

    chunks = [
        Chunk(text="x", chunk_idx=0, heading_path=[], metadata={}),
        Chunk(text="y", chunk_idx=1, heading_path=[], metadata={}),
    ]
    dense = [np.zeros(4)]  # length mismatch
    sparse = [
        SparseVector(indices=[0], values=[0.0]),
        SparseVector(indices=[0], values=[0.0]),
    ]

    with pytest.raises(ValueError, match="length"):
        asyncio.run(indexer.upsert_batch(chunks, dense, sparse))


def test_batch_size_respected() -> None:
    """250 chunk → 3 batch (100+100+50) sul mock client.upsert."""
    from qdrant_client.http.models import SparseVector

    from sft_knowledge.chunking.semantic import Chunk
    from sft_knowledge.stores.qdrant import QdrantIndexer

    client = AsyncMock()
    indexer = QdrantIndexer(client=client, collection="sop", batch_size=100)

    n = 250
    chunks = [
        Chunk(
            text=f"text-{i}",
            chunk_idx=i,
            heading_path=["H1"],
            metadata={
                "source_uri": "file://sop/x.md",
                "version": "1.0",
                "lang": "it",
                "acl_level": "public",
                "asset_family": "weaving",
                "sop_id": "SOP-LOOM-001",
            },
        )
        for i in range(n)
    ]
    dense = [np.zeros(1024) for _ in range(n)]
    sparse = [SparseVector(indices=[0], values=[0.0]) for _ in range(n)]

    total = asyncio.run(indexer.upsert_batch(chunks, dense, sparse))
    assert total == n, f"expected {n} upserts, got {total}"

    # 3 batch attesi: 100 + 100 + 50.
    assert client.upsert.await_count == 3, (
        f"expected 3 batches, got {client.upsert.await_count}"
    )
    call_sizes = [len(call.kwargs["points"]) for call in client.upsert.await_args_list]
    assert call_sizes == [100, 100, 50], f"unexpected batch sizes: {call_sizes}"


# ---------------------------------------------------------------------------
# Plan 05-08 — QdrantIndexer integration tests (testcontainer Qdrant)
# ---------------------------------------------------------------------------


def _make_chunk(
    idx: int,
    *,
    text: str | None = None,
    source_uri: str = "file://sop/SOP-LOOM-001-v1.md",
    version: str = "1.0",
    sop_id: str = "SOP-LOOM-001",
) -> Any:
    """Costruisce un Chunk con metadata KNW-05 completa."""
    from sft_knowledge.chunking.semantic import Chunk

    return Chunk(
        text=text or f"chunk text {idx}",
        chunk_idx=idx,
        heading_path=["Procedure", f"Step {idx}"],
        metadata={
            "source_uri": source_uri,
            "version": version,
            "lang": "it",
            "acl_level": "public",
            "asset_family": "weaving",
            "sop_id": sop_id,
        },
    )


@pytest.mark.integration
async def test_provenance_fields_complete(
    qdrant_client, request: pytest.FixtureRequest
) -> None:
    """KNW-05 SC#5: ogni payload upserted contiene tutti i provenance field."""
    from qdrant_client.http.models import SparseVector

    from sft_knowledge.stores.qdrant import QdrantIndexer

    url = _container_url(request)
    boot = _run_bootstrap(url)
    assert boot.returncode == 0, f"bootstrap failed: {boot.stderr!r}"

    indexer = QdrantIndexer(client=qdrant_client, collection="sop")
    chunks = [_make_chunk(i) for i in range(3)]
    dense = [np.zeros(EXPECTED_DENSE_DIM) for _ in range(3)]
    sparse = [SparseVector(indices=[1], values=[0.5]) for _ in range(3)]

    n = await indexer.upsert_batch(chunks, dense, sparse)
    assert n == 3

    # Scroll una manciata di punti per verificare il payload schema.
    points, _ = await qdrant_client.scroll(
        collection_name="sop",
        limit=3,
        with_payload=True,
        with_vectors=False,
    )
    assert len(points) >= 1, "no points in collection after upsert"

    for p in points:
        payload = p.payload or {}
        missing = REQUIRED_PAYLOAD_FIELDS - set(payload.keys())
        assert not missing, (
            f"payload missing KNW-05 fields: {missing} (have: {set(payload.keys())})"
        )
        # created_at deve essere parseable come ISO con tz.
        parsed = _dt.datetime.fromisoformat(payload["created_at"])
        assert parsed.tzinfo is not None, (
            f"created_at non tz-aware: {payload['created_at']!r}"
        )
        # category inferita dalla collection name.
        assert payload["category"] == "sop"
        # source_uri / sop_id non vuoti.
        assert payload["source_uri"]
        assert payload["sop_id"]


@pytest.mark.integration
async def test_upsert_idempotent(
    qdrant_client, request: pytest.FixtureRequest
) -> None:
    """D-69: re-upsert dello stesso chunk → point.id identico → no duplicati."""
    from qdrant_client.http.models import SparseVector

    from sft_knowledge.stores.qdrant import QdrantIndexer, point_id

    url = _container_url(request)
    boot = _run_bootstrap(url)
    assert boot.returncode == 0

    # Usa una collection separata per evitare contamination tra test.
    collection = "manuals"
    indexer = QdrantIndexer(client=qdrant_client, collection=collection)

    chunk = _make_chunk(
        7,
        text="idempotent text",
        source_uri="file://manuals/idempotent.md",
        sop_id="MAN-001",
    )
    dense = [np.zeros(EXPECTED_DENSE_DIM)]
    sparse = [SparseVector(indices=[0], values=[0.0])]

    expected_id = point_id(chunk.metadata["source_uri"], chunk.chunk_idx, chunk.text)

    await indexer.upsert_batch([chunk], dense, sparse)
    # Conta dopo il primo upsert.
    info_1 = await qdrant_client.count(
        collection_name=collection,
        exact=True,
    )

    # Re-upsert identico.
    await indexer.upsert_batch([chunk], dense, sparse)
    info_2 = await qdrant_client.count(
        collection_name=collection,
        exact=True,
    )

    assert info_2.count == info_1.count, (
        f"re-upsert non idempotent: prima={info_1.count} dopo={info_2.count}"
    )

    # Recupera il punto via id deterministico.
    retrieved = await qdrant_client.retrieve(
        collection_name=collection,
        ids=[expected_id],
        with_payload=True,
    )
    assert len(retrieved) == 1, f"point id deterministico non trovato: {expected_id!r}"


@pytest.mark.integration
async def test_delete_by_source_uri_version(
    qdrant_client, request: pytest.FixtureRequest
) -> None:
    """D-69 version-change purge: delete by source_uri+version rimuove tutti i punti."""
    from qdrant_client.http.models import SparseVector

    from sft_knowledge.stores.qdrant import QdrantIndexer

    url = _container_url(request)
    boot = _run_bootstrap(url)
    assert boot.returncode == 0

    collection = "troubleshooting"
    indexer = QdrantIndexer(client=qdrant_client, collection=collection)

    chunks = [
        _make_chunk(
            i,
            text=f"version1 chunk {i}",
            source_uri="file://troub/delete-me.md",
            version="1.0",
            sop_id="DEL-001",
        )
        for i in range(5)
    ]
    dense = [np.zeros(EXPECTED_DENSE_DIM) for _ in range(5)]
    sparse = [SparseVector(indices=[0], values=[0.0]) for _ in range(5)]
    await indexer.upsert_batch(chunks, dense, sparse)

    before = (await qdrant_client.count(collection_name=collection, exact=True)).count
    assert before >= 5

    n_deleted = await indexer.delete_by_source_uri_version(
        "file://troub/delete-me.md", "1.0"
    )
    assert n_deleted >= 0  # Qdrant può ritornare il numero o 0 (best-effort).

    after = (await qdrant_client.count(collection_name=collection, exact=True)).count
    assert after == before - 5, (
        f"delete non rimuove esattamente 5 punti: prima={before} dopo={after}"
    )


# ---------------------------------------------------------------------------
# Plan 05-08 Task 3 — end-to-end provenance (KNW-05 gate)
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_end_to_end_provenance_completeness(
    qdrant_client, request: pytest.FixtureRequest
) -> None:
    """KNW-05 SC#5: parsa una SOP reale, costruisce Chunk reali, upsert in Qdrant,
    poi verifica che il payload del primo hit contenga tutti i provenance field.
    """
    from qdrant_client.http.models import SparseVector

    from sft_knowledge.chunking.semantic import Chunk
    from sft_knowledge.parsers.markdown import MarkdownParser
    from sft_knowledge.stores.qdrant import QdrantIndexer

    url = _container_url(request)
    boot = _run_bootstrap(url)
    assert boot.returncode == 0

    sop_path = (
        WORKSPACE_ROOT
        / "simulators"
        / "synthetic-corpus"
        / "it"
        / "loom"
        / "SOP-LOOM-001-troubleshoot-broken-end-it.md"
    )
    assert sop_path.exists(), f"SOP fixture mancante: {sop_path}"

    parser = MarkdownParser()
    parsed = await parser.parse(sop_path)
    assert parsed is not None, "MarkdownParser ha ritornato None (status?)"

    # Per evitare la dipendenza dal modello BGE-M3 in CI, costruiamo Chunk
    # direttamente dalla parsed_doc (non passando per SemanticChunker, che è
    # già coperto da test propri).
    fm = parsed.frontmatter
    base_metadata = {
        "source_uri": parsed.source_uri,
        "version": parsed.version,
        "lang": parsed.lang,
        "acl_level": fm.get("acl_level", "internal"),
        "asset_family": str(fm.get("asset_family", "")),
        "sop_id": str(fm.get("id", "")),
    }
    chunks = [
        Chunk(
            text=section.text,
            chunk_idx=i,
            heading_path=list(section.heading_path),
            metadata=base_metadata,
        )
        for i, section in enumerate(parsed.sections)
    ]
    assert chunks, "no sections in parsed SOP"

    n = len(chunks)
    dense = [np.zeros(EXPECTED_DENSE_DIM) for _ in range(n)]
    sparse = [SparseVector(indices=[1], values=[0.0]) for _ in range(n)]

    # Reset collection sop per garantire che il primo hit sia il nostro.
    # Cancella tutti i punti via filter vuoto (delete-all idiomatico Qdrant 1.16).
    from qdrant_client.http.models import Filter as _Filter
    from qdrant_client.http.models import FilterSelector as _FilterSelector

    await qdrant_client.delete(
        collection_name="sop",
        points_selector=_FilterSelector(filter=_Filter(must=[])),
        wait=True,
    )

    indexer = QdrantIndexer(client=qdrant_client, collection="sop")
    upserted = await indexer.upsert_batch(chunks, dense, sparse)
    assert upserted == n

    points, _ = await qdrant_client.scroll(
        collection_name="sop",
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    assert len(points) >= 1

    payload = points[0].payload or {}
    missing = REQUIRED_PAYLOAD_FIELDS - set(payload.keys())
    assert not missing, (
        f"end-to-end payload manca KNW-05 fields: {missing} "
        f"(have: {set(payload.keys())})"
    )
    # created_at parseable + tz-aware (Shared Pattern 2).
    parsed_dt = _dt.datetime.fromisoformat(payload["created_at"])
    assert parsed_dt.tzinfo is not None
    # Tutti i field core sono non vuoti.
    for key in (
        "text",
        "source_uri",
        "version",
        "lang",
        "acl_level",
        "asset_family",
        "sop_id",
        "category",
    ):
        assert payload[key], f"payload[{key!r}] vuoto in end-to-end test"
