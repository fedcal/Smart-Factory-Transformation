"""Cross-lingual E2E test (Phase 5 SC#1).

Validates that an Italian query retrieves at least one English SOP chunk WITHOUT
machine translation of the query — exercises BGE-M3 multilingual alignment
end-to-end through ``RetrievalPipeline`` (D-64).

Acceptance gate:
    Binary "≥1 EN SOP" assertion (this file).
    The rigorous A/B Recall@10 ≥ 0.70 acceptance is in Plan 05-10
    (``run_ab_eval.py``).

CI behavior:
    Marked @pytest.mark.integration AND @pytest.mark.gpu — the real BGE-M3
    model is loaded; on CPU this takes ~30-60s for 2-3 SOPs which is tolerable
    on a GPU runner but skipped on the default CPU CI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

# Marca tutto il modulo come integration+gpu (skipped da default CPU CI).
pytestmark = [pytest.mark.integration, pytest.mark.gpu]


def _corpus_root() -> Path:
    """Find synthetic-corpus/en/loom under the monorepo root."""
    # Walk up from this test file to find the repo root.
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        candidate = parent / "simulators" / "synthetic-corpus" / "en" / "loom"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate simulators/synthetic-corpus/en/loom from "
        f"{here}"
    )


async def _bootstrap_collection(qdrant_client: Any) -> None:
    from qdrant_client.http.models import (
        Distance,
        SparseVectorParams,
        VectorParams,
    )

    try:
        await qdrant_client.delete_collection(collection_name="sop")
    except Exception:
        pass
    await qdrant_client.create_collection(
        collection_name="sop",
        vectors_config={
            "dense": VectorParams(size=1024, distance=Distance.COSINE),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(),
        },
    )


async def test_it_query_returns_en_sop(qdrant_client: Any) -> None:
    """SC#1: Italian query "come riparare rottura filo ordito" retrieves ≥1 EN SOP.

    Pipeline reale:
        1. Parse 2-3 EN SOPs (loom domain).
        2. Chunk via ``SemanticChunker``.
        3. Embed via real ``BgeM3Embedder`` (downloads ~2GB on first run).
        4. Index in Qdrant.
        5. Run ``RagSearchTool`` con query italiana e ruolo ``technician``.
        6. Assert almeno 1 citation con ``/en/`` nel ``source_uri``.

    Note: il vero gate A/B (Recall@10 ≥ 0.70) sta in Plan 05-10 run_ab_eval.py.
    """
    # Marker di skip ulteriore quando il modello non è disponibile in fp16
    # (eventuali ambienti CPU senza FlagEmbedding completo). In quel caso il
    # test viene skipped piuttosto che falsificare la condizione SC#1.
    try:
        from sft_knowledge.embedding.bge_m3 import _get_model
    except ImportError as exc:
        pytest.skip(f"BgeM3Embedder not available: {exc}")

    try:
        _ = _get_model()
    except RuntimeError as exc:
        pytest.skip(f"BGE-M3 backend unavailable: {exc}")

    from sft_knowledge.chunking import SemanticChunker
    from sft_knowledge.embedding import BgeM3Embedder
    from sft_knowledge.parsers import MarkdownParser
    from sft_knowledge.retrieval import RetrievalPipeline
    from sft_knowledge.stores import QdrantIndexer
    from sft_knowledge.tools import RagSearchTool

    # ---- Index 2-3 EN SOPs ----
    await _bootstrap_collection(qdrant_client)

    corpus = _corpus_root()
    en_sops = sorted(corpus.glob("*.md"))[:3]
    assert len(en_sops) >= 2, f"need ≥2 EN SOPs under {corpus}"

    parser = MarkdownParser()
    embedder = BgeM3Embedder()
    chunker = SemanticChunker()
    indexer = QdrantIndexer(client=qdrant_client, collection="sop")

    all_chunks = []
    for sop_path in en_sops:
        parsed = parser.parse(sop_path)
        chunks = chunker.chunk(parsed)
        all_chunks.extend(chunks)

    texts = [c.text for c in all_chunks]
    enc = embedder.encode(texts, return_dense=True, return_sparse=True)
    dense_vecs = enc.dense_vecs
    sparse_vecs = [
        embedder.to_qdrant_sparse(sw) for sw in enc.sparse_weights
    ]
    await indexer.upsert_batch(all_chunks, dense_vecs, sparse_vecs)

    # ---- IT query → expect ≥1 EN hit ----
    pipeline = RetrievalPipeline(
        qdrant_client=qdrant_client,
        embedder=embedder,
        # reranker default — will lazy-load bge-reranker-v2-m3
    )
    tool = RagSearchTool(pipeline=pipeline)

    citations = await tool.ainvoke(
        {
            "query": "come riparare rottura filo ordito",
            "user_roles": ["technician"],
            "k": 10,
            "lang": None,  # nessun filtro lingua → cross-lingual
        }
    )
    en_hits = [c for c in citations if "/en/" in c.source_uri]

    # Log per debug visibile via -s.
    for c in citations:
        print(f"  score={c.score:.3f} src={c.source_uri}")

    assert len(en_hits) >= 1, (
        "SC#1 FAIL: IT query retrieved zero EN SOPs. "
        f"All citations: {[c.source_uri for c in citations]}"
    )
