"""Tests for `LLM_BACKEND=mock` branch of `build_chat_model` (plan 06-03).

Verifies the third factory branch added by Phase 6:
    LLM_BACKEND=mock + MOCK_LLM_FIXTURE=<path> → MockReplayChatModel
"""

from __future__ import annotations

import json
import pathlib

import pytest

from sft_agents.llm.factory import build_chat_model


@pytest.fixture
def empty_fixture(tmp_path: pathlib.Path) -> pathlib.Path:
    fixture = tmp_path / "empty.jsonl"
    fixture.write_text(
        json.dumps({"prompt_hash": "0" * 64, "response": {"content": "ok"}}) + "\n"
    )
    return fixture


class TestFactoryMockBranch:
    def test_factory_returns_mock_when_env_set(
        self,
        monkeypatch: pytest.MonkeyPatch,
        empty_fixture: pathlib.Path,
    ) -> None:
        monkeypatch.setenv("LLM_BACKEND", "mock")
        monkeypatch.setenv("MOCK_LLM_FIXTURE", str(empty_fixture))

        llm = build_chat_model()

        assert type(llm).__name__ == "MockReplayChatModel"

    def test_factory_raises_when_mock_fixture_env_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_BACKEND", "mock")
        monkeypatch.delenv("MOCK_LLM_FIXTURE", raising=False)

        with pytest.raises(RuntimeError, match="MOCK_LLM_FIXTURE"):
            build_chat_model()

    def test_factory_validates_backend_whitelist_includes_mock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_BACKEND", "invalid")
        with pytest.raises(RuntimeError, match=r"mock"):
            build_chat_model()


class TestFactoryExistingBranchesUnchanged:
    """Smoke check: ollama branch still resolves to ChatOllama after extension."""

    def test_factory_existing_ollama_branch_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_BACKEND", "ollama")
        llm = build_chat_model()
        assert type(llm).__name__ == "ChatOllama"
