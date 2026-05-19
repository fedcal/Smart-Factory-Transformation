"""Integration tests for svc_knowledge_ingest.pipeline (Plan 05-10, Task 1).

Cover-matrix (per PLAN behavior block):
    test_reindex_idempotent             — KNW-07 SC#3: same content_hash → skipped
    test_ingest_state_tracked           — TRN-01: state row created with indexed_at
    test_content_hash_change_reingests  — modified file → re-ingest
    test_non_reviewed_skip              — status=draft → skipped, no writes
    test_neo4j_first_atomicity          — Qdrant failure leaves Neo4j written, state NOT upserted

All integration tests are marked ``@pytest.mark.integration`` (Docker required).
A pure unit smoke is included so `pytest -k unit` confirms the module imports.
"""

from __future__ import annotations

import asyncio
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Pipeline module under test (imported lazily inside tests when Docker-only).
from svc_knowledge_ingest import pipeline as pipeline_module
from svc_knowledge_ingest.pipeline import IngestResult, _infer_failure_mode_ids, ingest_file


# ---------------------------------------------------------------------------
# Unit-level smoke (no Docker).
# ---------------------------------------------------------------------------


def test_pipeline_module_exports() -> None:
    """Smoke: pipeline module exports IngestResult + ingest_file + _infer_failure_mode_ids."""
    assert hasattr(pipeline_module, "ingest_file")
    assert hasattr(pipeline_module, "IngestResult")
    assert hasattr(pipeline_module, "_infer_failure_mode_ids")


def test_ingest_result_is_frozen() -> None:
    """IngestResult is a frozen Pydantic v2 model."""
    res = IngestResult(skipped=True, reason="content_unchanged")
    assert res.skipped is True
    assert res.reason == "content_unchanged"
    # Frozen → assignment raises.
    with pytest.raises(Exception):
        res.skipped = False  # type: ignore[misc]


def test_infer_failure_mode_ids_matches_by_tag() -> None:
    """_infer_failure_mode_ids cross-references frontmatter tags with FailureMode names."""
    from sft_domain.failure_modes.models import FailureMode

    fms = (
        FailureMode(
            id="broken_end",
            name_it="rottura filo ordito",
            name_en="broken end",
            asset_families=["weaving"],
            parts=["warp"],
            severity="medium",
        ),
        FailureMode(
            id="slub",
            name_it="grumo",
            name_en="slub",
            asset_families=["spinning"],
            parts=["spindle"],
            severity="low",
        ),
    )
    frontmatter = {
        "id": "SOP-LOOM-001",
        "title": "Broken End Repair",
        "tags": ["broken_end", "loom"],
        "related_glossary": [],
    }
    matched = _infer_failure_mode_ids(frontmatter, fms)
    assert "broken_end" in matched
    assert "slub" not in matched


def test_infer_failure_mode_ids_matches_by_name() -> None:
    """Match also via name_it / name_en case-insensitive substring."""
    from sft_domain.failure_modes.models import FailureMode

    fms = (
        FailureMode(
            id="broken_end",
            name_it="rottura filo ordito",
            name_en="broken end",
            asset_families=["weaving"],
            parts=["warp"],
            severity="medium",
        ),
    )
    frontmatter = {
        "id": "SOP-LOOM-001",
        "title": "Riparazione Rottura Filo Ordito",
        "tags": [],
        "related_glossary": [],
    }
    matched = _infer_failure_mode_ids(frontmatter, fms)
    assert matched == ["broken_end"]


# ---------------------------------------------------------------------------
# Helpers — mock builder for unit-style integration tests.
# ---------------------------------------------------------------------------


def _make_parsed_doc(*, status: str = "reviewed", sop_id: str = "SOP-LOOM-001") -> Any:
    """Build a minimal ParsedDoc-like object for non-Docker tests."""
    from sft_knowledge.parsers.base import ParsedDoc, ParsedSection

    return ParsedDoc(
        source_uri=f"corpus://docs/sops/{sop_id}.md",
        frontmatter={
            "id": sop_id,
            "title": "Test SOP",
            "version": "1.0",
            "lang": "it",
            "status": status,
            "acl_level": "public",
            "asset_family": "weaving",
            "tags": ["broken_end"],
            "related_glossary": [],
        },
        sections=[ParsedSection(heading_path=["H1"], text="ciao mondo")],
        version="1.0",
        lang="it",
    )


def _make_chunk(idx: int = 0, source_uri: str = "corpus://docs/sops/x.md") -> Any:
    """Build a minimal Chunk instance."""
    from sft_knowledge.chunking.semantic import Chunk

    return Chunk(
        text="dummy text",
        chunk_idx=idx,
        heading_path=["H1"],
        metadata={
            "source_uri": source_uri,
            "lang": "it",
            "acl_level": "public",
            "version": "1.0",
            "asset_family": "weaving",
            "sop_id": "SOP-LOOM-001",
        },
    )


