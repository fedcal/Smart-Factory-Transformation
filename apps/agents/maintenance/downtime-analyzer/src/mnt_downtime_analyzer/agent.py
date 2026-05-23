"""DowntimeAnalyzer LangGraph node — on-demand /report generation (plan 07-09, D-DA-03).

Full implementation in Task 4. This stub satisfies imports during Tasks 2-3.
"""

from __future__ import annotations

#: Logical agent identifier (matches audit.actions.agent_id).
AGENT_ID: str = "downtime-analyzer"

#: Cluster the agent belongs to.
CLUSTER: str = "maintenance"


class DowntimeAnalyzer:
    """Stub — full implementation in Task 4."""

    def __init__(self, **kwargs: object) -> None:  # noqa: ANN401
        raise NotImplementedError("DowntimeAnalyzer stub — Task 4 implements this.")


__all__ = ["AGENT_ID", "CLUSTER", "DowntimeAnalyzer"]
