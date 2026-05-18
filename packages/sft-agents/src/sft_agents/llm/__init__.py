"""sft-agents LLM adapter (Phase 4, Plan 04-03).

Provider-agnostic LangChain adapter switched by env var ``LLM_BACKEND``:

    LLM_BACKEND=ollama  → ChatOllama (langchain-ollama) for dev (Qwen2.5-7B Q4_K_M)
    LLM_BACKEND=vllm    → ChatOpenAI (langchain-openai) for prod (Qwen2.5-14B AWQ)

Public API:
    build_chat_model     — factory: env-var dispatch + provider parity
    get_llm              — one-call convenience around build_chat_model
    BudgetingChatModel   — wrapper capturing usage_metadata + duration_ms
    extract_usage_metadata — pure helper reading AIMessage.usage_metadata
    resolve_model_id     — model identifier matching EvidencePanel.model regex
"""

from __future__ import annotations

from sft_agents.llm.budgeting import BudgetingChatModel
from sft_agents.llm.factory import LLMBackend, build_chat_model, get_llm
from sft_agents.llm.usage import extract_usage_metadata, resolve_model_id

__all__ = [
    "BudgetingChatModel",
    "LLMBackend",
    "build_chat_model",
    "extract_usage_metadata",
    "get_llm",
    "resolve_model_id",
]
