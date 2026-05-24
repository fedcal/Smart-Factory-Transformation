"""Prompt builders for DocumentationSynthesizer (D-DS-01, Pitfall §1).

Two prompts:
    - IT SOP generation: fixed sections + [SRC:N] anchors (D-DS-01)
    - EN translation: preserve [SRC:N] markers in place (Pitfall §1 mitigation)
"""

from __future__ import annotations

from typing import Any

from trn_documentation_synthesizer.models import SECTION_KEYS_IT


def build_it_generation_prompt(
    *,
    failure_mode: str,
    asset_id: str,
    events_summary: str,
    citations_text: str,
) -> list[Any]:
    """Build the IT SOP generation prompt (D-DS-01, Pitfall §1).

    Instructs the LLM to generate a 5-section Italian SOP with [SRC:N] anchors
    for the given failure mode and asset.

    Args:
        failure_mode:     The failure mode driving the SOP.
        asset_id:         Target asset identifier.
        events_summary:   Formatted historical events summary.
        citations_text:   Formatted RAG citations with [SRC:N] indices.

    Returns:
        List of LangChain-compatible messages (SystemMessage + HumanMessage).
    """
    section_list = "\n".join(f"## {key}\n[contenuto con [SRC:N] dove applicabile]" for key in SECTION_KEYS_IT)

    system_content = (
        "Sei un esperto di documentazione tecnica industriale specializzato in manutenzione di impianti tessili. "
        "Il tuo compito è generare un SOP (Standard Operating Procedure) in italiano "
        "per la gestione di un guasto specifico su un asset industriale. "
        "\n\nSTRUTTURA OBBLIGATORIA — il SOP deve avere esattamente queste 5 sezioni:\n"
        f"{section_list}\n\n"
        "REGOLE CRITICHE per le citazioni (Pitfall §1 — citation anchoring):\n"
        "1. Inserisci il marker [SRC:N] nel testo ESATTAMENTE dove citi la fonte N.\n"
        "2. Ogni fonte nella lista deve essere citata almeno una volta nel testo.\n"
        "3. NON inventare fonti o aggiungere [SRC:N] non presenti nella lista.\n"
        "4. I marker [SRC:N] devono apparire nel testo come riferimenti in-line.\n"
        "\nEsempio corretto: 'Verificare la temperatura del motore [SRC:1] prima di procedere.'\n"
        "Esempio errato: 'Verificare la temperatura.' (senza citazione)"
    )

    user_content = (
        f"Genera un SOP in italiano per:\n"
        f"- Modalità di guasto: {failure_mode}\n"
        f"- Asset: {asset_id}\n\n"
        f"Contesto storico (eventi RCA/downtime/coaching):\n{events_summary}\n\n"
        f"Fonti disponibili (usa queste e inserisci i marker [SRC:N]):\n{citations_text}\n\n"
        "Genera il SOP completo con tutte e 5 le sezioni e i marker [SRC:N] appropriati."
    )

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        return [SystemMessage(content=system_content), HumanMessage(content=user_content)]
    except ImportError:
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]


def build_en_translation_prompt(
    *,
    section_key_it: str,
    section_key_en: str,
    content_it: str,
    anchor_map: dict[str, str],
) -> list[Any]:
    """Build the EN translation prompt for a single IT SOP section (D-DS-01, Pitfall §1).

    Instructs the LLM to translate the section while preserving all [SRC:N] markers.

    Args:
        section_key_it:  Italian section key (e.g. "Scopo").
        section_key_en:  English section key (e.g. "Purpose").
        content_it:      Italian section content with [SRC:N] anchors.
        anchor_map:      Dict of "[SRC:N]" → source_uri (for LLM context).

    Returns:
        List of LangChain-compatible messages (SystemMessage + HumanMessage).
    """
    anchor_summary = "; ".join(
        f"{k} cites {v}" for k, v in sorted(anchor_map.items())
    ) if anchor_map else "none"

    system_content = (
        "You are a technical SOP translator from Italian to English for industrial maintenance documentation. "
        "\n\nCRITICAL RULES — citation re-anchoring (Pitfall §1):\n"
        "1. PRESERVE every [SRC:N] marker EXACTLY where it appears in the Italian text.\n"
        "2. Do NOT translate, modify, remove, or reorder [SRC:N] markers.\n"
        "3. Do NOT add new [SRC:N] markers not present in the Italian text.\n"
        "4. Output ONLY the translated section content — no headers, no section keys.\n"
        "5. Keep technical terms accurate for industrial maintenance context.\n"
        f"\nCitation context (reference only, do NOT reproduce in output): {anchor_summary}"
    )

    user_content = (
        f"Translate this Italian SOP section '{section_key_it}' to English '{section_key_en}'.\n"
        f"MUST preserve all [SRC:N] markers exactly.\n\n"
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


__all__ = [
    "build_en_translation_prompt",
    "build_it_generation_prompt",
]
