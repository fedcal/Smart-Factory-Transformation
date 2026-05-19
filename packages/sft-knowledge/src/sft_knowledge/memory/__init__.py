"""sft_knowledge.memory — Phase 5 LongTerm Memory implementations (D-70).

Exposes:
    QdrantLongTermMemory       — Memory ABC impl, replaces Phase 4 D-59 stub
    QdrantLongTermMemoryConfig — frozen Pydantic config
"""

from sft_knowledge.memory.qdrant_long_term import (
    QdrantLongTermMemory,
    QdrantLongTermMemoryConfig,
)

__all__ = ["QdrantLongTermMemory", "QdrantLongTermMemoryConfig"]
