"""mnt-maintenance-coach — MaintenanceCoach agent (MNT-03 + MNT-06).

Conversational multi-turn LangGraph agent that guides factory technicians
step-by-step through SOPs during a maintenance intervention.

Key features:
  - Async LangGraph thread with PG checkpoint persistence (Phase 4 migration 005)
  - Cross-shift resume via stable ``coach-<intervention_id>`` thread_id
  - MTTR measurement: elapsed + active-work separation
  - Bilingual IT/EN keyword detection for help escalation (D-MC-02)
  - Per-step COACH_STEP audit rows (MNT-06)
"""

from __future__ import annotations

__version__ = "0.1.0"

# Re-export public surface for downstream consumers (07-10 api-gateway, 07-12 E2E)
from mnt_maintenance_coach.agent import (
    AGENT_ID,
    CLUSTER,
    MaintenanceCoach,
    build_coach_graph,
)
from mnt_maintenance_coach.metadata import (
    DATA_SOURCES,
    KPIS_IMPACTED,
    TOOL_INVENTORY,
    build_ops05_evidence_panel,
)
from mnt_maintenance_coach.models import (
    CoachResponse,
    CoachStartRequest,
    CoachStepRequest,
    CoachThreadState,
    StepReport,
)
from mnt_maintenance_coach.mttr import compute_active_work_minutes, compute_mttr_minutes

__all__ = [
    # agent
    "AGENT_ID",
    "CLUSTER",
    "MaintenanceCoach",
    "build_coach_graph",
    # models
    "CoachThreadState",
    "StepReport",
    "CoachStartRequest",
    "CoachStepRequest",
    "CoachResponse",
    # mttr
    "compute_mttr_minutes",
    "compute_active_work_minutes",
    # metadata
    "TOOL_INVENTORY",
    "DATA_SOURCES",
    "KPIS_IMPACTED",
    "build_ops05_evidence_panel",
]
