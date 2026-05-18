"""AuditRecord Pydantic projection of audit.actions (D-56).

Cross-cutting validators (HITL-07 + Claude's Discretion line 431):
    - decision starts with 'hitl_' implies motivation non-empty AND approval_id NOT NULL
    - decision == 'auto' implies approval_id IS NULL

These are mechanical mirrors of the PG-side CHECK constraints (Plan 04-02 ships REVOKE
UPDATE/DELETE; this layer makes the constraint visible at the SDK boundary).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import Decision
from sft_agents.models.evidence import EvidencePanel


class AuditRecord(BaseModel):
    """Pydantic projection of audit.actions row (D-56).

    Trust boundary: untrusted LLM output (in evidence_panel) crosses into PG-persisted audit.
    Mitigations:
        - frozen + extra=forbid (post-construction tamper blocked)
        - HITL-07 motivation-required validator
        - approval_id consistency validator (auto vs hitl_*)
    """

    model_config = {"frozen": True, "extra": "forbid"}

    id: Annotated[UUID, Field(description="audit.actions.id (UUID PK)")]
    ts: Annotated[datetime, Field(description="UTC tz-aware write timestamp")]
    action_id: Annotated[UUID, Field(description="Agent's intra-execution action UUID")]
    agent_id: Annotated[str, Field(min_length=1)]
    thread_id: Annotated[str, Field(min_length=1)]
    cluster: Annotated[str, Field(min_length=1)]
    action_type: Annotated[str, Field(min_length=1)]
    evidence_panel: Annotated[EvidencePanel, Field(description="Embedded EvidencePanel (HITL-06)")]
    decision: Annotated[Decision, Field(description="Audit outcome")]
    decision_actor: Annotated[
        str | None,
        Field(default=None, description="user_id for HITL decisions; None for auto"),
    ] = None
    motivation: Annotated[
        str | None,
        Field(default=None, description="Required iff decision starts with hitl_ (HITL-07)"),
    ] = None
    budget_snapshot: Annotated[BudgetSnapshot, Field(description="Budget envelope at decision time")]
    approval_id: Annotated[
        UUID | None,
        Field(
            default=None,
            description="FK to hitl.approvals.id; required iff hitl_*; NULL for auto",
        ),
    ] = None

    @field_validator("ts")
    @classmethod
    def _check_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError(f"AuditRecord.ts must be tz-aware, got naive: {v!r}")
        return v

    @model_validator(mode="after")
    def _check_decision_consistency(self) -> "AuditRecord":
        """Enforce HITL-07 + Claude's Discretion line 431.

        Rules:
          1. decision in {hitl_operator, hitl_supervisor, hitl_manager}:
             motivation MUST be non-empty AND approval_id MUST NOT be None.
          2. decision == 'auto': approval_id MUST be None.
        """
        dec = self.decision.value
        is_hitl = dec.startswith("hitl_")

        if is_hitl:
            if not self.motivation:
                raise ValueError(
                    f"motivation is required when decision={dec!r} (HITL-07). "
                    f"Got motivation={self.motivation!r}."
                )
            if self.approval_id is None:
                raise ValueError(
                    f"approval_id is required when decision={dec!r} "
                    f"(audit.actions FK to hitl.approvals). Got None."
                )

        if dec == "auto" and self.approval_id is not None:
            raise ValueError(
                "approval_id must be None when decision='auto' "
                f"(Claude's Discretion line 431). Got approval_id={self.approval_id!r}."
            )

        return self
