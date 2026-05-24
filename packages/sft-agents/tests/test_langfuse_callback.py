"""Tests for langfuse v3 callback wiring (CORE-06, Pitfall §11).

Validates the *contract* — not the live integration — of the langfuse callback
helper. Live Langfuse integration is exercised by Phase 11 smoke (out of scope).

Key invariants (Pitfall §11 — v3 API breaking change):
    - get_langfuse_callback() returns None when LANGFUSE_HOST is unset (no exception)
    - build_invocation_metadata() puts session_id / user_id / tags inside the
      metadata dict — NOT in the CallbackHandler constructor (v2 deprecated)
    - build_invocation_config() returns a LangGraph-shaped config dict
"""

from __future__ import annotations

import pytest

from sft_agents.llm.langfuse_callback import (
    build_invocation_config,
    build_invocation_metadata,
    get_langfuse_callback,
)


class TestGetLangfuseCallbackDisabled:
    """Without LANGFUSE_HOST, callback must be None (no exception)."""

    def test_returns_none_when_host_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LANGFUSE_HOST", raising=False)
        monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        assert get_langfuse_callback() is None


class TestBuildInvocationMetadata:
    """build_invocation_metadata returns Pitfall §11 v3-compatible dict."""

    def test_session_id_uses_thread_id(self) -> None:
        meta = build_invocation_metadata("thread-abc")
        assert meta["langfuse_session_id"] == "thread-abc"

    def test_default_phase4_tag(self) -> None:
        meta = build_invocation_metadata("t1")
        assert "phase4" in meta["langfuse_tags"]

    def test_user_id_omitted_when_none(self) -> None:
        meta = build_invocation_metadata("t1")
        # Optional fields with None values must not leak into the dict (clean
        # Langfuse trace metadata)
        assert "langfuse_user_id" not in meta or meta["langfuse_user_id"] is None

    def test_user_id_included_when_provided(self) -> None:
        meta = build_invocation_metadata("t1", user_id="operator-7")
        assert meta["langfuse_user_id"] == "operator-7"

    def test_tags_appended_to_default(self) -> None:
        meta = build_invocation_metadata("t1", tags=["ops", "anomaly"])
        assert "phase4" in meta["langfuse_tags"]
        assert "ops" in meta["langfuse_tags"]
        assert "anomaly" in meta["langfuse_tags"]


class TestBuildInvocationConfig:
    """build_invocation_config returns LangGraph-shaped config dict."""

    def test_has_configurable_thread_id(self) -> None:
        cfg = build_invocation_config("thread-xyz")
        assert cfg["configurable"]["thread_id"] == "thread-xyz"

    def test_has_metadata_with_session_id(self) -> None:
        cfg = build_invocation_config("thread-xyz")
        assert cfg["metadata"]["langfuse_session_id"] == "thread-xyz"

    def test_has_recursion_limit(self) -> None:
        cfg = build_invocation_config("t1", recursion_limit=30)
        assert cfg["recursion_limit"] == 30

    def test_default_recursion_limit_25(self) -> None:
        cfg = build_invocation_config("t1")
        assert cfg["recursion_limit"] == 25

    def test_callbacks_list_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """callbacks must be a list (LangGraph accepts None entries — caller filters)."""
        monkeypatch.delenv("LANGFUSE_HOST", raising=False)
        cfg = build_invocation_config("t1")
        assert isinstance(cfg["callbacks"], list)
        # When LANGFUSE_HOST is unset, the callbacks list filters out None
        # entries (LangGraph still accepts an empty list)
        assert all(cb is not None for cb in cfg["callbacks"])

    def test_phase11_tag_always_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """build_invocation_config include 'phase11' nella lista tags (OBS-02, Plan 11-01).

        Il tag è additivo: 'phase4' esistente e qualsiasi tag caller-provided devono
        coesistere con 'phase11'. Non deve essere rimosso da tag esistenti.
        """
        monkeypatch.delenv("LANGFUSE_HOST", raising=False)
        cfg = build_invocation_config("thread-11", tags=["ops"])
        tags: list[str] = cfg["metadata"]["langfuse_tags"]
        assert "phase11" in tags, (
            f"'phase11' deve essere presente in langfuse_tags, ottenuto: {tags!r}"
        )
        # I tag pre-esistenti devono sopravvivere (additivo, non sostitutivo).
        assert "phase4" in tags, (
            f"'phase4' deve rimanere in langfuse_tags dopo aggiunta phase11: {tags!r}"
        )
        assert "ops" in tags, (
            f"Tag caller-provided 'ops' deve rimanere in langfuse_tags: {tags!r}"
        )