# ---------------------------------------------------------------------------
# Unit-level pipeline tests with mocked collaborators.
# These exercise the orchestrator logic (early-exit, ordering, state UPSERT)
# without needing Qdrant/Neo4j containers. Integration tests below exercise
# the same paths against real services when Docker is available.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unit_content_hash_early_exit(tmp_path: Path) -> None:
    """If state.content_hash == new_hash → IngestResult(skipped=True, reason='content_unchanged').

    Verifies: parser/chunker/embedder/indexer/builder are NOT called.
    """
    f = tmp_path / "sop.md"
    f.write_bytes(b"content-body")
    expected_hash = hashlib.sha256(b"content-body").hexdigest()

    parser = MagicMock()
    parser.parse = AsyncMock()
    chunker = MagicMock()
    embedder = MagicMock()
    qdrant_indexer = MagicMock()
    qdrant_indexer.upsert_batch = AsyncMock()
    neo4j_builder = MagicMock()
    neo4j_builder.merge_sop = AsyncMock()
    state_store = MagicMock()

    # State already has the same content_hash.
    from svc_knowledge_ingest.state import IngestStateRow
    from datetime import datetime, timezone

    state_store.get = AsyncMock(
        return_value=IngestStateRow(
            source_uri=f"corpus://{f.name}",
            content_hash=expected_hash,
            version="1.0",
            indexed_at=datetime.now(timezone.utc),
            chunk_count=1,
            collection="sop",
            acl_level="public",
        )
    )
    state_store.upsert = AsyncMock()

    result = await ingest_file(
        f,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        qdrant_indexer=qdrant_indexer,
        neo4j_builder=neo4j_builder,
        state_store=state_store,
        failure_modes=(),
    )

    assert result.skipped is True
    assert result.reason == "content_unchanged"
    parser.parse.assert_not_called()
    chunker.chunk.assert_not_called() if hasattr(chunker, "chunk") else None
    qdrant_indexer.upsert_batch.assert_not_called()
    neo4j_builder.merge_sop.assert_not_called()
    state_store.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_unit_non_reviewed_skip(tmp_path: Path) -> None:
    """parser returns None (status != reviewed) → IngestResult(skipped=True, reason='non_reviewed')."""
    f = tmp_path / "sop.md"
    f.write_bytes(b"body")

    parser = MagicMock()
    parser.parse = AsyncMock(return_value=None)
    chunker = MagicMock()
    embedder = MagicMock()
    qdrant_indexer = MagicMock()
    qdrant_indexer.upsert_batch = AsyncMock()
    neo4j_builder = MagicMock()
    neo4j_builder.merge_sop = AsyncMock()
    state_store = MagicMock()
    state_store.get = AsyncMock(return_value=None)
    state_store.upsert = AsyncMock()

    result = await ingest_file(
        f,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        qdrant_indexer=qdrant_indexer,
        neo4j_builder=neo4j_builder,
        state_store=state_store,
        failure_modes=(),
    )

    assert result.skipped is True
    assert result.reason == "non_reviewed"
    qdrant_indexer.upsert_batch.assert_not_called()
    neo4j_builder.merge_sop.assert_not_called()
    state_store.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_unit_dual_write_order_neo4j_first(tmp_path: Path) -> None:
    """Neo4j.merge_sop is awaited BEFORE Qdrant.upsert_batch (dual-write atomicity)."""
    f = tmp_path / "sop.md"
    f.write_bytes(b"body")

    parsed = _make_parsed_doc()
    parser = MagicMock()
    parser.parse = AsyncMock(return_value=parsed)
    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=[_make_chunk(0)])
    embedder = MagicMock()

    # encode returns a minimal EncodeOutput-shaped object.
    encode_output = MagicMock()
    encode_output.dense_vecs = [[0.0] * 1024]
    encode_output.sparse_weights = [{}]
    embedder.encode = MagicMock(return_value=encode_output)
    embedder.to_qdrant_sparse = MagicMock(return_value=MagicMock())

    call_order: list[str] = []

    async def _merge_sop(*args: Any, **kwargs: Any) -> int:
        call_order.append("neo4j")
        return 1

    async def _upsert_batch(*args: Any, **kwargs: Any) -> int:
        call_order.append("qdrant")
        return 1

    async def _state_upsert(*args: Any, **kwargs: Any) -> None:
        call_order.append("state")

    neo4j_builder = MagicMock()
    neo4j_builder.merge_sop = AsyncMock(side_effect=_merge_sop)
    qdrant_indexer = MagicMock()
    qdrant_indexer.collection = "sop"
    qdrant_indexer.upsert_batch = AsyncMock(side_effect=_upsert_batch)
    state_store = MagicMock()
    state_store.get = AsyncMock(return_value=None)
    state_store.upsert = AsyncMock(side_effect=_state_upsert)

    result = await ingest_file(
        f,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        qdrant_indexer=qdrant_indexer,
        neo4j_builder=neo4j_builder,
        state_store=state_store,
        failure_modes=(),
    )

    assert result.skipped is False
    assert call_order == ["neo4j", "qdrant", "state"]
    assert result.chunks_upserted == 1
    assert result.sop_id == "SOP-LOOM-001"


