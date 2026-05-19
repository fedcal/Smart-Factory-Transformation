"""svc_knowledge_ingest — CLI ingest pipeline scaffold (Phase 5, Plan 05-06).

This package currently ships only the ``state`` module (PG ingest state tracking
for incremental reindex per D-68 + TRN-01 scaffold). Plan 05-10 fills in the
``__main__`` Typer CLI and the ``pipeline`` orchestrator (parse → chunk → embed
→ upsert Qdrant + Neo4j MERGE).
"""

from __future__ import annotations

__all__: list[str] = []
