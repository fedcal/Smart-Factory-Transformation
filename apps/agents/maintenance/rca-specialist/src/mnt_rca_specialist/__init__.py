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

from mnt_rca_specialist.agent import AGENT_ID, CLUSTER, RCASpecialist
from mnt_rca_specialist.metadata import build_ops05_evidence_panel
from mnt_rca_specialist.models import (
    RCAChain,
    RCASpecialistRequest,
    RCASpecialistResponse,
    WhyStep,
)
from mnt_rca_specialist.validators import RCAChainValidator

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
