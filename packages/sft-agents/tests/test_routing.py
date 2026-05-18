"""Tests for sft_agents.policies.routing (Plan 04-05 Task 2, D-54).

HybridRouter Stage 1 (rules) + Stage 2 (LLM fallback) verification.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage


# ---------------------------------------------------------------------------
# routing.yaml shape
# ---------------------------------------------------------------------------


def test_routing_yaml_loads_via_safe_load() -> None:
    import yaml

    yaml_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "sft_agents"
        / "policies"
        / "routing.yaml"
    )
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    assert set(data.keys()) == {
        "ops",
        "maintenance",
        "knowledge-curation",
        "knowledge-training",
        "supply",
    }
    for _, cfg in data.items():
        assert "keywords" in cfg
        assert isinstance(cfg["keywords"], list)


def test_routing_module_uses_only_safe_load() -> None:
    """T-04-LLM-Inject — yaml.load on untrusted YAML is forbidden; safe_load only."""
    routing_py = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "sft_agents"
        / "policies"
        / "routing.py"
    ).read_text(encoding="utf-8")
    # No bare `yaml.load(` (safe_load is fine).
    bare_loads = re.findall(r"\byaml\.load\b(?!_)", routing_py)
    # Filter out yaml.load_all / yaml.load that includes safe_load via grep would
    # not match because we filter `\byaml\.load\b(?!_)` — but also confirm
    # safe_load appears at least once.
    forbidden = [m for m in bare_loads]
    assert forbidden == [], f"forbidden yaml.load occurrences: {forbidden}"
    assert "yaml.safe_load" in routing_py


# ---------------------------------------------------------------------------
# HybridRouter Stage 1: rules for each cluster
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "user_text, expected_cluster",
    [
        ("Allarme su macchina T-12 turno notte", "ops"),
        ("Manutenzione predittiva sul cuscinetto, downtime previsto", "maintenance"),
        ("Aggiorna il documento SOP e il glossario taxonomy", "knowledge-curation"),
        ("Briefing handover formazione training operatore neoassunto", "knowledge-training"),
        ("Verifica inventario ordine costo energia demand", "supply"),
    ],
)
async def test_stage1_rules_dispatches_each_cluster(
    user_text: str, expected_cluster: str
) -> None:
    from sft_agents.runtime import HybridRouter

    router = HybridRouter()
    decision = await router.route({"messages": [HumanMessage(user_text)]})
    assert decision.cluster == expected_cluster
    assert decision.strategy == "rules"
    assert decision.confidence == 1.0


async def test_stage1_zero_match_falls_back_when_no_llm() -> None:
    from sft_agents.runtime import HybridRouter

    router = HybridRouter()
    decision = await router.route(
        {"messages": [HumanMessage("xyzzy completely unrelated jibberish")]}
    )
    assert decision.cluster == "ops"
    assert decision.strategy == "fallback_default_ops"
    assert decision.confidence == 0.0


async def test_stage1_multiple_match_falls_back_when_no_llm() -> None:
    from sft_agents.runtime import HybridRouter

    router = HybridRouter()
    # "Manutenzione" hits maintenance; "inventario" hits supply — ambiguous → fallback.
    decision = await router.route(
        {"messages": [HumanMessage("Manutenzione e inventario di magazzino")]}
    )
    assert decision.strategy == "fallback_default_ops"


async def test_stage2_llm_confidence_below_threshold_falls_back(mock_llm) -> None:
    """If LLM returns confidence < 0.7 → fallback to ops."""
    from sft_agents.runtime import HybridRouter, RoutingDecision

    # Stub: replace `with_structured_output` to return an object whose ainvoke
    # yields a low-confidence decision.
    class _LowConfidenceLLM:
        def with_structured_output(self, schema):
            outer = self

            class _Bound:
                async def ainvoke(_self, _prompt):
                    return RoutingDecision(
                        cluster="maintenance", strategy="llm", confidence=0.4
                    )

            return _Bound()

    router = HybridRouter(llm=_LowConfidenceLLM())
    decision = await router.route(
        {"messages": [HumanMessage("xyzzy unrelated jibberish")]}
    )
    assert decision.cluster == "ops"
    assert decision.strategy == "fallback_default_ops"


async def test_stage2_llm_high_confidence_returned_as_is() -> None:
    from sft_agents.runtime import HybridRouter, RoutingDecision

    class _HighConfidenceLLM:
        def with_structured_output(self, schema):
            class _Bound:
                async def ainvoke(_self, _prompt):
                    return RoutingDecision(
                        cluster="supply", strategy="llm", confidence=0.9
                    )

            return _Bound()

    router = HybridRouter(llm=_HighConfidenceLLM())
    decision = await router.route(
        {"messages": [HumanMessage("xyzzy unrelated jibberish")]}
    )
    assert decision.cluster == "supply"
    assert decision.strategy == "llm"
    assert decision.confidence == 0.9


async def test_route_handles_empty_messages() -> None:
    from sft_agents.runtime import HybridRouter

    router = HybridRouter()
    decision = await router.route({"messages": []})
    assert decision.strategy == "fallback_default_ops"
