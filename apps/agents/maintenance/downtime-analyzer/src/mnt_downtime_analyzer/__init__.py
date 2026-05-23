"""mnt-downtime-analyzer — DowntimeAnalyzer agent package (Phase 7 plan 07-09).

Re-exports all public symbols so callers can do:

    from mnt_downtime_analyzer import DowntimeAnalyzer, OEEReport, run_da_consumer
"""

from __future__ import annotations

from mnt_downtime_analyzer.agent import AGENT_ID, CLUSTER, DowntimeAnalyzer
from mnt_downtime_analyzer.consumer import DA_CONSUMER_NAME, DA_SUBJECT_PATTERN, run_da_consumer
from mnt_downtime_analyzer.metadata import build_ops05_evidence_panel
from mnt_downtime_analyzer.models import (
    DowntimeEvent,
    OEEMetrics,
    OEEReport,
    ParetoEntry,
    ReportRequest,
)
from mnt_downtime_analyzer.repository import DowntimeEventRepository, QualityVerdictReader

__version__ = "0.1.0"

__all__ = [
    "AGENT_ID",
    "CLUSTER",
    "DA_CONSUMER_NAME",
    "DA_SUBJECT_PATTERN",
    "DowntimeAnalyzer",
    "DowntimeEvent",
    "DowntimeEventRepository",
    "OEEMetrics",
    "OEEReport",
    "ParetoEntry",
    "QualityVerdictReader",
    "ReportRequest",
    "build_ops05_evidence_panel",
    "run_da_consumer",
]
