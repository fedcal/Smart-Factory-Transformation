"""MockReplayChatModel — JSONL record/replay BaseChatModel for CI determinism (D-X-01).

Backs the ``LLM_BACKEND=mock`` branch of :func:`sft_agents.llm.factory.build_chat_model`.
Replays canned ``AIMessage`` / ``ToolCall`` responses keyed by a SHA-256 hash of the
incoming chat messages, with graceful ordered-fallback when the hash is absent.

References:
    - 06-RESEARCH.md §Pattern 2 (Mock LLM backend / record-replay)
    - 06-RESEARCH.md §Pitfall §10 (graceful fallback when prompt edits drift the hash;
      emits a structlog warning so a CI gate can flag drift before fixtures rot.)
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

import structlog
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ConfigDict, PrivateAttr

logger = structlog.get_logger(__name__)


class MockReplayChatModel(BaseChatModel):
    """Replay JSONL fixture keyed on prompt_hash (LLM_BACKEND=mock).

    The fixture file is a JSON-Lines document where each line follows the shape::

        {
          "prompt_hash": "<sha256-64chars>",
          "response": {
            "content": "...",
            "tool_calls": [{"id": "...", "name": "...", "args": {...}}],
            "usage_metadata": {"input_tokens": N, "output_tokens": M, "total_tokens": K}
          }
        }

    Hashing rule (matches the recorder script in ``scripts/regenerate-fixtures.py``)::

        sha256("\\n".join(f"{m.type}:{m.content}" for m in messages))

    When the computed hash is not found in the fixture, the model falls back to
    ordered replay (returning the next un-consumed entry) and emits a structlog
    warning event ``mock_llm_hash_miss_fallback`` so CI can gate on drift.
    """

    # BaseChatModel is a pydantic v2 BaseModel — allow extra ignored & arbitrary types
    model_config = ConfigDict(arbitrary_types_allowed=True)

    fixture_path: pathlib.Path

    # Private mutable state — PrivateAttr keeps these out of the pydantic schema
    _entries: list[dict[str, Any]] = PrivateAttr(default_factory=list)
    _index: int = PrivateAttr(default=0)

    def __init__(self, fixture_path: str | pathlib.Path, **kwargs: Any) -> None:
        super().__init__(fixture_path=pathlib.Path(fixture_path), **kwargs)
        self._entries = [
            json.loads(line)
            for line in self.fixture_path.read_text().splitlines()
            if line.strip()
        ]
        self._index = 0

    # ----- internal helpers --------------------------------------------------

    @staticmethod
    def _prompt_hash(messages: list[BaseMessage]) -> str:
        body = "\n".join(f"{m.type}:{m.content}" for m in messages)
        return hashlib.sha256(body.encode()).hexdigest()

    def _build_message(self, entry: dict[str, Any]) -> AIMessage:
        resp = entry.get("response", {})
        return AIMessage(
            content=resp.get("content", ""),
            tool_calls=resp.get("tool_calls", []),
            usage_metadata=resp.get("usage_metadata"),
        )

    # ----- BaseChatModel contract -------------------------------------------

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        ph = self._prompt_hash(messages)
        entry = next((e for e in self._entries if e.get("prompt_hash") == ph), None)

        if entry is None:
            # Pitfall §10 — graceful fallback to ordered replay; flag for CI gate.
            if self._index >= len(self._entries):
                raise RuntimeError(
                    "MockReplayChatModel exhausted: no fixture entry matched "
                    f"prompt_hash={ph!r} and ordered fallback index "
                    f"{self._index} >= len(entries)={len(self._entries)}. "
                    "Re-record fixtures via scripts/regenerate-fixtures.py."
                )
            entry = self._entries[self._index]
            logger.warning(
                "mock_llm_hash_miss_fallback",
                expected_hash=ph,
                index=self._index,
                fallback_hash=entry.get("prompt_hash"),
                fixture_path=str(self.fixture_path),
            )
            self._index += 1

        msg = self._build_message(entry)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError(
            "MockReplayChatModel is async-only. Use `await model.ainvoke(...)` instead."
        )

    @property
    def _llm_type(self) -> str:
        return "mock-replay"
