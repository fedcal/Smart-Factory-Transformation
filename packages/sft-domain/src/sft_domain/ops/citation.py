"""RagCitation — citazione singola di retrieval RAG.

Vive nel dominio (sft-domain) per evitare il ciclo
`sft-domain → sft-agents` che il piano 06-04 ha rilevato a runtime:
`sft-agents` dichiara `sft-domain` come dipendenza, quindi i modelli
condivisi (citazioni, evidence) devono risiedere nel layer di dominio.
`sft-agents.models.evidence.RagCitation` puo' importare questa classe
e re-esportarla per backward-compat nei plan successivi.

Mantiene 1:1 lo schema di `sft_agents.models.evidence.RagCitation`
(Phase 4, HITL-06): frozen + extra=forbid + tz-aware retrieved_at +
snippet max_length=2000 (T-04-Checkpoint-PII).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


def _tz_aware(v: datetime) -> datetime:
    """Reject naive datetime (Pitfall 7)."""
    if v.tzinfo is None:
        raise ValueError(
            f"Datetime field must be tz-aware, got naive: {v!r}. "
            "Use datetime.now(timezone.utc) or datetime(..., tzinfo=timezone.utc)."
        )
    return v


class RagCitation(BaseModel):
    """A single RAG retrieval citation (Phase 5 populates rag_citations[]).

    Snippet capped at 2000 chars to bound payload size (T-04-Checkpoint-PII).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    source_uri: Annotated[str, Field(min_length=1, description="URI of the source document")]
    snippet: Annotated[
        str,
        Field(min_length=1, max_length=2000, description="Excerpt from the source (<=2000 chars)"),
    ]
    score: Annotated[float, Field(ge=0.0, le=1.0, description="Similarity score in [0,1]")]
    retrieved_at: Annotated[datetime, Field(description="UTC tz-aware retrieval timestamp")]

    @field_validator("retrieved_at")
    @classmethod
    def _check_tz(cls, v: datetime) -> datetime:
        return _tz_aware(v)
