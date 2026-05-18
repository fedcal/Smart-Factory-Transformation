"""MemoryRecord Pydantic model (D-59).

Generic record returned by Memory.query() / accepted by Memory.store(). Phase 4 ships
the shape; Phase 5 implementations (QdrantLongTermMemory) populate score + content.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator


class MemoryRecord(BaseModel):
    """A single memory record returned by Memory.query() or persisted via Memory.store()."""

    model_config = {"frozen": True, "extra": "forbid"}

    source_uri: Annotated[str, Field(min_length=1, description="Origin URI (sop://, mem://, …)")]
    content: Annotated[str, Field(min_length=1, description="Memory text content")]
    score: Annotated[float, Field(ge=0.0, le=1.0, description="Relevance score in [0,1]")]
    ts: Annotated[datetime, Field(description="UTC tz-aware timestamp")]
    metadata: Annotated[dict[str, Any], Field(default_factory=dict)]

    @field_validator("ts")
    @classmethod
    def _check_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError(f"MemoryRecord.ts must be tz-aware, got naive: {v!r}")
        return v
