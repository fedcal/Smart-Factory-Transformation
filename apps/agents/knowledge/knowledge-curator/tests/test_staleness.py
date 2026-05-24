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

Wave 0 scaffold: test functions fail explicitly with a message naming the
unimplemented contract. NOT module-level pytest.skip (Phase 6/7 Wave 0 decision).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Contract 1: SOP staleness (365 days)
# ---------------------------------------------------------------------------


def test_sop_stale_after_366_days() -> None:
    """SOP document with age=366 days (injected now) is stale.

    D-KC-02: SOP threshold = 365 days. last_updated = now - 366 days -> is_stale=True.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: SOP is_stale=True when age > 365 days. "
        "Injected 'now' parameter for deterministic boundary test. "
        "D-KC-02 per-document-type staleness thresholds. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.staleness"
    )


def test_sop_not_stale_364_days() -> None:
    """SOP document with age=364 days (injected now) is NOT stale.

    D-KC-02: SOP threshold = 365 days. last_updated = now - 364 days -> is_stale=False.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: SOP is_stale=False when age < 365 days. "
        "Injected 'now' parameter for deterministic boundary test. "
        "D-KC-02 per-document-type staleness thresholds. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.staleness"
    )


# ---------------------------------------------------------------------------
# Contract 2: Runbook staleness (180 days)
# ---------------------------------------------------------------------------


def test_runbook_stale_after_181_days() -> None:
    """Runbook document with age=181 days (injected now) is stale.

    D-KC-02: Runbook threshold = 180 days. last_updated = now - 181 days -> is_stale=True.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: runbook is_stale=True when age > 180 days. "
        "D-KC-02 per-document-type staleness thresholds. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.staleness"
    )


def test_runbook_not_stale_179_days() -> None:
    """Runbook document with age=179 days (injected now) is NOT stale.

    D-KC-02: Runbook threshold = 180 days. last_updated = now - 179 days -> is_stale=False.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: runbook is_stale=False when age < 180 days. "
        "D-KC-02 per-document-type staleness thresholds. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.staleness"
    )


# ---------------------------------------------------------------------------
# Contract 3: Note staleness (90 days)
# ---------------------------------------------------------------------------


def test_note_stale_after_91_days() -> None:
    """Note document with age=91 days (injected now) is stale.

    D-KC-02: Note threshold = 90 days. last_updated = now - 91 days -> is_stale=True.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: note is_stale=True when age > 90 days. "
        "D-KC-02 per-document-type staleness thresholds. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.staleness"
    )


def test_note_not_stale_89_days() -> None:
    """Note document with age=89 days (injected now) is NOT stale.

    D-KC-02: Note threshold = 90 days. last_updated = now - 89 days -> is_stale=False.

    Implementation target: trn_knowledge_curator.staleness.StalenessChecker.is_stale()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: note is_stale=False when age < 90 days. "
        "D-KC-02 per-document-type staleness thresholds. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.staleness"
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
    pytest.fail(
        "NOT IMPLEMENTED — contract: StalenessChecker thresholds are configurable "
        "at construction (not hardcoded). Custom thresholds override defaults. "
        "D-KC-02 configurable per-document-type thresholds. "
        "Implement in plan 08-06 (knowledge-curator agent). "
        "Module: trn_knowledge_curator.staleness"
    )
