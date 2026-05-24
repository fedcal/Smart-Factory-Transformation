"""Contract tests for SOPCitationValidator — TRN-05 opaque-output rejection (canonical).

CONTRACT (TRN-05): SOPCitationValidator rejects any DocumentationSynthesizer output
that lacks source_uri AND timestamp on every citation.

Rules:
  - Each citation in the output must have a non-empty source_uri
  - Each citation must have a non-null timestamp (UTC-aware datetime)
  - A citation missing either source_uri or timestamp -> ValidationError raised
  - Empty citations list -> ValidationError raised (no uncited output)
  - A valid citation (source_uri + timestamp present) -> passes validation

Implementation target: trn_documentation_synthesizer.validators.SOPCitationValidator
(Wave 2-3 plan: 08-07)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sft_agents.models.evidence import RagCitation
from trn_documentation_synthesizer.models import SOPDraft
from trn_documentation_synthesizer.validators import SOPCitationValidator, ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_valid_citation(source_uri: str = "doc://sop-001") -> RagCitation:
    return RagCitation(
        source_uri=source_uri,
        snippet="Technical documentation snippet.",
        score=0.9,
        retrieved_at=_now(),
    )


def _make_valid_sop_draft(citations: list[RagCitation]) -> SOPDraft:
    """Build a valid SOPDraft with the given citations."""
    now = _now()
    sections = {
        "Scopo": "Procedura operativa. [SRC:1]",
        "Prerequisiti": "Attrezzatura necessaria.",
        "Passi": "1. Analisi. 2. Correzione.",
        "Sicurezza": "Norme di sicurezza.",
        "Riferimenti": "Documentazione tecnica.",
    }
    return SOPDraft(
        sop_id="sop-test-001",
        failure_mode="overheating",
        asset_id="loom-01",
        title_it="SOP: Surriscaldamento su Loom-01",
        title_en="SOP: Overheating on Loom-01",
        sections_it=sections,
        sections_en=sections,
        citations=citations,
        anchor_map={"[SRC:1]": "doc://sop-001"},
        generated_at=now,
        approved=False,
    )


# ---------------------------------------------------------------------------
# Contract 1: Valid output passes validation
# ---------------------------------------------------------------------------


def test_valid_citation_with_source_uri_and_timestamp_passes() -> None:
    """SOPCitationValidator accepts output where all citations have source_uri + timestamp.

    TRN-05: valid output has complete citation provenance (source_uri + timestamp).
    """
    citations = [_make_valid_citation("doc://sop-001")]
    sop_draft = _make_valid_sop_draft(citations)
    validator = SOPCitationValidator()

    # Must not raise
    result = validator.validate(sop_draft)
    assert result is sop_draft, "validate() must return the same sop_draft on success"


# ---------------------------------------------------------------------------
# Contract 2: Missing source_uri triggers rejection
# ---------------------------------------------------------------------------


def test_citation_missing_source_uri_raises_validation_error() -> None:
    """SOPCitationValidator rejects any citation with missing or empty source_uri.

    TRN-05: source_uri is mandatory on every citation.
    """
    # RagCitation enforces min_length=1 on source_uri at construction,
    # so we test the validator by patching a valid draft with a bad one.
    # We use a citation constructed with monkeypatching via model_construct.
    bad_citation = RagCitation.model_construct(
        source_uri="",  # empty source_uri — TRN-05 violation
        snippet="snippet",
        score=0.9,
        retrieved_at=_now(),
    )
    now = _now()
    sections = {
        "Scopo": "Procedura. [SRC:1]",
        "Prerequisiti": "Prerequisiti.",
        "Passi": "Passi.",
        "Sicurezza": "Sicurezza.",
        "Riferimenti": "Riferimenti.",
    }
    # Build SOPDraft via model_construct to bypass Pydantic validation
    sop_draft = SOPDraft.model_construct(
        sop_id="sop-bad-001",
        failure_mode="overheating",
        asset_id="loom-01",
        title_it="SOP IT",
        title_en="SOP EN",
        lang_primary="it",
        sections_it=sections,
        sections_en=sections,
        citations=[bad_citation],
        anchor_map={"[SRC:1]": "doc://sop-001"},
        generated_at=now,
        approved=False,
    )

    validator = SOPCitationValidator()
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(sop_draft)

    assert "source_uri" in str(exc_info.value).lower(), (
        "ValidationError must mention source_uri in its message"
    )


# ---------------------------------------------------------------------------
# Contract 3: Missing timestamp triggers rejection
# ---------------------------------------------------------------------------


def test_citation_missing_timestamp_raises_validation_error() -> None:
    """SOPCitationValidator rejects any citation with missing or null timestamp.

    TRN-05: timestamp is mandatory on every citation.
    """
    bad_citation = RagCitation.model_construct(
        source_uri="doc://sop-001",
        snippet="snippet",
        score=0.9,
        retrieved_at=None,  # null timestamp — TRN-05 violation
    )
    now = _now()
    sections = {
        "Scopo": "Procedura. [SRC:1]",
        "Prerequisiti": "Prerequisiti.",
        "Passi": "Passi.",
        "Sicurezza": "Sicurezza.",
        "Riferimenti": "Riferimenti.",
    }
    sop_draft = SOPDraft.model_construct(
        sop_id="sop-bad-002",
        failure_mode="overheating",
        asset_id="loom-01",
        title_it="SOP IT",
        title_en="SOP EN",
        lang_primary="it",
        sections_it=sections,
        sections_en=sections,
        citations=[bad_citation],
        anchor_map={"[SRC:1]": "doc://sop-001"},
        generated_at=now,
        approved=False,
    )

    validator = SOPCitationValidator()
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(sop_draft)

    assert "timestamp" in str(exc_info.value).lower() or "retrieved_at" in str(exc_info.value).lower(), (
        "ValidationError must mention timestamp/retrieved_at in its message"
    )


# ---------------------------------------------------------------------------
# Contract 4: Empty citations list triggers rejection
# ---------------------------------------------------------------------------


def test_empty_citations_list_raises_validation_error() -> None:
    """SOPCitationValidator rejects output with an empty citations list.

    TRN-05: all TRN agent outputs must include citations. An uncited SOP
    (citations=[]) is opaque output and must be rejected.
    """
    now = _now()
    sections = {
        "Scopo": "Procedura.",
        "Prerequisiti": "Prerequisiti.",
        "Passi": "Passi.",
        "Sicurezza": "Sicurezza.",
        "Riferimenti": "Riferimenti.",
    }
    sop_draft = SOPDraft.model_construct(
        sop_id="sop-empty-001",
        failure_mode="overheating",
        asset_id="loom-01",
        title_it="SOP IT",
        title_en="SOP EN",
        lang_primary="it",
        sections_it=sections,
        sections_en=sections,
        citations=[],  # empty — TRN-05 violation
        anchor_map={},
        generated_at=now,
        approved=False,
    )

    validator = SOPCitationValidator()
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(sop_draft)

    error_msg = str(exc_info.value).lower()
    assert "empty" in error_msg or "uncited" in error_msg or "citation" in error_msg, (
        "ValidationError must indicate that empty citations list is rejected"
    )


# ---------------------------------------------------------------------------
# Contract 5: Partial validity — one bad citation rejects the whole output
# ---------------------------------------------------------------------------


def test_one_invalid_citation_rejects_entire_output() -> None:
    """SOPCitationValidator rejects output if ANY citation is invalid.

    TRN-05: the entire output is rejected if any citation lacks source_uri or timestamp.
    """
    valid_citation = _make_valid_citation("doc://sop-001")
    bad_citation = RagCitation.model_construct(
        source_uri="",  # empty source_uri — TRN-05 violation
        snippet="second snippet",
        score=0.8,
        retrieved_at=_now(),
    )

    now = _now()
    sections = {
        "Scopo": "Procedura. [SRC:1]",
        "Prerequisiti": "Prerequisiti.",
        "Passi": "Passi.",
        "Sicurezza": "Sicurezza.",
        "Riferimenti": "Riferimenti.",
    }
    sop_draft = SOPDraft.model_construct(
        sop_id="sop-partial-001",
        failure_mode="overheating",
        asset_id="loom-01",
        title_it="SOP IT",
        title_en="SOP EN",
        lang_primary="it",
        sections_it=sections,
        sections_en=sections,
        citations=[valid_citation, bad_citation],
        anchor_map={"[SRC:1]": "doc://sop-001"},
        generated_at=now,
        approved=False,
    )

    validator = SOPCitationValidator()
    with pytest.raises(ValidationError):
        validator.validate(sop_draft)
