"""Provider-agnostic LLM factory (CORE-05, CORE-06).

Env-var dispatch idiom mirrors `services/ot-bridge/src/svc_ot_bridge/main.py:62-71`:
    LLM_BACKEND=ollama → langchain_ollama.ChatOllama (dev — Qwen2.5-7B Q4_K_M)
    LLM_BACKEND=vllm   → langchain_openai.ChatOpenAI (prod — Qwen2.5-14B AWQ + OpenAI-compatible)
    Anything else      → RuntimeError (T-04-LLM-Inject mitigation: whitelist Literal)

vLLM branch passes ``stream_usage=True`` (Pitfall §4): without this flag langchain-openai
drops ``usage_metadata`` on streaming responses, breaking BudgetTracker enforcement.
"""

from __future__ import annotations

import os
from typing import Any, Literal

import structlog
from langchain_core.language_models.chat_models import BaseChatModel

logger = structlog.get_logger(__name__)

LLMBackend = Literal["ollama", "vllm"]
_VALID_BACKENDS = ("ollama", "vllm")

# Defaults — locked for Phase 4 (D-CONTEXT line 421)
_DEFAULT_OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_K_M"
_DEFAULT_OLLAMA_HOST = "http://localhost:11434"
_DEFAULT_VLLM_MODEL = "Qwen/Qwen2.5-14B-Instruct-AWQ"
_DEFAULT_VLLM_BASE_URL = "http://localhost:8000/v1"
_DEFAULT_VLLM_API_KEY = "dummy"


def _resolve_backend(backend: LLMBackend | str | None) -> str:
    """Read LLM_BACKEND env var when arg is None; validate against whitelist."""
    if backend is None:
        backend = os.environ.get("LLM_BACKEND", "ollama")
    if backend not in _VALID_BACKENDS:
        raise RuntimeError(
            f"LLM_BACKEND must be one of ollama|vllm, got {backend!r}"
        )
    return backend


def build_chat_model(
    *,
    backend: LLMBackend | str | None = None,
    temperature: float = 0.0,
    seed: int = 42,
    **kw: Any,
) -> BaseChatModel:
    """Return a BaseChatModel for the requested backend.

    Args:
        backend: "ollama" or "vllm"; reads ``LLM_BACKEND`` env var when None.
        temperature: Sampling temperature (default 0.0 for deterministic output).
        seed: PRNG seed (default 42); honored by Ollama, accepted by ChatOpenAI.
        **kw: Forwarded to the underlying chat model constructor.

    Raises:
        RuntimeError: when ``backend`` (or ``LLM_BACKEND``) is not in the whitelist.

    NB Pitfall §4: vLLM branch passes ``stream_usage=True`` so streaming responses
    still populate ``usage_metadata``; BudgetTracker relies on this.
    """
    resolved = _resolve_backend(backend)

    if resolved == "ollama":
        # Local-only import keeps top-of-module load light + avoids forcing
        # langchain_ollama install in environments that only use vllm (and vice
        # versa). Both deps are pinned in pyproject.toml; this is a stylistic
        # mirror of services/ot-bridge late imports in main.run().
        from langchain_ollama import ChatOllama

        model = os.environ.get("OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL)
        base_url = os.environ.get("OLLAMA_HOST", _DEFAULT_OLLAMA_HOST)
        logger.info(
            "llm_factory_build",
            backend=resolved,
            model=model,
            base_url=base_url,
            temperature=temperature,
        )
        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            seed=seed,
            **kw,
        )

    # resolved == "vllm"
    from langchain_openai import ChatOpenAI

    model = os.environ.get("VLLM_MODEL", _DEFAULT_VLLM_MODEL)
    base_url = os.environ.get("VLLM_BASE_URL", _DEFAULT_VLLM_BASE_URL)
    api_key = os.environ.get("VLLM_API_KEY", _DEFAULT_VLLM_API_KEY)
    logger.info(
        "llm_factory_build",
        backend=resolved,
        model=model,
        base_url=base_url,
        temperature=temperature,
        stream_usage=True,
    )
    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        seed=seed,
        stream_usage=True,  # Pitfall §4 — required for vLLM streaming usage_metadata
        **kw,
    )


def get_llm(**kw: Any) -> BaseChatModel:
    """One-call convenience around ``build_chat_model()``.

    Reads ``LLM_BACKEND`` from env (default "ollama"), uses temperature=0.0, seed=42.
    """
    return build_chat_model(**kw)
