"""Tests for LLM factory (CORE-05, CORE-06).

Covers `sft_agents.llm.factory.build_chat_model` env-var dispatch + provider parity
and `sft_agents.llm.usage.resolve_model_id` model identifier formatting.
"""

from __future__ import annotations

import re

import pytest

from sft_agents.llm import build_chat_model, get_llm, resolve_model_id


class TestBuildChatModelOllamaBranch:
    """LLM_BACKEND=ollama returns ChatOllama with locked Qwen2.5-7B Q4_K_M model."""

    def test_ollama_branch_returns_chat_ollama(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_BACKEND", "ollama")
        monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
        llm = build_chat_model()
        assert type(llm).__name__ == "ChatOllama"

    def test_ollama_branch_uses_locked_default_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_BACKEND", "ollama")
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        llm = build_chat_model()
        # default model is qwen2.5:7b-instruct-q4_K_M (CONTEXT.md line 421)
        assert getattr(llm, "model", "").startswith("qwen2.5")

    def test_ollama_branch_temperature_seed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_BACKEND", "ollama")
        llm = build_chat_model(temperature=0.0, seed=42)
        # ChatOllama stores temperature as a top-level attribute
        assert getattr(llm, "temperature", None) == 0.0


class TestBuildChatModelVllmBranch:
    """LLM_BACKEND=vllm returns ChatOpenAI with stream_usage=True (Pitfall §4)."""

    def test_vllm_branch_returns_chat_openai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_BACKEND", "vllm")
        monkeypatch.setenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        monkeypatch.setenv("VLLM_API_KEY", "dummy")
        llm = build_chat_model()
        assert type(llm).__name__ == "ChatOpenAI"

    def test_vllm_branch_stream_usage_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Pitfall §4: vLLM streaming drops token_usage unless stream_usage=True."""
        monkeypatch.setenv("LLM_BACKEND", "vllm")
        llm = build_chat_model()
        # ChatOpenAI exposes stream_usage as a Pydantic field; check via getattr or __dict__
        stream_usage = getattr(llm, "stream_usage", None)
        if stream_usage is None:
            stream_usage = llm.__dict__.get("stream_usage")
        assert stream_usage is True, f"stream_usage must be True, got {stream_usage!r}"

    def test_vllm_branch_uses_locked_default_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_BACKEND", "vllm")
        monkeypatch.delenv("VLLM_MODEL", raising=False)
        llm = build_chat_model()
        model_id = getattr(llm, "model_name", "") or getattr(llm, "model", "")
        assert "Qwen2.5-14B" in model_id, (
            f"Expected Qwen2.5-14B in vllm default model id, got {model_id!r}"
        )


class TestBuildChatModelInvalidBackend:
    """LLM_BACKEND=foo raises RuntimeError with helpful message."""

    def test_invalid_backend_raises_runtime_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_BACKEND", "foo")
        with pytest.raises(RuntimeError, match=r"LLM_BACKEND.*(ollama|vllm)"):
            build_chat_model()

    def test_explicit_backend_arg_overrides_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_BACKEND", "vllm")
        llm = build_chat_model(backend="ollama")
        assert type(llm).__name__ == "ChatOllama"


class TestGetLlmConvenience:
    """get_llm() is a one-call convenience that delegates to build_chat_model()."""

    def test_get_llm_returns_default_backend_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LLM_BACKEND", raising=False)
        llm = get_llm()
        # default backend is ollama when LLM_BACKEND not set
        assert type(llm).__name__ == "ChatOllama"


class TestResolveModelId:
    """resolve_model_id matches EvidencePanel.model regex `^[a-z0-9.\\-]+@[a-z0-9.\\-]+$`."""

    EVIDENCE_REGEX = re.compile(r"^[a-z0-9.\-]+@[a-z0-9.\-]+$")

    def test_ollama_model_id_matches_evidence_panel_regex(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
        mid = resolve_model_id("ollama")
        assert self.EVIDENCE_REGEX.match(mid), (
            f"resolve_model_id output {mid!r} fails EvidencePanel.model regex"
        )
        assert "ollama" in mid

    def test_vllm_model_id_matches_evidence_panel_regex(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen2.5-14B-Instruct-AWQ")
        mid = resolve_model_id("vllm")
        assert self.EVIDENCE_REGEX.match(mid), (
            f"resolve_model_id output {mid!r} fails EvidencePanel.model regex"
        )
        assert "vllm" in mid

    def test_unknown_backend_raises(self) -> None:
        with pytest.raises(RuntimeError, match=r"LLM_BACKEND.*(ollama|vllm)"):
            resolve_model_id("foo")
