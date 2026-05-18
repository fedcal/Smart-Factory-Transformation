"""sft_agents.clusters — 5 cluster packages with 16 placeholder children (D-53).

Each cluster sub-package exposes:
    CHILD_AGENT_SLUGS — ordered list of Phase-1 agent slugs (kebab-case)
    CLUSTER_NAME      — hyphenated cluster identifier (matches VALID_CLUSTERS)

Real business logic lands Phase 6-9. This package only wires the LangGraph
StateGraph skeleton (Plan 04-05).
"""
from __future__ import annotations

#: Ordered tuple form — mirrors sft_agents.runtime.ALL_CLUSTERS.
ALL_CLUSTERS: tuple[str, ...] = (
    "ops",
    "maintenance",
    "knowledge-curation",
    "knowledge-training",
    "supply",
)

__all__ = ["ALL_CLUSTERS"]
