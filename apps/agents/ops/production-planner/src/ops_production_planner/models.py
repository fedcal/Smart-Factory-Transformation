"""Request/response Pydantic models for the ProductionPlanner agent (D-PP-04).

`PlanRequest` is the strict input contract validated by the agent at entry
(T-V6-injection mitigation: frozen + extra=forbid + Literal strategy +
bounded horizon_days). `PlanResponse` mirrors what the api-gateway returns
to the operator after the HITL cycle resumes.

Both models are immutable (Pydantic v2 ``frozen=True``) so downstream
consumers cannot mutate them post-validation.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    """Operator-supplied scheduling request (D-PP-04).

    Validated at agent entry. ``strategy`` is a Literal whitelist so any
    free-form string is rejected before reaching the heuristic dispatcher
    (T-V6-injection mitigation). ``horizon_days`` is bounded [1, 30] to
    prevent unbounded compute / huge ScheduleDraft payloads.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    strategy: Annotated[
        Literal["spt", "edd"],
        Field(description="Scheduling strategy: 'spt' (shortest-processing-time) or 'edd' (earliest-due-date)."),
    ]
    horizon_days: Annotated[
        int,
        Field(ge=1, le=30, description="Horizon window in days (1..30)."),
    ]
    user_roles: Annotated[
        list[str],
        Field(default_factory=list, description="Operator roles for RAG ACL pre-filter (Phase 5 D-72)."),
    ]


class PlanResponse(BaseModel):
    """ProductionPlanner response payload returned via api-gateway (D-PP-04).

    ``hitl_thread_id`` lets the UI poll the approval queue; ``proposed_action_id``
    matches the sha256-deterministic id derived from the ScheduleDraft so the
    UI can resolve the row idempotently.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    draft: Annotated[dict[str, Any], Field(description="ScheduleDraft dumped as JSON-mode dict.")]
    hitl_thread_id: Annotated[str, Field(min_length=1, description="LangGraph thread id used for the HITL interrupt.")]
    proposed_action_id: Annotated[UUID, Field(description="Deterministic ProposedAction id (sha256-derived).")]
