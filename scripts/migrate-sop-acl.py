#!/usr/bin/env python3
"""
scripts/migrate-sop-acl.py

One-shot idempotent migration (Plan 05-02) that adds the `acl_level` field to
every SOP frontmatter under simulators/synthetic-corpus per the D-72
audience -> acl_level mapping.

Behavior:
  - Walks `--corpus-dir` (default: simulators/synthetic-corpus) and processes
    every Markdown file whose filename matches the standard SOP convention
    `SOP-<ALPHA>-<NNN>-<slug>-<lang>.md` (same filter used by
    scripts/validate-corpus-frontmatter.py to skip README.md, etc.).
  - For each SOP:
      * If `acl_level` is already present in frontmatter -> SKIPPED (idempotent).
      * Otherwise compute `acl_level` from the existing `audience` field via
        the D-72 mapping (unknown / missing audience -> 'internal' fallback).
      * Build a NEW metadata dict (NEVER mutate `post.metadata` in place — see
        coding-style.md immutability rule) and write back via
        `frontmatter.dumps(updated_post)`.
  - Prints a human-readable summary line `MIGRATED: N, SKIPPED: M, ERRORS: K`.
  - Exits 0 iff `ERRORS == 0`.

Re-running the script after a successful migration must be a no-op:
  `MIGRATED: 0, SKIPPED: <total>, ERRORS: 0`.

Usage:
    uv run python scripts/migrate-sop-acl.py [--dry-run] [--corpus-dir PATH]

Exit codes:
    0 - Migration completed (or dry-run completed) with zero errors.
    1 - One or more files failed to parse / write.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Literal

import frontmatter

WORKSPACE_ROOT = Path(__file__).parent.parent

# Filter pattern shared with scripts/validate-corpus-frontmatter.py — ensures
# README.md and other non-SOP markdown files are skipped.
FILENAME_PATTERN = re.compile(r"^SOP-[A-Z]+-[0-9]{3}-[a-z0-9-]+-(it|en)\.md$")

# D-72 LOCKED mapping (audience -> acl_level). Module-level constant: never
# mutated at runtime.
AUDIENCE_TO_ACL: dict[str, str] = {
    "operations": "public",
    "maintenance": "internal",
    "quality": "internal",
    "engineering": "internal",
    "management": "restricted",
    "safety": "restricted",
}

# Conservative fallback per D-72 — applied when `audience` is missing or
# carries an unknown value. Never "public" to avoid accidental over-sharing.
DEFAULT_ACL_FALLBACK = "internal"

MigrationResult = Literal["migrated", "skipped", "error"]


def map_audience_to_acl(audience: str | None) -> str:
    """Map an SOP audience value to its acl_level per D-72.

    Unknown or missing audience -> conservative 'internal' fallback to avoid
    accidental information disclosure.

    Args:
        audience: The audience string from SOP frontmatter, or None if absent.

    Returns:
        One of {"public", "internal", "restricted"}.
    """
    if audience is None:
        return DEFAULT_ACL_FALLBACK
    return AUDIENCE_TO_ACL.get(audience, DEFAULT_ACL_FALLBACK)


def migrate_file(path: Path, dry_run: bool) -> MigrationResult:
    """Add `acl_level` to a single SOP frontmatter file.

    Idempotent: if `acl_level` is already present, returns "skipped" and does
    not touch the file.

    Args:
        path: Path to the SOP markdown file.
        dry_run: If True, do not write any changes to disk.

    Returns:
        "migrated" - acl_level was added (or would be added in dry-run).
        "skipped"  - acl_level was already present; no change.
        "error"    - frontmatter could not be parsed.
    """
    try:
        post = frontmatter.load(str(path))
    except Exception as exc:  # noqa: BLE001 — surface any parser error uniformly
        print(f"ERROR: failed to parse {path}: {exc}", file=sys.stderr)
        return "error"

    if "acl_level" in post.metadata:
        return "skipped"

    audience = post.metadata.get("audience")
    mapped = map_audience_to_acl(audience)

    # Immutable update: build a NEW metadata dict, never mutate post.metadata.
    new_meta = {**post.metadata, "acl_level": mapped}
    updated_post = frontmatter.Post(post.content, **new_meta)

    if not dry_run:
        with open(path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(updated_post))
            # frontmatter.dumps does not add a trailing newline; preserve POSIX
            # newline-at-EOF convention to match existing corpus files.
            f.write("\n")

    return "migrated"


def _iter_sop_files(corpus_dir: Path):
    """Yield SOP markdown files under corpus_dir matching FILENAME_PATTERN."""
    for md in sorted(corpus_dir.rglob("*.md")):
        if FILENAME_PATTERN.match(md.name):
            yield md


def run(corpus_dir: Path, dry_run: bool) -> int:
    """Migrate every SOP under corpus_dir. Returns process exit code."""
    if not corpus_dir.is_absolute():
        corpus_dir = WORKSPACE_ROOT / corpus_dir

    if not corpus_dir.exists():
        print(
            f"ERROR: corpus-dir does not exist: {corpus_dir}",
            file=sys.stderr,
        )
        return 1

    migrated = 0
    skipped = 0
    errors = 0
    scanned = 0

    for md_path in _iter_sop_files(corpus_dir):
        scanned += 1
        result = migrate_file(md_path, dry_run=dry_run)
        if result == "migrated":
            migrated += 1
            rel = (
                md_path.relative_to(WORKSPACE_ROOT)
                if md_path.is_relative_to(WORKSPACE_ROOT)
                else md_path
            )
            action = "WOULD MIGRATE" if dry_run else "MIGRATED"
            print(f"{action}: {rel}")
        elif result == "skipped":
            skipped += 1
        else:
            errors += 1

    mode = "DRY-RUN" if dry_run else "APPLIED"
    print(
        f"\n[{mode}] SCANNED: {scanned}, MIGRATED: {migrated}, "
        f"SKIPPED: {skipped}, ERRORS: {errors}"
    )

    return 0 if errors == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Add acl_level to all SOP frontmatter under simulators/synthetic-corpus "
            "per D-72 audience -> acl_level mapping. Idempotent."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to disk.",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=WORKSPACE_ROOT / "simulators" / "synthetic-corpus",
        help="Path to the synthetic-corpus directory.",
    )
    args = parser.parse_args()

    exit_code = run(args.corpus_dir, dry_run=args.dry_run)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
