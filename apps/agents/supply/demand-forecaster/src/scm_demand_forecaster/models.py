"""Pydantic models for DemandForecaster (SCM-04).

Models:
    SkuForecast  — forecast for a single SKU group.
    DemandPlan   — collection of SkuForecast covering >= 2 SKU groups.
    MapeReport   — rolling MAPE KPI with le=100 constraint (CR-05).

All models are frozen + extra="forbid" per project cross-cutting idioms.
plan_id is a string set by the agent from the stable thread_id hash (CR-04).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class SkuForecast(BaseModel):
    """Demand forecast for one SKU group.

    Attributes:
        sku_group:  SKU group identifier (e.g. "jersey", "twill").
        horizon:    Number of forecast months.
        forecast:   List of forecast values (monthly kg), len == horizon, all >= 0.
        method:     "holt_winters" | "seasonal_naive" (for downstream transparency).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    sku_group: Annotated[str, Field(min_length=1, description="SKU group identifier")]
    horizon: Annotated[int, Field(ge=1, description="Number of forecast steps")]
    forecast: Annotated[
        list[float],
        Field(description="Forecast values (kg/month), len == horizon, all >= 0"),
    ]
    method: Annotated[str, Field(min_length=1, description="holt_winters | seasonal_naive")]


class DemandPlan(BaseModel):
    """Approved demand plan covering >= 2 SKU groups (SCM-04).

    The plan is published to ProductionPlanner via state['demand_plan'] after
    supervisor sign-off (Open Question 2 — cross-cluster via state, not direct call).

    Attributes:
        plan_id:   Stable plan identifier derived from thread_id hash (CR-04).
        sku_groups: List of SkuForecast, must cover >= 2 different SKU groups.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    plan_id: Annotated[str, Field(min_length=1, description="Stable plan id from thread_id hash (CR-04)")]
    sku_groups: Annotated[
        list[SkuForecast],
        Field(min_length=2, description="Forecasts for >= 2 SKU groups"),
    ]


class MapeReport(BaseModel):
    """Rolling MAPE accuracy KPI for DemandForecaster.

    The mape field is constrained to [0.0, 100.0] (CR-05 — Phase 8 Pitfall 6:
    KPI exceeding le= constraint causes ValidationError at construction time).
    Callers MUST clamp the MAPE value to <= 100.0 before constructing this model.

    Attributes:
        mape:       MAPE percentage in [0.0, 100.0].
        n_pairs:    Number of (actual, forecast) pairs used in computation.
        plan_id:    Correlated plan_id for traceability.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    mape: Annotated[
        float,
        Field(ge=0.0, le=100.0, description="MAPE percentage, clamped to [0.0, 100.0] (CR-05)"),
    ]
    n_pairs: Annotated[int, Field(ge=0, description="Number of (actual, forecast) pairs used")]
    plan_id: Annotated[str, Field(min_length=1, description="Correlated plan_id")]


__all__ = ["SkuForecast", "DemandPlan", "MapeReport"]
