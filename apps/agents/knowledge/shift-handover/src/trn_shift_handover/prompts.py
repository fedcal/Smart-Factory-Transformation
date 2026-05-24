"""Bilingue system prompts for ShiftHandover (D-SH-01, Plan 08-02).

Prompt structure:
    1. SYSTEM_PROMPT_IT — Italian prompt for the narrative summary step.
    2. SYSTEM_PROMPT_EN — English mirror (BGE-M3 cross-lingual support Phase 5).
    3. build_system_prompt(lang) — returns the appropriate prompt.
    4. build_narrative_prompt(report_context) — builds the LLM narrative request.

Usage context:
    ShiftAggregator.build_report() is LLM-free (counts + citations derived
    deterministically from audit rows). The LLM is used ONLY to produce the
    3-5 line narrative_summary from the already-computed HandoverReport data.
    This keeps the LLM-free aggregation path under 30s (Pitfall §4).

Design decisions:
    - The narrative prompt injects only numeric summaries — no raw audit content —
      to prevent prompt injection from JSONB field values (T-08-04).
    - The prompt is capped: "Scrivi 3-5 righe." / "Write 3-5 lines." to bound
      LLM output length and response time.
    - HITL (dual supervisor sign-off) is handled by the agent, not the prompt.
"""

from __future__ import annotations

from typing import Any, Literal

# ---------------------------------------------------------------------------
# Italian system prompt (primary)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_IT: str = """\
Sei ShiftHandover, l'assistente di passaggio turno per una fabbrica tessile manifatturiera.
Il tuo compito è produrre un breve sommario esecutivo (3-5 righe) del turno appena concluso.

==========
CONTESTO RICEVUTO:
Riceverai dati aggregati dal turno: conteggi di alert, work order, fermi macchina, eventi
qualità, stato impianti. Questi dati sono già verificati e computati deterministicamente.

==========
REGOLE OUTPUT:
1. Scrivi SOLO 3-5 righe in italiano chiaro e conciso.
2. Non inventare dati — usa solo le informazioni fornite nel contesto del turno.
3. Indica i punti critici da segnalare al supervisore del turno successivo.
4. Non aggiungere intestazioni, elenchi puntati o formattazione Markdown — testo semplice.
5. Concludi con la raccomandazione più importante per il turno successivo.
"""

# ---------------------------------------------------------------------------
# English system prompt (BGE-M3 cross-lingual support Phase 5)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_EN: str = """\
You are ShiftHandover, the shift-handover assistant for a textile manufacturing plant.
Your task is to produce a brief executive summary (3-5 lines) of the completed shift.

==========
RECEIVED CONTEXT:
You will receive aggregated shift data: alert counts, work order counts, downtime events,
quality events, equipment status. These figures are pre-verified and deterministically computed.

==========
OUTPUT RULES:
1. Write ONLY 3-5 lines in clear, concise English.
2. Do NOT invent data — use only the information provided in the shift context.
3. Highlight critical points to be reported to the next shift supervisor.
4. No headings, bullet points, or Markdown formatting — plain text only.
5. Conclude with the single most important recommendation for the next shift.
"""

# ---------------------------------------------------------------------------
# Deterministic report template (used for HITL evidence + audit trail)
# ---------------------------------------------------------------------------

REPORT_TEMPLATE: str = """\
=== SHIFT HANDOVER REPORT ===
Period: {boundary_label} ({shift_start} → {shift_end})

COUNTS
  Open alerts:            {open_alerts}
  Completed work orders:  {completed_work_orders}
  Downtime events:        {downtime_events}
  Quality events:         {quality_events}

EQUIPMENT STATUS
{equipment_status_block}

CITATIONS
  Total RAG citations:    {citation_count}

NARRATIVE SUMMARY
{narrative_summary}
============================
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_system_prompt(*, lang: Literal["it", "en"] = "it") -> str:
    """Return the appropriate bilingue system prompt.

    Args:
        lang: Language selector. 'it' → Italian prompt (default);
              'en' → English prompt (BGE-M3 cross-lingual Phase 5).

    Returns:
        The system prompt string for the selected language.
    """
    if lang == "en":
        return SYSTEM_PROMPT_EN
    return SYSTEM_PROMPT_IT


