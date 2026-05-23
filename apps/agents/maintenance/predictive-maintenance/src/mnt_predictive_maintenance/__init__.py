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

from mnt_predictive_maintenance.agent import AGENT_ID, CLUSTER, PredictiveMaintenance
from mnt_predictive_maintenance.metadata import build_ops05_evidence_panel
from mnt_predictive_maintenance.models import PredictRequest, RULEstimate

__version__ = "0.1.0"

__all__ = [
    "AGENT_ID",
    "CLUSTER",
    "PredictiveMaintenance",
    "RULEstimate",
    "PredictRequest",
    "build_ops05_evidence_panel",
]
