"""Tests for BudgetingChatModel wrapper + extract_usage_metadata helper.

BudgetingChatModel captures usage_metadata + wall-clock duration without enforcing
budget limits (enforcement lives in Plan 04-06 BudgetTracker middleware).
"""

from __future__ import annotations

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage

from sft_agents.llm import BudgetingChatModel, extract_usage_metadata
from sft_agents.models import TokenUsage


class TestExtractUsageMetadata:
    """extract_usage_metadata reads langchain-core 0.3+ AIMessage.usage_metadata shape."""

    def test_extracts_input_output_total_tokens(self) -> None:
        msg = AIMessage(
            content="hello",
            usage_metadata={"input_tokens": 12, "output_tokens": 5, "total_tokens": 17},
        )
        usage = extract_usage_metadata(msg)
        assert isinstance(usage, TokenUsage)
        assert usage.input == 12
        assert usage.output == 5
        assert usage.total == 17

    def test_fallback_to_zero_when_metadata_missing(self) -> None:
        msg = AIMessage(content="hello")  # no usage_metadata
        usage = extract_usage_metadata(msg)
        assert isinstance(usage, TokenUsage)
        assert usage.input == 0
        assert usage.output == 0
        assert usage.total == 0

    def test_fallback_to_zero_on_none_input(self) -> None:
        usage = extract_usage_metadata(None)
        assert usage.input == 0 and usage.output == 0 and usage.total == 0


@pytest.mark.asyncio
class TestBudgetingChatModelAsync:
    """BudgetingChatModel.ainvoke populates last_token_usage + last_duration_ms."""

    async def test_ainvoke_captures_duration_ms(self) -> None:
        fake = FakeListChatModel(responses=["fake response"])
        wrapper = BudgetingChatModel(fake)
        result = await wrapper.ainvoke([HumanMessage(content="prompt")])
        assert isinstance(result, AIMessage)
        assert wrapper.last_duration_ms >= 0
        assert isinstance(wrapper.last_duration_ms, int)

    async def test_ainvoke_captures_token_usage_zero_for_fake_llm(self) -> None:
        """FakeListChatModel does not populate usage_metadata → TokenUsage(0,0,0)."""
        fake = FakeListChatModel(responses=["fake response"])
        wrapper = BudgetingChatModel(fake)
        await wrapper.ainvoke([HumanMessage(content="prompt")])
        assert isinstance(wrapper.last_token_usage, TokenUsage)
        assert wrapper.last_token_usage.total == 0


class TestBudgetingChatModelDelegation:
    """bind_tools / with_structured_output return BudgetingChatModel (chain preservation)."""

    def test_bind_tools_returns_budgeting_chat_model(self) -> None:
        from langchain_core.tools import tool

        @tool
        def add(a: int, b: int) -> int:
            """Sum two integers."""
            return a + b

        fake = FakeListChatModel(responses=["x"])
        wrapper = BudgetingChatModel(fake)
        bound = wrapper.bind_tools([add])
        assert isinstance(bound, BudgetingChatModel), (
            "bind_tools must return a BudgetingChatModel to preserve usage capture"
        )

    def test_wrapped_attribute_exposed(self) -> None:
        fake = FakeListChatModel(responses=["x"])
        wrapper = BudgetingChatModel(fake)
        # Wrapped chat model should be accessible for advanced introspection
        assert wrapper.wrapped is fake


class TestBudgetingChatModelInitialState:
    """Pre-invocation, last_token_usage/last_duration_ms have safe defaults."""

    def test_zero_defaults_before_first_invoke(self) -> None:
        fake = FakeListChatModel(responses=["x"])
        wrapper = BudgetingChatModel(fake)
        assert wrapper.last_duration_ms == 0
        assert isinstance(wrapper.last_token_usage, TokenUsage)
        assert wrapper.last_token_usage.total == 0
