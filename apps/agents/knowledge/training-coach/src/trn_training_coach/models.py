"""Domain models for TrainingCoach (TRN-02 / D-TC-01/02/03).

TrainingSession and CompetencyResult are frozen Pydantic models mirroring the
rca-specialist frozen-model pattern (mnt_rca_specialist.models).

RagCitation is imported from sft_agents.models.evidence (TRN-05 citation chain).
All models enforce frozen=True + extra="forbid" (immutability + injection prevention).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from sft_agents.models.evidence import RagCitation


class TrainingSession(BaseModel):
    """Record of a completed training quiz session (D-TC-01).

    Persisted as a TRAINING_SESSION audit row (ActionType.TRAINING_SESSION).
    On a passing session (score >= pass_threshold), written AFTER the supervisor
    HITL interrupt resumes (W4/CR-02 ordering — prevents double-write on LangGraph replay).
    On a failing session, written immediately after scoring (no interrupt).

    citations: RAG citations used to generate quiz questions (TRN-05 traceability).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: Annotated[str, Field(min_length=1, description="UUID session identifier.")]
    persona_role: Annotated[str, Field(min_length=1, description="SOP frontmatter role (D-X-03).")]
    score: Annotated[float, Field(ge=0.0, le=1.0, description="Deterministic score in [0, 1].")]
    passed: Annotated[bool, Field(description="True when score >= pass_threshold (D-TC-03).")]
    threshold: Annotated[
        float, Field(ge=0.0, le=1.0, description="Pass threshold used for evaluation (default 0.80).")
    ]
    completed_at: Annotated[datetime, Field(description="UTC tz-aware completion timestamp.")]
    citations: Annotated[
        list[RagCitation],
        Field(default_factory=list, description="RAG citations used in quiz generation (TRN-05)."),
    ]


class CompetencyResult(BaseModel):
    """Result of a competency assessment session (D-TC-03).

    Summarises the quiz outcome and the HITL lifecycle state.
    Returned by TrainingCoach as the agent output envelope.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    persona_role: Annotated[str, Field(min_length=1, description="SOP frontmatter role assessed.")]
    score: Annotated[float, Field(ge=0.0, le=1.0, description="Final deterministic score.")]
    passed: Annotated[bool, Field(description="True when score >= pass_threshold.")]
    threshold: Annotated[float, Field(ge=0.0, le=1.0, description="Pass threshold applied.")]
    citations: Annotated[
        list[RagCitation],
        Field(default_factory=list, description="Source citations for traceability (TRN-05)."),
    ]


__all__ = ["CompetencyResult", "RagCitation", "TrainingSession"]
