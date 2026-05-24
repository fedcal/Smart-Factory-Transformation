"""Fixed-section IT SOP builder for DocumentationSynthesizer (D-DS-01, Pitfall §1).

Generates an Italian SOP draft from historical events + RAG citations.
Embeds [SRC:N] anchors in section text and produces the anchor_map.

Fixed section structure (D-DS-01):
    Scopo, Prerequisiti, Passi, Sicurezza, Riferimenti

Citation anchor pattern (Pitfall §1):
    Each RAG citation is referenced in the SOP text as [SRC:N] where N is
    the 1-based citation index. The anchor_map maps "[SRC:N]" → source_uri.
    This ensures traceable, opaque-free output (TRN-05).

LLM usage:
    The builder calls the LLM with a system prompt instructing it to generate
    the IT SOP in the fixed-section format with [SRC:N] anchors. The LLM
    output is parsed section by section and the anchor_map is built from
    citations passed as context.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import structlog

from trn_documentation_synthesizer.models import SECTION_KEYS_IT, SOPDraft
from trn_documentation_synthesizer.translator import build_anchor_map_from_text

logger = structlog.get_logger("agent.documentation-synthesizer.sop_builder")


class SOPBuilder:
    """Generates a fixed-section Italian SOP from historical events + RAG citations.

    Calls the LLM with a structured prompt to generate IT SOP sections with
    [SRC:N] anchors, then builds the anchor_map from the citations list.

    Usage::

        builder = SOPBuilder(llm=my_llm)
        sop_draft = await builder.build(
            failure_mode="overheating",
            asset_id="loom-01",
            events=[...],
            citations=[...],
        )
    """

    def __init__(self, *, llm: Any) -> None:
        """Bind the LLM.

        Args:
            llm: LangChain-compatible LLM (BaseChatModel or equivalent).
        """
        self._llm = llm

    async def build(
        self,
        *,
        failure_mode: str,
        asset_id: str,
        events: list[dict[str, Any]],
        citations: list[Any],
        title_it: str | None = None,
    ) -> tuple[SOPDraft, dict[str, str]]:
        """Generate an Italian SOP draft with [SRC:N] anchors.

        Calls the LLM with a structured prompt that lists the historical events
        and RAG citations, instructing it to produce a 5-section IT SOP with
        [SRC:N] anchors. Builds the anchor_map from citations.

        Args:
            failure_mode: The failure mode for this SOP.
            asset_id:     Target asset identifier.
            events:       Historical audit events (from HistoricalEventAggregator).
            citations:    RAG citations (from RetrievalPipeline.search).
            title_it:     Optional IT title override. Defaults to generated title.

        Returns:
            Tuple of (SOPDraft_without_en_sections, anchor_map).
            The caller must then call SOPTranslator.translate() to fill sections_en.

        Note:
            The returned SOPDraft has sections_en copied from sections_it as a
            placeholder (will be replaced by the translator). anchor_map is returned
            separately for the translator to use.
        """
        prompt = _build_sop_generation_prompt(
            failure_mode=failure_mode,
            asset_id=asset_id,
            events=events,
            citations=citations,
        )

        response = await self._llm.ainvoke(prompt)
        if hasattr(response, "content"):
            raw_text = response.content
        else:
            raw_text = str(response)

        # Parse sections from LLM output
        sections_it = _parse_sections(raw_text, failure_mode=failure_mode, asset_id=asset_id, citations=citations)

        # Build anchor_map from the generated IT sections + citations
        anchor_map = build_anchor_map_from_text(sections_it, citations)

        # Generate the SOP draft (sections_en will be filled by translator)
        # We use sections_it as placeholder for sections_en to satisfy the model validator.
        # The agent will call translator.translate() and create a new SOPDraft with real EN.
        effective_title_it = title_it or f"SOP: {failure_mode} su {asset_id}"

        sop_id = str(uuid4())
        now = datetime.now(timezone.utc)

        sop_draft = SOPDraft(
            sop_id=sop_id,
            failure_mode=failure_mode,
            asset_id=asset_id,
            title_it=effective_title_it,
            title_en=f"SOP: {failure_mode} on {asset_id}",  # placeholder, overwritten after EN translation
            sections_it=sections_it,
            sections_en=sections_it,  # placeholder — agent replaces with translated sections
            citations=citations,
            anchor_map=anchor_map,
            generated_at=now,
            approved=False,
        )

        logger.info(
            "sop_builder_generated",
            sop_id=sop_id,
            failure_mode=failure_mode,
            asset_id=asset_id,
            anchor_count=len(anchor_map),
            citation_count=len(citations),
        )

        return sop_draft, anchor_map


def _parse_sections(
    raw_text: str,
    *,
    failure_mode: str,
    asset_id: str,
    citations: list[Any],
) -> dict[str, str]:
    """Parse LLM output into fixed-section dict with [SRC:N] anchors.

    Attempts to extract the 5 fixed IT sections from LLM output.
    Falls back to a structured stub if parsing fails (robustness).

    Args:
        raw_text:     Raw LLM output text.
        failure_mode: Used in fallback stub content.
        asset_id:     Used in fallback stub content.
        citations:    Used to generate citation references in fallback.

    Returns:
        Dict with all 5 SECTION_KEYS_IT as keys.
    """
    sections: dict[str, str] = {}

    # Try to parse sections from LLM output using section headers
    for key in SECTION_KEYS_IT:
        # Look for the section in the LLM output (case-insensitive header match)
        pattern = re.compile(
            rf"(?:#{'{1,3}'}\s*)?{re.escape(key)}[\s:]+(.+?)(?=(?:#{'{1,3}'}\s*)?(?:{'|'.join(SECTION_KEYS_IT)})|$)",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(raw_text)
        if match:
            content = match.group(1).strip()
            sections[key] = content if content else _fallback_section(key, failure_mode, asset_id, citations)
        else:
            sections[key] = _fallback_section(key, failure_mode, asset_id, citations)

    # Ensure all 5 sections are present
    for key in SECTION_KEYS_IT:
        if key not in sections or not sections[key]:
            sections[key] = _fallback_section(key, failure_mode, asset_id, citations)

    return sections


def _fallback_section(
    key: str,
    failure_mode: str,
    asset_id: str,
    citations: list[Any],
) -> str:
    """Generate a fallback section content with citation anchors.

    Used when LLM output cannot be parsed. Ensures [SRC:N] anchors
    are always present so anchor_map can be built correctly.
    """
    # Generate citation references
    citation_refs = ""
    if citations:
        refs = [f"[SRC:{i + 1}]" for i in range(min(len(citations), 3))]
        citation_refs = " " + " ".join(refs)

    fallback_content = {
        "Scopo": f"Procedura operativa per la gestione di {failure_mode} sull'asset {asset_id}.{citation_refs}",
        "Prerequisiti": f"Verificare disponibilità attrezzatura e sicurezza area per {asset_id}.{citation_refs}",
        "Passi": f"1. Analizzare causa guasto {failure_mode}.{citation_refs}\n2. Applicare azione correttiva.\n3. Verificare risoluzione.",
        "Sicurezza": f"Rispettare le norme di sicurezza previste per {asset_id}. Indossare DPI adeguati.",
        "Riferimenti": f"Documentazione tecnica {asset_id}.{citation_refs}",
    }
    return fallback_content.get(key, f"Sezione {key} per {failure_mode}.{citation_refs}")


def _build_sop_generation_prompt(
    *,
    failure_mode: str,
    asset_id: str,
    events: list[dict[str, Any]],
    citations: list[Any],
) -> list[Any]:
    """Build the LLM prompt for IT SOP generation.

    Instructs the LLM to generate a 5-section Italian SOP with [SRC:N] anchors.

    Returns:
        List of message dicts suitable for LangChain LLM invocation.
    """
    # Summarize historical events
    events_summary = _summarize_events(events)

    # Format citations for the prompt
    citations_text = _format_citations(citations)

    system_content = (
        "Sei un esperto di documentazione tecnica industriale. "
        "Il tuo compito è generare un SOP (Standard Operating Procedure) in italiano "
        "per la gestione di un guasto su un asset industriale. "
        "\n\nSTRUTTURA OBBLIGATORIA — genera esattamente queste 5 sezioni con i loro titoli:\n"
        "## Scopo\n[contenuto]\n\n"
        "## Prerequisiti\n[contenuto]\n\n"
        "## Passi\n[contenuto]\n\n"
        "## Sicurezza\n[contenuto]\n\n"
        "## Riferimenti\n[contenuto]\n\n"
        "\nCITAZIONI — usa le seguenti fonti e inserisci i marker [SRC:N] nel testo:\n"
        f"{citations_text}\n\n"
        "REGOLA CRITICA (Pitfall §1):\n"
        "- Inserisci i marker [SRC:N] nel testo ESATTAMENTE dove citi una fonte.\n"
        "- Ogni fonte deve essere citata almeno una volta.\n"
        "- NON aggiungere marker [SRC:N] senza la relativa fonte nella lista sopra."
    )

    user_content = (
        f"Genera un SOP in italiano per:\n"
        f"- Modalità di guasto: {failure_mode}\n"
        f"- Asset: {asset_id}\n\n"
        f"Contesto storico (eventi RCA/downtime/coaching):\n{events_summary}\n\n"
        f"Usa le fonti fornite e inserisci i marker [SRC:N] nel testo."
    )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        return [SystemMessage(content=system_content), HumanMessage(content=user_content)]
    except ImportError:
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]


def _summarize_events(events: list[dict[str, Any]]) -> str:
    """Format historical events for the LLM prompt."""
    if not events:
        return "Nessun evento storico disponibile."

    lines: list[str] = []
    for i, event in enumerate(events[:10]):  # cap at 10 for prompt size
        action_type = event.get("action_type", "unknown")
        agent_id = event.get("agent_id", "unknown")
        ts = event.get("ts", "")
        ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        lines.append(f"{i + 1}. [{ts_str}] {action_type} (agent: {agent_id})")

    if len(events) > 10:
        lines.append(f"... e altri {len(events) - 10} eventi.")

    return "\n".join(lines)


def _format_citations(citations: list[Any]) -> str:
    """Format RAG citations for the LLM prompt."""
    if not citations:
        return "Nessuna fonte disponibile."

    lines: list[str] = []
    for i, citation in enumerate(citations):
        source_uri = getattr(citation, "source_uri", f"source://unknown-{i + 1}")
        snippet = getattr(citation, "snippet", "")[:200]
        lines.append(f"[SRC:{i + 1}] {source_uri}: {snippet}")

    return "\n".join(lines)


__all__ = ["SOPBuilder"]