@pytest.mark.asyncio
async def test_unit_qdrant_failure_does_not_call_state_upsert(tmp_path: Path) -> None:
    """If Qdrant fails after Neo4j succeeded → state.upsert NOT called; exception re-raised."""
    f = tmp_path / "sop.md"
    f.write_bytes(b"body")

    parsed = _make_parsed_doc()
    parser = MagicMock()
    parser.parse = AsyncMock(return_value=parsed)
    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=[_make_chunk(0)])
    embedder = MagicMock()
    encode_output = MagicMock()
    encode_output.dense_vecs = [[0.0] * 1024]
    encode_output.sparse_weights = [{}]
    embedder.encode = MagicMock(return_value=encode_output)
    embedder.to_qdrant_sparse = MagicMock(return_value=MagicMock())

    neo4j_builder = MagicMock()
    neo4j_builder.merge_sop = AsyncMock(return_value=1)
    qdrant_indexer = MagicMock()
    qdrant_indexer.collection = "sop"
    qdrant_indexer.upsert_batch = AsyncMock(side_effect=RuntimeError("qdrant down"))
    state_store = MagicMock()
    state_store.get = AsyncMock(return_value=None)
    state_store.upsert = AsyncMock()

    with pytest.raises(RuntimeError, match="qdrant down"):
        await ingest_file(
            f,
            parser=parser,
            chunker=chunker,
            embedder=embedder,
            qdrant_indexer=qdrant_indexer,
            neo4j_builder=neo4j_builder,
            state_store=state_store,
            failure_modes=(),
        )

    # Neo4j was called, Qdrant failed, state.upsert never reached.
    neo4j_builder.merge_sop.assert_awaited_once()
    state_store.upsert.assert_not_called()


