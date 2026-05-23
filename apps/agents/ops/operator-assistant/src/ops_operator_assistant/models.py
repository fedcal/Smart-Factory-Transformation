"""Request/response Pydantic models for the OperatorAssistant agent.

OperatorChatRequest mitigates T-V6-injection:
    - ``frozen=True``  immutability (no in-place mutation after validation)
    - ``extra="forbid"``  reject unknown fields (prevents prompt-injection
      payload bloat via stray keys)
    - ``query`` is length-capped to [1, 2000] chars (the same cap used by
      ``EscalateToSupervisorTool.EscalateInput`` for symmetry).
    - ``user_roles`` is propagated per-request into the ACL-aware
      ``RagSearchTool`` (Pitfall §2).

OperatorChatResponse exposes the surface consumed by the API layer in
plan 06-12 + the EvidencePanel-shaped structure in plan 06-13:
    - ``response_md``: the final markdown answer.
    - ``citations``: the RagCitation-shaped list (kept as ``list[dict]``
      to avoid coupling this PoC layer to the full RagCitation Pydantic
      class; downstream callers re-validate as needed).
    - ``citations_missing``: D-OA-04 flag set when the citation validator
      could not enforce inline ``[N]`` references after one replan.
    - ``lang``: Literal["it","en"]; matches the detected query language.
    - ``tool_calls_count``: count of ToolMessage entries in the final
      conversation buffer (useful for Phase 11 observability).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OperatorChatRequest(BaseModel):
    """Operator chat request envelope (T-V6-injection mitigation)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(
        min_length=1,
        max_length=2000,
        description="Operator question (free text, IT or EN).",
    )
    user_roles: list[str] = Field(
        description=(
            "RBAC roles propagated to RagSearchTool ACL pre-filter. "
            "Per-request injection (Pitfall §2)."
        ),
    )
    thread_id: str = Field(
        min_length=1,
        max_length=200,
        description="LangGraph thread_id for checkpoint persistence.",
    )
    target_agent: str | None = Field(
        default=None,
        description=(
            "Optional explicit OPS-cluster routing target (set by API gateway "
            "or supervisor's HybridRouter); None means 'OperatorAssistant'."
        ),
    )


class OperatorChatResponse(BaseModel):
    """Operator chat response (consumed by API + EvidencePanel)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    response_md: str = Field(description="Final markdown answer to the operator.")
    citations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="RagCitation-shaped entries (D-66).",
    )
    citations_missing: bool = Field(
        default=False,
        description="True when validate_or_replan could not enforce [N] inline refs.",
    )
    lang: Literal["it", "en"] = Field(description="Detected query language.")
    tool_calls_count: int = Field(
        default=0,
        ge=0,
        description="Number of ToolMessage entries observed in the ReAct conversation.",
    )


__all__ = ["OperatorChatRequest", "OperatorChatResponse"]
