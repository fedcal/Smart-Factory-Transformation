"""LLM rationale prompt template for the ProductionPlanner agent (RESEARCH §Pattern 5).

The LLM's *only* job here is to write a human-readable explanation of the
already-computed ScheduleDraft and to cite SOPs from the provided RAG hits.
It MUST NOT propose alternative items, asset assignments, or timestamps —
those are deterministic outputs of `schedule_spt`/`schedule_edd` in
`packages/sft-domain/scheduling/` and must remain reproducible (D-PP-01 +
T-V6-llm-hallucination mitigation).

The output is forced into a strict JSON schema:
    {"rationale_md": "<markdown bullets>", "citation_ids": [<int>, ...]}

If parsing fails, the agent uses a static fallback rationale (see
``agent.py::_FALLBACK_RATIONALE``) — that path is exercised by
``test_llm_invalid_json_triggers_fallback_rationale``.
"""

from __future__ import annotations

from typing import Iterable

from sft_domain.ops.citation import RagCitation


# Authored in English — D-OA-03 (operator-language detection) is a Phase 10 concern.
# The operator UI may translate this rationale, but the underlying LLM prompt
# stays English for prompt-cache friendliness and consistent JSON-mode output.
RATIONALE_PROMPT = """You are a textile production planner explaining a pre-computed schedule.

The schedule items, asset assignments, and timestamps have ALREADY been determined
by a deterministic algorithm (strategy = {strategy}). You MUST NOT propose alternatives
or modify any item — your only job is to write the rationale.

Write a concise markdown explanation (3-6 bullet points) covering:
  1. Why the chosen strategy fits this batch ({strategy} = {strategy_long}).
  2. How the items were ordered and assigned to assets.
  3. Any unscheduled orders and the likely reason (capacity, eligibility, horizon).
  4. Reference the supplied SOP snippets where they justify a choice.

Cite SOPs by their integer index in the provided citations block, using the form
[SOP-{{index}}] inline in the markdown.

Output STRICT JSON only — no prose, no markdown fences, no preamble:

{{
  "rationale_md": "<your markdown bullets here>",
  "citation_ids": [<list of integer citation indices you cited>]
}}
"""


_STRATEGY_LONG_NAMES = {
    "spt": "shortest-processing-time first",
    "edd": "earliest-due-date first",
}


def render_system_prompt(strategy: str) -> str:
    """Fill in the {strategy} placeholders for the system prompt."""
    return RATIONALE_PROMPT.format(
        strategy=strategy,
        strategy_long=_STRATEGY_LONG_NAMES.get(strategy, strategy),
    )


def citations_block(citations: Iterable[RagCitation]) -> str:
    """Render citations as a numbered block the LLM can reference by index.

    Returns an empty placeholder string when no citations are available so
    the prompt remains well-formed (the LLM is instructed to cite when
    available, not to fabricate when absent).
    """
    items = list(citations)
    if not items:
        return "[no SOP citations available — write rationale without citations]"
    lines = []
    for idx, c in enumerate(items):
        # Hard-cap snippet to keep prompt size predictable (matches RagCitation cap).
        snippet = c.snippet.replace("\n", " ").strip()
        if len(snippet) > 400:
            snippet = snippet[:397] + "..."
        lines.append(f"[SOP-{idx}] ({c.source_uri}, score={c.score:.2f}): {snippet}")
    return "\n".join(lines)
