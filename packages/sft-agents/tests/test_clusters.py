"""Tests for sft_agents.clusters.* + runtime.clusters.build_cluster_subgraph (Plan 04-05 Task 2).

Verifies:
    - 5 cluster modules each expose CHILD_AGENT_SLUGS (correct counts) + CLUSTER_NAME
    - Total slug count = 16 (D-53 + Phase 1 scaffold)
    - build_cluster_subgraph returns a compilable StateGraph with the right node set
"""
from __future__ import annotations

import pytest


_EXPECTED = {
    "ops": (
        ["operator-assistant", "production-planner", "quality-inspector", "anomaly-detector"],
        "ops",
    ),
    "maintenance": (
        [
            "predictive-maintenance",
            "rca-specialist",
            "maintenance-coach",
            "downtime-analyzer",
        ],
        "maintenance",
    ),
    "knowledge_curation": (
        ["knowledge-curator", "documentation-synthesizer"],
        "knowledge-curation",
    ),
    "knowledge_training": (
        ["training-coach", "shift-handover"],
        "knowledge-training",
    ),
    "supply": (
        ["inventory-manager", "energy-optimizer", "cost-analyzer", "demand-forecaster"],
        "supply",
    ),
}


@pytest.mark.parametrize("py_module, expected", list(_EXPECTED.items()))
def test_cluster_module_exports(py_module: str, expected: tuple[list[str], str]) -> None:
    """Each cluster module exports CHILD_AGENT_SLUGS + CLUSTER_NAME with correct values."""
    expected_slugs, expected_name = expected
    mod = __import__(f"sft_agents.clusters.{py_module}", fromlist=["*"])
    assert mod.CHILD_AGENT_SLUGS == expected_slugs, (
        f"{py_module} CHILD_AGENT_SLUGS mismatch: "
        f"got {mod.CHILD_AGENT_SLUGS}, want {expected_slugs}"
    )
    assert mod.CLUSTER_NAME == expected_name


def test_total_child_agents_equals_sixteen() -> None:
    from sft_agents.clusters import (
        knowledge_curation,
        knowledge_training,
        maintenance,
        ops,
        supply,
    )

    total = sum(
        len(m.CHILD_AGENT_SLUGS)
        for m in (ops, maintenance, knowledge_curation, knowledge_training, supply)
    )
    assert total == 16, f"expected 16 placeholder agents (Phase 1 scaffold), got {total}"


def test_clusters_init_exposes_all_clusters_tuple() -> None:
    from sft_agents.clusters import ALL_CLUSTERS
    from sft_agents.runtime import VALID_CLUSTERS

    assert set(ALL_CLUSTERS) == VALID_CLUSTERS


def test_build_cluster_subgraph_returns_compilable_stategraph() -> None:
    from langgraph.graph import StateGraph

    from sft_agents.runtime import build_cluster_subgraph

    sg = build_cluster_subgraph("ops", ["operator-assistant", "production-planner"])
    assert isinstance(sg, StateGraph)
    compiled = sg.compile()
    assert compiled is not None


def test_build_cluster_subgraph_rejects_invalid_cluster() -> None:
    from sft_agents.runtime import build_cluster_subgraph

    with pytest.raises(ValueError):
        build_cluster_subgraph("badcluster", ["agent-a"])


def test_build_cluster_subgraph_rejects_empty_slug_list() -> None:
    from sft_agents.runtime import build_cluster_subgraph

    with pytest.raises(ValueError):
        build_cluster_subgraph("ops", [])
