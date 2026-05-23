"""Request/response + domain Pydantic models for RCASpecialist (D-RCA-01).

WhyStep + RCAChain implement the **form-based 5-Why fixed schema**:
    - 5 named fields why_1..why_5 (NOT a dynamic list) for explicitness + audit.
    - Every WhyStep carries at least 1 RagCitation (min_length=1).
    - Every RCAChain.created_at is tz-aware UTC (Pattern S-6).
    - All models frozen=True + extra=forbid (immutability + injection prevention).

Trust boundary mitigations:
    - T-V7-rca-injection-problem-statement: min_length=10 + max_length=2000 on
      problem_statement (both RCAChain + RCASpecialistRequest).
    - T-V7-rca-naive-datetime: field_validator on created_at rejects naive datetime.
    - Frozen + extra=forbid: no in-place mutation, no stray key injection.

D-RCA-01 field names verified against 07-CONTEXT.md L77-97:
    - WhyStep.citations uses `list[RagCitation]` imported from sft_agents.models.evidence.
    - RagCitation.source_uri is the canonical URI field (confirmed from sft_agents/models/evidence.py).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sft_agents.models.evidence import RagCitation


class WhyStep(BaseModel):
    """A single 'Why?' step in a 5-Why RCA chain (D-RCA-01).

    Every step is anchored by at least one RAG citation so the reasoning
    is traceable to a source document. The ``confidence`` field carries
    the LLM's self-reported certainty for observability dashboards.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    question: str = Field(
        min_length=1,
        max_length=500,
        description="The 'Why?' question for this step.",
    )
    answer: str = Field(
        min_length=1,
        max_length=2000,
        description="The answer to the 'Why?' question.",
    )
    citations: list[RagCitation] = Field(
        min_length=1,
        description=(
            "At least one RAG citation grounding the answer. "
            "Every source_uri is validated against PG documents table "
            "by RCAChainValidator (Open Q5 resolved as full PG lookup)."
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="LLM self-reported confidence for this step [0, 1].",
    )


class RCAChain(BaseModel):
    """5-Why Root Cause Analysis chain (D-RCA-01 form-based fixed schema).

    The 5 named ``why_*`` fields are intentional — they make the shape explicit
    and audit-friendly (EvidencePanel renderer, Phase 10) without requiring
    iteration logic on a dynamic list.

    ``downtime_event_id`` links to ``maintenance.downtime_events`` (07-05).
    ``created_at`` must be tz-aware UTC (Pattern S-6).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    chain_id: str = Field(description="UUID4 identifier for this RCA chain.")
    problem_statement: str = Field(
        min_length=10,
        max_length=2000,
        description="The failure / problem being investigated.",
    )
    why_1: WhyStep
    why_2: WhyStep
    why_3: WhyStep
    why_4: WhyStep
    why_5: WhyStep
    root_cause: str = Field(
        min_length=10,
        max_length=2000,
        description="The root cause identified at the end of the 5-Why chain.",
    )
    corrective_action_recommendation: str = Field(
        min_length=10,
        max_length=2000,
        description=(
            "Recommended corrective action. Always routed to supervisor HITL "
            "before being applied (D-RCA-02 literal)."
        ),
    )
    downtime_event_id: str | None = Field(
        default=None,
        description="Optional link to maintenance.downtime_events (07-05).",
    )
    created_at: datetime = Field(
        description="UTC tz-aware timestamp of chain creation."
    )

    @field_validator("created_at")
    @classmethod
    def _check_tz_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes (Pattern S-6 / T-V7-rca-naive-datetime)."""
        if v.tzinfo is None:
            raise ValueError(
                f"RCAChain.created_at must be tz-aware, got naive: {v!r}. "
                "Use datetime.now(timezone.utc) or datetime(..., tzinfo=timezone.utc)."
            )
        return v


class RCASpecialistRequest(BaseModel):
    """Input envelope for RCASpecialist (from API gateway 07-10).

    ``user_roles`` is propagated into ``RagSearchTool`` for ACL pre-filtering
    (Phase 5 D-66 — per-request injection, not cached on the agent).
    ``asset_id`` is an optional context hint for ``traverse_graph`` tool.

    Trust boundary: frozen + extra=forbid + length caps on ``problem_statement``
    (T-V7-rca-injection-problem-statement mitigation).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    problem_statement: str = Field(
        min_length=10,
        max_length=2000,
        description="The failure / problem to analyse.",
    )
    downtime_event_id: str | None = Field(
        default=None,
        description="Optional link to maintenance.downtime_events (07-05).",
    )
    user_roles: list[str] = Field(
        min_length=1,
        description="RBAC roles propagated to RagSearchTool ACL pre-filter.",
    )
    asset_id: str | None = Field(
        default=None,
        description="Optional asset identifier for traverse_graph context hint.",
    )


class RCASpecialistResponse(BaseModel):
    """Output envelope for RCASpecialist.

    ``chain`` is None when the validation loop was exhausted and no valid
    chain could be produced. ``hitl_status`` reflects the HITL lifecycle
    state after supervisor routing (D-RCA-02 ALWAYS supervisor).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    chain: RCAChain | None = Field(
        description=(
            "The validated RCAChain. None when rca_validation_exhausted=True "
            "and no valid chain was produced."
        )
    )
    hitl_status: Literal["supervisor_pending", "approved", "rejected"] = Field(
        description="HITL lifecycle state after supervisor routing.",
    )
    validation_exhausted: bool = Field(
        default=False,
        description=(
            "True when the retry loop exhausted all 3 attempts without "
            "producing a valid chain."
        ),
    )


__all__ = [
    "RCAChain",
    "RCASpecialistRequest",
    "RCASpecialistResponse",
    "WhyStep",
]
