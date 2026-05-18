"""Ops cluster — real-time factory floor, strict SLA (D-53).

Phase 1 scaffold maps to 4 child agents (Phase 6 fills business logic):
    operator-assistant, production-planner, quality-inspector, anomaly-detector
"""
from __future__ import annotations

CLUSTER_NAME: str = "ops"
CHILD_AGENT_SLUGS: list[str] = [
    "operator-assistant",
    "production-planner",
    "quality-inspector",
    "anomaly-detector",
]

__all__ = ["CHILD_AGENT_SLUGS", "CLUSTER_NAME"]
