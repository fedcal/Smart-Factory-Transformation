"""sft_agents.hitl — Human-in-the-Loop interrupt/resume cycle (Plan 04-06 Task 02).

Public surface:
    human_approval_node         — LangGraph node that calls interrupt()/resume
    ApprovalQueueWriter         — INSERT/UPDATE/escalation against hitl.approvals
    ApprovalNotFoundError       — raised on stale resume id (T-04-Resume-Replay)
    GDPRRedactor                — pre-checkpoint PII stripping (T-04-Checkpoint-PII)
    redact_str / redact_evidence — convenience helpers
    tier_to_decision            — Tier → audit Decision mapping helper
"""

from __future__ import annotations

from sft_agents.hitl.approval_queue import ApprovalNotFoundError, ApprovalQueueWriter
from sft_agents.hitl.interrupt import human_approval_node, tier_to_decision
from sft_agents.hitl.redactor import GDPRRedactor, redact_evidence, redact_str

__all__ = [
    "ApprovalNotFoundError",
    "ApprovalQueueWriter",
    "GDPRRedactor",
    "human_approval_node",
    "redact_evidence",
    "redact_str",
    "tier_to_decision",
]