# ---------------------------------------------------------------------------
# Integration tests (Docker required) — KNW-07 SC#3 + TRN-01 verification.
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reindex_idempotent(pg_pool, tmp_path: Path) -> None:
    """KNW-07 SC#3: re-ingesting same file returns IngestResult(skipped=True, reason='content_unchanged').

    Uses real PG (ingest_state) + mocked Qdrant/Neo4j (the SC#3 invariant is at the
    state-gate layer; Qdrant/Neo4j idempotence is tested at their respective unit
    test layers).
    """
    from svc_knowledge_ingest.state import IngestStateStore

    f = tmp_path / "sop.md"
    md = (
        "---\n"
        "id: SOP-LOOM-001\n"
        "title: Test\n"
        "version: '1.0'\n"
        "lang: it\n"
        "status: reviewed\n"
        "acl_level: public\n"
        "asset_family: weaving\n"
        "tags: []\n"
        "related_glossary: []\n"
        "---\n\n"
        "# Heading\n\nbody text\n"
    )
    f.write_text(md, encoding="utf-8")

    store = IngestStateStore(pg_pool)

    from sft_knowledge.parsers.markdown import MarkdownParser

    parser = MarkdownParser()
    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=[_make_chunk(0)])
    embedder = MagicMock()
    encode_output = MagicMock()
    encode_output.dense_vecs = [[0.0] * 1024]
    encode_output.sparse_weights = [{}]
    embedder.encode = MagicMock(return_value=encode_output)
    embedder.to_qdrant_sparse = MagicMock(return_value=MagicMock())
    neo4j_builder = MagicMock()
    neo4j_builder.merge_sop = AsyncMock(return_value=1)
    qdrant_indexer = MagicMock()
    qdrant_indexer.collection = "sop"
    qdrant_indexer.upsert_batch = AsyncMock(return_value=1)

    # First ingest → not skipped.
    r1 = await ingest_file(
        f,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        qdrant_indexer=qdrant_indexer,
        neo4j_builder=neo4j_builder,
        state_store=store,
        failure_modes=(),
    )
    assert r1.skipped is False
    assert r1.chunks_upserted == 1

    # Second ingest with no file change → skipped.
    r2 = await ingest_file(
        f,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        qdrant_indexer=qdrant_indexer,
        neo4j_builder=neo4j_builder,
        state_store=store,
        failure_modes=(),
    )
    assert r2.skipped is True
    assert r2.reason == "content_unchanged"

    # Qdrant/Neo4j should only have been called once (first ingest).
    assert qdrant_indexer.upsert_batch.await_count == 1
    assert neo4j_builder.merge_sop.await_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_state_tracked(pg_pool, tmp_path: Path) -> None:
    """TRN-01: after ingest, ingest_state row exists with non-null indexed_at + chunk_count > 0."""
    from svc_knowledge_ingest.state import IngestStateStore

    f = tmp_path / "sop.md"
    md = (
        "---\n"
        "id: SOP-LOOM-002\n"
        "title: Test\n"
        "version: '1.0'\n"
        "lang: it\n"
        "status: reviewed\n"
        "acl_level: internal\n"
        "asset_family: weaving\n"
        "tags: []\n"
        "related_glossary: []\n"
        "---\n\n"
        "# Heading\n\nbody\n"
    )
    f.write_text(md, encoding="utf-8")

    store = IngestStateStore(pg_pool)

    from sft_knowledge.parsers.markdown import MarkdownParser

    parser = MarkdownParser()
    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=[_make_chunk(0), _make_chunk(1)])
    embedder = MagicMock()
    encode_output = MagicMock()
    encode_output.dense_vecs = [[0.0] * 1024, [0.0] * 1024]
    encode_output.sparse_weights = [{}, {}]
    embedder.encode = MagicMock(return_value=encode_output)
    embedder.to_qdrant_sparse = MagicMock(return_value=MagicMock())
    neo4j_builder = MagicMock()
    neo4j_builder.merge_sop = AsyncMock(return_value=1)
    qdrant_indexer = MagicMock()
    qdrant_indexer.collection = "sop"
    qdrant_indexer.upsert_batch = AsyncMock(return_value=2)

    await ingest_file(
        f,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        qdrant_indexer=qdrant_indexer,
        neo4j_builder=neo4j_builder,
        state_store=store,
        failure_modes=(),
    )

    parsed = await parser.parse(f)
    assert parsed is not None
    row = await store.get(parsed.source_uri)
    assert row is not None
    assert row.chunk_count == 2
    assert row.acl_level == "internal"
    assert row.indexed_at is not None
    assert row.indexed_at.tzinfo is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_content_hash_change_reingests(pg_pool, tmp_path: Path) -> None:
    """Modify file body → re-ingest happens (state.content_hash updated)."""
    from svc_knowledge_ingest.state import IngestStateStore

    f = tmp_path / "sop.md"
    md_v1 = (
        "---\n"
        "id: SOP-LOOM-003\n"
        "title: Test\n"
        "version: '1.0'\n"
        "lang: it\n"
        "status: reviewed\n"
        "acl_level: public\n"
        "asset_family: weaving\n"
        "tags: []\n"
        "related_glossary: []\n"
        "---\n\n# A\n\nfirst body\n"
    )
    md_v2 = md_v1.replace("first body", "different body")
    f.write_text(md_v1, encoding="utf-8")

    store = IngestStateStore(pg_pool)
    from sft_knowledge.parsers.markdown import MarkdownParser

    parser = MarkdownParser()
    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=[_make_chunk(0)])
    embedder = MagicMock()
    encode_output = MagicMock()
    encode_output.dense_vecs = [[0.0] * 1024]
    encode_output.sparse_weights = [{}]
    embedder.encode = MagicMock(return_value=encode_output)
    embedder.to_qdrant_sparse = MagicMock(return_value=MagicMock())
    neo4j_builder = MagicMock()
    neo4j_builder.merge_sop = AsyncMock(return_value=1)
    qdrant_indexer = MagicMock()
    qdrant_indexer.collection = "sop"
    qdrant_indexer.upsert_batch = AsyncMock(return_value=1)

    r1 = await ingest_file(
        f,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        qdrant_indexer=qdrant_indexer,
        neo4j_builder=neo4j_builder,
        state_store=store,
        failure_modes=(),
    )
    assert r1.skipped is False

    # Modify file body.
    f.write_text(md_v2, encoding="utf-8")

    r2 = await ingest_file(
        f,
        parser=parser,
        chunker=chunker,
        embedder=embedder,
        qdrant_indexer=qdrant_indexer,
        neo4j_builder=neo4j_builder,
        state_store=store,
        failure_modes=(),
    )
    assert r2.skipped is False  # content_hash differs → re-ingest
    parsed = await parser.parse(f)
    assert parsed is not None
    row = await store.get(parsed.source_uri)
    assert row is not None
    assert row.content_hash == r2.content_hash
    assert row.content_hash != r1.content_hash
