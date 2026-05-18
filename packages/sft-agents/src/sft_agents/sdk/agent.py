"""Agent ABC interface (CORE-01).

Runtime composition class — not Pydantic. Subclasses bind together name + cluster +
tools[] + memory + policy and implement async `step(state) -> dict` (the LangGraph
node function called by the cluster subgraph).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sft_agents.sdk.memory import Memory
    from sft_agents.sdk.policy import Policy
    from sft_agents.sdk.tool import Tool


class Agent(ABC):
    """Abstract Agent — every domain agent (Phase 6-9) subclasses this.

    Composition attributes (set by `__init__` in subclasses):
        name     — stable identifier (matches apps/agents/<cluster>/<name>/ slug)
        cluster  — one of {ops, maintenance, knowledge-curation, knowledge-training, supply}
        tools    — list of Tool instances available to this agent
        memory   — Memory implementation (short-term checkpoint + episodic + stub long-term)
        policy   — Policy implementation (SafetyInterlock + Budget + custom)

    Subclasses MUST implement `step(state)` as an async function that returns the next
    state dict update (LangGraph node semantics).
    """

    name: str
    cluster: str
    tools: list[Tool]
    memory: Memory
    policy: Policy

    @abstractmethod
    async def step(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute one agent step against the current LangGraph state.

        Returns the state delta to merge (LangGraph TypedDict + Annotated reducer).
        """

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Convenience wrapper that delegates to `step`.

        Subclasses generally do NOT override this — keep `step` as the integration
        point. `execute` exists so callers outside LangGraph (e.g. unit tests) have a
        stable entry point even if `step` semantics change later.
        """
        return await self.step(state)
