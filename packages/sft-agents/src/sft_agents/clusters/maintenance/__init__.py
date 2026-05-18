"""Maintenance cluster — predictive horizon hours-to-days (D-53).

Phase 1 scaffold maps to 4 child agents (Phase 7 fills business logic):
    predictive-maintenance, rca-specialist, maintenance-coach, downtime-analyzer
"""
from __future__ import annotations

CLUSTER_NAME: str = "maintenance"
CHILD_AGENT_SLUGS: list[str] = [
    "predictive-maintenance",
    "rca-specialist",
    "maintenance-coach",
    "downtime-analyzer",
]

__all__ = ["CHILD_AGENT_SLUGS", "CLUSTER_NAME"]
