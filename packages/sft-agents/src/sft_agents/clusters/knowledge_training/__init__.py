"""Knowledge-Training cluster — pedagogical / handover, SLA loose (D-53).

Phase 1 scaffold maps to 2 child agents (Phase 8 fills business logic):
    training-coach, shift-handover
"""
from __future__ import annotations

CLUSTER_NAME: str = "knowledge-training"
CHILD_AGENT_SLUGS: list[str] = [
    "training-coach",
    "shift-handover",
]

__all__ = ["CHILD_AGENT_SLUGS", "CLUSTER_NAME"]
