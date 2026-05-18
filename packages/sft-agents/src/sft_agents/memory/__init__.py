"""sft_agents.memory — Phase 4 memory implementations (Plan 04-06 Task 02).

Ships:
    EpisodicReplay        — read-only projection of audit.actions (CORE-08, D-59)
    StubLongTermMemory    — placeholder for Phase 5 QdrantLongTermMemory (D-59)
    StubLongTermMemoryConfig — frozen Pydantic config (Phase 5 fills fields)
    LongTermMemory        — alias of StubLongTermMemory (swap target for Phase 5)

All three implement the ``sft_agents.sdk.memory.Memory`` ABC so downstream
agents code against a single interface.
"""

from __future__ import annotations

from sft_agents.memory.episodic import EpisodicReplay
from sft_agents.memory.long_term_stub import (
    StubLongTermMemory,
    StubLongTermMemoryConfig,
)

# Phase 5 will rebind this alias to ``QdrantLongTermMemory`` without touching
# downstream imports (`from sft_agents.memory import LongTermMemory`).
LongTermMemory = StubLongTermMemory

__all__ = [
    "EpisodicReplay",
    "LongTermMemory",
    "StubLongTermMemory",
    "StubLongTermMemoryConfig",
]
