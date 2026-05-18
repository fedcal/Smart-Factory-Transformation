"""BudgetSnapshot + BudgetLimits Pydantic models (D-60).

Per-thread+per-agent budget envelope passed alongside every AuditRecord.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class BudgetSnapshot(BaseModel):
    """Cumulative budget state for a single thread+agent (D-60).

    Phase 4 cost is simulated (no real $$/token mapping); Phase 11 wires real pricing.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    tokens_input: Annotated[int, Field(ge=0, default=0)] = 0
    tokens_output: Annotated[int, Field(ge=0, default=0)] = 0
    tokens_total: Annotated[int, Field(ge=0, default=0)] = 0
    cost_usd_simulated: Annotated[float, Field(ge=0.0, default=0.0)] = 0.0
    duration_ms: Annotated[int, Field(ge=0, default=0)] = 0
    limit_tokens: Annotated[int, Field(ge=0, description="Configured token cap")]
    limit_cost_usd: Annotated[float, Field(ge=0.0, description="Configured cost cap in USD")]
    limit_duration_s: Annotated[int, Field(ge=0, description="Configured wall-clock cap in seconds")]


class BudgetLimits(BaseModel):
    """Per-cluster / per-agent budget limits loaded from budgets.yaml (D-60)."""

    model_config = {"frozen": True, "extra": "forbid"}

    tokens: Annotated[int, Field(ge=0)]
    cost_usd: Annotated[float, Field(ge=0.0)]
    duration_s: Annotated[int, Field(ge=0)]
