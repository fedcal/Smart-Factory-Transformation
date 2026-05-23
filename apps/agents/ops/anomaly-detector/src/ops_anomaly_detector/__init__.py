"""Operations agent: anomaly detection on sensor streams (Plan 06-06).

Public exports:
    * ``AnomalyDetector`` — LangGraph node (async ``__call__``).
    * ``AGENT_ID`` / ``CLUSTER`` — identifiers shared with audit / rate-limit.
    * ``select_baseline`` — per-machine override-aware baseline lookup.
    * ``BaselineRegistry`` — registry type alias.
    * ``AnomalyScanRequest`` / ``AnomalyScanResponse`` — out-of-LangGraph
      I/O models for HTTP / CLI callers.
"""

from __future__ import annotations

from ops_anomaly_detector import metadata
from ops_anomaly_detector.agent import AGENT_ID, CLUSTER, AnomalyDetector
from ops_anomaly_detector.baseline import BaselineRegistry, select_baseline
from ops_anomaly_detector.metadata import build_ops05_evidence_panel
from ops_anomaly_detector.models import AnomalyScanRequest, AnomalyScanResponse

__version__ = "0.1.0"

__all__ = [
    "AGENT_ID",
    "CLUSTER",
    "AnomalyDetector",
    "AnomalyScanRequest",
    "AnomalyScanResponse",
    "BaselineRegistry",
    "build_ops05_evidence_panel",
    "metadata",
    "select_baseline",
]
