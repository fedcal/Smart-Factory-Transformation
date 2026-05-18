"""Tests for sft_agents.tools registry + builtin tool re-export (CORE-07).

Covers:
    - ToolRegistry register/get/all (+ duplicate ValueError + missing KeyError)
    - export_tool_schemas returns OpenAI function-calling shape
    - BUILTIN_TOOLS re-exports 3 Phase 3 tools (ReplayCMAPSSTool, ReplayUCITool,
      QueryTimescaleTool)
    - schema JSON-round-trips (json.dumps without error)
"""

from __future__ import annotations

import json

import pytest
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from sft_agents.tools import BUILTIN_TOOLS, ToolRegistry, export_tool_schemas


class _FakeArgs(BaseModel):
    """Args schema for FakeTool."""

    query: str = Field(description="A search query")
    top_k: int = Field(default=5, ge=1, le=100)


class _FakeTool(BaseTool):
    name: str = "fake_tool"
    description: str = "A fake tool for unit tests"
    args_schema: type[BaseModel] = _FakeArgs

    def _run(self, query: str, top_k: int = 5) -> str:
        return f"fake({query}, {top_k})"


class TestToolRegistry:
    """ToolRegistry CRUD operations."""

    def test_register_and_get(self) -> None:
        reg = ToolRegistry()
        tool = _FakeTool()
        reg.register("fake", tool)
        assert reg.get("fake") is tool

    def test_duplicate_register_raises_value_error(self) -> None:
        reg = ToolRegistry()
        reg.register("fake", _FakeTool())
        with pytest.raises(ValueError, match=r"already registered"):
            reg.register("fake", _FakeTool())

    def test_get_missing_raises_key_error(self) -> None:
        reg = ToolRegistry()
        with pytest.raises(KeyError):
            reg.get("missing")

    def test_all_returns_list(self) -> None:
        reg = ToolRegistry()
        t1 = _FakeTool()
        reg.register("fake", t1)
        all_tools = reg.all()
        assert isinstance(all_tools, list)
        assert t1 in all_tools

    def test_export_schemas_includes_registered(self) -> None:
        reg = ToolRegistry()
        reg.register("fake", _FakeTool())
        schemas = reg.export_schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "fake_tool"


class TestExportToolSchemas:
    """export_tool_schemas produces OpenAI function-calling shape."""

    def test_returns_openai_function_shape(self) -> None:
        schemas = export_tool_schemas([_FakeTool()])
        assert len(schemas) == 1
        entry = schemas[0]
        assert entry["type"] == "function"
        assert "function" in entry
        fn = entry["function"]
        assert fn["name"] == "fake_tool"
        assert "description" in fn
        assert fn["parameters"]["type"] == "object"
        assert "query" in fn["parameters"]["properties"]

    def test_empty_args_schema_emits_object_parameters(self) -> None:
        class _NoArgsTool(BaseTool):
            name: str = "no_args"
            description: str = "tool with no args"
            args_schema: type[BaseModel] | None = None

            def _run(self) -> str:
                return "x"

        schemas = export_tool_schemas([_NoArgsTool()])
        assert schemas[0]["function"]["parameters"] == {
            "type": "object",
            "properties": {},
        }

    def test_schemas_are_json_serializable(self) -> None:
        schemas = export_tool_schemas([_FakeTool()])
        s = json.dumps(schemas)
        assert "fake_tool" in s


class TestBuiltinTools:
    """BUILTIN_TOOLS re-exports 3 Phase 3 tools as ready instances."""

    def test_count(self) -> None:
        assert len(BUILTIN_TOOLS) == 3

    def test_export_schemas_for_builtins(self) -> None:
        schemas = export_tool_schemas(list(BUILTIN_TOOLS))
        assert len(schemas) == 3
        names = [s["function"]["name"] for s in schemas]
        assert "replay_cmapss" in names
        assert "replay_uci" in names
        assert "query_timescale" in names

    def test_builtins_have_valid_args_schemas(self) -> None:
        schemas = export_tool_schemas(list(BUILTIN_TOOLS))
        for entry in schemas:
            assert entry["type"] == "function"
            params = entry["function"]["parameters"]
            assert params["type"] == "object"
            # Pydantic v2 model_json_schema(by_alias=True) always produces 'properties'
            assert "properties" in params

    def test_builtins_json_round_trip(self) -> None:
        schemas = export_tool_schemas(list(BUILTIN_TOOLS))
        round_trip = json.loads(json.dumps(schemas))
        assert len(round_trip) == 3
