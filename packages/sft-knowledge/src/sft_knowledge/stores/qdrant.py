"""QdrantIndexer — batch upsert con point.id deterministico + payload provenance.

Layer di persistenza per i 4 indici vettoriali del knowledge layer (D-61):
    sop, manuals, troubleshooting, training

Garanzie (D-69 + RESEARCH §9):
    - point.id deterministico = sha256(source_uri|chunk_idx|text) → UUID 8-4-4-4-12.
      Re-upsert dello stesso chunk produce lo stesso id ⇒ idempotenza a livello
      di collection.
    - Ogni payload contiene tutti i provenance field KNW-05 SC#5:
        text, source_uri, chunk_idx, version, lang, acl_level, asset_family,
        sop_id, category, heading_path, created_at.
    - Batch upsert flush con batch_size (default 100, claudes_discretion).
    - delete_by_source_uri_version per version-change purge (D-69).

Threat model:
    - T-05-08-01 / Cypher injection NA per Qdrant: tutto passa per PointStruct
      tipizzato (Pydantic) → nessuna superficie di injection JSON/SQL.
    - T-05-08-02 / Collisioni point.id: sha256 ⇒ probabilità ~2^-128.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    import numpy as np
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.http.models import SparseVector

    from sft_knowledge.chunking.semantic import Chunk

logger = structlog.get_logger(__name__)

UTC = timezone.utc

# D-61 LOCKED — collection valide (deve restare in sync con scripts/qdrant-bootstrap.py).
_COLLECTIONS: frozenset[str] = frozenset({"sop", "manuals", "troubleshooting", "training"})

# claudes_discretion (CONTEXT D-69) — flush every 100 points.
_DEFAULT_BATCH_SIZE: int = 100

# Dense vector size (D-61 / BGE-M3).
_DENSE_DIM: int = 1024


def point_id(source_uri: str, chunk_idx: int, text: str) -> str:
    """Deterministic point id, UUID-formatted (RESEARCH §9 Risk 6).

    Args:
        source_uri: URI canonica del documento (es. "file://sop/SOP-LOOM-001-v1.md").
        chunk_idx: indice progressivo del chunk all'interno del documento.
        text: testo del chunk.

    Returns:
        Stringa hex 32 char nel formato `8-4-4-4-12` (UUID-shaped). Qdrant
        accetta sia int sia UUID-string sia plain string come point id; usiamo
        UUID-shape per massima compatibilità con la suite di tooling REST.
    """
    raw = hashlib.sha256(f"{source_uri}|{chunk_idx}|{text}".encode("utf-8")).hexdigest()
    h = raw[:32]
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def _vec_to_list(vec: Any) -> list[float]:
    """Converte un numpy.ndarray (o list) in list[float] senza importare numpy.

    Mantiene il modulo "leggero" al top-level: numpy è imported solo se i caller
    passano ndarray; un'iterable di float funziona ugualmente.
    """
    tolist = getattr(vec, "tolist", None)
    if callable(tolist):
        return list(tolist())
    return list(vec)


class QdrantIndexer:
    """Indexer batch su Qdrant con named-vector dense+sparse + payload provenance.

    Usage:
        indexer = QdrantIndexer(client=async_qdrant_client, collection="sop")
        await indexer.upsert_batch(chunks, dense_vecs, sparse_vecs)
        await indexer.delete_by_source_uri_version("file://sop/x.md", "1.0")
    """

    def __init__(
        self,
        client: AsyncQdrantClient,
        collection: str,
        batch_size: int = _DEFAULT_BATCH_SIZE,
    ) -> None:
        """Inizializza l'indexer.

        Args:
            client: AsyncQdrantClient già connesso.
            collection: nome della collection (deve essere uno tra D-61).
            batch_size: dimensione del batch flush (default 100).
        """
        if collection not in _COLLECTIONS:
            raise ValueError(
                f"collection '{collection}' non valida; "
                f"attese: {sorted(_COLLECTIONS)}"
            )
        if batch_size <= 0:
            raise ValueError(f"batch_size deve essere > 0, got {batch_size}")
        self._client = client
        self.collection = collection
        self.batch_size = batch_size
        self._log = logger.bind(collection=collection)

    async def upsert_batch(
        self,
        chunks: list[Chunk],
        dense_vecs: list[np.ndarray],
        sparse_vecs: list[SparseVector],
    ) -> int:
        """Upsert atomico per batch di `self.batch_size` punti.

        Args:
            chunks: lista di Chunk (con metadata KNW-05 propagata).
            dense_vecs: lista di vettori densi 1024-d (numpy.ndarray o list).
            sparse_vecs: lista di SparseVector (Qdrant http model).

        Returns:
            Numero totale di punti upserted.

        Raises:
            ValueError: se le tre liste hanno lunghezze diverse.
        """
        n = len(chunks)
        if len(dense_vecs) != n or len(sparse_vecs) != n:
            raise ValueError(
                f"length mismatch: chunks={n} dense={len(dense_vecs)} "
                f"sparse={len(sparse_vecs)} — devono coincidere"
            )
        if n == 0:
            return 0

        # Lazy import — qdrant_client può essere assente nei runner unit-only.
        from qdrant_client.http.models import PointStruct

        # created_at unico per il batch (deterministico nel record di un batch
        # ma non a livello di point: comunque NON entra in point.id quindi non
        # rompe l'idempotenza D-69).
        created_at = datetime.now(UTC).isoformat()

        points: list[PointStruct] = []
        for i, chunk in enumerate(chunks):
            payload: dict[str, Any] = {
                **chunk.metadata,
                "text": chunk.text,
                "chunk_idx": chunk.chunk_idx,
                "heading_path": list(chunk.heading_path),
                "category": self.collection,
                "created_at": created_at,
            }
            source_uri = chunk.metadata.get("source_uri", "")
            pid = point_id(source_uri, chunk.chunk_idx, chunk.text)
            vector = {
                "dense": _vec_to_list(dense_vecs[i]),
                "sparse": sparse_vecs[i],
            }
            points.append(PointStruct(id=pid, vector=vector, payload=payload))

        total = 0
        for start in range(0, len(points), self.batch_size):
            batch = points[start : start + self.batch_size]
            try:
                await self._client.upsert(
                    collection_name=self.collection,
                    points=batch,
                )
            except Exception as exc:
                self._log.error(
                    "qdrant_upsert_failed",
                    batch_start=start,
                    batch_size=len(batch),
                    error=str(exc),
                )
                raise
            total += len(batch)

        self._log.info("qdrant_upsert_done", total=total, batches=(total + self.batch_size - 1) // self.batch_size)
        return total

    async def delete_by_source_uri_version(
        self, source_uri: str, version: str
    ) -> int:
        """Cancella tutti i punti per (source_uri, version) — version-change purge.

        Args:
            source_uri: URI del documento.
            version: stringa version (es. "1.0").

        Returns:
            Numero di punti rimossi (best-effort: Qdrant ritorna lo status
            dell'operazione, non sempre conta esatto — ritorniamo 0 se l'API
            non riporta il count).
        """
        from qdrant_client.http.models import (
            FieldCondition,
            Filter,
            FilterSelector,
            MatchValue,
        )

        flt = Filter(
            must=[
                FieldCondition(key="source_uri", match=MatchValue(value=source_uri)),
                FieldCondition(key="version", match=MatchValue(value=version)),
            ],
        )

        try:
            result = await self._client.delete(
                collection_name=self.collection,
                points_selector=FilterSelector(filter=flt),
                wait=True,
            )
        except Exception as exc:
            self._log.error(
                "qdrant_delete_failed",
                source_uri=source_uri,
                version=version,
                error=str(exc),
            )
            raise

        # UpdateResult.status è "completed"; non riporta count diretto.
        # Ritorniamo 0 se il count non è disponibile (chiamanti possono
        # introspectare via count() pre/post).
        count = getattr(result, "deleted_count", 0) or 0
        self._log.info(
            "qdrant_delete_done",
            source_uri=source_uri,
            version=version,
            count=count,
        )
        return count


__all__ = ["QdrantIndexer", "point_id"]
