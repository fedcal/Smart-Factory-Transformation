"""Post-LLM citation validator with single-replan loop (D-OA-04).

Wraps the final ``AIMessage`` returned by ``create_react_agent`` and enforces
the citation rule from RESEARCH Pattern 7 (lines 722-754):

    1. If the thread never called ``rag_search`` -> no factual claim was made,
       no citation is required, return the response unchanged.
    2. If the thread DID call ``rag_search``:
         a. Check inline ``[N]`` references in the response content.
         b. Check ``additional_kwargs['citations']`` is a non-empty list.
       Both must be true to pass.
    3. On failure with ``retries < max_retries`` (default 1): re-invoke the
       react agent once with an appended ``SystemMessage`` (REPLAN_AUGMENT)
       asking it to re-emit with citations.
    4. On failure with ``retries >= max_retries``: log a structlog warning
       (`citation_missing_after_replan`) and return an immutable copy of the
       response with ``additional_kwargs['citations_missing'] = True``. We
       NEVER block the response — D-OA-04 explicitly prefers a flagged
       answer over a blocked thread.

Why an out-of-graph wrapper rather than a LangGraph node loop:
    A graph-level cycle would inflate ``recursion_limit`` accounting (we'd
    need 6 to allow one replan on top of D-OA-01's 5). An external wrapper
    keeps the recursion budget honest and produces a single Langfuse span
    for the retry that the audit pipeline can find by name.

Immutability (coding-style.md):
    The original ``response`` AIMessage is never mutated. On the failure
    branch we use ``response.model_copy(update={...})`` (Pydantic v2 idiom)
    so the original object passed in by the caller remains intact.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from ops_operator_assistant.prompts import REPLAN_AUGMENT

logger = structlog.get_logger("agent.operator-assistant.validators")


_INLINE_CITATION_PATTERN = re.compile(r"\[\d+\]")


def _used_rag_search(state: dict[str, Any]) -> bool:
    """Inspect state.messages for a ToolMessage(name='rag_search')."""
    for msg in state.get("messages", []):
        if isinstance(msg, ToolMessage) and msg.name == "rag_search":
            return True
    return False


def _has_inline_citation(content: str) -> bool:
    """Return True iff content contains at least one ``[N]`` reference."""
    return bool(_INLINE_CITATION_PATTERN.search(content))


def _has_citations_kwarg(response: AIMessage) -> bool:
    """Return True iff ``additional_kwargs['citations']`` is a non-empty list."""
    citations = response.additional_kwargs.get("citations")
    return bool(citations) and isinstance(citations, list)


async def validate_or_replan(
    state: dict[str, Any],
    response: AIMessage,
    *,
    react_agent: Any,
    config: dict[str, Any],
    retries: int = 0,
    max_retries: int = 1,
) -> AIMessage:
    """Validate the response's citations; replan once if missing.

    Args:
        state: AgentState dict with at least ``messages`` (list of BaseMessage).
        response: The final AIMessage returned by ``create_react_agent``.
        react_agent: The compiled react runnable (used to re-invoke on replan).
            Must expose ``ainvoke({"messages": [...]}, config=...)``.
        config: LangGraph invoke config (forwarded verbatim to the replan call).
        retries: Internal recursion counter; callers pass 0.
        max_retries: Maximum replan attempts (D-OA-04 locks 1).

    Returns:
        The original response when validation passes or no rag_search was used;
        the replan response when the second LLM call produces valid citations;
        an immutable copy with ``citations_missing=True`` when both attempts
        fail (the response is NOT blocked — flagged-and-emitted per D-OA-04).
    """
    if not _used_rag_search(state):
        # No factual claim => no citation required. Skip validation entirely.
        return response

    inline_ok = _has_inline_citation(response.content)
    citations_ok = _has_citations_kwarg(response)

    if inline_ok and citations_ok:
        return response

    if retries >= max_retries:
        logger.warning(
            "citation_missing_after_replan",
            agent="operator-assistant",
            thread_id=state.get("thread_id", "unknown"),
            inline_ok=inline_ok,
            citations_ok=citations_ok,
            retries=retries,
        )
        # Immutable copy — original response is left untouched (coding-style.md).
        merged_kwargs = {**response.additional_kwargs, "citations_missing": True}
        return response.model_copy(update={"additional_kwargs": merged_kwargs})

    # Replan: append the augmentation SystemMessage and re-invoke the agent once.
    augmented_messages = list(state.get("messages", [])) + [
        SystemMessage(content=REPLAN_AUGMENT)
    ]
    replan_result = await react_agent.ainvoke(
        {"messages": augmented_messages}, config=config
    )
    new_response = replan_result["messages"][-1]

    # Recurse with retries+1; max_retries=1 means we will not loop again.
    # The recursion terminates because retries is bounded by max_retries.
    return await validate_or_replan(
        state,
        new_response,
        react_agent=react_agent,
        config=config,
        retries=retries + 1,
        max_retries=max_retries,
    )


__all__ = ["validate_or_replan"]
