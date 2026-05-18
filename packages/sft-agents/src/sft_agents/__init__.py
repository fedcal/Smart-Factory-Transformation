"""sft-agents — Core SDK: Agent/Tool/Memory/Policy interfaces + LangGraph runtime adapter.

Phase 4 Plan 04-01 ships the public contract surface every downstream plan (02-08)
imports. Implementation of runtime concerns lives in subsequent plans (02-08).

Public API (Phase 4 lock):
    Agent, Tool, Memory, Policy                    — runtime ABCs (Plan 04-01)
    EvidencePanel, ToolCall, RagCitation, TokenUsage — HITL-06 schema (Plan 04-01)
    AuditRecord                                    — D-56 schema (Plan 04-01)
    ApprovalRequest, ApprovalDecision              — D-55 schema (Plan 04-01)
    BudgetSnapshot, BudgetLimits                   — D-60 schema (Plan 04-01)
    ProposedAction                                 — deterministic UUID action wrapper
    MemoryRecord                                   — D-59 schema (Plan 04-01)
    Tier, Decision, ActionType, ApprovalStatus     — enums (Plan 04-01)
"""

from __future__ import annotations

from sft_agents.models import (
    ActionType,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    AuditRecord,
    BudgetLimits,
    BudgetSnapshot,
    Decision,
    EvidencePanel,
    MemoryRecord,
    ProposedAction,
    RagCitation,
    Tier,
    TokenUsage,
    ToolCall,
)
from sft_agents.sdk import Agent, Memory, Policy, Tool

__version__ = "0.1.0"

__all__ = [
    # SDK ABCs
    "Agent",
    "Memory",
    "Policy",
    "Tool",
    # Approval
    "ApprovalDecision",
    "ApprovalRequest",
    # Audit
    "AuditRecord",
    # Budget
    "BudgetLimits",
    "BudgetSnapshot",
    # Evidence
    "EvidencePanel",
    "RagCitation",
    "ToolCall",
    "TokenUsage",
    # Memory
    "MemoryRecord",
    # Proposed action
    "ProposedAction",
    # Enums
    "ActionType",
    "ApprovalStatus",
    "Decision",
    "Tier",
    # Meta
    "__version__",
]
