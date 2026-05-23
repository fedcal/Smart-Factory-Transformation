"""Pydantic models for PredictiveMaintenance agent (D-PM-04).

RULEstimate: frozen + extra=forbid + D-PM-04 verbatim field set.
PredictRequest: NATS payload schema consumed by pm-consumer.

Pattern S-6: tz-aware datetime validators (@field_validator mode='after').
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RULEstimate(BaseModel):
    """Remaining Useful Life estimate per D-PM-04.

    Frozen + extra=forbid ensures the estimate is immutable once constructed
    and no undocumented fields can be injected downstream.

    Fields
    ------
    estimate_id:
        str(uuid4()) — unique identifier for this estimate.
    asset_id:
        Textile asset identifier (e.g. 'LOOM-01').
    rul_cycles:
        Point estimate of remaining useful cycles (>= 0).
    confidence_band_lower:
        Lower bound of the ±10% CI band (>= 0).
    confidence_band_upper:
        Upper bound of the ±10% CI band (>= 0).
    health_index:
        Derived deterministically from rul_cycles: clamp(rul_cycles / 125.0, 0.0, 1.0).
        Bound to [0.0, 1.0]; values < 0.3 trigger the HITL supervisor gate.
    recommended_action:
        Human-readable IT intervention message populated ONLY when health_index < 0.3
        (HITL branch). None for AUTO branch.
    triggered_by_action_id:
        UUID string of the upstream AnomalyDetector audit row's action_id.
        Enables MNT-06 SQL JOIN audit chain reconstruction.
    model_version:
        Identifier of the loaded joblib model (e.g. 'ridge-fd001-fd003-v1.0').
    created_at:
        UTC tz-aware timestamp of estimate creation. Naive datetime rejected
        (Pattern S-6 / T-V7-pm-naive-datetime).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    estimate_id: Annotated[str, Field(min_length=1, description="str(uuid4())")]
    asset_id: Annotated[str, Field(min_length=1, description="Asset identifier (e.g. LOOM-01)")]
    rul_cycles: Annotated[int, Field(ge=0, description="Remaining useful cycles point estimate")]
    confidence_band_lower: Annotated[int, Field(ge=0, description="CI lower bound (>=0)")]
    confidence_band_upper: Annotated[int, Field(ge=0, description="CI upper bound (>=0)")]
    health_index: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="clamp(rul_cycles / 125.0, 0.0, 1.0)"),
    ]
    recommended_action: Annotated[
        str | None,
        Field(default=None, description="HITL-branch IT intervention message; None for AUTO"),
    ] = None
    triggered_by_action_id: Annotated[
        str | None,
        Field(default=None, description="AnomalyDetector audit row action_id for MNT-06 chain"),
    ] = None
    model_version: Annotated[str, Field(min_length=1, description="Loaded model identifier")]
    created_at: Annotated[datetime, Field(description="UTC tz-aware timestamp")]

    @field_validator("created_at", mode="after")
    @classmethod
    def _check_tz(cls, v: datetime) -> datetime:
        """Reject naive datetime (Pattern S-6 / T-V7-pm-naive-datetime)."""
        if v.tzinfo is None:
            raise ValueError(
                f"RULEstimate.created_at must be tz-aware UTC, got naive: {v!r}. "
                "Use datetime.now(timezone.utc)."
            )
        return v


class PredictRequest(BaseModel):
    """NATS payload schema published by AnomalyDetector and consumed by pm-consumer.

    Frozen + extra=forbid — malformed payloads are ack-dropped as poison-pill
    in the consumer (T-V7-pm-payload-injection mitigation).

    severity is constrained to the three PM-relevant tier values:
    minor, major, critical. The AD publish hook filters to {major, critical}
    before publishing; minor is included here for completeness but the consumer
    can ack-drop minor messages if received.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: Annotated[str, Field(min_length=1, description="Asset identifier (e.g. LOOM-01)")]
    triggered_by_action_id: Annotated[
        str | None,
        Field(default=None, description="AD audit row action_id for MNT-06 chain"),
    ] = None
    severity: Annotated[
        Literal["minor", "major", "critical"],
        Field(description="Anomaly severity that triggered this request"),
    ]
    emitted_at: Annotated[datetime, Field(description="UTC tz-aware timestamp of AD emit")]

    @field_validator("emitted_at", mode="after")
    @classmethod
    def _check_tz(cls, v: datetime) -> datetime:
        """Reject naive datetime (Pattern S-6 / T-V7-pm-naive-datetime)."""
        if v.tzinfo is None:
            raise ValueError(
                f"PredictRequest.emitted_at must be tz-aware UTC, got naive: {v!r}. "
                "Use datetime.now(timezone.utc)."
            )
        return v


__all__ = ["RULEstimate", "PredictRequest"]
