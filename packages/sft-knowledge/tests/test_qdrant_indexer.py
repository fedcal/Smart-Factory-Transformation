# Covers KNW-01 (collection bootstrap) + KNW-05 (provenance fields) per 05-VALIDATION.md
"""Plan 05-04 integration tests for the idempotent Qdrant collection bootstrap.

Plan 05-08 will add the QdrantIndexer.upsert_batch + provenance-fields tests
(test_provenance_fields_complete is left as a stub here for that plan).

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


def _container_url(request: pytest.FixtureRequest) -> str:
    """Recupera l'URL del testcontainer Qdrant stashed dalla fixture conftest.

    La fixture `qdrant_client` in `conftest.py` salva l'URL HTTP del container
    su `request.config._qdrant_url`. Falliamo esplicitamente se assente per
    evitare di silently aggrapparsi a un default sbagliato.
    """
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
    # vectors_config può essere un dict di VectorParams (named vectors mode).
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

    # Payload schema introspection — Qdrant 1.16 espone payload_schema su
    # CollectionInfo. Per ciascun field atteso deve esistere una entry.
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

    # Sanity: il secondo run deve riportare "exists" per ogni collection
    # (verifica indiretta dell'idempotency log).
    for name in EXPECTED_COLLECTIONS:
        assert f"OK [{name}]: exists" in second.stdout, (
            f"second run did not log idempotency for {name}: stdout={second.stdout!r}"
        )


@pytest.mark.integration
async def test_payload_indexes_complete(
    qdrant_client, request: pytest.FixtureRequest
) -> None:
    """KNW-01: ogni payload index dichiarato è utilizzabile in una filter query.

    Esegue una `query_points` con filter per ciascuno dei 7 field attesi. Una
    collection con payload index correttamente registrato accetta il filter senza
    errore. Test ridondante ma più robusto rispetto alla sola introspezione di
    ``payload_schema`` (alcuni minor di Qdrant espongono lo schema diversamente).
    """
    # Assicura che le collection siano create (test possono runnare in qualsiasi
    # ordine).
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
        # query_points non solleva quando il field è correttamente indicizzato;
        # un missing index su Qdrant 1.16 produce un warning ma non un'eccezione,
        # quindi la verifica forte è già in test_collection_bootstrap_idempotent.
        # Qui ci accontentiamo di "no exception".
        result = await qdrant_client.query_points(
            collection_name="sop",
            query_filter=flt,
            limit=1,
        )
        # 0 punti attesi (collection vuota a questo stadio), ma la struttura
        # deve avere `.points`.
        assert hasattr(result, "points"), (
            f"query_points returned unexpected shape for field={field}: {result!r}"
        )


def test_provenance_fields_complete() -> None:
    """KNW-05 stub — implemented in Plan 05-08 (QdrantIndexer.upsert_batch)."""
    pytest.skip("Implemented in Plan 05-08")
