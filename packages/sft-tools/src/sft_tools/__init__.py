"""sft-tools: LangChain Tools cross-cutting per Phase 4+ agents.

Espone:
    REPLAY_TOOLS        — lista [ReplayCMAPSSTool(), ReplayUCITool()]
    TIMESCALE_TOOLS     — lista [QueryTimescaleTool()]
    ReplayCMAPSSTool    — NASA C-MAPSS turbofan replay tool
    ReplayUCITool       — UCI Manufacturing replay tool
    QueryTimescaleTool  — TimescaleDB read-only proxy tool
    ReplayRecord        — Pydantic model schema unificato output

Phase 3 decisions: D-46 (ReplayRecord schema), D-47 (sft-tools location), OQ5 (target_asset_id optional).
"""

from sft_tools.replay import REPLAY_TOOLS, ReplayCMAPSSTool, ReplayRecord, ReplayUCITool
from sft_tools.timescale import TIMESCALE_TOOLS, QueryTimescaleTool

__all__ = [
    "REPLAY_TOOLS",
    "TIMESCALE_TOOLS",
    "ReplayCMAPSSTool",
    "ReplayUCITool",
    "QueryTimescaleTool",
    "ReplayRecord",
]
