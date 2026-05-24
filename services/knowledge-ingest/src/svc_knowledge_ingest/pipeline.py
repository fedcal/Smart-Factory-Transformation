"""Pipeline orchestrator (Plan 05-10 Task 1).

Chains the Phase 5 SDK primitives into the end-to-end ingest flow per D-67 + D-68:

    parse → (content_hash gate) → chunk → embed → Neo4j MERGE first → Qdrant upsert
    → ingest_state UPSERT

The orchestrator is the only component aware of *all* collaborators; it owns:

* Content-hash early exit (KNW-07 SC#3): if `IngestStateStore.get(source_uri).content_hash`
  matches the new hash, the file is skipped without touching Qdrant/Neo4j.
* Dual-write order (D-68 + PATTERNS Pattern 1): Neo4j (ACID) is written *before*
  Qdrant (eventually consistent). If Qdrant fails afterwards, the state row is NOT
  upserted — subsequent runs detect the divergence via content_hash mismatch and
  re-run the whole pipeline (deterministic point.id + Cypher MERGE both idempotent).
* failure_mode_ids inference: cross-references `parsed.frontmatter` tags/title with
  the loaded `FailureMode` registry, providing the `DOCUMENTED_BY` edges that
  Neo4jGraphBuilder.merge_sop expects.

Threat mitigations (PLAN.md threat_model):

* T-05-10-02 (dual-write inconsistency): Neo4j first; Qdrant errors propagate, state
  upsert never runs, next ingest is fully recoverable thanks to deterministic IDs.
* T-V5-sql: state_store is the only SQL surface here; all queries inside
  `state.py` are pre-parametrized constants (verified by test_sql_constants_have_no_fstring).

Note: this module is intentionally backend-agnostic — collaborators are passed in
by the caller (the Typer CLI in __main__.py) and can be mocked in unit tests.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from pydantic import BaseModel
from sft_knowledge.path_utils import derive_source_uri

if TYPE_CHECKING:
    from sft_domain.failure_modes.models import FailureMode

    from sft_knowledge.chunking.semantic import Chunk, SemanticChunker
    from sft_knowledge.embedding.bge_m3 import BgeM3Embedder
    from sft_knowledge.parsers.base import DocumentParser
    from sft_knowledge.stores.neo4j import Neo4jGraphBuilder
    from sft_knowledge.stores.qdrant import QdrantIndexer

    from svc_knowledge_ingest.state import IngestStateStore

logger = structlog.get_logger(__name__)


class IngestResult(BaseModel):
    """Outcome of a single `ingest_file(...)` invocation (frozen, extra=forbid)."""

    model_config = {"frozen": True, "extra": "forbid"}

    skipped: bool
    reason: str | None = None
    chunks_upserted: int = 0
    sop_id: str | None = None
    content_hash: str | None = None


# ---------------------------------------------------------------------------
# Failure-mode inference heuristic
# ---------------------------------------------------------------------------


def _infer_failure_mode_ids(
    frontmatter: dict,
    failure_modes: "tuple[FailureMode, ...]",
) -> list[str]:
    """Heuristic: match frontmatter tags + related_glossary + title against FailureMode names.

    Strategy:
        - Build a lowercase search corpus from `tags`, `related_glossary`, and `title`.
        - For each FailureMode, return its id when *any* of (id, name_it.lower(),
          name_en.lower()) appears as a substring in the search corpus.

    The match is **substring** (not token) so that a multi-word `name_it` like
    `"rottura filo ordito"` matches a title `"Riparazione Rottura Filo Ordito"`.
    The corpus is joined into a single lowercase string per document.
    """
    tags = frontmatter.get("tags") or []
    glossary = frontmatter.get("related_glossary") or []
    title = str(frontmatter.get("title", ""))

    haystack_parts = []
    for item in tags:
        haystack_parts.append(str(item).lower())
    for item in glossary:
        haystack_parts.append(str(item).lower())
    haystack_parts.append(title.lower())
    haystack = " ".join(haystack_parts)

    matched: list[str] = []
    for fm in failure_modes:
        needles = (
            fm.id.lower(),
            fm.name_it.lower(),
            fm.name_en.lower(),
        )
        if any(needle in haystack for needle in needles):
            matched.append(fm.id)
    return matched


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def ingest_file(
    path: Path,
    *,
    parser: "DocumentParser",
    chunker: "SemanticChunker",
    embedder: "BgeM3Embedder",
    qdrant_indexer: "QdrantIndexer",
    neo4j_builder: "Neo4jGraphBuilder",
    state_store: "IngestStateStore",
    failure_modes: "tuple[FailureMode, ...]",
) -> IngestResult:
    """Ingest a single file end-to-end (D-67 + D-68).

    Steps:
        1. Compute content_hash = sha256(path.read_bytes())
        2. Query state_store; if existing.content_hash == new hash → early exit (skipped)
        3. parser.parse(path); if None (status != reviewed) → skipped non_reviewed
        4. chunker.chunk(parsed)
        5. embedder.encode(chunk_texts) → dense + sparse
        6. Infer failure_mode_ids from frontmatter
        7. neo4j_builder.merge_sop(parsed, failure_mode_ids)   ← FIRST
        8. qdrant_indexer.upsert_batch(chunks, dense, sparse)  ← SECOND
        9. state_store.upsert(source_uri, content_hash, version, chunk_count, ...)
        10. Return IngestResult(skipped=False, ...)

    Raises:
        Any exception raised by collaborators after step 7 — the dual-write atomicity
        is achieved at the *next* run via content_hash detection + idempotent MERGE.
    """
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    source_uri = derive_source_uri(path)
    log = logger.bind(source_uri=source_uri, content_hash=content_hash)

    # 1+2. Early-exit BEFORE parse on content_hash match (KNW-07 SC#3).
    existing = await state_store.get(source_uri)
    if existing is not None and existing.content_hash == content_hash:
        log.info("ingest_skipped_unchanged")
        return IngestResult(
            skipped=True,
            reason="content_unchanged",
            content_hash=content_hash,
        )

    # 3. Parse — None on status != reviewed gate (D-25).
    parsed = await parser.parse(path)
    if parsed is None:
        log.info("ingest_skipped_non_reviewed")
        return IngestResult(skipped=True, reason="non_reviewed")

    # Chunk + embed.
    chunks: list[Chunk] = chunker.chunk(parsed)
    if not chunks:
        log.warning("ingest_no_chunks")
        # Still update state to record we saw this version (avoids re-parsing next run).
        await state_store.upsert(
            source_uri=parsed.source_uri,
            content_hash=content_hash,
            version=parsed.version,
            chunk_count=0,
            collection=qdrant_indexer.collection,
            acl_level=str(parsed.frontmatter.get("acl_level", "internal")),
        )
        return IngestResult(
            skipped=False,
            chunks_upserted=0,
            sop_id=str(parsed.frontmatter.get("id", "")) or None,
            content_hash=content_hash,
        )

    encode_output = embedder.encode([c.text for c in chunks])
    dense_vecs = list(encode_output.dense_vecs)
    sparse_vecs = [embedder.to_qdrant_sparse(w) for w in encode_output.sparse_weights]

    # Infer failure_mode_ids from frontmatter for the DOCUMENTED_BY edges.
    fm_ids = _infer_failure_mode_ids(parsed.frontmatter, failure_modes)

    # 7. Neo4j FIRST (ACID anchor — D-68).
    await neo4j_builder.merge_sop(parsed, fm_ids)

    # 8. Qdrant SECOND (eventually consistent — recover by re-run on failure).
    try:
        chunk_count = await qdrant_indexer.upsert_batch(chunks, dense_vecs, sparse_vecs)
    except Exception as exc:
        log.error(
            "ingest_inconsistent_state",
            stage="qdrant_upsert_after_neo4j_merge",
            error=str(exc),
            recovery="re-run with same content_hash will succeed",
        )
        raise

    # 9. State UPSERT — only when both writes succeeded.
    await state_store.upsert(
        source_uri=parsed.source_uri,
        content_hash=content_hash,
        version=parsed.version,
        chunk_count=chunk_count,
        collection=qdrant_indexer.collection,
        acl_level=str(parsed.frontmatter.get("acl_level", "internal")),
    )

    log.info(
        "ingest_done",
        sop_id=str(parsed.frontmatter.get("id", "")),
        chunks_upserted=chunk_count,
        failure_modes=len(fm_ids),
    )

    return IngestResult(
        skipped=False,
        chunks_upserted=chunk_count,
        sop_id=str(parsed.frontmatter.get("id", "")) or None,
        content_hash=content_hash,
    )


__all__ = ["IngestResult", "ingest_file", "_infer_failure_mode_ids"]
