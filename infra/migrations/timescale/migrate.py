#!/usr/bin/env python3
"""
infra/migrations/timescale/migrate.py

Idempotent TimescaleDB migration runner using asyncpg.

Discovers all SQL migration files in the same directory matching the pattern
`NNN_<description>.sql` (three-digit prefix, sortable), executes them in
filename-sorted order against the given DSN.

Re-running is safe: all SQL statements use IF NOT EXISTS / DO block guards.

Exit codes:
    0 — All migrations applied (or dry-run completed successfully)
    1 — Connection error or SQL execution error
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# asyncpg is imported lazily inside migrate() to allow --dry-run without
# requiring asyncpg to be installed (dry-run never opens a DB connection).

_MIGRATIONS_DIR: Path = Path(__file__).parent


async def migrate(dsn: str, dry_run: bool = False) -> int:
    """Apply all SQL migration files in sorted order.

    Parameters
    ----------
    dsn:
        PostgreSQL connection string, e.g.
        ``postgresql://sft:sft_dev_pass@timescaledb:5432/sft``.
    dry_run:
        When True, print the migration files that would be executed without
        opening a database connection.  Returns 0.

    Returns
    -------
    int
        0 on success, 1 on error.
    """
    migration_files = sorted(_MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql"))

    if not migration_files:
        print("No migration files found in", _MIGRATIONS_DIR, file=sys.stderr)
        return 1

    if dry_run:
        print("[dry-run] Migration files that would be applied:")
        for f in migration_files:
            print(f"  {f.name}")
        return 0

    # Lazy import: asyncpg is only required when connecting to the database.
    # Dry-run mode above exits before reaching this import.
    import asyncpg  # noqa: PLC0415

    # statement_cache_size=0 is mandatory for TimescaleDB connections (Pitfall 6):
    # TimescaleDB uses dynamic plan optimization; stale cached plans cause errors on DDL.
    # command_timeout=60s because DDL (CREATE TABLE, add policies) can be slow on first run.
    try:
        conn: asyncpg.Connection = await asyncpg.connect(
            dsn,
            statement_cache_size=0,
            command_timeout=60.0,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to connect to TimescaleDB: {exc}", file=sys.stderr)
        return 1

    try:
        for migration_file in migration_files:
            sql = migration_file.read_text(encoding="utf-8")
            try:
                await conn.execute(sql)
                print(f"OK [{migration_file.name}]: applied")
            except asyncpg.PostgresError as exc:
                print(
                    f"ERROR [{migration_file.name}]: SQL execution failed: {exc}",
                    file=sys.stderr,
                )
                return 1
    finally:
        await conn.close()

    return 0


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description=(
            "Apply TimescaleDB migrations in infra/migrations/timescale/. "
            "All SQL files are idempotent (safe to re-run)."
        ),
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get("TIMESCALE_DSN"),
        help=(
            "PostgreSQL DSN, e.g. postgresql://sft:pass@localhost:5432/sft. "
            "Defaults to $TIMESCALE_DSN env var."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print migration files that would be applied without connecting to the DB.",
    )
    args = parser.parse_args()

    if not args.dsn and not args.dry_run:
        print(
            "ERROR: --dsn is required (or set $TIMESCALE_DSN env var).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Provide a dummy DSN for dry-run so migrate() does not complain about None
    dsn = args.dsn if args.dsn else "postgresql://dry-run:dry-run@localhost:5432/dry-run"
    sys.exit(asyncio.run(migrate(dsn, args.dry_run)))


if __name__ == "__main__":
    main()
