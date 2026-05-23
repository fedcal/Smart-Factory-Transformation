"""Internal request/response models for QualityInspector (D-QI-02 / D-QI-03).

These wrap the cross-cutting Pydantic models from ``sft_domain.ops.quality``
with agent-local context (user roles, HITL tier routing decision). They are
frozen + extra=forbid so they cannot drift from the strict shape that the
HITL pipeline expects.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from sft_domain.ops.quality import QualityEvent, QualityVerdict


class QualityInspectionRequest(BaseModel):
    """Wraps a QualityEvent with the operator/agent context (roles)."""

    model_config = {"frozen": True, "extra": "forbid"}

    event: Annotated[QualityEvent, Field(description="The defect event to grade.")]
    user_roles: Annotated[
        list[str],
        Field(
            default_factory=lambda: ["technician"],
            description="User roles for RAG ACL filtering (default: ['technician']).",
        ),
    ]


class QualityInspectionResponse(BaseModel):
    """The grading verdict plus the resolved HITL routing tier (D-QI-03).

    ``hitl_routed_to`` is one of:
        - ``"auto-log"``       : minor severity, no HITL.
        - ``"supervisor"``     : major severity (or failure_modes.yaml override).
        - ``"manager+safety"`` : critical severity (or YAML override).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    verdict: Annotated[QualityVerdict, Field(description="LLM-graded verdict.")]
    hitl_routed_to: Annotated[
        Literal["auto-log", "supervisor", "manager+safety"],
        Field(description="HITL tier routing decision (D-QI-03)."),
    ]


__all__ = ["QualityInspectionRequest", "QualityInspectionResponse"]
