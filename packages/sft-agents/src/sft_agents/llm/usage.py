"""Usage extraction + model identifier helpers (Plan 04-03 Task 1).

`extract_usage_metadata`: read langchain-core 0.3+ AIMessage.usage_metadata shape
into a frozen ``TokenUsage`` (zero-fallback on absence).

`resolve_model_id`: build a model identifier that matches the
``EvidencePanel.model`` regex ``^[a-z0-9.\\-]+@[a-z0-9.\\-]+$``.

Backend-specific runtime tag (e.g. ``@ollama-0.6``, ``@vllm-0.8``) is static for
Phase 4 — Phase 11 may dynamic-query runtime versions.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

from sft_agents.models import TokenUsage

logger = structlog.get_logger(__name__)

# Static runtime tags per backend (Phase 4 lock; Phase 11 may dynamic-query)
_OLLAMA_RUNTIME = "ollama-0.6"
_VLLM_RUNTIME = "vllm-0.8"

# Default model identifiers (must be lowercase per EvidencePanel regex)
_DEFAULT_OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_K_M"
_DEFAULT_VLLM_MODEL = "Qwen/Qwen2.5-14B-Instruct-AWQ"


def _sanitize_for_model_regex(raw: str) -> str:
    """Lowercase + replace illegal chars so the result matches EvidencePanel.model regex.

    Regex allows only ``[a-z0-9.\\-]``. We map ``:``, ``/``, ``_`` → ``-``.
    Any remaining illegal character is also replaced with ``-`` for safety.
    """
    out = raw.lower()
    for ch in (":", "/", "_"):
        out = out.replace(ch, "-")
    # Collapse anything outside [a-z0-9.-] to '-'
    safe_chars = set("abcdefghijklmnopqrstuvwxyz0123456789.-")
    out = "".join(c if c in safe_chars else "-" for c in out)
    # Collapse repeated dashes
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def extract_usage_metadata(response_or_message: Any) -> TokenUsage:
    """Return ``TokenUsage`` from an LLM response/message's ``usage_metadata``.

    langchain-core 0.3+ AIMessage.usage_metadata shape:
        {"input_tokens": int, "output_tokens": int, "total_tokens": int}

    Falls back to ``TokenUsage(0, 0, 0)`` when the attribute is missing or the
    payload is None — BudgetingChatModel relies on this for FakeListChatModel
    fixtures which do not populate usage_metadata.
    """
    if response_or_message is None:
        return TokenUsage(input=0, output=0, total=0)

    meta = getattr(response_or_message, "usage_metadata", None)
    if not meta:
        return TokenUsage(input=0, output=0, total=0)

    input_tokens = int(meta.get("input_tokens", 0) or 0)
    output_tokens = int(meta.get("output_tokens", 0) or 0)
    total = int(meta.get("total_tokens", input_tokens + output_tokens) or 0)
    return TokenUsage(input=input_tokens, output=output_tokens, total=total)


def resolve_model_id(backend: str) -> str:
    """Return model identifier matching the EvidencePanel.model regex.

    Args:
        backend: "ollama" or "vllm".

    Returns:
        Identifier of the form ``<sanitized-model>@<runtime>`` (lowercase,
        ``:`` and ``/`` replaced with ``-``).

    Raises:
        RuntimeError: when ``backend`` is not in the whitelist.
    """
    if backend == "ollama":
        raw_model = os.environ.get("OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL)
        return f"{_sanitize_for_model_regex(raw_model)}@{_OLLAMA_RUNTIME}"
    if backend == "vllm":
        raw_model = os.environ.get("VLLM_MODEL", _DEFAULT_VLLM_MODEL)
        return f"{_sanitize_for_model_regex(raw_model)}@{_VLLM_RUNTIME}"
    raise RuntimeError(
        f"LLM_BACKEND must be one of ollama|vllm, got {backend!r}"
    )
