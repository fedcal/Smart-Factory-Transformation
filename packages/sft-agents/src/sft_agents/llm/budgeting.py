"""BudgetingChatModel — usage_metadata + duration_ms capture wrapper.

Wraps any ``BaseChatModel`` and exposes after every invocation:
    - ``last_token_usage: TokenUsage`` — read from response.usage_metadata
    - ``last_duration_ms: int``        — wall-clock perf_counter delta

This module **measures** only; budget **enforcement** is implemented in Plan 04-06
BudgetTracker middleware. Keeping measure/enforce split honors single-responsibility
and lets EvidencePanel populate `tokens` + `duration_ms` regardless of whether a
BudgetTracker is wired in front.

bind_tools / with_structured_output return a fresh ``BudgetingChatModel`` wrapping
the delegated result so usage capture survives chained transformations
(``llm.bind_tools(tools).ainvoke(...)`` still records usage).
"""

from __future__ import annotations

import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from sft_agents.llm.usage import extract_usage_metadata
from sft_agents.models import TokenUsage


class BudgetingChatModel:
    """Decorator over a BaseChatModel that captures usage + duration per call.

    Does **not** subclass BaseChatModel — composition over inheritance keeps the
    contract narrow and avoids the Pydantic v2 BaseChatModel field surface.
    Delegating only the methods the runtime calls (ainvoke/invoke/bind_tools/
    with_structured_output) is sufficient for Phase 4 use cases.
    """

    def __init__(self, wrapped: BaseChatModel) -> None:
        self._wrapped: BaseChatModel = wrapped
        self._last_token_usage: TokenUsage = TokenUsage(input=0, output=0, total=0)
        self._last_duration_ms: int = 0

    # ------------------------------------------------------------------
    # Accessors (read-only snapshots — assignment via _capture only)
    # ------------------------------------------------------------------

    @property
    def wrapped(self) -> BaseChatModel:
        """The underlying BaseChatModel (escape hatch for advanced introspection)."""
        return self._wrapped

    @property
    def last_token_usage(self) -> TokenUsage:
        """TokenUsage from the most recent invocation (zero before first call)."""
        return self._last_token_usage

    @property
    def last_duration_ms(self) -> int:
        """Wall-clock duration in ms of the most recent invocation (zero before first)."""
        return self._last_duration_ms

    # ------------------------------------------------------------------
    # Capture helper
    # ------------------------------------------------------------------

    def _capture(self, start_ns: int, response: Any) -> None:
        """Update last_token_usage + last_duration_ms snapshots.

        Immutability: TokenUsage is frozen; we replace the attribute, never mutate.
        """
        self._last_duration_ms = max(0, (time.perf_counter_ns() - start_ns) // 1_000_000)
        self._last_token_usage = extract_usage_metadata(response)

    # ------------------------------------------------------------------
    # Async invocation
    # ------------------------------------------------------------------

    async def ainvoke(self, input: Any, config: Any | None = None, **kw: Any) -> Any:
        """Async invoke; capture duration + usage post-call."""
        start_ns = time.perf_counter_ns()
        response = await self._wrapped.ainvoke(input, config=config, **kw)
        self._capture(start_ns, response)
        return response

    # ------------------------------------------------------------------
    # Sync invocation
    # ------------------------------------------------------------------

    def invoke(self, input: Any, config: Any | None = None, **kw: Any) -> Any:
        """Sync invoke; capture duration + usage post-call."""
        start_ns = time.perf_counter_ns()
        response = self._wrapped.invoke(input, config=config, **kw)
        self._capture(start_ns, response)
        return response

    # ------------------------------------------------------------------
    # Tool binding / structured output — chain preservation
    # ------------------------------------------------------------------

    def bind_tools(self, tools: list[Any], **kw: Any) -> BudgetingChatModel:
        """Delegate to wrapped.bind_tools and rewrap the result.

        The returned BudgetingChatModel reuses *this* instance's state slots? No —
        we return a fresh BudgetingChatModel so the bound chain has its own usage
        snapshot (typical pattern in LangGraph is to bind once at graph build time
        and reuse across invocations).
        """
        bound = self._wrapped.bind_tools(tools, **kw)
        return BudgetingChatModel(bound)

    def with_structured_output(self, schema: Any, **kw: Any) -> BudgetingChatModel:
        """Delegate to wrapped.with_structured_output and rewrap."""
        structured = self._wrapped.with_structured_output(schema, **kw)
        return BudgetingChatModel(structured)

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"BudgetingChatModel(wrapped={type(self._wrapped).__name__}, "
            f"last_duration_ms={self._last_duration_ms}, "
            f"last_token_usage={self._last_token_usage!r})"
        )
