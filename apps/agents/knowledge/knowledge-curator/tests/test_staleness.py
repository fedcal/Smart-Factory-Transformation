"""Contract tests for KnowledgeCurator staleness detection (D-KC-02).

CONTRACT: Per-document-type configurable staleness thresholds with injected 'now':
  - SOP documents: stale after 365 days
  - Runbook documents: stale after 180 days
  - Note documents: stale after 90 days
  - 'now' is injected (not datetime.now()) for deterministic boundary testing

Boundary tests:
  - Exactly at threshold: still_stale boundary (edge case must be clearly documented)
  - 1 day before threshold: not stale
  - 1 day after threshold: stale

Implementation target: trn_knowledge_curator.staleness.StalenessChecker
(Wave 2-3 plan: 08-06)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trn_knowledge_curator.staleness import StalenessChecker, is_stale


# Reference 'now' for all boundary tests (deterministic).
_NOW = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Contract 1: SOP staleness (365 days)
# ---------------------------------------------------------------------------


def test_sop_stale_after_366_days() -> None:
    """SOP document with age=366 days (injected now) is stale.

    D-KC-02: SOP threshold = 365 days. last_updated = now - 366 days -> is_stale=True.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    last_updated = _NOW - timedelta(days=366)
    checker = StalenessChecker()
    result = checker.is_stale(doc_type="sop", last_updated=last_updated, now=_NOW)
    assert result is True, (
        f"SOP with age 366 days must be stale (threshold=365). "
        f"last_updated={last_updated!r}, now={_NOW!r}"
    )


def test_sop_not_stale_364_days() -> None:
    """SOP document with age=364 days (injected now) is NOT stale.

    D-KC-02: SOP threshold = 365 days. last_updated = now - 364 days -> is_stale=False.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    last_updated = _NOW - timedelta(days=364)
    checker = StalenessChecker()
    result = checker.is_stale(doc_type="sop", last_updated=last_updated, now=_NOW)
    assert result is False, (
        f"SOP with age 364 days must NOT be stale (threshold=365). "
        f"last_updated={last_updated!r}, now={_NOW!r}"
    )


# ---------------------------------------------------------------------------
# Contract 2: Runbook staleness (180 days)
# ---------------------------------------------------------------------------


def test_runbook_stale_after_181_days() -> None:
    """Runbook document with age=181 days (injected now) is stale.

    D-KC-02: Runbook threshold = 180 days. last_updated = now - 181 days -> is_stale=True.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    last_updated = _NOW - timedelta(days=181)
    checker = StalenessChecker()
    result = checker.is_stale(doc_type="runbook", last_updated=last_updated, now=_NOW)
    assert result is True, (
        f"Runbook with age 181 days must be stale (threshold=180). "
        f"last_updated={last_updated!r}, now={_NOW!r}"
    )


def test_runbook_not_stale_179_days() -> None:
    """Runbook document with age=179 days (injected now) is NOT stale.

    D-KC-02: Runbook threshold = 180 days. last_updated = now - 179 days -> is_stale=False.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    last_updated = _NOW - timedelta(days=179)
    checker = StalenessChecker()
    result = checker.is_stale(doc_type="runbook", last_updated=last_updated, now=_NOW)
    assert result is False, (
        f"Runbook with age 179 days must NOT be stale (threshold=180). "
        f"last_updated={last_updated!r}, now={_NOW!r}"
    )


# ---------------------------------------------------------------------------
# Contract 3: Note staleness (90 days)
# ---------------------------------------------------------------------------


def test_note_stale_after_91_days() -> None:
    """Note document with age=91 days (injected now) is stale.

    D-KC-02: Note threshold = 90 days. last_updated = now - 91 days -> is_stale=True.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    last_updated = _NOW - timedelta(days=91)
    checker = StalenessChecker()
    result = checker.is_stale(doc_type="note", last_updated=last_updated, now=_NOW)
    assert result is True, (
        f"Note with age 91 days must be stale (threshold=90). "
        f"last_updated={last_updated!r}, now={_NOW!r}"
    )


def test_note_not_stale_89_days() -> None:
    """Note document with age=89 days (injected now) is NOT stale.

    D-KC-02: Note threshold = 90 days. last_updated = now - 89 days -> is_stale=False.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    last_updated = _NOW - timedelta(days=89)
    checker = StalenessChecker()
    result = checker.is_stale(doc_type="note", last_updated=last_updated, now=_NOW)
    assert result is False, (
        f"Note with age 89 days must NOT be stale (threshold=90). "
        f"last_updated={last_updated!r}, now={_NOW!r}"
    )


# ---------------------------------------------------------------------------
# Contract 4: Thresholds are configurable (not hardcoded)
# ---------------------------------------------------------------------------


def test_staleness_thresholds_configurable_per_doc_type() -> None:
    """StalenessChecker accepts custom thresholds per doc_type at construction.

    Given StalenessChecker(thresholds={'sop': 30, 'runbook': 15}), a SOP with age=31d
    must be stale (not using the default 365d threshold).

    D-KC-02: per-document-type configurable thresholds.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker
    """
    checker = StalenessChecker(thresholds={"sop": 30, "runbook": 15})

    # SOP with age 31 days — must be stale with custom threshold=30 (not default 365).
    last_updated_sop = _NOW - timedelta(days=31)
    result_sop = checker.is_stale(doc_type="sop", last_updated=last_updated_sop, now=_NOW)
    assert result_sop is True, (
        "SOP with age 31d must be stale with custom threshold=30 (not default 365d). "
        f"Threshold used: 30, age: 31, result: {result_sop}"
    )

    # SOP with age 29 days — must NOT be stale with custom threshold=30.
    last_updated_sop_fresh = _NOW - timedelta(days=29)
    result_sop_fresh = checker.is_stale(
        doc_type="sop", last_updated=last_updated_sop_fresh, now=_NOW
    )
    assert result_sop_fresh is False, (
        "SOP with age 29d must NOT be stale with custom threshold=30."
    )

    # Runbook with age 16 days — must be stale with custom threshold=15.
    last_updated_rb = _NOW - timedelta(days=16)
    result_rb = checker.is_stale(doc_type="runbook", last_updated=last_updated_rb, now=_NOW)
    assert result_rb is True, (
        "Runbook with age 16d must be stale with custom threshold=15."
    )

    # Note type not overridden — still uses default 90d.
    last_updated_note = _NOW - timedelta(days=91)
    result_note = checker.is_stale(doc_type="note", last_updated=last_updated_note, now=_NOW)
    assert result_note is True, (
        "Note with age 91d must still be stale using default threshold=90."
    )
