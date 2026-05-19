"""QdrantLongTermMemory — Memory ABC impl che rimpiazza il D-59 stub Phase 4.

Wrappa il ``RetrievalPipeline`` (Plan 05-09 Task 1) per soddisfare il contratto
``sft_agents.sdk.memory.Memory``. Converte le ``RagCitation`` in ``MemoryRecord``
mantenendo il payload Phase-4-compatibile (D-70).

Vincoli architetturali (ARCHITECTURE.md):
    - Gli agenti NON scrivono mai direttamente nel knowledge store: ``store()``
      solleva ``NotImplementedError`` indirizzando a ``services/knowledge-ingest``
      (T-05-09-03 mitigation).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict
from sft_agents.models.memory_record import MemoryRecord
from sft_agents.sdk.memory import Memory

from sft_knowledge.embedding import BgeM3Embedder
from sft_knowledge.retrieval import BgeReranker, RetrievalPipeline

logger = structlog.get_logger(__name__)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Config (frozen + forbid)
# ---------------------------------------------------------------------------


class QdrantLongTermMemoryConfig(BaseModel):
    """Configurazione frozen per ``QdrantLongTermMemory`` (D-70)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "sop"
    embedding_device: str = "cpu"


# ---------------------------------------------------------------------------
# QdrantLongTermMemory
# ---------------------------------------------------------------------------


class QdrantLongTermMemory(Memory):
    """Long-term memory implementation backed by Qdrant + BGE-M3 (D-70).

    Replaces the Phase 4 ``StubLongTermMemory`` (D-59). Le query passano per
    ``RetrievalPipeline`` (ACL pre-filter + Prefetch+RRF + rerank). La scrittura
    è esplicitamente disabilitata: gli agenti devono usare
    ``services/knowledge-ingest``.

    Usage::

        memory = QdrantLongTermMemory()
        records = await memory.query("filo ordito", k=3,
                                     filters={"user_roles": ["technician"]})
    """

    def __init__(
        self, config: QdrantLongTermMemoryConfig | None = None
    ) -> None:
        """Bind configurazione (default = istanza con valori di fallback)."""
        self._config = config or QdrantLongTermMemoryConfig()
        self._pipeline: RetrievalPipeline | None = None
        self._log = logger.bind(
            component="qdrant_long_term_memory",
            collection=self._config.collection_name,
        )
        self._log.info("qdrant_long_term_memory_instantiated")

    def _get_pipeline(self) -> RetrievalPipeline:
        """Lazy-init il ``RetrievalPipeline`` al primo uso (singleton per istanza)."""
        if self._pipeline is None:
            from qdrant_client import AsyncQdrantClient

            client = AsyncQdrantClient(url=self._config.qdrant_url)
            embedder = BgeM3Embedder(device=self._config.embedding_device)
            reranker = BgeReranker(device=self._config.embedding_device)
            self._pipeline = RetrievalPipeline(
                qdrant_client=client,
                embedder=embedder,
                reranker=reranker,
            )
        return self._pipeline

    async def query(
        self,
        query: str,
        k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        """Esegui retrieval ibrido e mappa a ``MemoryRecord``.

        Args:
            query: testo della query.
            k: numero massimo di record (default 5).
            filters: dict opzionale; chiavi riconosciute:
                ``user_roles`` (list[str]): ruoli per ACL pre-filter. Default
                    ``["operator"]`` (massima restrizione — fail-safe).
                ``category`` (str): collection target (default "sop").
                ``lang``, ``sop_ids``, ``asset_family``: passati alla pipeline.

        Returns:
            Lista di ``MemoryRecord`` ordinata desc per ``score``.
        """
        filters = filters or {}
        # Default operator = ruolo più restrittivo (fail-safe).
        user_roles = filters.get("user_roles") or ["operator"]
        category = filters.get("category", "sop")
        lang = filters.get("lang")
        sop_ids = filters.get("sop_ids")
        asset_family = filters.get("asset_family")

        pipeline = self._get_pipeline()
        citations = await pipeline.search(
            query=query,
            user_roles=list(user_roles),
            category=str(category),
            k=k,
            lang=lang,
            sop_ids=sop_ids,
            asset_family=asset_family,
        )

        # Map RagCitation → MemoryRecord. MemoryRecord ha:
        #   source_uri, content (min_length=1), score [0,1], ts (tz-aware),
        #   metadata (default_factory=dict).
        records: list[MemoryRecord] = []
        ts = datetime.now(UTC)
        for c in citations:
            content = c.snippet if c.snippet else "(empty)"
            records.append(
                MemoryRecord(
                    source_uri=c.source_uri,
                    content=content,
                    score=c.score,
                    ts=ts,
                    metadata={
                        "retrieved_at": c.retrieved_at.isoformat(),
                        "category": category,
                    },
                )
            )
        return records

    async def store(self, record: MemoryRecord) -> str:
        """Sempre solleva ``NotImplementedError`` (T-05-09-03 mitigation).

        ARCHITECTURE.md anti-pattern: gli agenti non scrivono direttamente nei
        knowledge store. Usare ``services/knowledge-ingest`` pipeline.
        """
        self._log.warning("qdrant_long_term_memory_store_rejected")
        raise NotImplementedError(
            "Agents must not write directly to knowledge stores per "
            "ARCHITECTURE.md. Use services/knowledge-ingest pipeline."
        )


__all__ = ["QdrantLongTermMemory", "QdrantLongTermMemoryConfig"]
