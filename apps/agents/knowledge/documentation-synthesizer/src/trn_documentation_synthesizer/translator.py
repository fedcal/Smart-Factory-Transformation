"""IT→EN SOP translator with citation re-anchoring (D-DS-01, Pitfall §1, TRN-04).

Translation contract
--------------------
The translator takes an Italian SOP (sections_it + anchor_map) and produces
an English translation (sections_en) where every [SRC:N] anchor from the IT
text is preserved unchanged.

Pitfall §1 mitigation:
    The LLM is explicitly instructed to preserve every [SRC:N] marker in place.
    After translation, the translator verifies that every IT anchor survived:
        - If an anchor is present in IT but absent in EN → raises MissingAnchorError
        - If anchor_map has no entry for an IT anchor → raises CitationDriftError

Anchor map invariance:
    The anchor_map is produced during IT generation and is never modified by
    the translation pass. The LLM translates text but must not rewrite source_uri
    values (which are not in the text — they live in the anchor_map separately).

Section key translation:
    IT section keys (Scopo, Prerequisiti, etc.) are mapped to EN equivalents
    (Purpose, Prerequisites, etc.) using SECTION_KEY_MAP_IT_TO_EN.
    The LLM translates section content; key mapping is deterministic.

Implementation note — sync fallback:
    SOPTranslator.translate() is the async entry point. A synchronous shim
    (translate_sop()) wraps it via asyncio for non-async callers and tests.
"""

from __future__ import annotations

import re
from typing import Any

from trn_documentation_synthesizer.models import SECTION_KEY_MAP_IT_TO_EN, SECTION_KEYS_IT
from trn_documentation_synthesizer.validators import CitationDriftError, MissingAnchorError

# Regex for [SRC:N] anchors
_ANCHOR_RE = re.compile(r"\[SRC:\d+\]")


def _extract_anchors(text: str) -> set[str]:
    """Extract all [SRC:N] anchors from text."""
    return set(_ANCHOR_RE.findall(text))


def _verify_anchor_parity(
    it_sections: dict[str, str],
    en_sections: dict[str, str],
    anchor_map: dict[str, str],
) -> None:
    """Verify that all IT [SRC:N] anchors survive in EN sections.

    Also verifies anchor_map coverage (every IT anchor has an entry).

    Raises:
        MissingAnchorError: If any IT anchor is absent from EN sections (Pitfall §1).
        CitationDriftError: If any IT anchor has no anchor_map entry.
    """
    it_text = " ".join(it_sections.values())
    en_text = " ".join(en_sections.values())

    it_anchors = _extract_anchors(it_text)
    en_anchors = _extract_anchors(en_text)

    # Check anchor parity (Pitfall §1 — citation re-anchoring enforcement)
    for anchor in sorted(it_anchors):
        if anchor not in en_anchors:
            raise MissingAnchorError(anchor_id=anchor)

    # Check anchor map coverage (CitationDriftError)
    for anchor in sorted(it_anchors):
        if anchor not in anchor_map:
            raise CitationDriftError(anchor_id=anchor)


def build_anchor_map_from_text(
    it_sections: dict[str, str],
    citations: list[Any],
) -> dict[str, str]:
    """Build an anchor_map from the IT sections text and citation list.

    Assigns [SRC:1], [SRC:2], ... sequentially to citations as found in
    the IT text. Each anchor maps to the citation's source_uri.

    Args:
        it_sections: The IT SOP sections (with [SRC:N] anchors embedded).
        citations:   List of RagCitation objects (must have source_uri).

    Returns:
        Dict mapping "[SRC:N]" to source_uri.
    """
    it_text = " ".join(it_sections.values())
    anchors_found = sorted(
        _extract_anchors(it_text),
        key=lambda a: int(re.search(r"\d+", a).group()),  # type: ignore[union-attr]
    )

    anchor_map: dict[str, str] = {}
    for i, anchor in enumerate(anchors_found):
        if i < len(citations):
            anchor_map[anchor] = citations[i].source_uri
        else:
            anchor_map[anchor] = f"source://unknown-{i + 1}"

    return anchor_map


