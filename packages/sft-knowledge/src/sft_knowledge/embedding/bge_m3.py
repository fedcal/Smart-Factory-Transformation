"""BgeM3Embedder — wrapper BGE-M3 con dense+sparse output (D-62, KNW-02).

Backend primario: `FlagEmbedding.BGEM3FlagModel` (dense + sparse + colbert disponibili).
Fallback: `fastembed.TextEmbedding` (solo dense — sparse_weights resterà vuoto, modalità
degradata documentata). Se nessuno dei due backend è installabile, `_get_model()` solleva
`RuntimeError` con messaggio diagnostico (RESEARCH §2 / Open Question 1).

Pattern lazy singleton (PATTERNS.md Shared Pattern 8 + sft-assets._loader):
    @lru_cache(maxsize=1) def _get_model(): ...
    → primo accesso scarica/carica il modello (~2GB su `BAAI/bge-m3`),
    → accessi successivi ritornano la stessa istanza (verificato in unit test).

Configurazione (env):
    BGE_M3_DEVICE — "cpu" | "cuda" | "cuda:0" ... (default: "cpu" per CI CPU-only)

Threat model (PLAN.md):
    T-05-07-04 (DoS via OOM su doc lunghi) → mitigato da `max_length=8192` e
                                              chunking upstream (SemanticChunker).
    T-05-07-SC (supply chain) → entrambe le librerie sono dichiarate in
                                pyproject.toml di Plan 05-01 (audit RESEARCH).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# Costanti BGE-M3 (D-61 / RESEARCH §2).
_MODEL_NAME = "BAAI/bge-m3"
_DENSE_DIM = 1024


# ---------------------------------------------------------------------------
# FastEmbed adapter — espone shape FlagEmbedding-compatibile (solo dense)
# ---------------------------------------------------------------------------


class _FastEmbedAdapter:
    """Adatta `fastembed.TextEmbedding` per assomigliare a `BGEM3FlagModel.encode()`.

    BGE-M3 via fastembed espone solo embedding densi; sparse_weights torna come lista
    di dict vuoti (modalità degradata documentata). Questo è accettabile come fallback
    quando FlagEmbedding non è installabile (es. piattaforme senza torch nativo).
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        # FastEmbed non espone .tokenizer pubblico equivalente; sparse non supportato.
        self.tokenizer = None

    def encode(
        self,
        texts: list[str],
        batch_size: int = 12,
        max_length: int = 8192,
        return_dense: bool = True,
        return_sparse: bool = True,
        return_colbert_vecs: bool = False,
    ) -> dict[str, Any]:
        # fastembed TextEmbedding.embed() ritorna un generatore di np.ndarray (dim 1024).
        dense_list = list(self._inner.embed(texts))
        sparse_list: list[dict[str, float]] = [{} for _ in texts]
        return {
            "dense_vecs": dense_list,
            "lexical_weights": sparse_list,
        }


# ---------------------------------------------------------------------------
# Lazy singleton model loader
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_model() -> Any:
    """Carica il modello BGE-M3 una sola volta per processo.

    Strategia:
        1. Prova `FlagEmbedding.BGEM3FlagModel` (preferito — dense + sparse).
        2. In caso di `ImportError`, ricade su `fastembed.TextEmbedding` (solo dense).
        3. Se nessuno dei due è disponibile, solleva `RuntimeError`.

    Returns:
        Un oggetto con `.encode(texts, ...)` che ritorna un dict compatibile
        con FlagEmbedding (`dense_vecs`, `lexical_weights`).

    Raises:
        RuntimeError: nessun backend disponibile.
    """
    device = os.environ.get("BGE_M3_DEVICE", "cpu")
    try:
        from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-not-found]

        logger.info("bge_m3_backend_selected", backend="FlagEmbedding", device=device)
        return BGEM3FlagModel(_MODEL_NAME, use_fp16=True, device=device)
    except ImportError as primary_err:
        logger.warning(
            "bge_m3_flagembedding_missing",
            error=str(primary_err),
            fallback="fastembed",
        )
        try:
            from fastembed import TextEmbedding  # type: ignore[import-not-found]

            logger.info(
                "bge_m3_backend_selected",
                backend="fastembed",
                note="sparse_weights will be empty (degraded mode)",
            )
            return _FastEmbedAdapter(TextEmbedding(_MODEL_NAME))
        except ImportError as fallback_err:
            raise RuntimeError(
                "BgeM3Embedder requires either FlagEmbedding or fastembed to be "
                f"installed. FlagEmbedding error: {primary_err}; "
                f"fastembed error: {fallback_err}."
            ) from fallback_err


