"""Integration tests for svc_knowledge_ingest.state (Plan 05-06, Task 3).

All tests use a real PG (testcontainer) — they exercise the parametrized SQL,
ON CONFLICT upsert semantics, and the IngestStateRow Pydantic round-trip.

Test matrix:
    test_upsert_then_get                       — insert then fetch returns same values
    test_upsert_is_idempotent                  — re-upsert same hash leaves rowcount=1
    test_upsert_updates_on_content_hash_change — content_hash change reflected in get()
    test_get_returns_none_on_missing           — unknown source_uri returns None
    test_list_all_returns_all                  — list_all enumerates all rows
    test_sql_constants_have_no_fstring         — module SQL constants are parametrized
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
import pytest

from svc_knowledge_ingest import state as state_module
from svc_knowledge_ingest.state import IngestStateRow, IngestStateStore


@pytest.mark.integration
async def test_upsert_then_get(pg_pool: asyncpg.Pool) -> None:
    """upsert(row) followed by get(source_uri) returns the same field values + tz-aware indexed_at."""
    store = IngestStateStore(pg_pool)
    await store.upsert(
        source_uri="docs/foo.md",
        content_hash="hash-1",
        version="v1",
        chunk_count=5,
        collection="docs",
        acl_level="public",
    )

    row = await store.get("docs/foo.md")

    assert row is not None, "get() must return the upserted row"
    assert isinstance(row, IngestStateRow)
    assert row.source_uri == "docs/foo.md"
    assert row.content_hash == "hash-1"
    assert row.version == "v1"
    assert row.chunk_count == 5
    assert row.collection == "docs"
    assert row.acl_level == "public"
    assert isinstance(row.indexed_at, datetime)
    assert row.indexed_at.tzinfo is not None, "indexed_at must be tz-aware"


@pytest.mark.integration
async def test_upsert_is_idempotent(pg_pool: asyncpg.Pool) -> None:
    """Re-upserting same source_uri keeps row count at 1 (ON CONFLICT DO UPDATE)."""
    store = IngestStateStore(pg_pool)
    await store.upsert(
        source_uri="docs/bar.md",
        content_hash="hash-x",
        version="v1",
        chunk_count=3,
        collection="docs",
        acl_level="public",
    )
    await store.upsert(
        source_uri="docs/bar.md",
        content_hash="hash-x",
        version="v1",
        chunk_count=3,
        collection="docs",
        acl_level="public",
    )

    async with pg_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM knowledge.ingest_state WHERE source_uri = $1",
            "docs/bar.md",
        )
    assert count == 1, "Re-upserting same source_uri must not duplicate the row"


@pytest.mark.integration
async def test_upsert_updates_on_content_hash_change(pg_pool: asyncpg.Pool) -> None:
    """Second upsert with new content_hash replaces the previous hash."""
    store = IngestStateStore(pg_pool)
    await store.upsert(
        source_uri="docs/baz.md",
        content_hash="hash-old",
        version="v1",
        chunk_count=2,
        collection="docs",
        acl_level="public",
    )
    await store.upsert(
        source_uri="docs/baz.md",
        content_hash="hash-new",
        version="v2",
        chunk_count=7,
        collection="docs",
        acl_level="public",
    )

    row = await store.get("docs/baz.md")
    assert row is not None
    assert row.content_hash == "hash-new"
    assert row.version == "v2"
    assert row.chunk_count == 7


@pytest.mark.integration
async def test_get_returns_none_on_missing(pg_pool: asyncpg.Pool) -> None:
    """Querying an unknown source_uri returns None (not an exception)."""
    store = IngestStateStore(pg_pool)
    result = await store.get("docs/does-not-exist.md")
    assert result is None


@pytest.mark.integration
async def test_list_all_returns_all(pg_pool: asyncpg.Pool) -> None:
    """list_all() enumerates every row in the table."""
    store = IngestStateStore(pg_pool)
    for i in range(3):
        await store.upsert(
            source_uri=f"docs/item-{i}.md",
            content_hash=f"hash-{i}",
            version="v1",
            chunk_count=i + 1,
            collection="docs",
            acl_level="public",
        )

    rows = await store.list_all()
    assert len(rows) == 3
    source_uris = {r.source_uri for r in rows}
    assert source_uris == {"docs/item-0.md", "docs/item-1.md", "docs/item-2.md"}


def test_sql_constants_have_no_fstring() -> None:
    """Module-level SQL constants must be plain strings with $N placeholders only.

    Enforces T-V5-sql mitigation (T-05-06-01 threat in the plan): zero f-string
    interpolation of user-controlled values into SQL. We assert by inspecting
    the source text of the state module (the constants must be string literals,
    not f-strings, in the module source).
    """
    src_path = Path(state_module.__file__)
    src = src_path.read_text(encoding="utf-8")

    # Constants must be referenced
    for const in ("_UPSERT_SQL", "_SELECT_SQL", "_LIST_SQL"):
        assert const in src, f"Expected SQL constant {const} defined in state.py"

    # Module-level constants must contain $1 placeholders (parametrized)
    assert "$1" in state_module._UPSERT_SQL
    assert "$1" in state_module._SELECT_SQL
    # _LIST_SQL has no placeholders by design (no WHERE clause).
    assert "SELECT" in state_module._LIST_SQL

    # No f-string with sensitive variables in SQL constants region.
    fstring_pattern = re.compile(
        r'f["\'][^"\']*\{(source_uri|content_hash|version|collection|acl_level|chunk_count)\}'
    )
    violations = [m.group(0) for m in fstring_pattern.finditer(src)]
    assert violations == [], (
        f"state.py must not interpolate user-controlled values into f-string SQL; "
        f"found: {violations}"
    )
