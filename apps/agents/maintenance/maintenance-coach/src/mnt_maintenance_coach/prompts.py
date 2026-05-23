"""Bilingual IT+EN prompts for MaintenanceCoach (D-MC-02).

Contains:
  - ``SYSTEM_PROMPT_IT``: Italian role + keyword detection + output format
  - ``SYSTEM_PROMPT_EN``: English mirror
  - ``HELP_KEYWORDS_IT``: Italian help trigger keywords
  - ``HELP_KEYWORDS_EN``: English help trigger keywords
  - ``build_step_prompt``: compose per-step prompt for the LLM
  - ``detect_help_keyword``: heuristic defense-in-depth for keyword detection

Keyword detection strategy (D-MC-02):
  The system prompt instructs the LLM to invoke ``request_help`` when help
  keywords appear in technician input. ``detect_help_keyword`` is an additional
  heuristic safety net that the Coach can use to verify the LLM's tool call
  decision — false positives (e.g. the word "stuck" in a technical description
  rather than a help request) result in a supervisor interrupt, which is the
  correct safe-failure mode (T-V7-coach-bypass-help mitigation).

  False positive risk: documented. The LLM has broader context to disambiguate;
  the heuristic does not. The tradeoff is: occasional unnecessary supervisor
  interrupts vs. a missed help request. The safer failure mode is the interrupt.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from mnt_maintenance_coach.models import StepReport


# ---------------------------------------------------------------------------
# Help keyword tuples (D-MC-02 examples from 07-CONTEXT.md)
# ---------------------------------------------------------------------------

HELP_KEYWORDS_IT: tuple[str, ...] = (
    "aiuto",
    "non ci riesco",
    "sono fermo",
    "blocco",
    "bloccato",
    "non capisco",
    "ho bisogno di aiuto",
    "supervisore",
    "non riesco",
    "ho un problema",
    "non so come",
)

HELP_KEYWORDS_EN: tuple[str, ...] = (
    "help",
    "stuck",
    "blocked",
    "i need help",
    "i don't understand",
    "supervisor",
    "i can't",
    "don't know how",
    "having trouble",
    "need assistance",
)


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_IT = """\
Sei un coach di manutenzione che guida passo-passo un tecnico nell'esecuzione \
di una SOP (Standard Operating Procedure) per la riparazione di un asset tessile.

**Il tuo ruolo:**
- Fornisci istruzioni chiare e precise per ogni passo della procedura.
- Spiega il "perché" di ogni azione quando è rilevante per la sicurezza o la qualità.
- Usa le citazioni RAG per supportare le istruzioni (includi source_uri nella risposta).
- Adatta il linguaggio al livello tecnico del tecnico (usa il feedback precedente come segnale).

**Rilevamento richieste di aiuto:**
Quando il tecnico usa le seguenti parole chiave — o varianti equivalenti — DEVI invocare \
immediatamente il tool `request_help`:
- "aiuto", "non ci riesco", "sono fermo", "bloccato", "blocco"
- "non capisco", "ho bisogno di aiuto", "supervisore"
- "non riesco", "ho un problema", "non so come"

Non tentare di rispondere alla richiesta di aiuto da solo. Invoca `request_help` con:
- `reason`: descrizione breve del problema segnalato dal tecnico
- `context`: contesto del passo corrente + input del tecnico
- `intervention_id`: ID intervento dalla configurazione del thread
- `current_step`: numero passo corrente

**Formato risposta (output JSON per parsing):**
```json
{
  "guidance": "<istruzioni markdown per il passo corrente>",
  "step_complete": <true se il tecnico ha confermato il completamento, false altrimenti>,
  "citations": [{"source_uri": "...", "snippet": "...", "score": 0.95}]
}
```

**Sicurezza e qualità:**
- Se rilevi un potenziale rischio di sicurezza, segnalalo PRIMA di qualsiasi altra istruzione.
- Non inventare procedure non supportate dalla SOP o dalla knowledge base.
"""

SYSTEM_PROMPT_EN = """\
You are a maintenance coach guiding a technician step-by-step through a Standard \
Operating Procedure (SOP) for repairing a textile asset.

**Your role:**
- Provide clear, precise instructions for each procedure step.
- Explain the "why" behind each action when relevant for safety or quality.
- Use RAG citations to support instructions (include source_uri in response).
- Adapt your language to the technician's expertise level (use prior feedback as signal).

**Help request detection:**
When the technician uses the following keywords — or equivalent variants — you MUST \
immediately invoke the `request_help` tool:
- "help", "stuck", "blocked", "i need help"
- "i don't understand", "supervisor", "i can't"
- "don't know how", "having trouble", "need assistance"

