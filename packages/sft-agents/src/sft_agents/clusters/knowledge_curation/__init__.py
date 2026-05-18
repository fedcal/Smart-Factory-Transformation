"""Knowledge-Curation cluster — editorial/governance, SLA hours (D-53).

Phase 1 scaffold maps to 2 child agents (Phase 8 fills business logic):
    knowledge-curator, documentation-synthesizer
"""
from __future__ import annotations

CLUSTER_NAME: str = "knowledge-curation"
CHILD_AGENT_SLUGS: list[str] = [
    "knowledge-curator",
    "documentation-synthesizer",
]

__all__ = ["CHILD_AGENT_SLUGS", "CLUSTER_NAME"]
