"""sft_agents.policies — declarative routing/escalation/safety policy YAMLs.

Plan 04-05 ships routing.yaml + HybridRouter (D-54).
Plans 04-06 will add escalation-sla.yaml + safety-interlock.yaml + budgets.yaml.
"""
from __future__ import annotations

from sft_agents.policies.routing import HybridRouter

__all__ = ["HybridRouter"]