class SOPTranslator:
    """IT→EN SOP section translator with citation re-anchoring validation.

    Uses an LLM (LangChain-compatible) to translate IT sections to EN,
    with an explicit system instruction to preserve all [SRC:N] anchors.
    After translation, validates that every IT anchor survived (Pitfall §1).

    Usage::

        translator = SOPTranslator(llm=my_llm)
        en_sections = await translator.translate(it_sections, anchor_map)
        # raises MissingAnchorError if any anchor was dropped
    """

    def __init__(self, *, llm: Any) -> None:
        """Bind the LLM.

        Args:
            llm: LangChain-compatible LLM (BaseChatModel or equivalent).
                 Must support ainvoke(messages) returning a response with .content.
        """
        self._llm = llm

    async def translate(
        self,
        sections_it: dict[str, str],
        anchor_map: dict[str, str],
    ) -> dict[str, str]:
        """Translate IT SOP sections to EN, preserving all [SRC:N] anchors.

        For each IT section, calls the LLM with an explicit instruction to
        preserve every [SRC:N] marker in place (Pitfall §1 mitigation).
        Maps IT section keys to EN equivalents deterministically.

        After translation, validates anchor parity and anchor map coverage.

        Args:
            sections_it:  Dict of IT section key → content (must include all SECTION_KEYS_IT).
            anchor_map:   Dict of "[SRC:N]" → source_uri (produced during IT generation).

        Returns:
            Dict of EN section key → translated content, with anchors preserved.

        Raises:
            MissingAnchorError: If any IT anchor is absent from EN output (Pitfall §1).
            CitationDriftError: If any IT anchor has no anchor_map entry.
        """
        sections_en: dict[str, str] = {}

        for it_key in SECTION_KEYS_IT:
            it_content = sections_it.get(it_key, "")
            en_key = SECTION_KEY_MAP_IT_TO_EN.get(it_key, it_key)

            # Build the translation prompt for this section
            prompt = _build_section_translation_prompt(
                section_key_it=it_key,
                section_key_en=en_key,
                content_it=it_content,
                anchor_map=anchor_map,
            )

            # Invoke the LLM
            response = await self._llm.ainvoke(prompt)
            if hasattr(response, "content"):
                translated = response.content
            else:
                translated = str(response)

            sections_en[it_key] = translated.strip()

        # Validate anchor parity post-translation (Pitfall §1 enforcement)
        _verify_anchor_parity(sections_it, sections_en, anchor_map)

        return sections_en


def _build_section_translation_prompt(
    *,
    section_key_it: str,
    section_key_en: str,
    content_it: str,
    anchor_map: dict[str, str],
) -> list[Any]:
    """Build the LLM prompt for translating a single SOP section IT→EN.

    The prompt explicitly instructs the LLM to preserve all [SRC:N] markers.
    Anchor map entries are provided for context (not to be rewritten).

    Returns:
        List of message dicts suitable for LangChain LLM invocation.
    """
    anchor_summary = "; ".join(
        f"{k} -> {v}" for k, v in sorted(anchor_map.items())
    ) if anchor_map else "none"

    system_content = (
        "You are a technical SOP translator from Italian to English for industrial maintenance documentation. "
        "Your task is to translate the given SOP section accurately. "
        "\n\nCRITICAL RULES (Pitfall §1 — citation re-anchoring):\n"
        "1. PRESERVE every [SRC:N] marker EXACTLY as written (e.g. [SRC:1], [SRC:2]). "
        "   These are citation anchors and must appear in the English output at the same logical position.\n"
        "2. Do NOT translate, remove, or modify [SRC:N] markers in any way.\n"
        "3. Do NOT add new [SRC:N] markers that were not in the Italian text.\n"
        "4. Do NOT include the section key/header in your output — only translate the content.\n"
        f"\nAnchor map (for your reference, do NOT rewrite): {anchor_summary}"
    )

    user_content = (
        f"Translate the following Italian SOP section '{section_key_it}' to English '{section_key_en}'.\n"
        f"Preserve all [SRC:N] markers exactly.\n\n"
        f"Italian content:\n{content_it}"
    )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        return [SystemMessage(content=system_content), HumanMessage(content=user_content)]
    except ImportError:
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]


def translate_sop(
    sections_it: dict[str, str],
    anchor_map: dict[str, str],
    *,
    llm: Any,
) -> dict[str, str]:
    """Synchronous shim for SOPTranslator.translate() (for non-async callers and tests).

    Uses asyncio.run() or asyncio.get_event_loop() to run the async translate method.

    Args:
        sections_it: Dict of IT section key → content.
        anchor_map:  Dict of "[SRC:N]" → source_uri.
        llm:         LangChain-compatible LLM.

    Returns:
        Dict of EN section key → translated content.

    Raises:
        MissingAnchorError: If any IT anchor is absent from EN output.
        CitationDriftError: If any IT anchor has no anchor_map entry.
    """
    import asyncio

    translator = SOPTranslator(llm=llm)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, translator.translate(sections_it, anchor_map))
                return future.result()
        else:
            return loop.run_until_complete(translator.translate(sections_it, anchor_map))
    except RuntimeError:
        return asyncio.run(translator.translate(sections_it, anchor_map))


__all__ = [
    "MissingAnchorError",
    "SOPTranslator",
    "build_anchor_map_from_text",
    "translate_sop",
]
