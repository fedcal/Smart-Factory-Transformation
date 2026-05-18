"""sft_agents.audit — NATS audit dual-write substrate (Plan 04-04).

Public surface:
    AuditNatsPublisher              — JetStream publisher (Task 04-04-02)
    subject_for_audit               — D-56 dual-write audit replica subject
    subject_for_approval_new        — D-55 new approval notify subject
    subject_for_approval_resolved   — D-55 approval decided notify subject
    subject_for_governor_alert      — D-58 governor alert constant
    validate_subject                — defense-in-depth subject validator
    STREAM_SUBJECTS / VALID_CLUSTERS — module constants
"""

from __future__ import annotations

from sft_agents.audit.nats_publisher import AuditNatsPublisher
from sft_agents.audit.subjects import (
    STREAM_SUBJECTS,
    VALID_CLUSTERS,
    subject_for_approval_new,
    subject_for_approval_resolved,
    subject_for_audit,
    subject_for_governor_alert,
    validate_subject,
)

__all__ = [
    "STREAM_SUBJECTS",
    "VALID_CLUSTERS",
    "AuditNatsPublisher",
    "subject_for_approval_new",
    "subject_for_approval_resolved",
    "subject_for_audit",
    "subject_for_governor_alert",
    "validate_subject",
]
