#!/usr/bin/env python3
"""
scripts/timescale-migrate.py

Top-level CLI wrapper for the TimescaleDB migration runner.
Invokes ``infra/migrations/timescale/migrate.py`` with env + argparse configuration.

This script follows the same structure as ``scripts/sync-python-versions.py`` (Pattern S-3):
  - WORKSPACE_ROOT derived from __file__
  - argparse with --dry-run and --dsn
  - sys.path.insert(0, WORKSPACE_ROOT) for workspace-relative imports
  - Exit codes 0 (success) / 1 (error)

Usage:
    python3 scripts/timescale-migrate.py [--dry-run] [--dsn DSN]

    # With env var (typical CI/dev usage):
    export TIMESCALE_DSN="postgresql://sft:sft_dev_pass@localhost:5432/sft"
    python3 scripts/timescale-migrate.py

    # Dry run to see what would be applied:
    python3 scripts/timescale-migrate.py --dry-run

Exit codes:
    0 — All migrations applied (or dry-run completed)
    1 — Connection error, SQL error, or missing DSN
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent

# Insert workspace root so that `infra.migrations.timescale.migrate` is importable
# regardless of the caller's PYTHONPATH / working directory.
sys.path.insert(0, str(WORKSPACE_ROOT))

from infra.migrations.timescale.migrate import migrate  # noqa: E402


def main() -> None:
    """Parse CLI arguments and delegate to the migration runner."""
    parser = argparse.ArgumentParser(
        description=(
            "Apply TimescaleDB migrations from infra/migrations/timescale/. "
            "All SQL files are idempotent: safe to re-run. "
            "Reads TIMESCALE_DSN from environment by default."
        ),
    )
    parser.add_argument(
        "--dsn",
        default=os.environ.get("TIMESCALE_DSN"),
        help=(
            "PostgreSQL DSN, e.g. postgresql://sft:pass@localhost:5432/sft. "
            "Defaults to $TIMESCALE_DSN environment variable."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print the migration files that would be applied without connecting "
            "to the database.  Exits 0."
        ),
    )
    parser.add_argument(
        "--migrations-dir",
        default=str(WORKSPACE_ROOT / "infra" / "migrations" / "timescale"),
        help=(
            "Override the migrations directory (default: "
            "WORKSPACE_ROOT/infra/migrations/timescale)."
        ),
    )
    args = parser.parse_args()

    if not args.dsn and not args.dry_run:
        print(
            "ERROR: --dsn is required (or set $TIMESCALE_DSN).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Provide dummy DSN for dry-run (migrate() will not connect)
    dsn = args.dsn if args.dsn else "postgresql://dry-run:dry-run@localhost:5432/dry-run"
    sys.exit(asyncio.run(migrate(dsn, args.dry_run)))


if __name__ == "__main__":
    main()
