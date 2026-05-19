"""sft_agents.memory — Memory ABC implementations.

Ships:
    EpisodicReplay        — read-only projection of audit.actions (CORE-08, D-59)
    StubLongTermMemory    — Phase 4 placeholder (D-59)
    StubLongTermMemoryConfig — frozen Pydantic config
    LongTermMemory        — alias (swapped to QdrantLongTermMemory in Phase 5)

Phase 5 swap (Plan 05-09 Task 4):
    Try to import ``QdrantLongTermMemory`` from ``sft_knowledge.memory`` and bind
    it to ``LongTermMemory``. If sft-knowledge is not installed (or fails to
    import for env reasons), gracefully fall back to ``StubLongTermMemory`` so
    Phase 4 agent imports continue to resolve.
"""

from __future__ import annotations

from sft_agents.memory.episodic import EpisodicReplay
from sft_agents.memory.long_term_stub import (
    StubLongTermMemory,
    StubLongTermMemoryConfig,
)

# Phase 5 swap (D-70). Graceful fallback preserves Phase 4 test fixtures that
# may not have sft-knowledge installed.
try:
    from sft_knowledge.memory import QdrantLongTermMemory

    LongTermMemory: type = QdrantLongTermMemory
except ImportError:
    LongTermMemory = StubLongTermMemory

__all__ = [
    "EpisodicReplay",
    "LongTermMemory",
    "StubLongTermMemory",
    "StubLongTermMemoryConfig",
]
