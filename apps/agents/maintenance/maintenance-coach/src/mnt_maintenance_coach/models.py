"""Pydantic models for MaintenanceCoach agent (MNT-03 + MNT-06).

All models use ``frozen=True + extra='forbid'`` for immutability and strict
validation. tz-aware datetime validators follow Pattern S-6 (Pitfall §7).

Trust boundary: HTTP client input crosses into PG-persisted LangGraph state.
Mitigations:
  - ``technician_input``: min_length=1, max_length=4000
  - ``intervention_id``: min_length=1, max_length=64
  - ``current_step``: ge=0, le=100 (SOP cap per D-MC-01)
  - ``duration_minutes``: ge=0, le=10080 (1 week cap)
  - All datetime fields: tz-aware validator (T-V7-coach-naive-datetime)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sft_agents.models.evidence import RagCitation


# ---------------------------------------------------------------------------
# Shared tz-aware validator (Pattern S-6)
# ---------------------------------------------------------------------------


def _require_tz_aware(v: datetime) -> datetime:
    """Reject naive datetime (Pitfall §7 / T-V7-coach-naive-datetime)."""
    if v.tzinfo is None or v.utcoffset() is None:
        raise ValueError(
            f"datetime must be tz-aware (UTC), got naive: {v!r}. "
            "Use datetime.now(timezone.utc) or datetime(..., tzinfo=timezone.utc)."
        )
    return v


# ---------------------------------------------------------------------------
# StepReport — one completed SOP step (D-MC-01)
# ---------------------------------------------------------------------------


class StepReport(BaseModel):
    """A completed SOP step in the coached intervention.

    Captured after the technician confirms completion of a guided step.
    ``citations`` are the RAG snippets that grounded the LLM's instruction;
    they are optional because some SOP steps may be retrieved without RAG
    (e.g. LLM relies on embedded context).

    Constraints per D-MC-01 + trust boundary (T-V7-coach-injection-technician-input):
      - ``step_no``: ge=0 (zero-indexed), le=100 (SOP cap)
      - ``instruction``: min_length=1 (never empty)
      - ``technician_input``: min_length=1 (never empty)
      - ``duration_minutes``: ge=0, le=10080 (1 week cap; protects MTTR KPI)
      - ``completed_at``: tz-aware UTC (T-V7-coach-naive-datetime)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_no: int = Field(ge=0, le=100, description="Zero-indexed SOP step number")
    instruction: str = Field(min_length=1, description="LLM-generated guidance for this step")
    technician_input: str = Field(
        min_length=1,
        max_length=4000,
        description="Technician confirmation / notes for this step",
    )
    duration_minutes: int = Field(
        ge=0,
        le=10080,
        description="Active time spent on this step in minutes (1 week cap)",
    )
    completed_at: datetime = Field(description="UTC tz-aware completion timestamp")
    citations: list[RagCitation] = Field(
        default_factory=list,
        description="RAG citations that grounded the instruction (may be empty)",
    )

    @field_validator("completed_at")
    @classmethod
    def _check_completed_at_tz(cls, v: datetime) -> datetime:
        return _require_tz_aware(v)


# ---------------------------------------------------------------------------
# CoachThreadState — LangGraph persisted thread state (D-MC-01)
# ---------------------------------------------------------------------------


