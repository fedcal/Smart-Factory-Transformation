"""Tool ABC interface (CORE-01).

Async-first LangChain `BaseTool` subclass. Mirrors the Phase 3 pattern from
`packages/sft-tools/src/sft_tools/timescale/query.py`:
    - `_run` raises NotImplementedError to force callers onto `_arun`
    - subclasses implement `async def _arun(...)`
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.tools import BaseTool


class Tool(BaseTool, ABC):
    """Async-first Tool base class for sft-agents.

    Phase 4 contract: agents call tools via `await tool.ainvoke({...})` (LangChain
    standard). Sync `_run` is disabled because every Phase 4 tool surface (Timescale,
    NATS, FastAPI client) is fundamentally async.

    Subclasses MUST implement `_arun(*args, **kwargs)`. They MAY override `_run` only
    to provide a richer error message; the default already raises NotImplementedError.
    """

    def _run(self, *args: Any, **kwargs: Any) -> Any:  # noqa: D401, ANN401
        """Disabled — Tool is async-only. Use `await tool.ainvoke({...})`."""
        raise NotImplementedError(
            f"{type(self).__name__} is async-only. "
            "Use `await tool.ainvoke({...})` or `await tool._arun(...)` instead."
        )

    @abstractmethod
    async def _arun(self, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """Async tool implementation — subclasses provide concrete behavior."""
