"""Wave 0 stub for LLM adapter (CORE-05, CORE-06) — Plan 04-03 implements."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "sft_agents.llm.adapter",
    reason="W0 stub — Plan 04-03 implements LLM_BACKEND=ollama|vllm adapter",
)


def test_llm_adapter_switch_stub() -> None:
    pytest.skip(reason="Wave 0 stub — Plan 04-03 implements")