class CoachThreadState(BaseModel):
    """LangGraph thread state for a maintenance intervention.

    This model is the unit of checkpoint persistence via ``AsyncPostgresSaver``
    (Phase 4 migration 005 / ``langgraph_checkpoints`` table).

    Key design notes:
      - ``technician_id`` is nullable per the RCA auto-open path: the supervisor
        may open an intervention before assigning a technician. The first
        ``step_node`` invocation enforces non-null via HITL interrupt
        (Open Q3 RESOLVED — validator pre-step, not Pydantic constraint).
      - ``messages`` is ``list[Any]`` because ``langchain_core.messages.BaseMessage``
        is not Pydantic-natively-serializable in all versions. Serialization is
        delegated to ``AsyncPostgresSaver``'s msgpack codec (Phase 4 reuse).
      - ``current_step`` is bounded at 100 to match ``StepReport.step_no``
        and guard against unbounded LangGraph recursion.

    Trust boundary: validated at API ingestion (CoachStartRequest) and re-validated
    on checkpoint load (Pydantic model_validate on deserialization).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    intervention_id: str = Field(
        min_length=1,
        max_length=64,
        description="Client-generated UUID4 or server-assigned. Stable for the intervention lifecycle.",
    )
    asset_id: str = Field(min_length=1, description="Asset under maintenance (e.g. 'LOOM-01')")
    sop_id: str = Field(min_length=1, description="SOP identifier (e.g. 'SOP-LOOM-001')")
    technician_id: str | None = Field(
        default=None,
        description=(
            "Assigned technician ID. None on RCA auto-open path; "
            "step_node enforces non-null before executing step 0 via HITL interrupt."
        ),
    )
    current_step: int = Field(
        ge=0,
        le=100,
        description="Index of the next SOP step to execute (0-based)",
    )
    completed_steps: list[StepReport] = Field(
        default_factory=list,
        description="Steps completed so far (ordered by step_no)",
    )
    messages: list[Any] = Field(
        default_factory=list,
        description=(
            "LangChain message history (list[BaseMessage] in practice). "
            "Stored as list[Any] — serialization by AsyncPostgresSaver msgpack codec."
        ),
    )
    mttr_start: datetime = Field(
        description="UTC tz-aware timestamp when the intervention began (mttr_start)"
    )
    mttr_end: datetime | None = Field(
        default=None,
        description="UTC tz-aware timestamp when the intervention completed; None = open",
    )

    @field_validator("mttr_start")
    @classmethod
    def _check_mttr_start_tz(cls, v: datetime) -> datetime:
        return _require_tz_aware(v)

    @field_validator("mttr_end")
    @classmethod
    def _check_mttr_end_tz(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            return _require_tz_aware(v)
        return v


# ---------------------------------------------------------------------------
# CoachStartRequest — input from 07-10 api-gateway /start endpoint
# ---------------------------------------------------------------------------


class CoachStartRequest(BaseModel):
    """Request payload for POST /v1/agents/maintenance-coach/start.

    ``technician_id`` is optional — callers on the RCA auto-open path do not
    always know the technician at open time. The coach handles the None case
    by emitting a ``technician_assignment_required`` HITL interrupt at step 0.

    ``user_roles`` is required for RAG search ACL enforcement (Phase 5).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    intervention_id: str = Field(
        min_length=1,
        max_length=64,
        description="Client-generated UUID4; server rejects 409 if collision detected",
    )
    asset_id: str = Field(min_length=1)
    sop_id: str = Field(min_length=1)
    technician_id: str | None = Field(
        default=None,
        description="Optional: omit for RCA auto-open path",
    )
    user_roles: list[str] = Field(
        default_factory=list,
        description="Caller's roles for RAG search ACL (Phase 5)",
    )


# ---------------------------------------------------------------------------
# CoachStepRequest — input from 07-10 api-gateway /step endpoint
# ---------------------------------------------------------------------------


class CoachStepRequest(BaseModel):
    """Request payload for POST /v1/agents/maintenance-coach/step.

    ``technician_input`` is the technician's confirmation / notes / question
    for the current step. Length capped at 4000 chars to mitigate prompt injection
    payload bloat (T-V7-coach-injection-technician-input).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    intervention_id: str = Field(min_length=1, max_length=64)
    technician_input: str = Field(
        min_length=1,
        max_length=4000,
        description="Technician text input for the current step",
    )


# ---------------------------------------------------------------------------
# CoachResponse — API response shape for 07-10 api-gateway
# ---------------------------------------------------------------------------


class CoachResponse(BaseModel):
    """Response envelope for all maintenance-coach endpoints.

    ``state`` encodes the current phase of the coached intervention:
      - ``in_progress``: next guidance step returned; technician should continue.
      - ``awaiting_help``: technician triggered request_help; supervisor reviewing.
      - ``awaiting_technician_assignment``: intervention opened without technician_id;
        HITL supervisor must assign via /resume with ``{technician_id: '<id>'}``.
      - ``completed``: all SOP steps done; mttr_end is set; MTTR available.

    ``guidance_md``: next step guidance as Markdown (or completion message).
    ``completed_step``: the step report for the step just completed (None on first call).
    ``mttr_minutes_so_far``: pause-inclusive elapsed minutes (None if mttr_end not set).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    intervention_id: str = Field(min_length=1, max_length=64)
    current_step: int = Field(ge=0, le=100)
    guidance_md: str = Field(description="Next step guidance as Markdown")
    completed_step: StepReport | None = Field(
        default=None,
        description="Step report for the step just completed; None on first invocation",
    )
    mttr_minutes_so_far: int | None = Field(
        default=None,
        description="Pause-inclusive elapsed minutes since intervention start; None if open",
    )
    state: Literal[
        "in_progress",
        "awaiting_help",
        "awaiting_technician_assignment",
        "completed",
    ] = Field(description="Current lifecycle state of the coached intervention")


__all__ = [
    "CoachResponse",
    "CoachStartRequest",
    "CoachStepRequest",
    "CoachThreadState",
    "StepReport",
]
