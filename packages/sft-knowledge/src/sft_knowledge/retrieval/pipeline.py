"""RetrievalPipeline — embed → Qdrant query_points hybrid (Prefetch+RRF) → rerank.

Orchestratore di retrieval del knowledge layer Phase 5 (D-63 LOCKED + KNW-09).

Flusso single-shot (RESEARCH §1, Qdrant ≥1.10 Query API):
    1. ``BgeM3Embedder.encode`` → dense_vec (1024D) + sparse_weights (lexical).
    2. Build ``Filter`` composito = ACL pre-filter (ROLE_TO_ACL) + lang/sop_ids/asset_family.
    3. ``await client.query_points(collection, prefetch=[Prefetch(dense), Prefetch(sparse)],
        query=FusionQuery(RRF), limit=20)`` → fusione single-roundtrip.
    4. Se ``rerank=True``: ``BgeReranker.rerank(query, fused_hits)`` → top-k.
    5. Map ad ``RagCitation(source_uri, snippet=text[:200], score, retrieved_at)``.

ACL (D-63 + T-05-09-01 mitigation):
    Il filtro è applicato a livello di engine Qdrant (mai post-filter Python).
    ``build_acl_filter`` solleva ``ValueError`` se nessun role mappa ad alcun
    livello (fail-closed).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

from sft_knowledge.embedding.bge_m3 import BgeM3Embedder
from sft_knowledge.models import RagCitation
from sft_knowledge.retrieval.reranker import BgeReranker

if TYPE_CHECKING:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.http.models import Filter

logger = structlog.get_logger(__name__)

UTC = timezone.utc

# claudes_discretion (PLAN <interfaces>): snippet cap 200 char.
_SNIPPET_MAX = 200

# claudes_discretion (D-63): prefetch limit 20 per leg (dense + sparse).
_PREFETCH_LIMIT = 20


# ---------------------------------------------------------------------------
# ACL (D-63 LOCKED — exact mapping)
# ---------------------------------------------------------------------------

ROLE_TO_ACL: dict[str, frozenset[str]] = {
    "operator":   frozenset({"public"}),
    "technician": frozenset({"public", "internal"}),
    "supervisor": frozenset({"public", "internal"}),
    "manager":    frozenset({"public", "internal", "restricted"}),
    "engineer":   frozenset({"public", "internal", "restricted"}),
    "safety":     frozenset({"public", "internal", "restricted"}),
}


def build_acl_filter(user_roles: list[str]) -> Filter:
    """Costruisce il ``Filter`` Qdrant pre-filter per i livelli ACL ammessi.

    Args:
        user_roles: lista di role string per l'utente corrente.

    Returns:
        ``Filter(must=[FieldCondition(key="acl_level", match=MatchAny(any=[...]))])``
        con i livelli ACL allowed in ordine alfabetico (deterministico per i test).

    Raises:
        ValueError: se ``user_roles`` non risolve ad alcun livello ACL — fail-closed
        per evitare leak (T-05-09-01).
    """
    # Lazy import: qdrant_client non sempre necessario al top-level.
    from qdrant_client.http.models import FieldCondition, Filter, MatchAny

    # Immutability (coding-style.md): frozenset.union ritorna un nuovo frozenset.
    allowed = frozenset().union(
        *(ROLE_TO_ACL.get(r, frozenset()) for r in user_roles)
    )
    if not allowed:
        raise ValueError(
            f"No ACL levels resolved for roles: {user_roles}. "
            f"Known roles: {sorted(ROLE_TO_ACL.keys())}"
        )

    return Filter(
        must=[
            FieldCondition(
                key="acl_level",
                match=MatchAny(any=sorted(allowed)),
            )
        ]
    )


# ---------------------------------------------------------------------------
# RetrievalPipeline
# ---------------------------------------------------------------------------


class RetrievalPipeline:
    """Pipeline single-shot hybrid retrieval + rerank (D-63 LOCKED).

    Esegue embed → Qdrant ``query_points`` (Prefetch dense+sparse + FusionQuery RRF)
    → opzionale BGE rerank → top-k → conversione a ``list[RagCitation]``.

    Usage::

        pipeline = RetrievalPipeline(qdrant_client, embedder)
        citations = await pipeline.search(
            "come riparare rottura filo ordito",
            user_roles=["technician"],
            k=5,
        )
    """

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        embedder: BgeM3Embedder,
        reranker: BgeReranker | None = None,
    ) -> None:
        """Inizializza la pipeline.

        Args:
            qdrant_client: ``AsyncQdrantClient`` già connesso.
            embedder: ``BgeM3Embedder`` (Plan 05-07).
            reranker: ``BgeReranker`` opzionale; se ``None`` ne viene creato uno
                con singleton lazy (lazy-load del modello al primo rerank).
        """
        self._client = qdrant_client
        self._embedder = embedder
        self._reranker = reranker if reranker is not None else BgeReranker()
        self._log = logger.bind(component="retrieval_pipeline")

    async def search(
        self,
        query: str,
        user_roles: list[str],
        category: str = "sop",
        k: int = 5,
        lang: str | None = None,
        sop_ids: list[str] | None = None,
        asset_family: str | None = None,
        rerank: bool = True,
    ) -> list[RagCitation]:
        """Esegui retrieval ibrido + ACL pre-filter + rerank opzionale.

        Args:
            query: testo della query (qualsiasi lingua — BGE-M3 multilingue).
            user_roles: ruoli utente per ACL pre-filter (mai vuoto).
            category: collection Qdrant target (sop/manuals/troubleshooting/training).
            k: numero massimo di citazioni in output (1..20 raccomandato).
            lang: se impostato, filtra per ``payload.lang == lang``.
            sop_ids: se impostato, filtra per ``payload.sop_id ∈ sop_ids``.
            asset_family: se impostato, filtra per ``payload.asset_family``.
            rerank: se ``True`` applica BGE cross-encoder rerank; altrimenti
                usa lo score Fusion RRF.

        Returns:
            Lista di ``RagCitation`` ordinata desc per score, lunghezza ≤ k.

        Raises:
            ValueError: ``user_roles`` non risolve ad alcun ACL (fail-closed).
            RuntimeError: errori embedding / query Qdrant / rerank propagati con
            contesto diagnostico.
        """
        # Lazy import per evitare hard-dep di qdrant_client al collection time.
        from qdrant_client.http.models import (
            FieldCondition,
            Filter,
            Fusion,
            FusionQuery,
            MatchAny,
            MatchValue,
            Prefetch,
        )

        # ---- 1. Embed ------------------------------------------------------
        try:
            output = self._embedder.encode(
                [query], return_dense=True, return_sparse=True
            )
        except Exception as exc:
            self._log.error("embed_failed", error=str(exc))
            raise

        if not output.dense_vecs:
            raise RuntimeError(
                "BgeM3Embedder returned no dense vector for query — cannot retrieve"
            )

        dense_vec = output.dense_vecs[0]
        dense_list = (
            list(dense_vec.tolist())
            if hasattr(dense_vec, "tolist")
            else list(dense_vec)
        )

        sparse_vec: Any | None = None
        if output.sparse_weights and output.sparse_weights[0]:
            try:
                sparse_vec = self._embedder.to_qdrant_sparse(
                    output.sparse_weights[0]
                )
            except RuntimeError as exc:
                # Backend senza tokenizer (es. fastembed) → degraded mode dense-only.
                self._log.warning(
                    "sparse_unavailable_degraded_dense_only",
                    error=str(exc),
                )
                sparse_vec = None

        # ---- 2. Build composite Filter ------------------------------------
        acl_filter = build_acl_filter(user_roles)
        # ``Filter.must`` è una sequenza Pydantic; ricostruiamo una lista nuova
        # (coding-style.md immutability).
        must_conditions: list[Any] = list(acl_filter.must or [])

        if lang is not None:
            must_conditions.append(
                FieldCondition(key="lang", match=MatchValue(value=lang))
            )
        if sop_ids:
            must_conditions.append(
                FieldCondition(key="sop_id", match=MatchAny(any=sorted(sop_ids)))
            )
        if asset_family is not None:
            must_conditions.append(
                FieldCondition(
                    key="asset_family", match=MatchValue(value=asset_family)
                )
            )

        composite_filter = Filter(must=must_conditions)

        # ---- 3. query_points (Prefetch + Fusion RRF, single roundtrip) ----
        prefetch: list[Any] = [
            Prefetch(
                query=dense_list,
                using="dense",
                limit=_PREFETCH_LIMIT,
                filter=composite_filter,
            )
        ]
        if sparse_vec is not None:
            prefetch.append(
                Prefetch(
                    query=sparse_vec,
                    using="sparse",
                    limit=_PREFETCH_LIMIT,
                    filter=composite_filter,
                )
            )

        try:
            result = await self._client.query_points(
                collection_name=category,
                prefetch=prefetch,
                query=FusionQuery(fusion=Fusion.RRF),
                limit=_PREFETCH_LIMIT,
                with_payload=True,
            )
        except Exception as exc:
            self._log.error(
                "query_points_failed",
                collection=category,
                error=str(exc),
            )
            raise

        fused_hits = list(result.points or [])
        if not fused_hits:
            self._log.info(
                "no_hits", collection=category, roles=sorted(set(user_roles))
            )
            return []

        # ---- 4. Rerank or take top-k by fusion score ----------------------
        if rerank:
            try:
                ranked = await self._reranker.rerank(query, fused_hits)
            except Exception as exc:
                self._log.error("rerank_failed", error=str(exc))
                raise
            top_k = ranked[:k]
        else:
            top_k = [(h, float(h.score)) for h in fused_hits[:k]]

        # ---- 5. Map → RagCitation ----------------------------------------
        retrieved_at = datetime.now(UTC)
        citations: list[RagCitation] = []
        for hit, score in top_k:
            payload = hit.payload or {}
            text = str(payload.get("text", ""))
            snippet = text[:_SNIPPET_MAX] if text else "(empty)"
            source_uri = str(payload.get("source_uri", "")) or f"qdrant://{hit.id}"
            # Clamp score in [0,1] per soddisfare il vincolo RagCitation.
            clamped = max(0.0, min(1.0, float(score)))
            citations.append(
                RagCitation(
                    source_uri=source_uri,
                    snippet=snippet,
                    score=clamped,
                    retrieved_at=retrieved_at,
                )
            )

        self._log.info(
            "retrieval_done",
            collection=category,
            roles=sorted(set(user_roles)),
            returned=len(citations),
            reranked=rerank,
        )
        return citations


__all__ = ["ROLE_TO_ACL", "RetrievalPipeline", "build_acl_filter"]
