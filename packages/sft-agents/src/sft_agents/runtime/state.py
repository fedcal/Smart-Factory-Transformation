"""AgentState TypedDict + RoutingDecision Pydantic model (Plan 04-05 Task 1).

Mirrors CONTEXT.md Claude's Discretion line 419 (AgentState shape) and D-54
(RoutingDecision contract).

AgentState is a TypedDict (not a Pydantic model) because LangGraph's StateGraph
consumes TypedDicts natively and uses the field annotations to dispatch reducers
(see ``messages: Annotated[..., add_messages]``). Pydantic models would force
re-serialisation at every node boundary.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal, TypedDict
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from sft_agents.models import BudgetSnapshot, EvidencePanel, ProposedAction


# ---------------------------------------------------------------------------
# Cluster name constants (D-53)
# ---------------------------------------------------------------------------

#: The 5 cluster names (D-53). Hyphenated form — mirrors NATS subject convention
#: + audit.actions.cluster string values. Python module names use underscores
#: (see sft_agents.clusters.knowledge_curation etc) but the cluster identifier
#: string is hyphenated.
VALID_CLUSTERS: frozenset[str] = frozenset(
    {
        "ops",
        "maintenance",
        "knowledge-curation",
        "knowledge-training",
        "supply",
    }
)

#: Ordered tuple form of VALID_CLUSTERS for deterministic graph wiring +
#: conditional_edges target mapping.
ALL_CLUSTERS: tuple[str, ...] = (
    "ops",
    "maintenance",
    "knowledge-curation",
    "knowledge-training",
    "supply",
)


# ---------------------------------------------------------------------------
# RoutingDecision (D-54)
# ---------------------------------------------------------------------------


class RoutingDecision(BaseModel):
    """Output of the HybridRouter Stage 1 / Stage 2 routing decision (D-54).

    Trust boundary: Stage 2 LLM output passes through Pydantic frozen + Literal
    strategy + bounded confidence to mitigate T-04-LLM-Inject. Cluster is
    validated against VALID_CLUSTERS by a model_validator (see below) — the
    Pydantic Literal would have to enumerate all 5 cluster names which is
    redundant with VALID_CLUSTERS, so we use ``str`` + custom validation.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    cluster: Annotated[
        str,
        Field(description="One of VALID_CLUSTERS (validated post-construction)."),
    ]
    strategy: Annotated[
        Literal["rules", "llm", "fallback_default_ops"],
        Field(description="Which router stage produced this decision."),
    ]
    confidence: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="1.0 for rules; LLM confidence for llm; 0.0 for fallback."),
    ]
    matched_keyword: Annotated[
        str | None,
        Field(default=None, description="Debug aid for the rules strategy."),
    ] = None

    def model_post_init(self, __context: Any) -> None:
        if self.cluster not in VALID_CLUSTERS:
            raise ValueError(
                f"RoutingDecision.cluster must be one of {sorted(VALID_CLUSTERS)}, "
                f"got {self.cluster!r}"
            )


# ---------------------------------------------------------------------------
# AgentState — LangGraph TypedDict (CONTEXT.md Claude's Discretion line 419)
# ---------------------------------------------------------------------------


class AgentState(TypedDict, total=False):
    """LangGraph state TypedDict — all keys optional (total=False).

    Shape mirrors CONTEXT.md Claude's Discretion line 419. ``messages`` is
    annotated with the ``add_messages`` reducer so LangGraph appends rather than
    replaces on every node return.

    Fields:
        messages           — Chat history (reducer: add_messages)
        thread_id          — `{cluster}.{agent_id}.{session_uuid}` (D-59)
        cluster            — Routing target; one of VALID_CLUSTERS
        proposed_actions   — Agent-proposed actions awaiting HITL/Safety review
        budget             — Token/cost/duration snapshot (D-60)
        evidence           — EvidencePanel attached to the latest decision (HITL-06)
        pending_approval_id— UUID of an in-flight hitl.approvals row, if any
        routing_decision   — Latest router output (set by supervisor `route` node)
    """

    messages: Annotated[list[BaseMessage], add_messages]
    thread_id: str
    cluster: str
    proposed_actions: list[ProposedAction]  # type: ignore[valid-type]
    budget: BudgetSnapshot  # type: ignore[valid-type]
    evidence: EvidencePanel | None  # type: ignore[valid-type]
    pending_approval_id: UUID | None
    routing_decision: RoutingDecision | None


__all__ = [
    "ALL_CLUSTERS",
    "AgentState",
    "RoutingDecision",
    "VALID_CLUSTERS",
]
