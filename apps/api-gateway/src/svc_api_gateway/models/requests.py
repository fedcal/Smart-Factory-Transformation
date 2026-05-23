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


# ---------------------------------------------------------------------------
# OPS-agent request shapes (Plan 06-12).
#
# These intentionally mirror the per-agent ``models.py`` Pydantic contracts
# from apps/agents/ops/<slug>/src/ops_<slug>/models.py — re-declared here so
# the api-gateway does not need to depend on every ops-agent package as a
# Python import. Validation rules MUST stay in sync; the integration tests in
# plan 06-13 verify identical behaviour at the HTTP boundary.
# ---------------------------------------------------------------------------


class AnomalyScanRequestBody(BaseModel):
    """POST /v1/agents/anomaly-detector/scan body (mirrors ops_anomaly_detector.models.AnomalyScanRequest)."""

    model_config = {"frozen": True, "extra": "forbid"}

    window_minutes: Annotated[
        int,
        Field(
            default=15,
            ge=1,
            le=180,
            description="Sliding window in minutes (1..180; default 15).",
        ),
    ] = 15
    triggered_by: Annotated[
        Literal["scheduler", "operator", "agent"],
        Field(
            default="scheduler",
            description="Caller class — observability tag for the audit row.",
        ),
    ] = "scheduler"


class PlanRequestBody(BaseModel):
    """POST /v1/agents/production-planner/plan body (mirrors ops_production_planner.models.PlanRequest)."""

    model_config = {"frozen": True, "extra": "forbid"}

    strategy: Annotated[
        Literal["spt", "edd"],
        Field(description="Scheduling strategy: 'spt' or 'edd'."),
    ]
    horizon_days: Annotated[
        int,
        Field(ge=1, le=30, description="Horizon window in days (1..30)."),
    ]
    user_roles: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="Operator roles for RAG ACL pre-filter (Phase 5 D-72).",
        ),
    ]


class OperatorChatRequestBody(BaseModel):
    """POST /v1/agents/operator-assistant/chat body (mirrors ops_operator_assistant.models.OperatorChatRequest)."""

    model_config = {"frozen": True, "extra": "forbid"}

    query: Annotated[
        str,
        Field(
            min_length=1,
            max_length=2000,
            description="Operator question (free text, IT or EN).",
        ),
    ]
    user_roles: Annotated[
        list[str],
        Field(description="RBAC roles propagated to RagSearchTool ACL pre-filter."),
    ]
    thread_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="LangGraph thread_id for checkpoint persistence.",
        ),
    ]


__all__ = [
    "AnomalyScanRequestBody",
    "DecideRequest",
    "OperatorChatRequestBody",
    "PlanRequestBody",
    "ResumeRequest",
]
