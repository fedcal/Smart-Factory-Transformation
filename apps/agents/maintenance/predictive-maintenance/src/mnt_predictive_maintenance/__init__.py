"""PredictiveMaintenance agent package (MNT-01 / D-PM-04).

Re-exports the public surface consumed by the 07-10 api-gateway router
and 07-12 E2E scenarios:

    from mnt_predictive_maintenance import (
        AGENT_ID, CLUSTER,
        PredictiveMaintenance,
        RULEstimate, PredictRequest,
        build_ops05_evidence_panel,
    )
"""

from __future__ import annotations

from mnt_predictive_maintenance.metadata import build_ops05_evidence_panel
from mnt_predictive_maintenance.models import PredictRequest, RULEstimate

# Agent module: provides PredictiveMaintenance, AGENT_ID, CLUSTER.
# Imported at package init so callers can do:
#   from mnt_predictive_maintenance import PredictiveMaintenance
try:
    from mnt_predictive_maintenance.agent import AGENT_ID, CLUSTER, PredictiveMaintenance
except ImportError:
    # During TDD RED phase: agent.py not yet implemented.
    # Callers importing agent-level names will get ImportError when they try
    # to use them — this is correct RED behaviour.
    pass

__version__ = "0.1.0"

__all__ = [
    "AGENT_ID",
    "CLUSTER",
    "PredictiveMaintenance",
    "RULEstimate",
    "PredictRequest",
    "build_ops05_evidence_panel",
]
