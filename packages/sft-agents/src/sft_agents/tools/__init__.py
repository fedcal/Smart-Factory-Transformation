"""sft-agents tools — re-export of Phase 3 builtin tools + Tool registry.

Phase 4 (Plan 04-03 Task 2) ships a thin registry on top of LangChain BaseTool:
    BUILTIN_TOOLS      — tuple of 3 ready-to-use Phase 3 tools (instances)
    ToolRegistry       — name-keyed registry with .register / .get / .all / .export_schemas
    export_tool_schemas — pure function returning OpenAI function-calling JSON shape

Phase 5+ agents construct their own per-cluster registries, optionally seeded
with BUILTIN_TOOLS. The registry surface is intentionally minimal —
LangGraph's ToolNode consumes BaseTool instances directly, the registry is for
schema export and human inspection (Phase 11 admin UI).
"""

from __future__ import annotations

from sft_tools import QueryTimescaleTool, ReplayCMAPSSTool, ReplayUCITool

from sft_agents.tools.audit import EventType, LogEventInput, LogEventTool
from sft_agents.tools.hitl import EscalateInput, EscalateToSupervisorTool
from sft_agents.tools.registry import ToolRegistry, export_tool_schemas

# Builtin tools — instantiated once at import time (tools are stateless after
# Phase 3 — actual asyncpg connections happen per-invocation inside _arun).
BUILTIN_TOOLS: tuple = (
    ReplayCMAPSSTool(),
    ReplayUCITool(),
    QueryTimescaleTool(),
)

__all__ = [
    "BUILTIN_TOOLS",
    "EscalateInput",
    "EscalateToSupervisorTool",
    "EventType",
    "LogEventInput",
    "LogEventTool",
    "ToolRegistry",
    "export_tool_schemas",
]
