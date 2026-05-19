"""SemanticChunker — chunking semantico via LlamaIndex `SemanticSplitterNodeParser`.

D-62: buffer_size=1, breakpoint_percentile_threshold=95 (default LlamaIndex sui SOP tessili).

Pipeline:
    1. `ParsedDoc.sections` → ricostruisce il body completo (join `\\n\\n`) e una mappa
       cumulativa (offset_iniziale → heading_path) per recuperare il heading_path di
       ciascun chunk via `bisect_right(node.start_char_idx)`.
    2. Crea `llama_index.core.Document` con metadata derivata dal frontmatter:
        source_uri, lang, acl_level, version, asset_family, sop_id.
       `excluded_embed_metadata_keys` impedisce che metadati di tracking (source_uri,
       acl_level, sop_id) contaminino il vettore semantico (Risk 7 mitigation).
    3. Esegue `SemanticSplitterNodeParser.get_nodes_from_documents([doc])` con
       l'embedding model `HuggingFaceEmbedding("BAAI/bge-m3")` (singleton lru_cache).
    4. Per ogni `TextNode`: costruisce `Chunk(text, chunk_idx, heading_path, metadata)`.
       Ogni chunk include TUTTE le chiavi di Document.metadata (KNW-05 prerequisite).

Threat model (T-05-07-03): `excluded_embed_metadata_keys` impedisce data leakage da
identificatori (source_uri/sop_id) nell'embedding semantico — l'ACL filter è applicato a
livello di retrieval (Plan 05-09), non di embedding.
"""

from __future__ import annotations

import os
from bisect import bisect_right
from functools import lru_cache
from typing import Any

import structlog
from pydantic import BaseModel

from sft_knowledge.parsers.base import ParsedDoc

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Chunk model
# ---------------------------------------------------------------------------


class Chunk(BaseModel):
    """Singolo chunk semantico — frozen, extra forbidden (Shared Pattern 1).

    Attributi:
        text:         testo del chunk (output del semantic splitter).
        chunk_idx:    indice progressivo 0-based all'interno del documento.
        heading_path: catena di heading H1→H6 che contiene il chunk (D-67).
        metadata:     metadati propagati (source_uri, lang, acl_level, version,
                      asset_family, sop_id) — KNW-05 prerequisite.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    text: str
    chunk_idx: int
    heading_path: list[str]
    metadata: dict


# ---------------------------------------------------------------------------
# Lazy singleton embedding model for the splitter
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_embed_model() -> Any:
    """Carica `HuggingFaceEmbedding("BAAI/bge-m3")` una sola volta per processo.

    Lo splitter LlamaIndex usa l'embedding solo come "judge" per i breakpoint
    semantici; non vogliamo pagare il costo di un nuovo modello per documento.
    """
    try:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "llama-index-embeddings-huggingface non installato — è dichiarato in "
            "packages/sft-knowledge/pyproject.toml. Errore: " + str(exc)
        ) from exc

    device = os.environ.get("BGE_M3_DEVICE", "cpu")
    logger.info("semantic_chunker_embed_model_init", model="BAAI/bge-m3", device=device)
    return HuggingFaceEmbedding(
        model_name="BAAI/bge-m3",
        device=device,
        embed_batch_size=10,
    )


# ---------------------------------------------------------------------------
# SemanticChunker
# ---------------------------------------------------------------------------


class SemanticChunker:
    """Chunker semantico con preservazione della metadata frontmatter (D-62).

    Args:
        buffer_size: ampiezza della finestra (in frasi) usata dallo splitter per
                     valutare la similarità tra blocchi adiacenti. Default D-62: 1.
        breakpoint_percentile_threshold: percentile della distribuzione di distanza
                     coseno oltre cui inserire un break (Default D-62: 95).
    """

    def __init__(
        self,
        buffer_size: int = 1,
        breakpoint_percentile_threshold: int = 95,
    ) -> None:
        self.buffer_size = buffer_size
        self.breakpoint_percentile_threshold = breakpoint_percentile_threshold

    def chunk(self, parsed_doc: ParsedDoc) -> list[Chunk]:
        """Splitta `parsed_doc` in chunk semantici preservando metadata + heading_path.

        Args:
            parsed_doc: output di `DocumentParser.parse()` (D-67).

        Returns:
            Lista di `Chunk` ordinati per `chunk_idx`. Se il documento non ha sezioni
            (corner case Phase 5 corpus: ParsedDoc valido richiede almeno una sezione),
            la funzione ritorna lista vuota.
        """
        if not parsed_doc.sections:
            logger.warning(
                "semantic_chunker_empty_doc",
                source_uri=parsed_doc.source_uri,
            )
            return []

        # Lazy import per mantenere il top-level leggero (LlamaIndex import costoso).
        from llama_index.core import Document  # type: ignore[import-not-found]
        from llama_index.core.node_parser import (  # type: ignore[import-not-found]
            SemanticSplitterNodeParser,
        )

        # 1. Costruisce body + mappa offset → heading_path.
        body_parts: list[str] = []
        offsets: list[int] = []  # offset di inizio di ciascuna sezione nel body
        heading_paths: list[list[str]] = []
        cursor = 0
        separator = "\n\n"
        for i, section in enumerate(parsed_doc.sections):
            offsets.append(cursor)
            heading_paths.append(list(section.heading_path))
            body_parts.append(section.text)
            cursor += len(section.text)
            if i < len(parsed_doc.sections) - 1:
                cursor += len(separator)
        body = separator.join(body_parts)

        # 2. Metadata propagata a ciascun chunk (Risk 7 mitigation).
        fm = parsed_doc.frontmatter
        metadata = {
            "source_uri": parsed_doc.source_uri,
            "lang": parsed_doc.lang,
            "acl_level": fm.get("acl_level", "internal"),
            "version": parsed_doc.version,
            "asset_family": str(fm.get("asset_family", "")),
            "sop_id": str(fm.get("id", "")),
        }

        # 3. Costruisci Document. `excluded_embed_metadata_keys` evita data leakage
        # di identificatori nel vettore semantico (T-05-07-03).
        doc = Document(
            text=body,
            metadata=metadata,
            excluded_embed_metadata_keys=["source_uri", "acl_level", "sop_id"],
        )

        # 4. Splitter LlamaIndex.
        splitter = SemanticSplitterNodeParser(
            buffer_size=self.buffer_size,
            breakpoint_percentile_threshold=self.breakpoint_percentile_threshold,
            embed_model=_get_embed_model(),
        )
        nodes = splitter.get_nodes_from_documents([doc])

        # 5. Costruisci Chunk con heading_path ricostruito via bisect.
        chunks: list[Chunk] = []
        for i, node in enumerate(nodes):
            start_idx = getattr(node, "start_char_idx", None) or 0
            # bisect_right → indice della prima sezione il cui offset > start_idx.
            # La sezione contenente start_idx è quella immediatamente precedente.
            section_idx = max(0, bisect_right(offsets, start_idx) - 1)
            section_idx = min(section_idx, len(heading_paths) - 1)
            node_metadata = getattr(node, "metadata", None) or {}
            # Copia immutabile dei metadati (Coding Style: never mutate).
            chunk_metadata = {**node_metadata}
            chunks.append(
                Chunk(
                    text=node.text,
                    chunk_idx=i,
                    heading_path=heading_paths[section_idx],
                    metadata=chunk_metadata,
                )
            )

        logger.info(
            "semantic_chunker_done",
            source_uri=parsed_doc.source_uri,
            num_chunks=len(chunks),
            num_sections=len(parsed_doc.sections),
        )
        return chunks


__all__ = ["SemanticChunker", "Chunk"]
