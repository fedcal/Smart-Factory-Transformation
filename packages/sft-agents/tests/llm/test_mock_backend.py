"""Tests for MockReplayChatModel (plan 06-03).

Covers `sft_agents.llm.mock.MockReplayChatModel` JSONL record/replay behavior
backing the `LLM_BACKEND=mock` factory branch.

References:
    - RESEARCH §Pattern 2 (Mock LLM backend / record-replay)
    - RESEARCH §Pitfall 10 (graceful fallback when prompt_hash drifts)
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import pytest
import structlog
from langchain_core.messages import HumanMessage

from sft_agents.llm.mock import MockReplayChatModel


def _hash_messages(*pairs: tuple[str, str]) -> str:
    """Replicate MockReplayChatModel._prompt_hash for test fixture authoring."""
    body = "\n".join(f"{mtype}:{content}" for mtype, content in pairs)
    return hashlib.sha256(body.encode()).hexdigest()


def _write_jsonl(path: pathlib.Path, entries: list[dict]) -> None:
    with path.open("w") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")


@pytest.fixture
def two_entry_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    fixture = tmp_path / "fixture.jsonl"
    entries = [
        {
            "prompt_hash": _hash_messages(("human", "hello")),
            "response": {
                "content": "ciao",
                "usage_metadata": {
                    "input_tokens": 5,
                    "output_tokens": 2,
                    "total_tokens": 7,
                },
            },
        },
        {
            "prompt_hash": _hash_messages(("human", "how are you")),
            "response": {
                "content": "fine",
                "usage_metadata": {
                    "input_tokens": 6,
                    "output_tokens": 1,
                    "total_tokens": 7,
                },
            },
        },
    ]
    _write_jsonl(fixture, entries)
    return fixture


class TestMockReplayChatModelLoading:
    def test_loads_jsonl_fixture(self, two_entry_fixture: pathlib.Path) -> None:
        model = MockReplayChatModel(fixture_path=two_entry_fixture)
        assert len(model._entries) == 2

    def test_llm_type_property(self, two_entry_fixture: pathlib.Path) -> None:
        model = MockReplayChatModel(fixture_path=two_entry_fixture)
        assert model._llm_type == "mock-replay"


class TestMockReplayChatModelAgenerate:
    @pytest.mark.asyncio
    async def test_agenerate_returns_aimessage_keyed_by_hash(
        self, two_entry_fixture: pathlib.Path
    ) -> None:
        model = MockReplayChatModel(fixture_path=two_entry_fixture)
        result = await model.ainvoke([HumanMessage(content="hello")])
        assert result.content == "ciao"

    @pytest.mark.asyncio
    async def test_agenerate_falls_back_to_ordered_when_hash_missing(
        self, tmp_path: pathlib.Path
    ) -> None:
        fixture = tmp_path / "fallback.jsonl"
        entries = [
            {
                "prompt_hash": "deadbeef" * 8,
                "response": {"content": "first-ordered"},
            },
            {
                "prompt_hash": "cafefade" * 8,
                "response": {"content": "second-ordered"},
            },
        ]
        _write_jsonl(fixture, entries)

        model = MockReplayChatModel(fixture_path=fixture)

        with structlog.testing.capture_logs() as logs:
            r1 = await model.ainvoke([HumanMessage(content="missing-1")])
            r2 = await model.ainvoke([HumanMessage(content="missing-2")])

        assert r1.content == "first-ordered"
        assert r2.content == "second-ordered"
        events = [log.get("event") for log in logs]
        assert events.count("mock_llm_hash_miss_fallback") == 2

    @pytest.mark.asyncio
    async def test_agenerate_emits_tool_calls(self, tmp_path: pathlib.Path) -> None:
        fixture = tmp_path / "tool.jsonl"
        ph = _hash_messages(("human", "search the SOP"))
        entries = [
            {
                "prompt_hash": ph,
                "response": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "name": "rag_search",
                            "args": {"query": "SOP"},
                        }
                    ],
                },
            }
        ]
        _write_jsonl(fixture, entries)

        model = MockReplayChatModel(fixture_path=fixture)
        result = await model.ainvoke([HumanMessage(content="search the SOP")])

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "rag_search"
        assert result.tool_calls[0]["id"] == "call_1"
        assert result.tool_calls[0]["args"] == {"query": "SOP"}

    @pytest.mark.asyncio
    async def test_agenerate_includes_usage_metadata(
        self, two_entry_fixture: pathlib.Path
    ) -> None:
        model = MockReplayChatModel(fixture_path=two_entry_fixture)
        result = await model.ainvoke([HumanMessage(content="hello")])
        assert result.usage_metadata is not None
        assert result.usage_metadata["input_tokens"] == 5
        assert result.usage_metadata["output_tokens"] == 2
        assert result.usage_metadata["total_tokens"] == 7


class TestMockReplayChatModelSyncDisallowed:
    def test_sync_generate_raises_not_implemented(
        self, two_entry_fixture: pathlib.Path
    ) -> None:
        model = MockReplayChatModel(fixture_path=two_entry_fixture)
        with pytest.raises(NotImplementedError, match="async-only"):
            model._generate([HumanMessage(content="hello")])
