"""Pydantic response shapes — Plan 04-07 Task 2.

The router decouples wire-format from DB record by translating asyncpg row dicts
into Pydantic response models — this gives us a stable OpenAPI surface
independent of schema drift on hitl.approvals.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalResponse(BaseModel):
    """Mirror of hitl.approvals (D-55) decoupled from DB record shape."""

    model_config = {"frozen": True, "extra": "forbid"}

    id: UUID
    agent_id: str
    thread_id: str
    tier: str
    action_type: str
    payload: dict[str, Any]
    status: str
    created_at: datetime
    sla_deadline: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision: dict[str, Any] | None = None
    escalated_to_id: UUID | None = None


class ApprovalListResponse(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    items: list[ApprovalResponse]
    total: int
    limit: int
    offset: int


class DecideResponse(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    approval: ApprovalResponse
    audit_id: UUID | None = None
    resumed: bool


class ResumeResponse(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    thread_id: str
    state_after: dict[str, Any]
    audit_ids: list[UUID]
    completed: bool


class ErrorResponse(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    detail: str


def row_to_approval_response(row: dict[str, Any] | Any) -> ApprovalResponse:
    """Translate an asyncpg Record (or row-shaped dict) into ApprovalResponse.

    ``payload_json`` / ``decision_json`` arrive as text from PG (we select
    ``::text``); parse them defensively here so the wire shape is dict-based.
    """

    def _parse_json(v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return v
        if isinstance(v, (bytes, bytearray)):
            v = v.decode("utf-8")
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                # Some asyncpg paths return already-decoded values when JSONB.
                return {"_raw": v}
        return v

    return ApprovalResponse(
        id=row["id"],
        agent_id=row["agent_id"],
        thread_id=row["thread_id"],
        tier=row["tier"],
        action_type=row["action_type"],
        payload=_parse_json(row.get("payload_json")) or {},
        status=row["status"],
        created_at=row["created_at"],
        sla_deadline=row["sla_deadline"],
        decided_at=row.get("decided_at"),
        decided_by=row.get("decided_by"),
        decision=_parse_json(row.get("decision_json")),
        escalated_to_id=row.get("escalated_to_id"),
    )


__all__ = [
    "ApprovalListResponse",
    "ApprovalResponse",
    "DecideResponse",
    "ErrorResponse",
    "ResumeResponse",
    "row_to_approval_response",
]
