"""Replay loaders: NASA C-MAPSS + UCI Manufacturing come LangChain Tools.

Espone:
    ReplayCMAPSSTool    — NASA C-MAPSS FD001 run-to-failure replay
    ReplayUCITool       — UCI Manufacturing dataset replay
    ReplayRecord        — Pydantic model schema unificato
    ReplayCMAPSSArgs    — Pydantic args schema per ReplayCMAPSSTool
    ReplayUCIArgs       — Pydantic args schema per ReplayUCITool
    REPLAY_TOOLS        — lista [ReplayCMAPSSTool(), ReplayUCITool()]
"""

from sft_tools.replay.cmapss import ReplayCMAPSSTool
from sft_tools.replay.models import ReplayCMAPSSArgs, ReplayRecord, ReplayUCIArgs
from sft_tools.replay.uci import ReplayUCITool

REPLAY_TOOLS = [ReplayCMAPSSTool(), ReplayUCITool()]

__all__ = [
    "ReplayCMAPSSTool",
    "ReplayUCITool",
    "ReplayRecord",
    "ReplayCMAPSSArgs",
    "ReplayUCIArgs",
    "REPLAY_TOOLS",
]
