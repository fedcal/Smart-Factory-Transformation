"""Wave 0 stub for LLM factory (CORE-05, CORE-06) — Plan 04-03 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.llm.factory",
    reason="W0 stub — Plan 04-03 implements build_chat_model factory",
)


def test_llm_factory_build_chat_model_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-03 implements")
