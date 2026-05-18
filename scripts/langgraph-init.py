#!/usr/bin/env python3
"""
scripts/langgraph-init.py

Idempotent bootstrap of LangGraph's PostgreSQL checkpoint tables.

This script invokes ``AsyncPostgresSaver.setup()`` from
``langgraph-checkpoint-postgres>=3.1``, which creates (or no-ops on re-run)
the tables:

    public.checkpoints
    public.checkpoint_blobs
    public.checkpoint_migrations

It is **[BLOCKING]** for Phase 4 Waves 3 and 4 — every Plan that uses LangGraph
checkpointing must run this first, after ``scripts/timescale-migrate.py``.

W3 driver note (statement_cache_size=0 is NOT required here):
    ``langgraph-checkpoint-postgres>=3.1`` ships ``AsyncPostgresSaver`` built on
    **psycopg3** (``psycopg[binary,pool]``), NOT asyncpg. The asyncpg-specific
    PgBouncer constraint requiring ``statement_cache_size=0`` to disable
    server-side prepared statements does NOT apply here — psycopg3 uses
    client-side prepared statements by default and is PgBouncer
    transaction-mode-compatible without per-connection tuning. The script
    therefore takes no driver-tuning parameters; it simply invokes
    ``from_conn_string`` which the library configures internally. Do not
    "helpfully" add an asyncpg pool override.

Exit codes:
    0 — setup() succeeded (first run created tables; subsequent runs are no-ops)
    1 — connection failure or unexpected exception

Usage:
    export TIMESCALE_DSN="postgresql://sft:sft_dev_pass@localhost:5432/sft"
    python3 scripts/langgraph-init.py

    # Dry-run (no DB connection):
    python3 scripts/langgraph-init.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import structlog

logger = structlog.get_logger(__name__)


async def bootstrap(dsn: str, dry_run: bool = False) -> int:
    """Run ``AsyncPostgresSaver.setup()`` against the given DSN.

    Parameters
    ----------
    dsn:
        PostgreSQL DSN, e.g.
        ``postgresql://sft:sft_dev_pass@timescaledb:5432/sft``.
    dry_run:
        When True, log the intent and return 0 without opening a connection.

    Returns
    -------
    int
        0 on success, 1 on error.
    """
    if dry_run:
        logger.info("langgraph_init_dry_run", dsn_prefix=dsn[:24])
        return 0

    # Lazy import: keeps --dry-run usable without the langgraph package installed.
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: PLC0415
    except ImportError as exc:
        logger.error("langgraph_init_failed", reason="import", error=str(exc))
        return 1

    try:
        async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
            await saver.setup()
        logger.info("langgraph_init_ok", dsn_prefix=dsn[:24])
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.error("langgraph_init_failed", reason="setup", error=str(exc))
        return 1


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Idempotent bootstrap for LangGraph PostgreSQL checkpoint tables. "
            "Invokes AsyncPostgresSaver.setup() from langgraph-checkpoint-postgres>=3.1."
        ),
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get("TIMESCALE_DSN"),
        help=(
            "PostgreSQL DSN. Defaults to $TIMESCALE_DSN environment variable. "
            "Example: postgresql://sft:sft_dev_pass@localhost:5432/sft"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log intent and exit 0 without connecting to the database.",
    )
    args = parser.parse_args()

    if not args.dsn and not args.dry_run:
        print(
            "ERROR: --dsn is required (or set $TIMESCALE_DSN env var).",
            file=sys.stderr,
        )
        sys.exit(1)

    dsn = args.dsn if args.dsn else "postgresql://dry-run:dry-run@localhost:5432/dry-run"

    # structlog: render JSON to stdout in production-style format
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
    )

    sys.exit(asyncio.run(bootstrap(dsn, args.dry_run)))


if __name__ == "__main__":
    main()
