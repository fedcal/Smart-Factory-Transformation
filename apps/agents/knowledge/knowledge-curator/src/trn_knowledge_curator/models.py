"""Domain models for KnowledgeCurator (D-KC-01/02/03).

Provides:
  - IngestRequest: frozen Pydantic model for incoming document ingest requests.
  - CurationReport: frozen Pydantic model carrying dedup + staleness + reuse_rate results.
  - RagCitation: citation entry (re-exported from sft_agents if available, else local).

All models are frozen=True + extra=forbid per Phase 4 cross-cutting idioms.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# RagCitation — local definition (avoids circular import from sft_agents.models)
# ---------------------------------------------------------------------------


class RagCitation(BaseModel):
    """A single RAG citation reference in a curation report.

    Attributes:
        source_uri: Document URI (e.g. Qdrant point ID or file path).
        chunk_id: Optional chunk identifier within the document.
        score: Retrieval similarity score in [0.0, 1.0].
    """

    model_config = {"frozen": True, "extra": "forbid"}

    source_uri: Annotated[str, Field(min_length=1, description="Document URI")]
    chunk_id: Annotated[str | None, Field(default=None, description="Chunk ID within document")]
    score: Annotated[float, Field(ge=0.0, le=1.0, description="Similarity score")]


# ---------------------------------------------------------------------------
# IngestRequest — incoming document for curation
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    """Request to ingest (and curate) a document (D-KC-01/02).

    Trust boundary: untrusted external input — validated before processing.
    All fields are required (fail fast on incomplete data).

    Attributes:
        document_id: Unique identifier for the document.
        document_text: Raw document text (used for dedup hashing and embedding).
        doc_type: Document type for staleness threshold selection (e.g. "sop", "runbook", "note").
        last_updated: UTC tz-aware datetime of last document update.
        source_uri: Source URI for tracking and citation.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    document_id: Annotated[str, Field(min_length=1, description="Unique document identifier")]
    document_text: Annotated[str, Field(min_length=1, description="Raw document text")]
    doc_type: Annotated[
        str,
        Field(min_length=1, description="Document type key (sop / runbook / note / ...)"),
    ]
    last_updated: Annotated[
        datetime,
        Field(description="UTC tz-aware datetime of last document update"),
    ]
    source_uri: Annotated[str, Field(min_length=1, description="Document source URI")]


# ---------------------------------------------------------------------------
# CurationReport — output of KnowledgeCurator.__call__
# ---------------------------------------------------------------------------


class CurationReport(BaseModel):
    """Report produced by KnowledgeCurator after processing an IngestRequest.

    Carries results of all three KPI dimensions:
      - dedup_result: is_duplicate, dup_type, source_uri, score (D-KC-01)
      - is_stale: whether the document exceeds its type-specific staleness threshold (D-KC-02)
      - reuse_rate: rolling-window KPI value (D-KC-03)
      - citations: RAG citations associated with this curation run

    Attributes:
        document_id: Mirrored from IngestRequest for traceability.
        is_duplicate: True when exact or near-duplicate detected.
        dup_type: "exact" | "near" | None.
        dup_source_uri: Matched document URI when duplicate; None otherwise.
        dup_score: Cosine score for near-dup; 1.0 for exact; None when new.
        is_stale: True when document age exceeds its type-specific threshold.
        reuse_rate: Current rolling-window reuse-rate KPI value.
        citations: RAG citations in this curation run.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    document_id: Annotated[str, Field(min_length=1, description="Mirrored from IngestRequest")]
    is_duplicate: Annotated[bool, Field(description="True when duplicate detected (D-KC-01)")]
    dup_type: Annotated[str | None, Field(default=None, description='"exact" | "near" | None')]
    dup_source_uri: Annotated[str | None, Field(default=None, description="Matched source URI")]
    dup_score: Annotated[float | None, Field(default=None, description="Similarity score")]
    is_stale: Annotated[bool, Field(description="True when past staleness threshold (D-KC-02)")]
    reuse_rate: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="Rolling-window reuse-rate KPI (D-KC-03)"),
    ]
    citations: Annotated[
        list[RagCitation],
        Field(default_factory=list, description="RAG citations in this curation run"),
    ] = []


__all__ = [
    "CurationReport",
    "IngestRequest",
    "RagCitation",
]
