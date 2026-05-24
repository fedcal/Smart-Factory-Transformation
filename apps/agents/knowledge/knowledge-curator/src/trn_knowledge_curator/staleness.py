"""Per-document-type staleness detection for KnowledgeCurator (D-KC-02).

Provides:
  - StalenessChecker: class-based staleness checker with configurable thresholds.
  - is_stale: standalone pure function for staleness check.

Design:
  - Pure computation (no I/O, no side effects).
  - 'now' is injected for deterministic boundary testing.
  - Thresholds are configurable at construction (class) or call time (function).

Default thresholds (D-KC-02):
  sop:     365 days
  runbook: 180 days
  note:    90 days
  unknown: 90 days (fall-through default)

Pattern reference: 08-PATTERNS.md staleness.py section (lines 912-950).
"""

from __future__ import annotations

from datetime import datetime, timezone

# D-KC-02: per-document-type default staleness thresholds (days).
_DEFAULT_THRESHOLDS: dict[str, int] = {
    "sop": 365,
    "runbook": 180,
    "note": 90,
}

#: Fall-through default for unknown document types (90 days — same as note).
_UNKNOWN_TYPE_DEFAULT_DAYS: int = 90


def is_stale(
    *,
    doc_type: str,
    last_updated: datetime,
    thresholds: dict[str, int] | None = None,
    now: datetime | None = None,
) -> bool:
    """Return True if the document is past its type-specific staleness threshold.

    Pure function (testable without mocks). Uses injected 'now' for deterministic
    boundary tests (D-KC-02).

    Args:
        doc_type: Document type key (e.g. "sop", "runbook", "note").
        last_updated: UTC tz-aware datetime of last document update.
        thresholds: Per-type threshold in days; uses _DEFAULT_THRESHOLDS if None.
        now: Reference datetime (UTC tz-aware); uses datetime.now(UTC) if None.

    Returns:
        True when (now - last_updated).days > threshold[doc_type].
        False when age is within the threshold.

    Raises:
        ValueError: If last_updated is naive (tz-unaware) to prevent boundary errors.
    """
    if last_updated.tzinfo is None:
        raise ValueError(
            f"last_updated must be tz-aware, got naive: {last_updated!r}. "
            "Use datetime(..., tzinfo=timezone.utc) or datetime.now(timezone.utc)."
        )

    effective_thresholds = thresholds if thresholds is not None else _DEFAULT_THRESHOLDS
    threshold_days = effective_thresholds.get(doc_type, _UNKNOWN_TYPE_DEFAULT_DAYS)
    effective_now = now if now is not None else datetime.now(timezone.utc)

    age_days = (effective_now - last_updated).days
    return age_days > threshold_days


class StalenessChecker:
    """Per-document-type staleness checker (D-KC-02).

    Wraps the is_stale() pure function with configurable thresholds set at
    construction time. Thresholds can be overridden per call for test isolation.

    Args:
        thresholds: Custom per-type staleness thresholds (days). Merged on top of
                    _DEFAULT_THRESHOLDS so only overridden keys need to be supplied.
                    Passing thresholds={'sop': 30} makes SOP threshold 30d while
                    runbook and note remain at defaults.

    Example:
        >>> checker = StalenessChecker(thresholds={'sop': 30, 'runbook': 15})
        >>> checker.is_stale(doc_type='sop', last_updated=<31 days ago>, now=<now>)
        True
    """

    def __init__(self, thresholds: dict[str, int] | None = None) -> None:
        """Initialise with optional threshold overrides.

        Args:
            thresholds: If supplied, merged on top of _DEFAULT_THRESHOLDS.
                        This allows partial override (e.g. only sop threshold).
        """
        if thresholds is not None:
            # Merge: default first, then caller's overrides (immutable final result).
            merged = {**_DEFAULT_THRESHOLDS, **thresholds}
        else:
            merged = dict(_DEFAULT_THRESHOLDS)
        self._thresholds: dict[str, int] = merged

    def is_stale(
        self,
        *,
        doc_type: str,
        last_updated: datetime,
        now: datetime | None = None,
    ) -> bool:
        """Check if a document is stale using the checker's configured thresholds.

        Args:
            doc_type: Document type key (e.g. "sop", "runbook", "note").
            last_updated: UTC tz-aware datetime of last document update.
            now: Reference datetime (UTC tz-aware); uses datetime.now(UTC) if None.

        Returns:
            True when (now - last_updated).days > threshold[doc_type].
        """
        return is_stale(
            doc_type=doc_type,
            last_updated=last_updated,
            thresholds=self._thresholds,
            now=now,
        )


__all__ = [
    "StalenessChecker",
    "is_stale",
]
