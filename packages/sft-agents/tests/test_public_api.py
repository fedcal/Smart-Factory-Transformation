"""Public API contract test (Plan 04-01 Task 3).

Verifies the locked Phase 4 public symbol surface every downstream plan imports.
"""

from __future__ import annotations

import sft_agents


PUBLIC_SYMBOLS = [
    # SDK ABCs (4)
    "Agent",
    "Tool",
    "Memory",
    "Policy",
    # Approval (2)
    "ApprovalRequest",
    "ApprovalDecision",
    # Audit (1)
    "AuditRecord",
    # Budget (2)
    "BudgetSnapshot",
    "BudgetLimits",
    # Evidence (4)
    "EvidencePanel",
    "ToolCall",
    "RagCitation",
    "TokenUsage",
    # Memory (1)
    "MemoryRecord",
    # Proposed action (1)
    "ProposedAction",
    # Enums (4)
    "Tier",
    "Decision",
    "ActionType",
    "ApprovalStatus",
]


class TestPublicAPI:
    def test_all_public_symbols_resolve(self) -> None:
        for name in PUBLIC_SYMBOLS:
            assert hasattr(sft_agents, name), f"sft_agents missing public symbol: {name}"

    def test_public_symbol_count_is_at_least_19(self) -> None:
        # Plan 04-01 done criteria: "Public API imports 19+ symbols"
        assert len(PUBLIC_SYMBOLS) >= 19

    def test_version_string(self) -> None:
        assert sft_agents.__version__ == "0.1.0"

    def test_dunder_all_matches_documented(self) -> None:
        # __all__ should expose every public symbol we documented + __version__
        for name in PUBLIC_SYMBOLS:
            assert name in sft_agents.__all__, f"{name} missing from __all__"
        assert "__version__" in sft_agents.__all__

    def test_abc_classes_are_classes(self) -> None:
        import inspect

        for name in ("Agent", "Tool", "Memory", "Policy"):
            obj = getattr(sft_agents, name)
            assert inspect.isclass(obj), f"{name} should be a class"

    def test_enum_values_are_str(self) -> None:
        # Tier / Decision / ActionType / ApprovalStatus all str-Enum (JSON-stable)
        from enum import Enum

        for name in ("Tier", "Decision", "ActionType", "ApprovalStatus"):
            cls = getattr(sft_agents, name)
            assert issubclass(cls, Enum)
            assert issubclass(cls, str)
