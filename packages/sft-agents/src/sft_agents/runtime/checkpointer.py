"""AsyncPostgresSaver wiring + thread_id helpers (Plan 04-05 Task 1, D-59 + CORE-04).

The PG checkpointer is exposed as an async context manager so callers compose
with ``async with``:

    async with get_postgres_checkpointer(dsn) as saver:
        graph = build_supervisor_graph(checkpointer=saver, router=router)
        await graph.ainvoke(state, config={"configurable": {"thread_id": ...}, ...})

The optional ``SFT_LANGGRAPH_AUTO_SETUP=1`` env var triggers
``await saver.setup()`` from inside the context manager. In production the tables
are created once by ``scripts/langgraph-init.py`` (Plan 04-02 BLOCKING task),
so AUTO_SETUP defaults off.

W3 driver note: ``langgraph-checkpoint-postgres>=3.1`` is built on **psycopg3**
(not asyncpg). The asyncpg-specific ``statement_cache_size=0`` PgBouncer hack
does NOT apply here; do not "helpfully" add one.
"""
from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from sft_agents.runtime.state import VALID_CLUSTERS

if TYPE_CHECKING:
    # langgraph.checkpoint.postgres.aio.AsyncPostgresSaver is a heavy import
    # (drags psycopg3 binary). Lazy at call-time.
    pass

_log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# thread_id helpers (D-59)
# ---------------------------------------------------------------------------

# Phase 1 agent slugs are kebab-case lowercase + digits (e.g. operator-assistant,
# anomaly-detector, downtime-analyzer). The regex deliberately FORBIDS '.'
# because the dot is the field separator inside the thread_id.
_AGENT_ID_RE = re.compile(r"^[a-z0-9-]+$")


def format_thread_id(cluster: str, agent_id: str, session_uuid: UUID | str) -> str:
    """Build the canonical thread_id string ``{cluster}.{agent_id}.{session_uuid}``.

    Validates:
      - cluster ∈ VALID_CLUSTERS (D-53)
      - agent_id matches kebab-case regex (Phase 1 slug convention)
      - session_uuid is a valid UUID (or a str parsable as one)

    Raises ValueError on any violation so misformed thread_ids never reach the
    PG checkpointer.
    """
    if cluster not in VALID_CLUSTERS:
        raise ValueError(
            f"cluster must be one of {sorted(VALID_CLUSTERS)}, got {cluster!r}"
        )
    if not isinstance(agent_id, str) or not _AGENT_ID_RE.match(agent_id):
        raise ValueError(
            f"agent_id must match {_AGENT_ID_RE.pattern!r} (lowercase kebab-case), "
            f"got {agent_id!r}"
        )

    if isinstance(session_uuid, UUID):
        session_str = str(session_uuid)
    else:
        # Reject non-string non-UUID types AND validate UUID syntax.
        if not isinstance(session_uuid, str):
            raise TypeError(
                f"session_uuid must be UUID or str, got {type(session_uuid).__name__}"
            )
        # Round-trip through UUID() to enforce canonical hex.
        session_str = str(UUID(session_uuid))

    return f"{cluster}.{agent_id}.{session_str}"


def parse_thread_id(thread_id: str) -> tuple[str, str, UUID]:
    """Inverse of format_thread_id — splits and validates each component.

    Raises ValueError if the input doesn't conform to ``{cluster}.{agent_id}.{uuid}``
    with exactly three dot-separated parts.
    """
    if not isinstance(thread_id, str):
        raise ValueError(f"thread_id must be str, got {type(thread_id).__name__}")
    parts = thread_id.split(".")
    if len(parts) != 3:
        raise ValueError(
            f"thread_id must have exactly 3 dot-separated parts "
            f"({{cluster}}.{{agent_id}}.{{uuid}}), got {len(parts)} in {thread_id!r}"
        )
    cluster, agent_id, session_str = parts
    if cluster not in VALID_CLUSTERS:
        raise ValueError(
            f"cluster {cluster!r} from thread_id not in VALID_CLUSTERS "
            f"({sorted(VALID_CLUSTERS)})"
        )
    if not _AGENT_ID_RE.match(agent_id):
        raise ValueError(
            f"agent_id {agent_id!r} from thread_id violates kebab-case regex "
            f"{_AGENT_ID_RE.pattern!r}"
        )
    # UUID() raises ValueError on malformed input.
    session_uuid = UUID(session_str)
    return cluster, agent_id, session_uuid


# ---------------------------------------------------------------------------
# AsyncPostgresSaver context manager (CORE-04)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def get_postgres_checkpointer(dsn: str) -> AsyncIterator[object]:
    """Yield a configured ``AsyncPostgresSaver`` for the supplied DSN.

    Parameters
    ----------
    dsn:
        PostgreSQL DSN. Caller is responsible for picking the right scheme
        (postgresql:// for psycopg3 — the langgraph-checkpoint-postgres driver).

    Yields
    ------
    AsyncPostgresSaver
        Ready to attach to ``graph.compile(checkpointer=saver)``.

    Notes
    -----
    - If env ``SFT_LANGGRAPH_AUTO_SETUP=1`` is set, ``await saver.setup()`` runs
      inside the CM (idempotent — first call creates tables, re-runs no-op).
    - In production / CI the tables are created once by
      ``scripts/langgraph-init.py`` (Plan 04-02 BLOCKING task).
    """
    if not isinstance(dsn, str) or not dsn:
        raise ValueError(f"dsn must be a non-empty str, got {dsn!r}")

    # Lazy import: keeps test_format_thread_id_* unit tests cheap (no psycopg3 load).
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: PLC0415

    auto_setup = os.environ.get("SFT_LANGGRAPH_AUTO_SETUP") == "1"
    _log.info(
        "postgres_checkpointer_open",
        dsn_prefix=dsn[:24],
        auto_setup=auto_setup,
    )
    async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
        if auto_setup:
            await saver.setup()
        try:
            yield saver
        finally:
            _log.info("postgres_checkpointer_close", dsn_prefix=dsn[:24])


__all__ = [
    "format_thread_id",
    "get_postgres_checkpointer",
    "parse_thread_id",
]
