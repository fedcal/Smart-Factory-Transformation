"""sft-agents LLM adapter (Phase 4, Plan 04-03; extended Phase 6, Plan 06-03).

Provider-agnostic LangChain adapter switched by env var ``LLM_BACKEND``:

    LLM_BACKEND=ollama  → ChatOllama (langchain-ollama) for dev (Qwen2.5-7B Q4_K_M)
    LLM_BACKEND=vllm    → ChatOpenAI (langchain-openai) for prod (Qwen2.5-14B AWQ)
    LLM_BACKEND=mock    → MockReplayChatModel (JSONL replay for CI determinism; D-X-01)

Public API:
    build_chat_model      — factory: env-var dispatch + provider parity
    get_llm               — one-call convenience around build_chat_model
    BudgetingChatModel    — wrapper capturing usage_metadata + duration_ms
    extract_usage_metadata — pure helper reading AIMessage.usage_metadata
    resolve_model_id      — model identifier matching EvidencePanel.model regex
    MockReplayChatModel   — JSONL record/replay chat model (CI determinism)
"""

from __future__ import annotations

from sft_agents.llm.budgeting import BudgetingChatModel
from sft_agents.llm.factory import LLMBackend, build_chat_model, get_llm
from sft_agents.llm.langfuse_callback import (
    build_invocation_config,
    build_invocation_metadata,
    get_langfuse_callback,
)
from sft_agents.llm.mock import MockReplayChatModel
from sft_agents.llm.usage import extract_usage_metadata, resolve_model_id

__all__ = [
    "BudgetingChatModel",
    "LLMBackend",
    "MockReplayChatModel",
    "build_chat_model",
    "build_invocation_config",
    "build_invocation_metadata",
    "extract_usage_metadata",
    "get_langfuse_callback",
    "get_llm",
    "resolve_model_id",
]
