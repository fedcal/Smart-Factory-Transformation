"""Policy ABC interface (CORE-01).

Policies hook into the agent lifecycle at two points:
    - pre_tool_check  — invoked before every tool call (SafetyInterlock + Budget enforcement)
    - post_decision_check — invoked after every AuditRecord is written (governance hooks)

Phase 4 Plan 04-06 ships:
    - SafetyInterlockPolicy (rejects forbidden NATS subjects + ActionTypes)
    - BudgetPolicy (rejects when limits exceeded → ApprovalRequest)
    - GovernorPolicy (1h sliding-window auto-rate alert)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sft_agents.models.audit import AuditRecord
from sft_agents.models.proposed_action import ProposedAction


class Policy(ABC):
    """Abstract policy — pre-tool and post-decision hooks.

    Subclasses MUST implement `pre_tool_check`. `post_decision_check` defaults to
    a no-op so simple policies that only gate tool calls don't need to override it.

    Both methods raise on policy failure (e.g. `SafetyInterlockRejection`,
    `BudgetExceeded`) to short-circuit the agent step. Returning None means OK.
    """

    @abstractmethod
    async def pre_tool_check(self, action: ProposedAction) -> None:
        """Validate a proposed action before any tool/LLM call mutates state.

        Raises a policy-specific exception (subclass of RuntimeError) on rejection.
        """

    async def post_decision_check(self, record: AuditRecord) -> None:
        """Post-decision hook invoked after an AuditRecord is persisted.

        Default no-op; concrete policies (e.g. Governor) override to scan for emerging
        patterns. MUST NOT raise on transient issues — log instead.
        """
        return None
