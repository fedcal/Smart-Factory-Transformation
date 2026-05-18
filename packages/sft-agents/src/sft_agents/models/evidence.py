"""EvidencePanel + ToolCall + RagCitation + TokenUsage (HITL-06, D-56).

All models follow Phase 4 cross-cutting idioms:
    - frozen=True + extra='forbid'
    - field_validator enforcing tz-aware datetime (Pitfall 7)
    - Pattern validators on model identifier + prompt_hash (T-04-LLM-Inject mitigation)
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator


def _tz_aware(v: datetime) -> datetime:
    """Reject naive datetime (Pitfall 7)."""
    if v.tzinfo is None:
        raise ValueError(
            f"Datetime field must be tz-aware, got naive: {v!r}. "
            "Use datetime.now(timezone.utc) or datetime(..., tzinfo=timezone.utc)."
        )
    return v


class TokenUsage(BaseModel):
    """LLM token accounting per call."""

    model_config = {"frozen": True, "extra": "forbid"}

    input: Annotated[int, Field(ge=0, description="Input prompt tokens")]
    output: Annotated[int, Field(ge=0, description="Generated output tokens")]
    total: Annotated[int, Field(ge=0, description="Sum input + output (may include overhead)")]


class ToolCall(BaseModel):
    """A single tool invocation captured in EvidencePanel.

    args/result are plain dicts (JSON-serializable shapes only).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    name: Annotated[str, Field(min_length=1, description="Tool name (matches BaseTool.name)")]
    args: Annotated[dict[str, Any], Field(description="Input args dict (JSON-serializable)")]
    result: Annotated[
        dict[str, Any] | None,
        Field(default=None, description="Result dict; None on error or void return"),
    ]
    duration_ms: Annotated[int, Field(ge=0, description="Wall-clock duration in ms")]
    ts: Annotated[datetime, Field(description="UTC tz-aware invocation timestamp")]

    @field_validator("ts")
    @classmethod
    def _check_tz(cls, v: datetime) -> datetime:
        return _tz_aware(v)


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


class EvidencePanel(BaseModel):
    """HITL-06 evidence schema attached to every AI decision (D-56).

    Trust boundary: untrusted LLM output crosses into PG-persisted audit. Mitigations:
        - input_summary length cap (500 chars) + input_truncated flag (T-04-Checkpoint-PII)
        - model identifier pattern (`name@runtime`) blocks malformed identifiers
        - prompt_hash regex enforces sha256 hex (T-04-LLM-Inject)
        - frozen + extra=forbid prevents post-hoc mutation
    """

    model_config = {"frozen": True, "extra": "forbid"}

    input_summary: Annotated[
        str,
        Field(
            max_length=500,
            description="Intent summary capped at 500 chars (T-04-Checkpoint-PII mitigation)",
        ),
    ]
    input_truncated: Annotated[
        bool,
        Field(default=False, description="True when original input exceeded 500 chars"),
    ]
    tool_calls: Annotated[
        list[ToolCall],
        Field(default_factory=list, description="Ordered list of tool invocations"),
    ]
    rag_citations: Annotated[
        list[RagCitation],
        Field(default_factory=list, description="RAG citations (Phase 5 populates)"),
    ]
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Model self-reported confidence")]
    model: Annotated[
        str,
        Field(
            pattern=r"^[a-z0-9.\-]+@[a-z0-9.\-]+$",
            description="Model identifier: name@runtime (e.g. qwen2.5-7b@ollama-0.6)",
        ),
    ]
    prompt_hash: Annotated[
        str,
        Field(
            pattern=r"^[a-f0-9]{64}$",
            description="sha256 hex of final prompt+system (64 chars)",
        ),
    ]
    tokens: Annotated[TokenUsage, Field(description="Token accounting for this call")]
    duration_ms: Annotated[int, Field(ge=0, description="End-to-end duration in ms")]
