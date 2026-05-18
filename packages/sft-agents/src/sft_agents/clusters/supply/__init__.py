"""Supply cluster — batch-oriented forecasting, SLA loose (D-53).

Phase 1 scaffold maps to 4 child agents (Phase 9 fills business logic):
    inventory-manager, energy-optimizer, cost-analyzer, demand-forecaster
"""
from __future__ import annotations

CLUSTER_NAME: str = "supply"
CHILD_AGENT_SLUGS: list[str] = [
    "inventory-manager",
    "energy-optimizer",
    "cost-analyzer",
    "demand-forecaster",
]

__all__ = ["CHILD_AGENT_SLUGS", "CLUSTER_NAME"]
