"""RagSearchTool — LangChain BaseTool for hybrid retrieval with ACL pre-filter.

D-66 LOCKED schema:
    - ``args_schema = RagSearchInput`` (frozen + extra=forbid).
    - Async-only — ``_run`` raises ``NotImplementedError`` (PATTERNS Shared Pattern 7).
    - Pipeline iniettato via ``__init__`` (private attribute ``_pipeline``).

Trust boundary (T-05-09-04 mitigation):
    Pydantic ``extra="forbid"`` rifiuta argomenti sconosciuti; il typing è
    enforced runtime sulle Literal e sui range Field(ge/le).
"""

from __future__ import annotations

from typing import Any, Literal

import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from sft_knowledge.models import RagCitation

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Input schema (D-66 LOCKED — schema non negoziabile)
# ---------------------------------------------------------------------------


class RagSearchInput(BaseModel):
    """Input schema per ``RagSearchTool`` (D-66 LOCKED).

    Tutti i campi sono validati run-time: ``frozen=True`` previene mutazioni
    in-place, ``extra="forbid"`` rifiuta argomenti sconosciuti.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str
    user_roles: list[str]
    category: Literal["sop", "manuals", "troubleshooting", "training"] = "sop"
    k: int = Field(default=5, ge=1, le=20)
    lang: Literal["it", "en"] | None = None
    sop_ids: list[str] | None = None
    asset_family: str | None = None
    rerank: bool = True


# ---------------------------------------------------------------------------
# RagSearchTool
# ---------------------------------------------------------------------------


class RagSearchTool(BaseTool):
    """LangChain BaseTool che espone la ``RetrievalPipeline`` agli agenti (D-66).

    Async-only: ``_run`` solleva ``NotImplementedError`` per evitare deadlock
    quando agenti chiamano in modo sincrono (PATTERNS Shared Pattern 7).

    Usage::

        tool = RagSearchTool(pipeline=retrieval_pipeline)
        citations = await tool.ainvoke({
            "query": "filo ordito",
            "user_roles": ["technician"],
        })
    """

    name: str = "rag_search"
    description: str = (
        "Search knowledge base chunks with hybrid retrieval (dense+sparse+rerank). "
        "Applies ACL pre-filter based on user_roles. Returns RagCitation list. "
        "Use category to scope to a specific corpus (sop/manuals/troubleshooting/training). "
        "Optional filters: lang, sop_ids, asset_family."
    )
    args_schema: type[BaseModel] = RagSearchInput

    # Pipeline iniettato a costruzione; usiamo PrivateAttr per evitare che
    # langchain_core lo tratti come parametro tool.
    _pipeline: Any = PrivateAttr()

    def __init__(self, pipeline: Any, **kwargs: Any) -> None:
        """Init the tool with the retrieval pipeline.

        Args:
            pipeline: ``RetrievalPipeline`` instance (already wired with
                qdrant_client + embedder + reranker).
        """
        super().__init__(**kwargs)
        self._pipeline = pipeline

    def _run(self, *args: Any, **kwargs: Any) -> list[RagCitation]:
        """Sync ``_run`` disabilitato — usa ``await tool.ainvoke(...)``."""
        raise NotImplementedError(
            "RagSearchTool is async-only. "
            "Use `await tool.ainvoke({...})` or `await tool._arun(...)` instead."
        )

    async def _arun(
        self,
        query: str,
        user_roles: list[str],
        category: str = "sop",
        k: int = 5,
        lang: str | None = None,
        sop_ids: list[str] | None = None,
        asset_family: str | None = None,
        rerank: bool = True,
        **kwargs: Any,
    ) -> list[RagCitation]:
        """Esegui retrieval ibrido tramite ``RetrievalPipeline.search``."""
        return await self._pipeline.search(
            query=query,
            user_roles=user_roles,
            category=category,
            k=k,
            lang=lang,
            sop_ids=sop_ids,
            asset_family=asset_family,
            rerank=rerank,
        )


__all__ = ["RagSearchInput", "RagSearchTool"]