Do NOT attempt to answer the help request yourself. Invoke `request_help` with:
- `reason`: brief description of the problem reported by the technician
- `context`: current step context + technician input
- `intervention_id`: intervention ID from the thread configuration
- `current_step`: current step number

**Response format (JSON output for parsing):**
```json
{
  "guidance": "<markdown instructions for current step>",
  "step_complete": <true if technician confirmed completion, false otherwise>,
  "citations": [{"source_uri": "...", "snippet": "...", "score": 0.95}]
}
```

**Safety and quality:**
- If you detect a potential safety risk, flag it BEFORE any other instruction.
- Do not invent procedures not supported by the SOP or knowledge base.
"""


# ---------------------------------------------------------------------------
# build_step_prompt — compose per-step prompt for the LLM
# ---------------------------------------------------------------------------


def build_step_prompt(
    *,
    sop_id: str,
    step_no: int,
    completed_summary: list["StepReport"],
    lang: Literal["it", "en"] = "it",
) -> str:
    """Compose the step-level prompt for the LLM.

    Includes:
      - Selected language system prompt (IT or EN)
      - SOP identifier and current step number
      - Summary of last ≤3 completed steps (token-efficient context)

    Args:
        sop_id: SOP identifier (e.g. 'SOP-LOOM-001')
        step_no: Current zero-indexed step number
        completed_summary: List of recently completed steps to include as context.
            Caller should pass ``state.completed_steps[-3:]`` to cap token usage.
        lang: Language selection ('it' or 'en'). Defaults to 'it'.

    Returns:
        Formatted prompt string for the LLM call.
    """
    system = SYSTEM_PROMPT_IT if lang == "it" else SYSTEM_PROMPT_EN

    # Build context from completed steps (last ≤3)
    recent = completed_summary[-3:] if completed_summary else []
    steps_context = ""
    if recent:
        lines = []
        for step in recent:
            lines.append(
                f"  - Step {step.step_no}: '{step.instruction[:100]}...' "
                f"— Tech: '{step.technician_input[:80]}...' ({step.duration_minutes} min)"
                if len(step.instruction) > 100 or len(step.technician_input) > 80
                else f"  - Step {step.step_no}: '{step.instruction}' "
                f"— Tech: '{step.technician_input}' ({step.duration_minutes} min)"
            )
        steps_context_label = (
            "Passi completati di recente:" if lang == "it" else "Recently completed steps:"
        )
        steps_context = f"\n{steps_context_label}\n" + "\n".join(lines)

    if lang == "it":
        return (
            f"{system}\n\n"
            f"SOP: {sop_id}\n"
            f"Passo corrente: {step_no}"
            f"{steps_context}\n\n"
            "Recupera il contenuto della SOP per questo passo via rag_search e "
            "fornisci le istruzioni nel formato JSON specificato sopra."
        )
    else:
        return (
            f"{system}\n\n"
            f"SOP: {sop_id}\n"
            f"Current step: {step_no}"
            f"{steps_context}\n\n"
            "Retrieve the SOP content for this step via rag_search and "
            "provide instructions in the JSON format specified above."
        )


# ---------------------------------------------------------------------------
# detect_help_keyword — heuristic defense-in-depth (D-MC-02)
# ---------------------------------------------------------------------------


def detect_help_keyword(technician_input: str, lang: Literal["it", "en"]) -> bool:
    """Heuristic keyword detection for help requests (D-MC-02 defense-in-depth).

    Performs a case-insensitive substring scan against the appropriate keywords
    tuple. This is a supplement to the LLM's tool call detection — not a
    replacement. The LLM has broader context; this heuristic covers cases where
    the LLM misses an obvious keyword.

    False positive risk:
        Words like "stuck" (e.g. in "the bolt is stuck") may trigger a false
        positive in a non-help context. This is an accepted tradeoff: a false
        positive causes a supervisor interrupt (safe), while a false negative
        means a technician's help request is ignored (unsafe). The LLM's
        context-aware analysis is the primary detector; this is the failsafe.

    Args:
        technician_input: Raw text from the technician.
        lang: Language to check keywords for.

    Returns:
        True if any keyword is found in the input (case-insensitive). False otherwise.
    """
    normalized = technician_input.lower()
    keywords = HELP_KEYWORDS_IT if lang == "it" else HELP_KEYWORDS_EN
    return any(kw in normalized for kw in keywords)


__all__ = [
    "HELP_KEYWORDS_EN",
    "HELP_KEYWORDS_IT",
    "SYSTEM_PROMPT_EN",
    "SYSTEM_PROMPT_IT",
    "build_step_prompt",
    "detect_help_keyword",
]
