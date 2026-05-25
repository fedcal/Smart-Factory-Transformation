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

Audit (SEC-07 — Phase 11):
    Se ``audit_writer`` è fornito e la query restituisce ≥1 chunk con
    ``acl_level == 'restricted'``, viene scritto un ``AuditRecord`` con
    ``action_type = ActionType.RESTRICTED_DOC_ACCESS`` e ``decision = Decision.LOGGED``.
    I chunk_ids e query_hash sono inclusi nei details (T-11-03-04 mitigation).
    Il testo della query NON viene incluso in chiaro (solo hash SHA-256).

    Dipendenza circolare (Assumption A4, Piano 11-03): sft_knowledge importa già da
    sft_agents.models.* (RagCitation, Decision, ecc.) — import da sft_agents.models.enums
    e sft_agents.models.audit NON è una nuova dipendenza circolare. L'audit_writer è
    passato come collaboratore (protocol duck-typing) per evitare coupling con
    sft_agents.tools.audit (tool LangChain).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

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
    "operator":        frozenset({"public"}),
    "technician":      frozenset({"public", "internal"}),
    "supervisor":      frozenset({"public", "internal"}),
    "shift-supervisor": frozenset({"public", "internal"}),       # ruolo canonico JWT (alias di supervisor)
    "manager":         frozenset({"public", "internal", "restricted"}),
    "engineer":        frozenset({"public", "internal", "restricted"}),
    "safety":          frozenset({"public", "internal", "restricted"}),
    "admin":           frozenset({"public", "internal", "restricted"}),   # SEC-03 Phase 11
    "auditor":         frozenset({"public", "internal", "restricted"}),   # SEC-03 Phase 11: read-only su tutti i livelli
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
        audit_writer: Any | None = None,
    ) -> None:
        """Inizializza la pipeline.

        Args:
            qdrant_client: ``AsyncQdrantClient`` già connesso.
            embedder: ``BgeM3Embedder`` (Plan 05-07).
            reranker: ``BgeReranker`` opzionale; se ``None`` ne viene creato uno
                con singleton lazy (lazy-load del modello al primo rerank).
            audit_writer: Collaboratore con metodo ``async write(AuditRecord)`` per
                l'audit SEC-07 su chunk restricted. Se ``None``, nessun audit viene scritto.
                Passato come collaboratore duck-typed per evitare coupling con
                sft_agents.tools.audit (T-11-03-04 mitigation).
        """
        self._client = qdrant_client
        self._embedder = embedder
        self._reranker = reranker if reranker is not None else BgeReranker()
        self._audit_writer = audit_writer
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
        principal: dict[str, Any] | None = None,
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
            principal: dict JWT payload (sub, role) per l'audit SEC-07.
                Se ``None``, principal_id sarà "anonymous".

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

        # ---- 6. Audit restricted chunk access (SEC-07, T-11-03-04) --------
        # If audit_writer is configured and any returned hit has acl_level=='restricted',
        # write a RESTRICTED_DOC_ACCESS audit row. The query text is never stored in
        # clear — only query_hash (SHA-256) to avoid information leakage (T-11-03-04).
        # WR-03: l'audit è eseguito sui chunk top-k effettivamente restituiti all'utente,
        # non su fused_hits pre-top-k. Auditare il prefetch completo produceva falsi positivi
        # su chunk restricted mai visti dall'utente (chunk in posizione 11-20 non restituiti).
        if self._audit_writer is not None:
            await self._write_restricted_audit(
                top_k_hits=[hit for hit, _ in top_k],
                query=query,
                principal=principal or {},
                retrieved_at=retrieved_at,
            )

        return citations

    async def _write_restricted_audit(
        self,
        top_k_hits: list[Any],
        query: str,
        principal: dict[str, Any],
        retrieved_at: datetime,
    ) -> None:
        """Scrive AuditRecord RESTRICTED_DOC_ACCESS se ≥1 hit ha acl_level='restricted'.

        Chiamata solo se self._audit_writer è configurato (non None).
        Il query hash SHA-256 è incluso nei details (T-11-03-04 mitigation).

        Args:
            top_k_hits: lista di ScoredPoint da Qdrant effettivamente restituiti all'utente
                (post-rerank, post-top-k slicing). WR-03: NON includere il prefetch completo
                pre-top-k per evitare falsi positivi su chunk mai visti dall'utente.
            query: testo della query originale (non incluso in chiaro nell'audit).
            principal: dict JWT payload (sub, role) del chiamante.
            retrieved_at: timestamp UTC del retrieval.
        """
        # Cerca chunk restricted SOLO tra quelli effettivamente restituiti all'utente (top-k)
        restricted_hits = [
            h for h in top_k_hits
            if (h.payload or {}).get("acl_level") == "restricted"
        ]

        if not restricted_hits:
            return  # nessun chunk restricted — nessun audit (no false positive)

        # Import lazy per non creare circolarità a livello di modulo
        from sft_agents.models.audit import AuditRecord
        from sft_agents.models.budget import BudgetSnapshot
        from sft_agents.models.enums import ActionType, Decision
        from sft_agents.models.evidence import EvidencePanel, TokenUsage

        # query_hash SHA-256 — non il testo in chiaro (T-11-03-04)
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()

        chunk_ids = [str(h.id) for h in restricted_hits]
        principal_id = str(principal.get("sub", "anonymous"))

        # EvidencePanel minimale — row osservazionale (Decision.LOGGED)
        evidence = EvidencePanel(
            input_summary=f"Restricted chunk access: {len(restricted_hits)} chunk(s)",
            input_truncated=False,
            tool_calls=[],
            rag_citations=[],
            confidence=1.0,
            model="retrieval-pipeline@sft-knowledge",
            prompt_hash="0" * 64,  # nessun prompt LLM — zero hash sentinella
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=0,
        )

        # BudgetSnapshot zero — nessun LLM invocato
        budget = BudgetSnapshot(
            tokens_input=0,
            tokens_output=0,
            tokens_total=0,
            cost_usd_simulated=0.0,
            duration_ms=0,
            limit_tokens=50000,
            limit_cost_usd=1.0,
            limit_duration_s=60,
        )

        record = AuditRecord(
            id=uuid4(),
            ts=retrieved_at,
            action_id=uuid4(),
            agent_id="retrieval-pipeline",
            thread_id=f"retrieval.{query_hash[:8]}",
            cluster="knowledge",
            action_type=ActionType.RESTRICTED_DOC_ACCESS.value,
            evidence_panel=evidence,
            decision=Decision.LOGGED,
            decision_actor=None,
            motivation=None,
            budget_snapshot=budget,
            approval_id=None,
        )

        try:
            await self._audit_writer.write(record)
            self._log.info(
                "restricted_doc_access_audited",
                principal_id=principal_id,
                chunk_ids=chunk_ids,
                query_hash=query_hash,
                restricted_count=len(restricted_hits),
            )
        except Exception as exc:
            # Audit failure is best-effort — never prevent retrieval from completing
            self._log.error(
                "restricted_audit_write_failed",
                error=str(exc),
                principal_id=principal_id,
            )


__all__ = ["ROLE_TO_ACL", "RetrievalPipeline", "build_acl_filter"]
