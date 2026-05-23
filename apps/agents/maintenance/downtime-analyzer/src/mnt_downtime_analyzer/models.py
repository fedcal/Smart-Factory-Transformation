"""Pydantic models for DowntimeAnalyzer (plan 07-09, D-DA-03).

Models (all frozen + extra=forbid):
    - OEEReport   — OEE A×P×Q decomposition report + Pareto entries.
    - OEEMetrics  — Per-asset OEE breakdown.
    - ParetoEntry — Single Pareto entry with cumulative percent.
    - ReportRequest — On-demand /report endpoint body.

Re-exports:
    - DowntimeEvent from sim_textile.downtime_event_generator so callers can
      ``from mnt_downtime_analyzer.models import DowntimeEvent`` without
      coupling to sim-textile directly.

Security:
    - All datetime fields must be tz-aware UTC (Pattern S-6 / T-V7-naive-datetime).
    - Cross-field validator: OEEReport.window_end > window_start.
    - Sanity validator: OEEReport.oee ≈ availability × performance × quality (1e-6 tol).
    - ParetoEntry.reason_code: regex ``^[A-Z][A-Z0-9-]+$`` (MNT-05 stable code format).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Re-export DowntimeEvent so callers don't need to import sim_textile directly.
from sim_textile.downtime_event_generator import DowntimeEvent

__all__ = [
    "DowntimeEvent",
    "OEEMetrics",
    "OEEReport",
    "ParetoEntry",
    "ReportRequest",
]


# ---------------------------------------------------------------------------
# ParetoEntry
# ---------------------------------------------------------------------------


class ParetoEntry(BaseModel):
    """Single Pareto downtime entry with cumulative percent (D-DA-03).

    reason_code matches MNT-05 format ``^[A-Z][A-Z0-9-]+$``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason_code: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^[A-Z][A-Z0-9-]+$",
            description="MNT-05 reason code (e.g. WEAVING-BE-001).",
        ),
    ]
    total_downtime_min: Annotated[int, Field(ge=0, description="Total downtime minutes.")]
    occurrence_count: Annotated[int, Field(ge=0, description="Number of occurrences.")]
    cumulative_percent: Annotated[
        float,
        Field(ge=0.0, le=100.0, description="Running cumulative % of total downtime."),
    ]


# ---------------------------------------------------------------------------
# OEEMetrics (per-asset breakdown)
# ---------------------------------------------------------------------------


class OEEMetrics(BaseModel):
    """Per-asset OEE metrics breakdown (D-DA-03).

    Used in OEEReport.by_asset dict values.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: Annotated[str, Field(min_length=1)]
    availability: Annotated[float, Field(ge=0.0, le=1.0)]
    performance: Annotated[float, Field(ge=0.0, le=1.0)]
    quality: Annotated[float, Field(ge=0.0, le=1.0)]
    oee: Annotated[float, Field(ge=0.0, le=1.0)]
    total_downtime_min: Annotated[int, Field(ge=0)]
    event_count: Annotated[int, Field(ge=0)]


# ---------------------------------------------------------------------------
# OEEReport
# ---------------------------------------------------------------------------


class OEEReport(BaseModel):
    """OEE A×P×Q decomposition report (D-DA-03).

    Security / correctness invariants:
    - window_end > window_start (model_validator).
    - oee ≈ availability × performance × quality within 1e-6 (sanity check).
    - All datetime fields must be tz-aware UTC (Pattern S-6).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    window_start: Annotated[datetime, Field(description="UTC tz-aware window start.")]
    window_end: Annotated[datetime, Field(description="UTC tz-aware window end (> window_start).")]
    availability: Annotated[float, Field(ge=0.0, le=1.0)]
    performance: Annotated[float, Field(ge=0.0, le=1.0)]
    quality: Annotated[float, Field(ge=0.0, le=1.0)]
    oee: Annotated[float, Field(ge=0.0, le=1.0)]
    by_asset: Annotated[dict[str, OEEMetrics] | None, Field(default=None)]
    pareto: Annotated[list[ParetoEntry], Field(description="Top-N Pareto downtime entries.")]
    report_id: Annotated[str, Field(min_length=1, description="UUID4 report identifier.")]
    generated_at: Annotated[datetime, Field(description="UTC tz-aware generation timestamp.")]

    @field_validator("window_start", "window_end", "generated_at")
    @classmethod
    def _ensure_tz_aware(cls, v: datetime) -> datetime:
        """Reject naive datetime (Pattern S-6 / T-V7-naive-datetime)."""
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError(f"Datetime field must be tz-aware UTC, got naive: {v!r}")
        return v

    @model_validator(mode="after")
    def _check_window_order(self) -> "OEEReport":
        """window_end must be strictly after window_start."""
        if self.window_end <= self.window_start:
            raise ValueError(
                f"window_end ({self.window_end}) must be strictly after "
                f"window_start ({self.window_start})"
            )
        return self

    @model_validator(mode="after")
    def _check_oee_product(self) -> "OEEReport":
        """Sanity check: oee ≈ availability × performance × quality (tolerance 1e-6).

        Guards against caller-side miscalculation before the report is persisted.
        """
        expected = self.availability * self.performance * self.quality
        if abs(self.oee - expected) > 1e-6:
            raise ValueError(
                f"OEEReport.oee ({self.oee:.8f}) does not equal "
                f"availability × performance × quality ({expected:.8f}); "
                f"delta={abs(self.oee - expected):.2e}"
            )
        return self


# ---------------------------------------------------------------------------
# ReportRequest
# ---------------------------------------------------------------------------


class ReportRequest(BaseModel):
    """Request body for the on-demand POST /v1/agents/downtime-analyzer/report endpoint.

    top_n_pareto is capped at 100 (T-V7-da-pareto-flood mitigation).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    window_start: Annotated[datetime, Field(description="Window start (tz-aware).")]
    window_end: Annotated[datetime, Field(description="Window end (tz-aware, > window_start).")]
    by_asset: Annotated[bool, Field(default=False, description="Include per-asset breakdown.")]
    top_n_pareto: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=100,
            description="Top-N Pareto entries to return (1..100; T-V7-da-pareto-flood cap).",
        ),
    ]
