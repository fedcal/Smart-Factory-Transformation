"""PG ingest state tracking (D-68 incremental reindex + TRN-01 stale-detection scaffold).

This module is the only deliverable of Plan 05-06's state layer; Plan 05-10
consumes it to gate the ingest pipeline on ``(source_uri, content_hash)`` so
unchanged sources skip parse/chunk/embed and to surface stale rows whose
``indexed_at`` has aged out.

Threat mitigations (T-V5-sql / T-05-06-01):
    - All SQL is stored as module-level ``str`` constants — never f-strings.
    - All values cross asyncpg via ``$N`` placeholders.
    - Errors are logged and re-raised (D-56 invariant from audit/pg_writer.py).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

import asyncpg
import structlog
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Row model
# ---------------------------------------------------------------------------


class IngestStateRow(BaseModel):
    """Frozen Pydantic v2 mirror of ``knowledge.ingest_state`` (Shared Pattern 1).

    ``indexed_at`` must be tz-aware (Shared Pattern 2 — Phase 3+4 invariant).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    source_uri: str
    content_hash: str
    version: str
    indexed_at: datetime
    chunk_count: Annotated[int, Field(ge=0)]
    collection: str
    acl_level: str

    @field_validator("indexed_at")
    @classmethod
    def _ensure_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError(
                f"indexed_at must be tz-aware, got naive: {v!r}. "
                "Use datetime.now(timezone.utc) or rely on the PG NOW() default."
            )
        return v


# ---------------------------------------------------------------------------
# SQL constants — T-V5-sql mitigation (zero f-string interpolation)
# ---------------------------------------------------------------------------


# UPSERT: INSERT ... ON CONFLICT (source_uri) DO UPDATE.
# indexed_at is set to NOW() server-side both on insert and on update so the
# row always reflects the most-recent indexing event (TRN-01 stale detection).
_UPSERT_SQL: str = (
    "INSERT INTO knowledge.ingest_state "
    "(source_uri, content_hash, version, indexed_at, chunk_count, collection, acl_level) "
    "VALUES ($1, $2, $3, NOW(), $4, $5, $6) "
    "ON CONFLICT (source_uri) DO UPDATE SET "
    "content_hash = $2, version = $3, indexed_at = NOW(), "
    "chunk_count = $4, collection = $5, acl_level = $6"
)

_SELECT_SQL: str = (
    "SELECT source_uri, content_hash, version, indexed_at, "
    "chunk_count, collection, acl_level "
    "FROM knowledge.ingest_state WHERE source_uri = $1"
)

_LIST_SQL: str = (
    "SELECT source_uri, content_hash, version, indexed_at, "
    "chunk_count, collection, acl_level "
    "FROM knowledge.ingest_state ORDER BY indexed_at DESC"
)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class IngestStateStore:
    """asyncpg-backed CRUD for ``knowledge.ingest_state``.

    Usage::

        pool = await asyncpg.create_pool(dsn, statement_cache_size=0)
        store = IngestStateStore(pool)
        await store.upsert("docs/a.md", "hash", "v1", 4, "docs", "public")
        row = await store.get("docs/a.md")

    Single responsibility: this class is the read/write surface for the
    ingest-state row. It does not own the pool lifecycle (the caller, e.g.
    Plan 05-10's pipeline orchestrator, creates and disposes the pool).
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool
        self._logger = structlog.get_logger(__name__)

    async def upsert(
        self,
        source_uri: str,
        content_hash: str,
        version: str,
        chunk_count: int,
        collection: str,
        acl_level: str,
    ) -> None:
        """Insert or update the row keyed by ``source_uri``.

        ``indexed_at`` is set to ``NOW()`` server-side on both branches so
        callers cannot drift the timestamp; this preserves TRN-01 invariants.

        Raises:
            asyncpg.PostgresError: re-raised after logging (D-56).
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    _UPSERT_SQL,
                    source_uri,
                    content_hash,
                    version,
                    chunk_count,
                    collection,
                    acl_level,
                )
        except Exception as exc:
            self._logger.error(
                "ingest_state_upsert_failed",
                error=str(exc),
                source_uri=source_uri,
                version=version,
            )
            raise

        self._logger.debug(
            "ingest_state_upsert_ok",
            source_uri=source_uri,
            version=version,
            chunk_count=chunk_count,
        )

    async def get(self, source_uri: str) -> IngestStateRow | None:
        """Return the row for ``source_uri`` or ``None`` if absent."""
        try:
            async with self._pool.acquire() as conn:
                record = await conn.fetchrow(_SELECT_SQL, source_uri)
        except Exception as exc:
            self._logger.error(
                "ingest_state_get_failed",
                error=str(exc),
                source_uri=source_uri,
            )
            raise

        if record is None:
            return None
        return IngestStateRow.model_validate(dict(record))

    async def list_all(self) -> list[IngestStateRow]:
        """Return every row, newest ``indexed_at`` first (TRN-01 stale scaffold)."""
        try:
            async with self._pool.acquire() as conn:
                records = await conn.fetch(_LIST_SQL)
        except Exception as exc:
            self._logger.error("ingest_state_list_failed", error=str(exc))
            raise

        return [IngestStateRow.model_validate(dict(r)) for r in records]
