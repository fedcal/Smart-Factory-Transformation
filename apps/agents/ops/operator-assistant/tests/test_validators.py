"""Tests for ``ops_operator_assistant.validators.validate_or_replan`` (Plan 06-10).

Covers (D-OA-04, RESEARCH Pattern 7 lines 722-754):
    - test_no_rag_call_skips_validation: response is returned unchanged when the
      thread never invoked ``rag_search`` (no factual claim => no citation
      required).
    - test_inline_citation_passes: response with ``[N]`` inline + citations
      list is returned unchanged.
    - test_missing_inline_triggers_replan: one replan invocation is issued
      when inline citations are absent after a rag_search call.
    - test_replan_max_one_retry_emits_warning_flag: after the replan still
      produces no inline citations, the final AIMessage carries
      ``additional_kwargs['citations_missing'] = True`` (max 1 retry).
    - test_warning_event_emitted: ``structlog.warning`` is emitted on the
      failed-after-replan branch (audit-friendly observability).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from ops_operator_assistant.validators import validate_or_replan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(*, used_rag: bool) -> dict[str, Any]:
    """Build a fake AgentState dict with optional rag_search ToolMessage."""
    messages: list[Any] = [HumanMessage(content="Procedura per rottura ordito?")]
    if used_rag:
        messages.append(
            ToolMessage(
                content='[{"source_uri":"sop://loom/warp","snippet":"...","score":0.9}]',
                tool_call_id="call_rag_1",
                name="rag_search",
            )
        )
    return {"messages": messages, "thread_id": "ops.operator-assistant.t1"}


def _make_react_agent_with_responses(*responses: AIMessage) -> AsyncMock:
    """Return AsyncMock whose ``ainvoke`` yields the configured responses on each call."""
    agent = AsyncMock()
    if responses:
        agent.ainvoke.side_effect = [{"messages": [r]} for r in responses]
    return agent


# ---------------------------------------------------------------------------
# Test 1 — no rag => skip validation (response returned as-is)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_rag_call_skips_validation() -> None:
    state = _make_state(used_rag=False)
    response = AIMessage(content="Risposta libera senza claim fattuali.")
    react_agent = _make_react_agent_with_responses()  # must NOT be called

    result = await validate_or_replan(
        state, response, react_agent=react_agent, config={"recursion_limit": 5}
    )

    assert result is response
    react_agent.ainvoke.assert_not_called()
    assert "citations_missing" not in result.additional_kwargs


# ---------------------------------------------------------------------------
# Test 2 — inline [N] + citations present => passes unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inline_citation_passes() -> None:
    state = _make_state(used_rag=True)
    response = AIMessage(
        content="Procedura [1]: chiamare manutenzione.",
        additional_kwargs={
            "citations": [{"source_uri": "sop://loom/warp", "snippet": "..."}],
        },
    )
    react_agent = _make_react_agent_with_responses()  # must NOT be called

    result = await validate_or_replan(
        state, response, react_agent=react_agent, config={"recursion_limit": 5}
    )

    assert result is response
    react_agent.ainvoke.assert_not_called()
    assert result.additional_kwargs.get("citations_missing") is not True


# ---------------------------------------------------------------------------
# Test 3 — missing inline triggers exactly one replan (good replan succeeds)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_inline_triggers_replan() -> None:
    state = _make_state(used_rag=True)
    response = AIMessage(content="Risposta senza citazioni.")
    good_replan = AIMessage(
        content="Risposta con citazione [1].",
        additional_kwargs={
            "citations": [{"source_uri": "sop://loom/warp", "snippet": "..."}],
        },
    )
    react_agent = _make_react_agent_with_responses(good_replan)

    result = await validate_or_replan(
        state, response, react_agent=react_agent, config={"recursion_limit": 5}
    )

    assert react_agent.ainvoke.call_count == 1
    assert result is good_replan
    assert result.additional_kwargs.get("citations_missing") is not True


# ---------------------------------------------------------------------------
# Test 4 — replan still fails => emit response with citations_missing=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replan_max_one_retry_emits_warning_flag() -> None:
    state = _make_state(used_rag=True)
    response = AIMessage(content="Prima risposta senza citazioni.")
    bad_replan = AIMessage(content="Seconda risposta ancora senza citazioni.")
    react_agent = _make_react_agent_with_responses(bad_replan)

    result = await validate_or_replan(
        state,
        response,
        react_agent=react_agent,
        config={"recursion_limit": 5},
        max_retries=1,
    )

    # Exactly ONE replan attempt; after second failure we emit the flag, not a 3rd retry.
    assert react_agent.ainvoke.call_count == 1
    assert result.additional_kwargs.get("citations_missing") is True
    # Original AIMessage MUST NOT be mutated (immutability — coding-style.md).
    assert "citations_missing" not in response.additional_kwargs
    assert "citations_missing" not in bad_replan.additional_kwargs


# ---------------------------------------------------------------------------
# Test 5 — structlog warning emitted on failed-after-replan branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warning_event_emitted(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _make_state(used_rag=True)
    response = AIMessage(content="Senza cit.")
    bad_replan = AIMessage(content="Ancora senza cit.")
    react_agent = _make_react_agent_with_responses(bad_replan)

    warning_calls: list[tuple[str, dict[str, Any]]] = []

    def _capture_warning(event: str, **kwargs: Any) -> None:
        warning_calls.append((event, kwargs))

    from ops_operator_assistant import validators as validators_mod

    monkeypatch.setattr(validators_mod.logger, "warning", _capture_warning)

    await validate_or_replan(
        state, response, react_agent=react_agent, config={"recursion_limit": 5}
    )

    event_names = [c[0] for c in warning_calls]
    assert "citation_missing_after_replan" in event_names
    # Audit-friendly identity triple should be present in the structured event.
    entry = next(c for c in warning_calls if c[0] == "citation_missing_after_replan")
    assert entry[1].get("agent") == "operator-assistant"
