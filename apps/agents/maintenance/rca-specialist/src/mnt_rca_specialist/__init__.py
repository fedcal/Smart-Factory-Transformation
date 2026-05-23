"""Maintenance RCA Specialist agent — 5-Why Root Cause Analysis with citation grounding.

MNT-02 + MNT-05 (Phase 7 D-RCA-01 + D-RCA-02).

Re-exports the main public API for external consumers (API gateway, tests):

    from mnt_rca_specialist import (
        AGENT_ID, CLUSTER,
        RCASpecialist,
        RCAChain, WhyStep,
        RCASpecialistRequest, RCASpecialistResponse,
        RCAChainValidator,
        build_ops05_evidence_panel,
    )
"""

from __future__ import annotations

from mnt_rca_specialist.metadata import build_ops05_evidence_panel
from mnt_rca_specialist.models import (
    RCAChain,
    RCASpecialistRequest,
    RCASpecialistResponse,
    WhyStep,
)
from mnt_rca_specialist.validators import RCAChainValidator

# agent.py is imported last to avoid circular deps; available after Task 3.
try:
    from mnt_rca_specialist.agent import AGENT_ID, CLUSTER, RCASpecialist
except ModuleNotFoundError:
    # agent.py not yet implemented (scaffold / wave-0 state)
    AGENT_ID = "rca-specialist"  # type: ignore[assignment]
    CLUSTER = "maintenance"  # type: ignore[assignment]
    RCASpecialist = None  # type: ignore[assignment,misc]

__version__ = "0.1.0"

__all__ = [
    "AGENT_ID",
    "CLUSTER",
    "RCAChain",
    "RCAChainValidator",
    "RCASpecialist",
    "RCASpecialistRequest",
    "RCASpecialistResponse",
    "WhyStep",
    "build_ops05_evidence_panel",
]
