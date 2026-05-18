"""Test suite for sft_agents.audit.subjects (Plan 04-04 Task 01).

Verifies NATS subject derivation helpers used by the audit dual-write (D-56) and
HITL approval / governor notifications (D-55, D-58):

    - subject_for_audit          → audit.actions.<cluster>.<agent_id>
    - subject_for_approval_new   → hitl.approvals.new.<tier>
    - subject_for_approval_resolved → hitl.approvals.resolved.<tier>
    - subject_for_governor_alert → hitl.governor.alert (constant)

Security focus (T-04-NATS-Spoofed):
    Subject derivation MUST refuse user-controlled strings that could hijack
    the NATS subject namespace (`*`, `>`, whitespace, semicolons, dots used as
    extra hierarchy levels). Inputs are constrained to enum values + a tight
    token regex `^[a-z0-9._-]+$`.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.audit.subjects",
    reason="Plan 04-04 Task 01 implements subject derivation helpers",
)

from sft_agents.audit.subjects import (  # noqa: E402
    STREAM_SUBJECTS,
    VALID_CLUSTERS,
    subject_for_approval_new,
    subject_for_approval_resolved,
    subject_for_audit,
    subject_for_governor_alert,
    validate_subject,
)
from sft_agents.models.enums import Tier  # noqa: E402

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """STREAM_SUBJECTS and VALID_CLUSTERS are the contract between the bootstrap
    script and the publisher helpers."""

    def test_stream_subjects_exact_wildcards(self) -> None:
        # MUST match the AUDIT_STREAM declaration in scripts/nats-bootstrap-streams.py
        assert tuple(STREAM_SUBJECTS) == (
            "audit.actions.>",
            "hitl.approvals.>",
            "hitl.governor.>",
        )

    def test_valid_clusters_exactly_five(self) -> None:
        # D-53 — 5 cluster subgraphs
        assert VALID_CLUSTERS == frozenset(
            {
                "ops",
                "maintenance",
                "knowledge-curation",
                "knowledge-training",
                "supply",
            }
        )


# ---------------------------------------------------------------------------
# subject_for_audit happy paths (1 per cluster)
# ---------------------------------------------------------------------------


class TestSubjectForAudit:
    """Happy-path derivation for every D-53 cluster."""

    def test_ops(self) -> None:
        assert (
            subject_for_audit(cluster="ops", agent_id="operator-assistant")
            == "audit.actions.ops.operator-assistant"
        )

    def test_maintenance(self) -> None:
        assert (
            subject_for_audit(cluster="maintenance", agent_id="predictive-maintenance")
            == "audit.actions.maintenance.predictive-maintenance"
        )

    def test_knowledge_curation(self) -> None:
        assert (
            subject_for_audit(cluster="knowledge-curation", agent_id="knowledge-curator")
            == "audit.actions.knowledge-curation.knowledge-curator"
        )

    def test_knowledge_training(self) -> None:
        assert (
            subject_for_audit(cluster="knowledge-training", agent_id="training-coach")
            == "audit.actions.knowledge-training.training-coach"
        )

    def test_supply(self) -> None:
        assert (
            subject_for_audit(cluster="supply", agent_id="inventory-manager")
            == "audit.actions.supply.inventory-manager"
        )


# ---------------------------------------------------------------------------
# subject_for_audit — cluster validation
# ---------------------------------------------------------------------------


class TestClusterValidation:
    """cluster MUST be in VALID_CLUSTERS — server-controlled enum, not user input."""

    def test_unknown_cluster_rejected(self) -> None:
        with pytest.raises(ValueError, match=r"cluster"):
            subject_for_audit(cluster="badcluster", agent_id="operator-assistant")

    def test_wildcard_cluster_rejected(self) -> None:
        with pytest.raises(ValueError):
            subject_for_audit(cluster=">", agent_id="operator-assistant")

    def test_empty_cluster_rejected(self) -> None:
        with pytest.raises(ValueError):
            subject_for_audit(cluster="", agent_id="operator-assistant")

    def test_case_mismatch_rejected(self) -> None:
        # VALID_CLUSTERS is lowercase only
        with pytest.raises(ValueError):
            subject_for_audit(cluster="Ops", agent_id="operator-assistant")


# ---------------------------------------------------------------------------
# subject_for_audit — agent_id injection attempts (T-04-NATS-Spoofed)
# ---------------------------------------------------------------------------


class TestAgentIdInjection:
    """agent_id MUST be rejected if it contains chars outside [a-z0-9._-].

    Inputs of these shapes are the canonical subject-hijack vectors per
    T-04-NATS-Spoofed.
    """

    @pytest.mark.parametrize(
        "bad_agent_id",
        [
            "*",  # NATS wildcard (single-token)
            ">",  # NATS wildcard (multi-token)
            "a>b",  # embedded multi-token wildcard
            "a*b",  # embedded single-token wildcard
            "a b",  # whitespace
            "a;rm -rf /",  # shell injection shape
            "evil; DROP",  # SQL-flavored injection
            "agent\nname",  # newline
            "UPPERCASE",  # uppercase forbidden
            "agent@evil",  # @ sign
            "a/b",  # slash
            "",  # empty
        ],
    )
    def test_invalid_agent_id_raises(self, bad_agent_id: str) -> None:
        with pytest.raises(ValueError):
            subject_for_audit(cluster="ops", agent_id=bad_agent_id)

    def test_extra_dot_hierarchy_rejected(self) -> None:
        # agent_id contains additional NATS hierarchy levels — the function would
        # accept the token regex on each piece, but the regex requires the full
        # string to be a single token, so dots are forbidden.
        # NOTE: the regex [a-z0-9._-] DOES allow '.', so we explicitly forbid this
        # at the subject_for_audit level (cluster.agent_id, no extra levels).
        with pytest.raises(ValueError):
            subject_for_audit(cluster="ops", agent_id="audit.actions.ops.evil")


# ---------------------------------------------------------------------------
# subject_for_approval_new / resolved — Tier enum
# ---------------------------------------------------------------------------


class TestApprovalSubjects:
    """tier MUST be a Tier enum value — server-controlled."""

    @pytest.mark.parametrize(
        ("tier", "expected"),
        [
            (Tier.OPERATOR, "hitl.approvals.new.operator"),
            (Tier.SUPERVISOR, "hitl.approvals.new.supervisor"),
            (Tier.MANAGER, "hitl.approvals.new.manager"),
            (Tier.SAFETY_INTERLOCK, "hitl.approvals.new.safety_interlock"),
        ],
    )
    def test_new_for_each_tier(self, tier: Tier, expected: str) -> None:
        assert subject_for_approval_new(tier=tier) == expected

    @pytest.mark.parametrize(
        ("tier", "expected"),
        [
            (Tier.OPERATOR, "hitl.approvals.resolved.operator"),
            (Tier.SUPERVISOR, "hitl.approvals.resolved.supervisor"),
            (Tier.MANAGER, "hitl.approvals.resolved.manager"),
            (Tier.SAFETY_INTERLOCK, "hitl.approvals.resolved.safety_interlock"),
        ],
    )
    def test_resolved_for_each_tier(self, tier: Tier, expected: str) -> None:
        assert subject_for_approval_resolved(tier=tier) == expected

    def test_string_tier_accepted_if_valid(self) -> None:
        # Allow string for direct DB-row hydration paths (DB stores tier as text)
        assert (
            subject_for_approval_new(tier="operator") == "hitl.approvals.new.operator"
        )

    def test_string_tier_rejected_if_invalid(self) -> None:
        with pytest.raises(ValueError):
            subject_for_approval_new(tier="god-mode")

    def test_string_tier_injection_rejected(self) -> None:
        with pytest.raises(ValueError):
            subject_for_approval_new(tier="operator.>")


# ---------------------------------------------------------------------------
# subject_for_governor_alert — constant
# ---------------------------------------------------------------------------


class TestGovernorAlert:
    def test_constant(self) -> None:
        assert subject_for_governor_alert() == "hitl.governor.alert"


# ---------------------------------------------------------------------------
# validate_subject — overall sanity
# ---------------------------------------------------------------------------


class TestValidateSubject:
    """validate_subject is a defense-in-depth check on the assembled subject string."""

    def test_valid_subject_passes(self) -> None:
        assert validate_subject("audit.actions.ops.operator-assistant") is True

    def test_subject_with_wildcard_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_subject("audit.actions.>")

    def test_subject_with_single_wildcard_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_subject("audit.actions.*.agent")

    def test_subject_with_whitespace_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_subject("audit.actions.ops agent")

    def test_subject_too_long_rejected(self) -> None:
        long_subject = "a." * 130  # 260 chars > 256
        with pytest.raises(ValueError):
            validate_subject(long_subject)
