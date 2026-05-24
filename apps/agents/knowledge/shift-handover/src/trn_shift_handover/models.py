"""Request/response + domain Pydantic models for ShiftHandover (D-SH-01/02/03).

ShiftWindow + HandoverReport implement the frozen, citation-bearing handover schema:
    - ShiftWindow: tz-aware boundary validated (Pattern S-6).
    - HandoverReport: carries structured counts, equipment_status, narrative_summary,
      source_events, and citations list[RagCitation] for TRN-05 evidence tracing.
    - All models frozen=True + extra="forbid" (immutability + injection prevention).

Trust boundary mitigations:
    - T-08-04: ShiftWindow uses Pydantic field_validator for tz-aware datetimes
      and model_validator enforcing end > start; SQL uses $N parameterized
      placeholders in ShiftAggregator (aggregator.py).
    - Frozen + extra=forbid: no in-place mutation, no stray key injection.

D-SH-02 (resolved post-research): HandoverReport derives alerts, work-orders, quality
and downtime counts from audit.actions action_type rows only — NO ops.alerts /
ops.work_orders tables. The ShiftAggregator (aggregator.py) enforces this boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sft_agents.models.evidence import RagCitation


class ShiftWindow(BaseModel):
    """Validated shift time window (D-SH-01).

    Both boundaries must be tz-aware UTC datetimes (Pattern S-6).
    The model_validator enforces shift_end > shift_start so the aggregator
    never receives an inverted or zero-width window.

    Trust boundary (T-08-04):
        - field_validator rejects naive datetimes before any DB query.
        - frozen=True + extra="forbid" prevents post-creation mutation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    shift_start: datetime = Field(description="Shift window start (tz-aware UTC)")
    shift_end: datetime = Field(description="Shift window end (tz-aware UTC)")
    boundary_label: str = Field(description="Human-readable label, e.g. '06:00-14:00'")

    @field_validator("shift_start", "shift_end")
    @classmethod
    def _check_tz_aware(cls, v: datetime) -> datetime:
        """Reject naive datetimes (Pattern S-6 / T-08-04)."""
        if v.tzinfo is None:
            raise ValueError(
                f"ShiftWindow datetime must be tz-aware, got naive: {v!r}. "
                "Use datetime(..., tzinfo=timezone.utc) or datetime.now(timezone.utc)."
            )
        return v

    @model_validator(mode="after")
    def _check_end_after_start(self) -> "ShiftWindow":
        """Enforce shift_end > shift_start (reject inverted or zero-width windows)."""
        if self.shift_end <= self.shift_start:
            raise ValueError(
                f"shift_end must be strictly after shift_start, "
                f"got shift_start={self.shift_start!r}, shift_end={self.shift_end!r}."
            )
        return self


class HandoverReport(BaseModel):
    """Structured shift handover report compiled by ShiftAggregator (D-SH-01/02).

    Carries:
    - Count fields derived from audit.actions + maintenance.downtime_events
      (D-SH-02: NO ops.alerts / ops.work_orders tables).
    - equipment_status: latest per-asset status from audit rows.
    - narrative_summary: short executive summary (3-5 lines, LLM-generated).
    - source_events: raw event references for audit trail.
    - citations: list[RagCitation] for TRN-05 evidence tracing.

    All fields are frozen — ShiftAggregator.build_report() returns a new report;
    no field is mutated after construction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    shift_start: datetime = Field(description="Shift window start (tz-aware UTC)")
    shift_end: datetime = Field(description="Shift window end (tz-aware UTC)")
    boundary_label: str = Field(
        default="",
        description="Human-readable shift label, e.g. '06:00-14:00'",
    )

    # Derived counts (D-SH-02: from audit.actions action_type + downtime_events)
    open_alerts: int = Field(
        default=0,
        ge=0,
        description=(
            "Count of ANOMALY_ALERT action_type rows in the shift window. "
            "D-SH-02: no ops.alerts table — derived from audit.actions."
        ),
    )
    completed_work_orders: int = Field(
        default=0,
        ge=0,
        description=(
            "Count of DOWNTIME_VERDICT rows with work_order_id in audit.actions. "
            "D-SH-02: no ops.work_orders table — derived from audit.actions."
        ),
    )
    downtime_events: int = Field(
        default=0,
        ge=0,
        description="Count of maintenance.downtime_events rows in the shift window.",
    )
    quality_events: int = Field(
        default=0,
        ge=0,
        description="Count of QUALITY_VERDICT action_type rows in the shift window.",
    )

    # Equipment summary
    equipment_status: dict[str, str] = Field(
        default_factory=dict,
        description="Latest per-asset status string from audit rows: {asset_id: status}.",
    )

    # Narrative (LLM-generated, capped to 3-5 lines)
    narrative_summary: str = Field(
        default="",
        description=(
            "Executive summary of the shift (3-5 lines). "
            "Generated by LLM only for the narrative_summary field; "
            "all counts are computed deterministically. Kept LLM-free path under 30s (Pitfall §4)."
        ),
    )

    # Source event references for audit trail
    source_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Raw event dicts from audit.actions for audit traceability.",
    )

    # TRN-05: RAG citations for evidence panel
    citations: list[RagCitation] = Field(
        default_factory=list,
        description=(
            "RAG citations collected from evidence_panel JSONB rag_citations. "
            "Required by TRN-05 for shift-level evidence tracing."
        ),
    )


__all__ = [
    "HandoverReport",
    "ShiftWindow",
]
