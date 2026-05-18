"""ApprovalRequest + ApprovalDecision (D-55).

Pydantic projection of `hitl.approvals` PG table (D-55 DDL — CONTEXT.md lines 131-150).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from sft_agents.models.enums import ApprovalStatus, Tier


def _tz_aware(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError(f"Datetime must be tz-aware, got naive: {v!r}")
    return v


class ApprovalRequest(BaseModel):
    """A pending / decided / escalated approval row from hitl.approvals (D-55)."""

    model_config = {"frozen": True, "extra": "forbid"}

    id: Annotated[UUID, Field(description="UUID primary key")]
    agent_id: Annotated[str, Field(min_length=1)]
    thread_id: Annotated[str, Field(min_length=1)]
    tier: Annotated[Tier, Field(description="Escalation tier")]
    action_type: Annotated[str, Field(min_length=1)]
    payload_json: Annotated[dict[str, Any], Field(description="Original action payload")]
    status: Annotated[ApprovalStatus, Field(default=ApprovalStatus.PENDING)] = ApprovalStatus.PENDING
    created_at: Annotated[datetime, Field(description="UTC tz-aware creation timestamp")]
    sla_deadline: Annotated[datetime, Field(description="UTC tz-aware SLA cutoff")]
    decided_at: Annotated[datetime | None, Field(default=None)] = None
    decided_by: Annotated[str | None, Field(default=None)] = None
    decision_json: Annotated[dict[str, Any] | None, Field(default=None)] = None
    escalated_to_id: Annotated[UUID | None, Field(default=None)] = None

    @field_validator("created_at", "sla_deadline")
    @classmethod
    def _check_required_tz(cls, v: datetime) -> datetime:
        return _tz_aware(v)

    @field_validator("decided_at")
    @classmethod
    def _check_optional_tz(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        return _tz_aware(v)


class ApprovalDecision(BaseModel):
    """The decision body posted to `POST /v1/approvals/{id}/decide` (D-55)."""

    model_config = {"frozen": True, "extra": "forbid"}

    decision: Annotated[
        Literal["approve", "reject", "escalate"],
        Field(description="Outcome decision verb"),
    ]
    motivation: Annotated[
        str,
        Field(min_length=1, description="Human-readable motivation (HITL-07 mandates non-empty)"),
    ]
    decided_by: Annotated[str, Field(min_length=1, description="User identifier who decided")]
