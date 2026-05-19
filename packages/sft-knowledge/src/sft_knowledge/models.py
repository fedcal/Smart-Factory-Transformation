"""sft_knowledge.models — GraphNode + re-export RagCitation from sft-agents.

Wave-1 scaffold stub. Implementazione completa in Plan 05-01 Task 2 (GraphNode definito qui).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel
from sft_agents.models.evidence import RagCitation  # re-export per D-59; NO redefine


class GraphNode(BaseModel):
    """Nodo del knowledge graph (Neo4j)."""

    model_config = {"frozen": True, "extra": "forbid"}

    label: Literal["Machine", "Part", "FailureMode", "SOP"]
    node_id: str
    properties: dict[str, Any] = {}


__all__ = ["RagCitation", "GraphNode"]
