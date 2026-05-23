"""Tests for ``OperatorAssistantAgent`` (Plan 06-10 — D-OA-01..04 + OPS-01).

Covers:
    - test_init_with_collaborators: constructor wires collaborators without crashing.
    - test_call_per_request_tools_instantiated: Pitfall §2 — RagSearchTool
      instantiated fresh per request (count == invocation count).
    - test_safe_invoke_used_with_recursion_limit_5: D-OA-01 — safe_invoke
      receives ``config['recursion_limit'] == 5``.
    - test_lang_detect_called_on_query: detect_language invoked with the
      operator's query (not e.g. with prompt).
    - test_response_lang_matches_query: Italian query -> response['lang'] == 'it'.
    - test_citation_validator_invoked_on_response: validate_or_replan called
      once with the (state, response, react_agent=..., config=...).
    - test_response_includes_citations_field: dict has 'citations' key.
    - test_response_includes_lang_field: dict has 'lang' key.

The agent is exercised with monkeypatched dependencies so the test suite
neither spawns an LLM nor touches Postgres/Qdrant/Neo4j.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from ops_operator_assistant import OperatorAssistantAgent
from ops_operator_assistant.models import OperatorChatRequest, OperatorChatResponse


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def collaborators() -> dict[str, Any]:
    """Return a dict of mocked collaborators for OperatorAssistantAgent.__init__."""
    return {
        "rag_pipeline": MagicMock(name="rag_pipeline"),
        "neo4j_driver": MagicMock(name="neo4j_driver"),
        "pool": MagicMock(name="pool"),
        "audit_writer": MagicMock(write=AsyncMock(return_value=None)),
        "queue_writer": MagicMock(name="queue_writer"),
        "nats": MagicMock(name="nats"),
        "safety_middleware": MagicMock(check=AsyncMock(return_value=None)),
        "checkpointer": MagicMock(name="checkpointer"),
    }


def _make_react_runnable(response: AIMessage, *, tool_messages: int = 0) -> Any:
    """Return an AsyncMock react runnable whose ainvoke yields ``response``."""
    messages: list[Any] = [HumanMessage(content="x")]
    for i in range(tool_messages):
        messages.append(
            ToolMessage(
                content="[]",
                tool_call_id=f"call_{i}",
                name="rag_search",
            )
        )
    messages.append(response)
    runnable = AsyncMock()
    runnable.ainvoke.return_value = {"messages": messages}
    return runnable


def _make_request(*, query: str = "Il telaio LOOM-01 si è fermato.") -> OperatorChatRequest:
    return OperatorChatRequest(
        query=query,
        user_roles=["technician"],
        thread_id="ops.operator-assistant.t-1",
    )


def _patch_agent_internals(
    monkeypatch: pytest.MonkeyPatch,
    *,
    react_runnable: Any,
    lang: str = "it",
    rag_tool_factory_spy: Any | None = None,
    validate_spy: Any | None = None,
    safe_invoke_spy: Any | None = None,
) -> None:
    """Centralize the monkeypatches so each test stays focused on its assertion."""
    from ops_operator_assistant import agent as agent_mod

    # Skip LLM construction.
    monkeypatch.setattr(agent_mod, "build_chat_model", lambda **kw: MagicMock(name="llm"))

    # Replace create_react_agent so we never compile a real graph.
    def _fake_create_react_agent(*args: Any, **kwargs: Any) -> Any:
        return react_runnable

    monkeypatch.setattr(agent_mod, "create_react_agent", _fake_create_react_agent)

    # Stub detect_language with a deterministic return.
    monkeypatch.setattr(agent_mod, "detect_language", lambda text: lang)

    # Spy on RagSearchTool constructor calls (Pitfall §2 per-request check).
    if rag_tool_factory_spy is not None:
        monkeypatch.setattr(agent_mod, "RagSearchTool", rag_tool_factory_spy)

    # Spy validate_or_replan (Task 3 module) so we test call shape not behavior.
    if validate_spy is not None:
        monkeypatch.setattr(agent_mod, "validate_or_replan", validate_spy)

    # Spy on safe_invoke to assert recursion_limit propagation.
    if safe_invoke_spy is not None:
        monkeypatch.setattr(agent_mod, "safe_invoke", safe_invoke_spy)


# ---------------------------------------------------------------------------
# Test 1 — construction
# ---------------------------------------------------------------------------


def test_init_with_collaborators(collaborators: dict[str, Any]) -> None:
    agent = OperatorAssistantAgent(**collaborators)
    assert isinstance(agent, OperatorAssistantAgent)


# ---------------------------------------------------------------------------
# Test 2 — Pitfall §2: tools instantiated PER REQUEST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_per_request_tools_instantiated(
    collaborators: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    response = AIMessage(content="Soluzione [1].", additional_kwargs={"citations": [{}]})
    react_runnable = _make_react_runnable(response, tool_messages=1)

    # Track RagSearchTool ctor calls.
    rag_ctor_calls: list[Any] = []

    class _SpyRag:
        def __init__(self, pipeline: Any, **kw: Any) -> None:
            rag_ctor_calls.append((pipeline, kw))
            # Mimic BaseTool minimally so tests do not depend on real init.
            self.pipeline = pipeline
        name = "rag_search"

    _patch_agent_internals(
        monkeypatch,
        react_runnable=react_runnable,
        rag_tool_factory_spy=_SpyRag,
        validate_spy=AsyncMock(side_effect=lambda state, resp, **kw: resp),
    )

    agent = OperatorAssistantAgent(**collaborators)

    await agent(_make_request())
    await agent(_make_request())

    # Pitfall §2: a fresh RagSearchTool per invocation, not a cached singleton.
    assert len(rag_ctor_calls) == 2, (
        f"RagSearchTool must be instantiated per request (Pitfall §2); "
        f"got {len(rag_ctor_calls)} ctor calls for 2 invocations."
    )


# ---------------------------------------------------------------------------
# Test 3 — safe_invoke called with recursion_limit=5 (D-OA-01)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_safe_invoke_used_with_recursion_limit_5(
    collaborators: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    response = AIMessage(content="ok [1].", additional_kwargs={"citations": [{}]})
    react_runnable = _make_react_runnable(response, tool_messages=1)

    captured_config: dict[str, Any] = {}

    async def _spy_safe_invoke(runnable: Any, state: Any, *, config: Any) -> Any:
        captured_config.update(config)
        return await runnable.ainvoke(state, config=config)

    _patch_agent_internals(
        monkeypatch,
        react_runnable=react_runnable,
        safe_invoke_spy=_spy_safe_invoke,
        validate_spy=AsyncMock(side_effect=lambda state, resp, **kw: resp),
    )

    agent = OperatorAssistantAgent(**collaborators)
    await agent(_make_request())

    assert captured_config.get("recursion_limit") == 5, (
        f"D-OA-01 mandates recursion_limit=5; got {captured_config.get('recursion_limit')!r}"
    )
    # thread_id must propagate into LangGraph config.configurable.
    assert (
        captured_config.get("configurable", {}).get("thread_id")
        == "ops.operator-assistant.t-1"
    )


# ---------------------------------------------------------------------------
# Test 4 — detect_language is called with the query (D-OA-03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lang_detect_called_on_query(
    collaborators: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    response = AIMessage(content="ok [1].", additional_kwargs={"citations": [{}]})
    react_runnable = _make_react_runnable(response, tool_messages=1)

    from ops_operator_assistant import agent as agent_mod

    captured: list[str] = []

    def _spy_detect(text: str) -> str:
        captured.append(text)
        return "it"

    # Apply standard patches, then override detect_language with our spy.
    _patch_agent_internals(
        monkeypatch,
        react_runnable=react_runnable,
        validate_spy=AsyncMock(side_effect=lambda state, resp, **kw: resp),
    )
    monkeypatch.setattr(agent_mod, "detect_language", _spy_detect)

    agent = OperatorAssistantAgent(**collaborators)
    await agent(_make_request(query="Il telaio LOOM-01 si è fermato."))

    assert captured == ["Il telaio LOOM-01 si è fermato."], (
        f"detect_language must be called exactly once with the operator query; "
        f"got {captured!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — response.lang matches detected language
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_lang_matches_query(
    collaborators: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    response = AIMessage(content="ok [1].", additional_kwargs={"citations": [{}]})
    react_runnable = _make_react_runnable(response, tool_messages=1)

    _patch_agent_internals(
        monkeypatch,
        react_runnable=react_runnable,
        lang="it",
        validate_spy=AsyncMock(side_effect=lambda state, resp, **kw: resp),
    )

    agent = OperatorAssistantAgent(**collaborators)
    result = await agent(_make_request(query="Il telaio ha problemi"))

    assert result["lang"] == "it"


# ---------------------------------------------------------------------------
# Test 6 — validate_or_replan invoked exactly once with the proper args
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_citation_validator_invoked_on_response(
    collaborators: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    response = AIMessage(content="ok [1].", additional_kwargs={"citations": [{}]})
    react_runnable = _make_react_runnable(response, tool_messages=1)

    spy = AsyncMock(side_effect=lambda state, resp, **kw: resp)

    _patch_agent_internals(
        monkeypatch,
        react_runnable=react_runnable,
        validate_spy=spy,
    )

    agent = OperatorAssistantAgent(**collaborators)
    await agent(_make_request())

    assert spy.await_count == 1
    args, kwargs = spy.await_args
    # state is the AgentState dict; response is the AIMessage from react.
    state_arg, response_arg = args
    assert isinstance(state_arg, dict)
    assert "messages" in state_arg
    assert response_arg is response
    assert kwargs["react_agent"] is react_runnable
    assert kwargs["config"]["recursion_limit"] == 5


# ---------------------------------------------------------------------------
# Test 7 — response dict carries 'citations' field
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_includes_citations_field(
    collaborators: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    citations_payload = [
        {"source_uri": "sop://loom/warp", "snippet": "...", "score": 0.9}
    ]
    response = AIMessage(
        content="Soluzione [1].",
        additional_kwargs={"citations": citations_payload},
    )
    react_runnable = _make_react_runnable(response, tool_messages=1)

    _patch_agent_internals(
        monkeypatch,
        react_runnable=react_runnable,
        validate_spy=AsyncMock(side_effect=lambda state, resp, **kw: resp),
    )

    agent = OperatorAssistantAgent(**collaborators)
    result = await agent(_make_request())

    assert result["citations"] == citations_payload


# ---------------------------------------------------------------------------
# Test 8 — response dict carries 'lang' field (Literal["it","en"])
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_includes_lang_field(
    collaborators: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    response = AIMessage(content="ok [1].", additional_kwargs={"citations": [{}]})
    react_runnable = _make_react_runnable(response, tool_messages=1)

    _patch_agent_internals(
        monkeypatch,
        react_runnable=react_runnable,
        lang="en",
        validate_spy=AsyncMock(side_effect=lambda state, resp, **kw: resp),
    )

    agent = OperatorAssistantAgent(**collaborators)
    result = await agent(_make_request(query="The loom is broken"))

    assert result["lang"] == "en"
    assert "citations_missing" in result
    assert result["citations_missing"] is False
    # tool_calls_count counts ToolMessage entries (one rag_search call was simulated).
    assert result["tool_calls_count"] == 1


# ---------------------------------------------------------------------------
# Models smoke test — request/response Pydantic shape
# ---------------------------------------------------------------------------


def test_operator_chat_request_frozen_and_extra_forbid() -> None:
    req = OperatorChatRequest(
        query="x",
        user_roles=["op"],
        thread_id="t",
    )
    with pytest.raises(Exception):
        # frozen=True -> AttributeError or ValidationError on assignment.
        req.query = "y"  # type: ignore[misc]
    with pytest.raises(Exception):
        # extra=forbid -> ValidationError on unknown field.
        OperatorChatRequest(
            query="x",
            user_roles=["op"],
            thread_id="t",
            unknown_field="boom",  # type: ignore[call-arg]
        )


def test_operator_chat_request_length_bounds() -> None:
    with pytest.raises(Exception):
        OperatorChatRequest(query="", user_roles=["op"], thread_id="t")
    with pytest.raises(Exception):
        OperatorChatRequest(
            query="x" * 2001, user_roles=["op"], thread_id="t"
        )


def test_operator_chat_response_construction() -> None:
    resp = OperatorChatResponse(
        response_md="hello",
        citations=[],
        lang="it",
        tool_calls_count=0,
    )
    assert resp.citations_missing is False
    assert resp.lang == "it"
