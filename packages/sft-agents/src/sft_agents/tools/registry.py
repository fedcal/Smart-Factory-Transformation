"""Tool registry + OpenAI function-calling schema export (CORE-07).

The registry stores LangChain ``BaseTool`` instances keyed by name and exports
their Pydantic v2 ``args_schema`` as OpenAI function-calling JSON via
``model_json_schema(by_alias=True)`` (Pitfall — must use by_alias for clean
parameter names that don't leak Pydantic Field aliasing).

Registry surface is intentionally small — LangGraph's ToolNode consumes BaseTool
instances directly. The registry exists for:
    1. Schema export (OpenAI function calling spec) used by both Ollama and vLLM
    2. Name-keyed lookup for human inspection (Phase 11 admin UI)
    3. Duplicate-name detection (defense against accidental tool shadowing)
"""

from __future__ import annotations

from typing import Any

import structlog
from langchain_core.tools import BaseTool

logger = structlog.get_logger(__name__)

# Empty parameters schema when a tool declares no args_schema (rare — most
# BaseTool subclasses provide one). OpenAI function-calling spec requires
# parameters to be a JSON-schema object even when empty.
_EMPTY_PARAMETERS: dict[str, Any] = {"type": "object", "properties": {}}


def _tool_schema_entry(tool: BaseTool) -> dict[str, Any]:
    """Build a single OpenAI function-calling entry for a BaseTool.

    Shape:
        {
          "type": "function",
          "function": {
            "name":        tool.name,
            "description": tool.description,
            "parameters":  <JSON Schema of args_schema>,
          },
        }
    """
    args_schema = getattr(tool, "args_schema", None)
    if args_schema is None:
        parameters: dict[str, Any] = dict(_EMPTY_PARAMETERS)
    else:
        # Pydantic v2: model_json_schema(by_alias=True) returns OpenAPI-ish dict
        # (T-04-LLM-Inject mitigation: first-party Pydantic schemas only —
        # no user-supplied schemas are admitted into export.)
        parameters = args_schema.model_json_schema(by_alias=True)

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters,
        },
    }


def export_tool_schemas(tools: list[BaseTool]) -> list[dict[str, Any]]:
    """Return a list of OpenAI function-calling schema entries.

    Args:
        tools: A list of LangChain BaseTool instances.

    Returns:
        list of dicts (OpenAI function calling shape) — JSON-serializable.
    """
    return [_tool_schema_entry(t) for t in tools]


class ToolRegistry:
    """Name-keyed registry over BaseTool instances.

    Use cases:
        - Schema export across both Ollama and vLLM (provider-agnostic)
        - Duplicate-name detection at registration time (defense in depth)
        - Admin UI listing (Phase 11)

    Note: storage is a private dict — register and get are the only public
    state mutation/inspection paths (forward-compatible with thread-safe
    refactor if needed in Phase 11).
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, name: str, tool: BaseTool) -> None:
        """Register a tool under ``name``.

        Raises:
            ValueError: when ``name`` is already registered (prevents
                accidental shadowing — common bug when two clusters define
                tools with overlapping names).
        """
        if name in self._tools:
            raise ValueError(f"Tool {name!r} is already registered")
        self._tools[name] = tool
        logger.info("tool_registered", name=name, tool_class=type(tool).__name__)

    def get(self, name: str) -> BaseTool:
        """Return the tool registered under ``name``.

        Raises:
            KeyError: when ``name`` is not registered.
        """
        if name not in self._tools:
            raise KeyError(f"No tool registered under {name!r}")
        return self._tools[name]

    def all(self) -> list[BaseTool]:
        """Return all registered tools (ordered by insertion)."""
        return list(self._tools.values())

    def export_schemas(self) -> list[dict[str, Any]]:
        """Export OpenAI function-calling schemas for all registered tools."""
        return export_tool_schemas(self.all())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools
