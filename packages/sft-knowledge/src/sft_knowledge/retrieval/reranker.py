"""BgeReranker — wrapper BGE-reranker-v2-m3 con async bridge (D-63 + KNW-09).

Backend primario: ``FlagEmbedding.FlagReranker`` (cross-encoder che produce score
calibrati in [0,1] con ``normalize=True``).

Pattern lazy singleton (PATTERNS.md Shared Pattern 8 + bge_m3.py analog):
    @lru_cache(maxsize=1) def _get_reranker(): ...
    → primo accesso scarica il modello (~600MB su ``BAAI/bge-reranker-v2-m3``),
    → accessi successivi ritornano la stessa istanza.

Sync→async bridge:
    ``FlagReranker.compute_score`` è sync e CPU/GPU bound; usiamo
    ``asyncio.to_thread`` per evitare di bloccare l'event loop (PATTERNS.md §reranker.py).

Configurazione (env):
    BGE_M3_DEVICE — "cpu" | "cuda" | "cuda:0" ... (default: "cpu" per CI CPU-only)

Threat model (PLAN.md):
    T-05-09-05 (DoS) → input ``hits`` viene tipicamente troncato a ≤20 elementi
                        dal Prefetch+Fusion del RetrievalPipeline (D-63).
"""

from __future__ import annotations

import asyncio
import os
from functools import lru_cache
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


_MODEL_NAME = "BAAI/bge-reranker-v2-m3"


# ---------------------------------------------------------------------------
# Lazy singleton reranker loader
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_reranker() -> Any:
    """Carica il reranker BGE-reranker-v2-m3 una sola volta per processo.

    Returns:
        Un oggetto ``FlagReranker`` (FlagEmbedding) con ``.compute_score(pairs, normalize)``.

    Raises:
        RuntimeError: ``FlagEmbedding`` non installato — il reranker è obbligatorio
        per garantire i score calibrati in [0,1] richiesti da KNW-09.
    """
    device = os.environ.get("BGE_M3_DEVICE", "cpu")
    try:
        from FlagEmbedding import FlagReranker  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "BgeReranker requires FlagEmbedding to be installed. "
            f"Import error: {exc}."
        ) from exc

    logger.info("bge_reranker_loaded", model=_MODEL_NAME, device=device)
    # use_fp16=True auto-cade su fp32 quando il device è CPU (FlagEmbedding README).
    return FlagReranker(_MODEL_NAME, use_fp16=True, device=device)


# ---------------------------------------------------------------------------
# BgeReranker
# ---------------------------------------------------------------------------


class BgeReranker:
    """Cross-encoder reranker per RAG hybrid retrieval (D-63).

    Espone un'API ``async`` che fa da bridge verso il ``compute_score`` sync di
    FlagReranker. Gli score in output sono calibrati in [0,1] (``normalize=True``)
    come richiesto da KNW-09 SC#2.

    Esempio::

        reranker = BgeReranker()
        ranked = await reranker.rerank("query it", hits)
        # ranked è list[tuple[hit, score]] ordinata desc per score
    """

    def __init__(self, device: str | None = None) -> None:
        """Inizializza il wrapper.

        Args:
            device: opzionale override di ``BGE_M3_DEVICE``. Se impostato e il
                singleton non è ancora stato inizializzato, sarà usato come device
                effettivo. No-op se il singleton è già caricato (documentato).
        """
        if device is not None:
            os.environ["BGE_M3_DEVICE"] = device
        self._device = device

    async def rerank(
        self,
        query: str,
        hits: list[Any],
    ) -> list[tuple[Any, float]]:
        """Ri-ordina ``hits`` per pertinenza rispetto a ``query``.

        Args:
            query: stringa query (es. testo dell'utente).
            hits: lista di ScoredPoint Qdrant; ogni elemento deve avere
                ``payload["text"]`` (chunk text). Lista vuota → ritorna [].

        Returns:
            Lista di ``(hit, score)`` ordinata desc per ``score``; gli ``score``
            sono nel range [0,1] (FlagReranker ``normalize=True``).
        """
        if not hits:
            return []

        # Costruisce le coppie (query, chunk_text); coding-style.md immutability:
        # nessuna mutazione di ``hits``.
        pairs: list[tuple[str, str]] = [
            (query, str(hit.payload.get("text", ""))) for hit in hits
        ]

        reranker = _get_reranker()
        try:
            # Sync→async bridge (PATTERNS.md §reranker.py); normalize=True per [0,1].
            raw_scores = await asyncio.to_thread(reranker.compute_score, pairs, True)
        except Exception as exc:
            # Mai swallowed (coding-style.md error handling): rialza con contesto.
            raise RuntimeError(
                f"BgeReranker.rerank failed on {len(pairs)} pair(s): {exc}"
            ) from exc

        # ``compute_score`` può ritornare ``float`` (singola coppia) o ``list[float]``.
        if isinstance(raw_scores, (int, float)):
            scores: list[float] = [float(raw_scores)]
        else:
            scores = [float(s) for s in raw_scores]

        # Ordinamento immutabile: ``sorted`` ritorna una nuova lista.
        return sorted(zip(hits, scores), key=lambda pair: -pair[1])


__all__ = ["BgeReranker"]
