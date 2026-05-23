"""Request / response Pydantic models for the AnomalyDetector agent (Plan 06-06).

These are NOT persisted shapes — they only document the I/O contract callers
should use when invoking the agent outside of LangGraph (e.g. a one-shot
scheduler tick, an HTTP endpoint, a CLI tool). Inside LangGraph the agent's
``__call__`` receives the ``AgentState`` TypedDict directly.

Both models are ``frozen=True, extra='forbid'`` to keep boundary inputs
immutable + schema-strict (T-V6-injection mitigation, mirrors the convention
used throughout sft-domain / sft-agents).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field
from sft_domain.ops.anomaly import Anomaly


class AnomalyScanRequest(BaseModel):
    """Inputs for one AnomalyDetector scan tick (D-AD-01).

    ``window_minutes`` mirrors the ``state.get("window_minutes", 15)`` read
    inside ``AnomalyDetector.__call__``: the agent looks at the last N
    minutes of sensor history for every asset in the registry.

    ``triggered_by`` is metadata so audit consumers can chart who pulled the
    trigger (scheduled background loop, operator-issued one-shot, peer-agent
    cascade).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    window_minutes: Annotated[
        int,
        Field(
            default=15,
            ge=1,
            le=180,
            description="Sliding window size in minutes (1..180; default 15).",
        ),
    ] = 15
    triggered_by: Annotated[
        Literal["scheduler", "operator", "agent"],
        Field(
            default="scheduler",
            description="Caller class — observability tag for the audit row.",
        ),
    ] = "scheduler"


class AnomalyScanResponse(BaseModel):
    """Result of one AnomalyDetector scan tick (D-AD-01).

    ``anomalies`` are the rows that crossed the 12-alert/h gate and were
    emitted. ``suppressed_count`` is how many additional rows were dropped by
    the rate limiter — surfaced separately so the caller can chart the
    suppression rate without scanning ``audit.actions``.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    anomalies: Annotated[
        list[Anomaly],
        Field(description="Out-of-band anomalies emitted in this tick."),
    ]
    suppressed_count: Annotated[
        int,
        Field(
            default=0,
            ge=0,
            description="Anomalies that crossed the band but were dropped "
            "by the 12/h RateLimiter — written to audit as "
            "Decision.SUPPRESSED for traceability.",
        ),
    ] = 0


__all__ = ["AnomalyScanRequest", "AnomalyScanResponse"]
