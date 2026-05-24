"""Knowledge agent: generates shift handover reports and action items.

Phase 8 Wave 3 (Plan 08-04): ShiftHandover dual-supervisor sequential HITL node.
"""

from trn_shift_handover.agent import AGENT_ID, CLUSTER, ShiftHandover

__version__ = "0.1.0"

__all__ = [
    "AGENT_ID",
    "CLUSTER",
    "ShiftHandover",
]
