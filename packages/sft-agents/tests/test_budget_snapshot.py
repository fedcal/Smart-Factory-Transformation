"""Test suite for sft_agents.models.budget (Plan 04-01 Task 2)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def _make_snapshot(**overrides):
    from sft_agents.models import BudgetSnapshot

    base = {
        "tokens_input": 100,
        "tokens_output": 50,
        "tokens_total": 150,
        "cost_usd_simulated": 0.01,
        "duration_ms": 100,
        "limit_tokens": 50_000,
        "limit_cost_usd": 1.0,
        "limit_duration_s": 60,
    }
    base.update(overrides)
    return BudgetSnapshot(**base)


class TestBudgetSnapshotConstruction:
    def test_valid(self) -> None:
        s = _make_snapshot()
        assert s.tokens_total == 150
        assert s.cost_usd_simulated == 0.01

    def test_defaults_zero(self) -> None:
        from sft_agents.models import BudgetSnapshot

        s = BudgetSnapshot(
            limit_tokens=1000,
            limit_cost_usd=0.5,
            limit_duration_s=30,
        )
        assert s.tokens_input == 0
        assert s.tokens_output == 0
        assert s.tokens_total == 0
        assert s.cost_usd_simulated == 0.0
        assert s.duration_ms == 0


class TestBudgetSnapshotConstraints:
    def test_negative_tokens_input_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_snapshot(tokens_input=-1)

    def test_negative_cost_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_snapshot(cost_usd_simulated=-0.01)

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_snapshot(duration_ms=-1)


class TestBudgetSnapshotImmutability:
    def test_frozen(self) -> None:
        s = _make_snapshot()
        with pytest.raises(ValidationError):
            s.tokens_total = 9999

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            _make_snapshot(rogue=1)


class TestBudgetLimits:
    def test_construct(self) -> None:
        from sft_agents.models import BudgetLimits

        limits = BudgetLimits(tokens=50_000, cost_usd=1.0, duration_s=60)
        assert limits.tokens == 50_000

    def test_frozen(self) -> None:
        from sft_agents.models import BudgetLimits

        limits = BudgetLimits(tokens=1000, cost_usd=0.5, duration_s=30)
        with pytest.raises(ValidationError):
            limits.tokens = 9999
