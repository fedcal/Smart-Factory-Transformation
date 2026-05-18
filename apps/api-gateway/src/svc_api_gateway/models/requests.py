"""Pydantic request shapes — Plan 04-07 Task 2.

DecideRequest is the body of POST /v1/approvals/{id}/decide.
ResumeRequest is the body of POST /v1/threads/{thread_id}/resume.

NOTE on motivation:
    Pydantic-level validation only enforces the Literal decision verb +
    decided_by min_length. The tier-based motivation requirement (mandatory
    for hitl_supervisor / hitl_manager / safety_interlock when decision in
    {approve, reject}) is enforced inside the router AFTER fetching the row
    (the tier is a DB-only fact, not a body field).
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DecideRequest(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    decision: Literal["approve", "reject", "escalate"]
    motivation: Annotated[
        str,
        Field(
            default="",
            description=(
                "Free-text motivation. REQUIRED for supervisor/manager/"
                "safety_interlock tiers on approve/reject (router-level check)."
            ),
        ),
    ] = ""
    decided_by: Annotated[
        str,
        Field(min_length=1, description="Identifier of the human decision-maker"),
    ]


class ResumeRequest(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    approval_id: Annotated[UUID, Field(description="Pending hitl.approvals row id")]
    decision: Literal["approve", "reject", "escalate"]
    motivation: Annotated[
        str,
        Field(
            default="",
            description="Mandatory on supervisor/manager/safety_interlock tiers",
        ),
    ] = ""
    decided_by: Annotated[str, Field(min_length=1)]


__all__ = ["DecideRequest", "ResumeRequest"]