def build_narrative_prompt(report_context: dict[str, Any]) -> str:
    """Build the LLM narrative request from pre-computed HandoverReport data.

    Injects only numeric summaries and equipment status — no raw JSONB content —
    to prevent prompt injection from audit field values (T-08-04 mitigation).

    Args:
        report_context: Dict with keys: open_alerts, completed_work_orders,
                        downtime_events, quality_events, equipment_status,
                        boundary_label. Typically built from HandoverReport fields.

    Returns:
        A human-turn message string for the LLM narrative step.
    """
    open_alerts = int(report_context.get("open_alerts", 0))
    completed_work_orders = int(report_context.get("completed_work_orders", 0))
    downtime_events = int(report_context.get("downtime_events", 0))
    quality_events = int(report_context.get("quality_events", 0))
    equipment_status: dict[str, str] = report_context.get("equipment_status", {})
    boundary_label: str = str(report_context.get("boundary_label", ""))

    # Equipment status block (sanitized — only asset_id + status, no raw JSONB)
    if equipment_status:
        eq_lines = "\n".join(
            f"  {asset_id}: {status}"
            for asset_id, status in sorted(equipment_status.items())
        )
    else:
        eq_lines = "  Nessun dato disponibile / No data available"

    return (
        f"Turno / Shift: {boundary_label}\n"
        f"Alert aperti / Open alerts: {open_alerts}\n"
        f"Work order completati / Completed work orders: {completed_work_orders}\n"
        f"Fermi macchina / Downtime events: {downtime_events}\n"
        f"Eventi qualità / Quality events: {quality_events}\n"
        f"Stato impianti / Equipment status:\n{eq_lines}\n\n"
        "Produci il sommario esecutivo (3-5 righe). / Produce the executive summary (3-5 lines)."
    )


def format_report(
    *,
    boundary_label: str,
    shift_start: str,
    shift_end: str,
    open_alerts: int,
    completed_work_orders: int,
    downtime_events: int,
    quality_events: int,
    equipment_status: dict[str, str],
    citation_count: int,
    narrative_summary: str,
) -> str:
    """Format a HandoverReport as a human-readable text block.

    Used for HITL supervisor display and audit trail evidence panels.

    Args:
        boundary_label:       e.g. '06:00-14:00'
        shift_start:          ISO string of shift start.
        shift_end:            ISO string of shift end.
        open_alerts:          Count of ANOMALY_ALERT rows.
        completed_work_orders: Count of DOWNTIME_VERDICT rows with work_order_id.
        downtime_events:      Count of maintenance.downtime_events rows.
        quality_events:       Count of QUALITY_VERDICT rows.
        equipment_status:     Dict {asset_id: status}.
        citation_count:       Number of RagCitation objects collected.
        narrative_summary:    LLM-generated executive summary text.

    Returns:
        Formatted plain-text report string.
    """
    if equipment_status:
        eq_block = "\n".join(
            f"  {asset_id}: {status}"
            for asset_id, status in sorted(equipment_status.items())
        )
    else:
        eq_block = "  (no data)"

    return REPORT_TEMPLATE.format(
        boundary_label=boundary_label,
        shift_start=shift_start,
        shift_end=shift_end,
        open_alerts=open_alerts,
        completed_work_orders=completed_work_orders,
        downtime_events=downtime_events,
        quality_events=quality_events,
        equipment_status_block=eq_block,
        citation_count=citation_count,
        narrative_summary=narrative_summary or "(pending LLM narrative)",
    )


__all__ = [
    "REPORT_TEMPLATE",
    "SYSTEM_PROMPT_EN",
    "SYSTEM_PROMPT_IT",
    "build_narrative_prompt",
    "build_system_prompt",
    "format_report",
]
