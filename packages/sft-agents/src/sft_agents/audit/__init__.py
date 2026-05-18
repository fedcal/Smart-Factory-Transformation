"""sft_agents.audit — NATS audit dual-write substrate (Plan 04-04).

Module surface (Plan 04-04):
    - subjects helpers + constants (Task 04-04-01)
    - AuditNatsPublisher (Task 04-04-02)

Public re-exports are populated by Task 04-04-02 once the publisher lands.
"""

from __future__ import annotations

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
    "subject_for_approval_new",
    "subject_for_approval_resolved",
    "subject_for_audit",
    "subject_for_governor_alert",
    "validate_subject",
]
