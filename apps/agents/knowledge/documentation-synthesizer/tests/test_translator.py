"""Contract tests for DocumentationSynthesizer IT→EN translation with citation re-anchoring (TRN-04).

CONTRACT: Every [SRC:N] anchor present in the Italian SOP text must survive
unchanged in the English translation output.

If any [SRC:N] anchor appears in the IT source but is absent from the EN output,
the translator must raise MissingAnchorError (not silently drop the citation).

The translator uses an explicit anchor map ({anchor_id -> source_uri}) to verify
re-anchoring completeness post-translation.

Implementation target: trn_documentation_synthesizer.translator
  - SOPTranslator (or translate_sop function)
  - MissingAnchorError exception class
(Wave 2-3 plan: 08-07)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from trn_documentation_synthesizer.models import SECTION_KEYS_IT, SOPDraft
from trn_documentation_synthesizer.translator import MissingAnchorError, SOPTranslator
from trn_documentation_synthesizer.validators import CitationDriftError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_it_sections(anchors: list[str] | None = None) -> dict[str, str]:
    """Build IT sections with the given anchors embedded in the text."""
    if anchors is None:
        anchors = ["[SRC:1]", "[SRC:2]"]
    anchor_str = " ".join(anchors)
    return {
        "Scopo": f"Questo SOP descrive la procedura. {anchor_str}",
        "Prerequisiti": "Verificare disponibilità attrezzatura.",
        "Passi": "1. Analizzare il guasto. 2. Applicare la correzione.",
        "Sicurezza": "Rispettare le norme di sicurezza.",
        "Riferimenti": "Documentazione tecnica.",
    }


def _make_en_sections_with_anchors(anchors: list[str]) -> dict[str, str]:
    """Build EN sections that preserve all the given anchors."""
    anchor_str = " ".join(anchors)
    return {
        "Scopo": f"This SOP describes the procedure. {anchor_str}",
        "Prerequisiti": "Verify equipment availability.",
        "Passi": "1. Analyze the fault. 2. Apply the correction.",
        "Sicurezza": "Follow safety regulations.",
        "Riferimenti": "Technical documentation.",
    }


def _make_mock_llm(response_text: str) -> MagicMock:
    """Build a mock LLM that returns the given response text."""
    llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = response_text
    llm.ainvoke = AsyncMock(return_value=mock_response)
    return llm


def _make_anchor_map(anchors: list[str]) -> dict[str, str]:
    """Build an anchor map for the given anchors."""
    return {anchor: f"doc://sop-{i + 1:03d}" for i, anchor in enumerate(anchors)}


# ---------------------------------------------------------------------------
# Contract 1: All IT anchors survive in EN output
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_src_anchors_in_it_survive_in_en_output() -> None:
    """Every [SRC:N] anchor in the IT text is present in the EN translation.

    D-DS-01 citation re-anchoring: given IT text with [SRC:1] and [SRC:2] anchors
    and a mock LLM that returns EN text also containing [SRC:1] and [SRC:2],
    the translator must return the EN text unchanged (anchors preserved).
    """
    anchors = ["[SRC:1]", "[SRC:2]"]
    sections_it = _make_it_sections(anchors)
    anchor_map = _make_anchor_map(anchors)

    # LLM returns EN text that preserves both anchors
    en_response = "This SOP describes the procedure. [SRC:1] [SRC:2]"
    llm = _make_mock_llm(en_response)

    translator = SOPTranslator(llm=llm)
    sections_en = await translator.translate(sections_it, anchor_map)

    # Verify both anchors survived in EN output
    en_text = " ".join(sections_en.values())
    assert "[SRC:1]" in en_text, "Anchor [SRC:1] must be present in EN output"
    assert "[SRC:2]" in en_text, "Anchor [SRC:2] must be present in EN output"


@pytest.mark.asyncio
async def test_missing_anchor_in_en_raises_missing_anchor_error() -> None:
    """MissingAnchorError raised when an IT anchor is absent from EN output.

    Given IT text with [SRC:1] and [SRC:2], if the mock LLM returns EN text
    containing only [SRC:1] (dropping [SRC:2]), the translator must raise
    MissingAnchorError with details about the missing anchor.
    """
    anchors = ["[SRC:1]", "[SRC:2]"]
    sections_it = _make_it_sections(anchors)
    anchor_map = _make_anchor_map(anchors)

    # LLM drops [SRC:2] from the translation — simulating citation drift
    en_response = "This SOP describes the procedure. [SRC:1]"
    llm = _make_mock_llm(en_response)

    translator = SOPTranslator(llm=llm)

    with pytest.raises(MissingAnchorError) as exc_info:
        await translator.translate(sections_it, anchor_map)

    assert "[SRC:2]" in str(exc_info.value), (
        "MissingAnchorError must identify the missing anchor [SRC:2]"
    )


@pytest.mark.asyncio
async def test_anchor_map_covers_all_src_anchors_in_it_text() -> None:
    """anchor_map must contain an entry for every [SRC:N] anchor in the IT text.

    D-DS-01: the anchor map ({anchor_id: source_uri}) is produced during IT generation.
    Given IT text with [SRC:1], [SRC:2], [SRC:3], the anchor_map must have 3 entries.
    """
    from trn_documentation_synthesizer.translator import build_anchor_map_from_text
    from datetime import datetime, timezone
    from sft_agents.models.evidence import RagCitation

    sections_it = {
        "Scopo": "Procedura per guasto. [SRC:1] [SRC:2]",
        "Prerequisiti": "Attrezzatura necessaria. [SRC:3]",
        "Passi": "1. Analisi. 2. Correzione.",
        "Sicurezza": "Norme di sicurezza.",
        "Riferimenti": "Documentazione.",
    }

    now = datetime.now(timezone.utc)
    citations = [
        RagCitation(source_uri="doc://sop-001", snippet="first", score=0.9, retrieved_at=now),
        RagCitation(source_uri="doc://sop-002", snippet="second", score=0.85, retrieved_at=now),
        RagCitation(source_uri="doc://sop-003", snippet="third", score=0.8, retrieved_at=now),
    ]

    anchor_map = build_anchor_map_from_text(sections_it, citations)

    assert len(anchor_map) == 3, f"anchor_map must have 3 entries, got {len(anchor_map)}"
    assert "[SRC:1]" in anchor_map, "anchor_map must contain [SRC:1]"
    assert "[SRC:2]" in anchor_map, "anchor_map must contain [SRC:2]"
    assert "[SRC:3]" in anchor_map, "anchor_map must contain [SRC:3]"


@pytest.mark.asyncio
async def test_anchor_map_source_uri_preserved_after_translation() -> None:
    """source_uri values in anchor_map are not modified by the translation pass.

    The anchor_map is invariant through translation: same anchor_id -> same source_uri
    before and after the IT→EN translation.
    """
    anchors = ["[SRC:1]", "[SRC:2]"]
    sections_it = _make_it_sections(anchors)
    anchor_map_before = {
        "[SRC:1]": "doc://sop-original-001",
        "[SRC:2]": "doc://sop-original-002",
    }

    # LLM preserves anchors in EN
    en_response = "This SOP describes the procedure. [SRC:1] [SRC:2]"
    llm = _make_mock_llm(en_response)

    translator = SOPTranslator(llm=llm)
    await translator.translate(sections_it, anchor_map_before)

    # anchor_map must be identical after translation (immutable — not modified)
    assert anchor_map_before["[SRC:1]"] == "doc://sop-original-001", (
        "source_uri for [SRC:1] must be unchanged after translation"
    )
    assert anchor_map_before["[SRC:2]"] == "doc://sop-original-002", (
        "source_uri for [SRC:2] must be unchanged after translation"
    )


@pytest.mark.asyncio
async def test_translation_preserves_all_fixed_section_keys() -> None:
    """All fixed SOP section keys survive in EN output (Scopo->Purpose etc.).

    D-DS-03: fixed-section SOP template. The EN output must contain corresponding
    section headers in the sections_en dict (same IT keys, translated content).
    """
    anchors = ["[SRC:1]"]
    sections_it = _make_it_sections(anchors)
    anchor_map = _make_anchor_map(anchors)

    # LLM returns EN content that preserves the anchor
    en_response = "Procedure description [SRC:1]"
    llm = _make_mock_llm(en_response)

    translator = SOPTranslator(llm=llm)
    sections_en = await translator.translate(sections_it, anchor_map)

    # All 5 section keys must be present in the EN output
    for key in SECTION_KEYS_IT:
        assert key in sections_en, (
            f"Section key '{key}' must be present in sections_en dict. "
            f"D-DS-03 requires all 5 sections in IT→EN translation."
        )
