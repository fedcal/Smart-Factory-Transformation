"""NATS subject derivation helpers for the Phase 4 audit + HITL surface (Plan 04-04).

Subject conventions (CONTEXT.md Claude's Discretion line 422):
    audit.actions.<cluster>.<agent_id>          — D-56 dual-write audit replica
    hitl.approvals.new.<tier>                   — D-55 new approval notify
    hitl.approvals.resolved.<tier>              — D-55 approval decided notify
    hitl.governor.alert                         — D-58 governor alert (no further suffix)

JetStream stream `AUDIT_STREAM` (declared in scripts/nats-bootstrap-streams.py) owns
all three wildcard subjects below. Publishers MUST derive subject strings via these
helpers — never accept user-controlled strings.

Security (T-04-NATS-Spoofed):
    All cluster/tier/agent_id tokens are validated against `_TOKEN_RE` and (for
    enum-bounded fields) against the relevant frozenset. NATS wildcards (`*`, `>`)
    and whitespace are explicitly rejected.

    NOTE: defense-in-depth — Plan 04-06 layers further validation on AuditRecord
    Pydantic fields; this module is the LAST line of validation before bytes hit
    the JetStream context.
"""

from __future__ import annotations

import re

from sft_agents.models.enums import Tier

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: D-53 — 5 cluster subgraphs (Ops, Maintenance, Knowledge-Curation,
#: Knowledge-Training, Supply). Frozen set — any cluster outside this set is a
#: spoofing attempt or a stale config.
VALID_CLUSTERS: frozenset[str] = frozenset(
    {
        "ops",
        "maintenance",
        "knowledge-curation",
        "knowledge-training",
        "supply",
    }
)

#: Wildcards owned by `AUDIT_STREAM` — MUST match
#: scripts/nats-bootstrap-streams.py StreamConfig(subjects=...).
STREAM_SUBJECTS: tuple[str, ...] = (
    "audit.actions.>",
    "hitl.approvals.>",
    "hitl.governor.>",
)

#: Token regex — lowercase ASCII letters, digits, hyphen, underscore ONLY.
#: Dot is excluded deliberately: tokens are single NATS hierarchy levels, never
#: composite paths. The full subject string is built by joining tokens with '.'.
_TOKEN_RE: re.Pattern[str] = re.compile(r"^[a-z0-9_-]+$")

#: NATS subject length cap (server enforces 256; we cap defensively at 256).
_MAX_SUBJECT_LEN: int = 256

#: Allowed Tier values (mirrors `Tier` enum but evaluated at module load to avoid
#: enum lookup on every call).
_VALID_TIER_VALUES: frozenset[str] = frozenset({t.value for t in Tier})

#: Characters that NEVER appear in a published subject (only in stream
#: declarations). Used by `validate_subject` as defense-in-depth.
_FORBIDDEN_SUBJECT_CHARS: tuple[str, ...] = ("*", ">", " ", "\t", "\n", "\r")


# ---------------------------------------------------------------------------
# Internal validators
# ---------------------------------------------------------------------------


def _validate_token(token: str, *, name: str) -> None:
    """Reject tokens containing chars outside `[a-z0-9_-]`.

    Args:
        token: The single hierarchy-level string to validate.
        name: Field name used in the error message (e.g. "agent_id", "tier").

    Raises:
        ValueError: If the token is empty, contains a NATS wildcard, whitespace,
            uppercase letters, or any other character outside the regex class.
    """
    if not isinstance(token, str) or not token:
        raise ValueError(f"{name} must be a non-empty string; got {token!r}")
    # Explicit checks for the highest-impact injection chars before the regex —
    # produces a clearer error message than "didn't match regex".
    if "*" in token or ">" in token:
        raise ValueError(
            f"{name} must not contain NATS wildcards ('*', '>'); got {token!r}"
        )
    if not _TOKEN_RE.fullmatch(token):
        raise ValueError(
            f"{name} contains invalid characters "
            f"(allowed: [a-z0-9_-], no dots); got {token!r}"
        )


# ---------------------------------------------------------------------------
# Public derivation helpers
# ---------------------------------------------------------------------------


def subject_for_audit(*, cluster: str, agent_id: str) -> str:
    """Derive the audit subject for an `audit.actions` row (D-56).

    Format: ``audit.actions.<cluster>.<agent_id>``

    Args:
        cluster: One of the 5 D-53 cluster names (must appear in VALID_CLUSTERS).
        agent_id: PATTERNS §3.3 kebab-case agent slug (e.g. "operator-assistant").

    Returns:
        The dot-joined subject string, ready for `js.publish(subject, payload)`.

    Raises:
        ValueError: If cluster is not in VALID_CLUSTERS, or agent_id fails
            token validation (T-04-NATS-Spoofed mitigation).
    """
    if cluster not in VALID_CLUSTERS:
        raise ValueError(
            f"cluster must be one of {sorted(VALID_CLUSTERS)}; got {cluster!r}"
        )
    _validate_token(agent_id, name="agent_id")
    return f"audit.actions.{cluster}.{agent_id}"


def subject_for_approval_new(*, tier: Tier | str) -> str:
    """Derive the subject for a newly-created approval row (D-55).

    Format: ``hitl.approvals.new.<tier>``

    Args:
        tier: Either a Tier enum member or its string value
            (accepted for direct DB-row hydration paths where tier is stored as text).

    Returns:
        Dot-joined subject string.

    Raises:
        ValueError: If tier is not a valid Tier value.
    """
    tier_value = _coerce_tier(tier)
    return f"hitl.approvals.new.{tier_value}"


def subject_for_approval_resolved(*, tier: Tier | str) -> str:
    """Derive the subject for an approval that has been decided (D-55).

    Format: ``hitl.approvals.resolved.<tier>``
    """
    tier_value = _coerce_tier(tier)
    return f"hitl.approvals.resolved.{tier_value}"


def subject_for_governor_alert() -> str:
    """Return the constant governor-alert subject (D-58).

    Returns:
        "hitl.governor.alert" — no further suffix; governor alerts are a single
        global stream, not per-cluster.
    """
    return "hitl.governor.alert"


def validate_subject(subject: str) -> bool:
    """Defense-in-depth check on the assembled subject string.

    Asserts:
        - length <= 256 chars (NATS server cap)
        - no NATS wildcards (`*`, `>`)
        - no whitespace
        - ASCII only

    Args:
        subject: The full subject string about to be published.

    Returns:
        True if the subject is safe to publish.

    Raises:
        ValueError: If any of the above invariants is violated.
    """
    if not isinstance(subject, str) or not subject:
        raise ValueError(f"subject must be a non-empty string; got {subject!r}")
    if len(subject) > _MAX_SUBJECT_LEN:
        raise ValueError(
            f"subject too long ({len(subject)} > {_MAX_SUBJECT_LEN}): {subject!r}"
        )
    for bad in _FORBIDDEN_SUBJECT_CHARS:
        if bad in subject:
            raise ValueError(
                f"subject contains forbidden character {bad!r}: {subject!r}"
            )
    try:
        subject.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(
            f"subject must be ASCII; got non-ASCII char in {subject!r}"
        ) from exc
    return True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_tier(tier: Tier | str) -> str:
    """Return the string value of a Tier (enum or string), validating membership."""
    if isinstance(tier, Tier):
        return tier.value
    if not isinstance(tier, str):
        raise ValueError(f"tier must be Tier or str; got {type(tier).__name__}")
    _validate_token(tier, name="tier")
    if tier not in _VALID_TIER_VALUES:
        raise ValueError(
            f"tier must be one of {sorted(_VALID_TIER_VALUES)}; got {tier!r}"
        )
    return tier
