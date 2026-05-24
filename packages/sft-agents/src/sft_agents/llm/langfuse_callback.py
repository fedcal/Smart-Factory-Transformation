"""Langfuse v3 callback + LangGraph invocation config helpers (Pitfall §11).

**Pitfall §11 — v3 API breaking change vs v2:**

In Langfuse v2 the LangChain callback handler accepted ``session_id`` /
``user_id`` / ``tags`` directly in the constructor. In v3 those are passed
**per-invocation** via ``config['metadata']``:

    config = {
        "configurable": {"thread_id": "..."},
        "callbacks": [langfuse_handler],          # constructor takes NO session id
        "metadata": {                             # session id LIVES HERE
            "langfuse_session_id": thread_id,
            "langfuse_user_id":    user_id,
            "langfuse_tags":       ["phase4", ...],
        },
        "recursion_limit": 25,
    }
    await graph.ainvoke(state, config=config)

Public API:
    get_langfuse_callback        — None when LANGFUSE_HOST unset; CallbackHandler otherwise
    build_invocation_metadata    — dict shape for `config["metadata"]`
    build_invocation_config      — full LangGraph invocation config dict
"""

from __future__ import annotations

import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def get_langfuse_callback() -> Any | None:
    """Return a Langfuse v3 CallbackHandler if configured, else None.

    Reads three env vars:
        LANGFUSE_HOST        — gates the integration (unset → returns None)
        LANGFUSE_PUBLIC_KEY  — required when host is set
        LANGFUSE_SECRET_KEY  — required when host is set

    Returns ``None`` and logs ``langfuse_disabled`` when LANGFUSE_HOST is unset
    so callers can pass the result directly into a config callbacks list and
    filter Nones (LangGraph tolerates the empty list).

    Returns ``None`` and logs ``langfuse_import_failed`` when ``langfuse`` is
    installed but the LangChain integration submodule cannot be imported (e.g.
    the optional ``langchain`` peer dependency is missing). This is treated as
    a soft failure so unit tests can run without the full Langfuse stack.
    """
    host = os.environ.get("LANGFUSE_HOST")
    if not host:
        logger.info("langfuse_disabled", reason="LANGFUSE_HOST unset")
        return None

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not (public_key and secret_key):
        logger.warning(
            "langfuse_keys_missing",
            host=host,
            has_public_key=bool(public_key),
            has_secret_key=bool(secret_key),
        )
        return None

    try:
        # Langfuse v3: CallbackHandler lives under langfuse.langchain (Pitfall §11).
        from langfuse.langchain import CallbackHandler  # type: ignore[import-not-found]
    except ImportError as exc:
        logger.warning("langfuse_import_failed", error=str(exc))
        return None

    # Langfuse v3 callback handler takes NO session_id — session_id is in
    # invocation metadata (Pitfall §11). Constructor accepts only auth/host.
    logger.info("langfuse_enabled", host=host)
    return CallbackHandler()


def build_invocation_metadata(
    thread_id: str,
    user_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Return Langfuse v3 invocation metadata dict (Pitfall §11).

    Args:
        thread_id: LangGraph thread_id; reused as Langfuse session_id for trace
            grouping across multiple agent invocations within one user session.
        user_id: Optional operator identifier for trace attribution.
        tags: Additional Langfuse tags appended after the default ["phase4", "phase11"].

    Returns:
        Immutable-style dict (caller should treat as frozen) with keys:
            langfuse_session_id
            langfuse_user_id  (only present when ``user_id`` is not None)
            langfuse_tags
    """
    # "phase11" aggiunto additivamente (Plan 11-01 OBS-02 SC-1).
    # I tag esistenti ("phase4") e quelli caller-provided coesistono.
    out: dict[str, Any] = {
        "langfuse_session_id": thread_id,
        "langfuse_tags": ["phase4", "phase11", *(tags or [])],
    }
    if user_id is not None:
        out["langfuse_user_id"] = user_id
    return out


def build_invocation_config(
    thread_id: str,
    user_id: str | None = None,
    tags: list[str] | None = None,
    recursion_limit: int = 25,
) -> dict[str, Any]:
    """Return LangGraph invocation config dict (Pitfall §11 shape).

    The shape is the canonical config every Phase 4+ agent invocation will use:
        {
          "configurable": {"thread_id": thread_id},
          "callbacks":    [<langfuse handler or empty>],
          "metadata":     {"langfuse_session_id": thread_id, ...},
          "recursion_limit": recursion_limit,
        }

    callbacks list filters out ``None`` returned by ``get_langfuse_callback()``
    so the integration is fully opt-in.
    """
    handler = get_langfuse_callback()
    callbacks: list[Any] = [h for h in (handler,) if h is not None]
    return {
        "configurable": {"thread_id": thread_id},
        "callbacks": callbacks,
        "metadata": build_invocation_metadata(thread_id, user_id=user_id, tags=tags),
        "recursion_limit": recursion_limit,
    }
