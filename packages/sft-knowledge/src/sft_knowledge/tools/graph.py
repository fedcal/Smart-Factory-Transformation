"""TraverseGraphTool — LangChain BaseTool for Neo4j graph traversal (D-66).

Injection defense (T-05-09-02 + RESEARCH §5):
    - ``seed_label`` is a Pydantic ``Literal`` whitelist → safe to interpolate
      as Cypher label slot (label slot non accetta $param).
    - ``relation_path`` è ``list[Literal[...]]`` → safe per il join nel
      pattern relazione.
    - ``seed_id`` rimane SEMPRE un ``$param`` Cypher (mai f-string).
    - ``max_depth`` è ``int`` Pydantic con ``ge=1, le=5`` → safe per interpolazione
      (range chiuso, validato runtime).

Defense-in-depth: ``_arun`` re-validates inputs via ``TraverseGraphInput`` so
direct calls cannot bypass the Literal whitelist. The ``args_schema`` path
(``ainvoke``) still validates first; ``_arun`` re-validates as a second gate
before any Cypher is composed.

Async-only — ``_run`` raises ``NotImplementedError`` (PATTERNS Shared Pattern 7).
"""

from __future__ import annotations

from typing import Any, Literal

import structlog
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from sft_knowledge.models import GraphNode

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Input schema (D-66 LOCKED)
# ---------------------------------------------------------------------------


class TraverseGraphInput(BaseModel):
    """Input schema per ``TraverseGraphTool`` (D-66 LOCKED).

    Tutti i campi sono ``Literal``-validati o range-validati: nessuna stringa
    arbitraria può raggiungere la Cypher query (injection defense).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed_label: Literal["Machine", "Part", "FailureMode", "SOP"]
    seed_id: str
    relation_path: list[
        Literal["HAS_PART", "HAS_FAILURE_MODE", "DOCUMENTED_BY"]
    ]
    max_depth: int = Field(default=3, ge=1, le=5)


# ---------------------------------------------------------------------------
# TraverseGraphTool
# ---------------------------------------------------------------------------


class TraverseGraphTool(BaseTool):
    """LangChain BaseTool che traversa il knowledge graph Neo4j (D-66).

    Async-only: ``_run`` solleva ``NotImplementedError``.

    La Cypher è costruita SOLO con identificatori da Literal whitelist:

        MATCH (n:{seed_label} {{id: $seed_id}})-[:{rel_pipe}*1..{max_depth}]->(m)
        RETURN DISTINCT m LIMIT 100

    ``seed_id`` viene passato come ``$param`` a ``session.run`` (RESEARCH §5).
    """

    name: str = "traverse_graph"
    description: str = (
        "Navigate the knowledge entity graph "
        "(Machine→Part→FailureMode→SOP) along a relation_path. "
        "Returns list[GraphNode]. seed_label and relation_path are restricted "
        "to fixed whitelists for safety."
    )
    args_schema: type[BaseModel] = TraverseGraphInput

    _driver: Any = PrivateAttr()

    def __init__(self, driver: Any, **kwargs: Any) -> None:
        """Init the tool with a Neo4j ``AsyncDriver``."""
        super().__init__(**kwargs)
        self._driver = driver

    def _run(self, *args: Any, **kwargs: Any) -> list[GraphNode]:
        """Sync ``_run`` disabilitato — usa ``await tool.ainvoke({...})`` only."""
        raise NotImplementedError(
            "TraverseGraphTool is async-only. "
            "Use `await tool.ainvoke({...})` only."
        )

    async def _arun(
        self,
        seed_label: str,
        seed_id: str,
        relation_path: list[str],
        max_depth: int = 3,
        **kwargs: Any,
    ) -> list[GraphNode]:
        """Esegui il traversal del grafo.

        Args:
            seed_label: label di partenza (validato Literal).
            seed_id: id del nodo seed (passato come ``$param``).
            relation_path: lista di tipi relazione (validati Literal).
            max_depth: profondità massima (1..5).

        Returns:
            Lista di ``GraphNode`` (label + node_id + properties).

        Raises:
            pydantic.ValidationError: se seed_label, relation_path o max_depth
                non rispettano il Literal whitelist / range — anche quando
                ``_arun`` è invocato direttamente (difesa-in-profondità).
        """
        # Defense-in-depth: re-validate ALL inputs via TraverseGraphInput before
        # composing ANY Cypher string. This ensures the Pydantic Literal whitelist
        # is enforced regardless of whether the caller used ainvoke() (which fires
        # args_schema validation) or called _arun() directly (which would otherwise
        # bypass it). Any ValidationError propagates naturally to the caller.
        validated = TraverseGraphInput(
            seed_label=seed_label,  # type: ignore[arg-type]
            seed_id=seed_id,
            relation_path=relation_path,  # type: ignore[arg-type]
            max_depth=max_depth,
        )

        # Build rel pipe — Literal-validated; safe da interpolare.
        if not validated.relation_path:
            # Vuoto → nessun pattern utile; ritorniamo lista vuota.
            return []
        rel_pipe = "|".join(validated.relation_path)

        # CRITICAL: seed_id PASSA SOLO via $seed_id parameter.
        # seed_label e rel_pipe vengono dalla whitelist Pydantic.
        cypher = (
            f"MATCH (n:{validated.seed_label} {{id: $seed_id}})"
            f"-[:{rel_pipe}*1..{validated.max_depth}]->(m) "
            "RETURN DISTINCT m LIMIT 100"
        )

        nodes: list[GraphNode] = []
        try:
            async with self._driver.session(database="neo4j") as session:
                result = await session.run(cypher, seed_id=validated.seed_id)
                records = [record async for record in result]
        except Exception as exc:
            logger.error(
                "traverse_graph_failed",
                seed_label=validated.seed_label,
                seed_id=validated.seed_id,
                error=str(exc),
            )
            raise

        for record in records:
            m = record["m"]
            # Neo4j Node: ``labels`` è frozenset[str], ``items()`` props.
            labels = list(getattr(m, "labels", []))
            label = labels[0] if labels else validated.seed_label
            # Restringi al whitelist (defense in depth).
            if label not in {"Machine", "Part", "FailureMode", "SOP"}:
                label = validated.seed_label
            properties = dict(m.items()) if hasattr(m, "items") else {}
            node_id = str(properties.get("id", "")) or str(getattr(m, "id", ""))
            nodes.append(
                GraphNode(
                    label=label,  # type: ignore[arg-type]
                    node_id=node_id,
                    properties=properties,
                )
            )
        return nodes


__all__ = ["TraverseGraphInput", "TraverseGraphTool"]