# ---------------------------------------------------------------------------
# EncodeOutput — frozen dataclass (np.ndarray non è facilmente serializzabile via Pydantic)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EncodeOutput:
    """Output di `BgeM3Embedder.encode()`.

    Attributi:
        dense_vecs:      lista di np.ndarray di shape (1024,) — uno per testo input.
        sparse_weights:  lista di dict[token_str, peso] — vuoto su fallback fastembed.
    """

    dense_vecs: list[Any]  # list[np.ndarray] — Any evita import numpy in firma
    sparse_weights: list[dict[str, float]]


# ---------------------------------------------------------------------------
# BgeM3Embedder
# ---------------------------------------------------------------------------


class BgeM3Embedder:
    """Wrapper BGE-M3 con dense+sparse output e conversione SparseVector per Qdrant.

    Usa il lazy singleton `_get_model()` per amortizzare il costo di caricamento del
    modello (~2GB pesi). `device`, se passato, sovrascrive `BGE_M3_DEVICE` env per
    istanza (effettivo solo se il singleton non è ancora stato inizializzato).

    Esempio:
        embedder = BgeM3Embedder()
        out = embedder.encode(["hello world"])
        sparse_vec = embedder.to_qdrant_sparse(out.sparse_weights[0])
    """

    def __init__(
        self,
        device: str | None = None,
        batch_size: int = 12,
        max_length: int = 8192,
    ) -> None:
        if device is not None:
            # Imposta env prima dell'inizializzazione del singleton; sarà no-op se il
            # modello è già stato caricato (lru_cache hit) — comportamento documentato.
            os.environ["BGE_M3_DEVICE"] = device
        self._batch_size = batch_size
        self._max_length = max_length

    def encode(
        self,
        texts: list[str],
        return_dense: bool = True,
        return_sparse: bool = True,
    ) -> EncodeOutput:
        """Codifica `texts` in vettori densi (1024D) + pesi sparsi lessicali.

        Args:
            texts: lista di stringhe da embeddare.
            return_dense: se True ritorna i vettori densi.
            return_sparse: se True ritorna i pesi sparsi (fastembed → sempre vuoti).

        Returns:
            EncodeOutput con `dense_vecs` e `sparse_weights` allineati per indice.
        """
        if not texts:
            return EncodeOutput(dense_vecs=[], sparse_weights=[])

        model = _get_model()
        try:
            result = model.encode(
                texts,
                batch_size=self._batch_size,
                max_length=self._max_length,
                return_dense=return_dense,
                return_sparse=return_sparse,
                return_colbert_vecs=False,
            )
        except Exception as exc:
            # Mai swallowed: rialza con contesto diagnostico (CLAUDE.md error handling).
            raise RuntimeError(
                f"BgeM3Embedder.encode failed on {len(texts)} text(s): {exc}"
            ) from exc

        dense_vecs = list(result.get("dense_vecs", [])) if return_dense else []
        sparse_weights = (
            list(result.get("lexical_weights", [])) if return_sparse else []
        )
        return EncodeOutput(dense_vecs=dense_vecs, sparse_weights=sparse_weights)

    def to_qdrant_sparse(self, lexical_weights: dict[str, float]) -> Any:
        """Converte i pesi sparsi BGE-M3 (token→peso) in `SparseVector` Qdrant.

        BGE-M3 sparse output è `dict[token_str, float]`. Qdrant si aspetta
        `SparseVector(indices: list[int], values: list[float])` dove gli indici sono
        ID di token nel vocabolario del modello. I token che mappano su `unk_token_id`
        vengono filtrati (RESEARCH §2 Assumption A2 + Open Question 1).

        Args:
            lexical_weights: output sparse di `encode()`.

        Returns:
            `qdrant_client.http.models.SparseVector` con `len(indices) == len(values)`.

        Raises:
            RuntimeError: se il backend corrente non espone un tokenizer (es. fastembed).
        """
        # Lazy import: evita di pagare qdrant-client import quando si usa solo encode().
        from qdrant_client.http.models import SparseVector

        model = _get_model()
        tokenizer = getattr(model, "tokenizer", None)
        if tokenizer is None:
            raise RuntimeError(
                "to_qdrant_sparse requires a backend with a tokenizer (FlagEmbedding). "
                "Current backend does not expose `.tokenizer` (e.g. fastembed fallback)."
            )

        unk_id = getattr(tokenizer, "unk_token_id", None)
        indices: list[int] = []
        values: list[float] = []
        for token, weight in lexical_weights.items():
            token_id = tokenizer.convert_tokens_to_ids(token)
            if unk_id is not None and token_id == unk_id:
                # T-05-07-XX mitigation: UNK tokens darebbero collisioni sparse.
                continue
            indices.append(int(token_id))
            values.append(float(weight))

        # Invariante per Qdrant API.
        assert len(indices) == len(values), "indices/values length mismatch"
        return SparseVector(indices=indices, values=values)


__all__ = ["BgeM3Embedder", "EncodeOutput"]
