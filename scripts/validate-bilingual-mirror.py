#!/usr/bin/env python3
"""
scripts/validate-bilingual-mirror.py

Validates that every Markdown page under docs/docs/ (IT default) has a
corresponding mirror under docs/docs/en/ with matching heading structure.

Per D-24 and Claude's discretion (CONTEXT.md line 429-430):
  - Match: H1 heading + first 5 H2 headings (NOT body text — translations differ).
  - Heading count must also match (total H2 count must be equal).

Excluded directories: 'en', 'assets' (these are mirrors or static content).

--allow-missing-en mode: demotes missing EN mirrors from errors to warnings.
This flag is used during Plan 02-02/02-04 (IT-only phases). Drop it after
all EN pages are committed (Plan 02-05/02-06).

CONTRACT NOTE (Plan 02-05): Once this flag is dropped and all EN mirrors
exist, this script enforces the bilingual symmetry invariant permanently.

Graceful handling: if docs-dir does not exist or has no .md files, exits 0.

Usage:
    python3 scripts/validate-bilingual-mirror.py [--docs-dir PATH] [--allow-missing-en]

Exit codes:
    0 - All IT pages have matching EN mirrors (or --allow-missing-en, or no pages)
    1 - One or more mirror violations found
"""
import argparse
import re
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent

H1_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
H2_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

# Directories to exclude when scanning IT pages
EXCLUDE_DIRS = {"en", "assets"}

# Max H2 headings to compare between IT and EN (per CONTEXT.md Claude's discretion)
MAX_H2_COMPARE = 5


def extract_headings(md_path: Path) -> tuple[list[str], list[str]]:
    """
    Extract H1 headings and H2 headings from a Markdown file.

    Returns (h1_list, h2_list).
    """
    content = md_path.read_text(encoding="utf-8")
    h1_list = H1_PATTERN.findall(content)
    h2_list = H2_PATTERN.findall(content)
    return h1_list, h2_list


def validate(docs_dir: Path, allow_missing_en: bool) -> bool:
    """
    Validate bilingual mirror structure under docs_dir.

    Returns True if all IT pages have valid EN mirrors (or allow_missing_en), False otherwise.
    """
    # Resolve relative paths against workspace root
    if not docs_dir.is_absolute():
        docs_dir = WORKSPACE_ROOT / docs_dir

    if not docs_dir.exists():
        docs_rel = docs_dir.relative_to(WORKSPACE_ROOT) if docs_dir.is_relative_to(WORKSPACE_ROOT) else docs_dir
        print(f"OK: docs-dir does not exist: {docs_rel} — nothing to validate")
        return True

    en_dir = docs_dir / "en"

    # Collect all IT .md files (not under excluded dirs)
    it_pages: list[Path] = []
    for md_path in sorted(docs_dir.rglob("*.md")):
        # Check if any parent dir (relative to docs_dir) is in EXCLUDE_DIRS
        try:
            rel_parts = md_path.relative_to(docs_dir).parts
        except ValueError:
            continue
        if rel_parts[0] in EXCLUDE_DIRS:
            continue
        it_pages.append(md_path)

    if not it_pages:
        print(
            f"OK: no Markdown pages found under {docs_dir.relative_to(WORKSPACE_ROOT)} — nothing to validate"
        )
        return True

    errors: list[str] = []
    warnings: list[str] = []

    for it_path in it_pages:
        rel_to_docs = it_path.relative_to(docs_dir)
        en_path = en_dir / rel_to_docs
        rel_it = it_path.relative_to(WORKSPACE_ROOT)
        rel_en = en_path.relative_to(WORKSPACE_ROOT)

        # Check EN mirror exists
        if not en_path.exists():
            msg = (
                f"{rel_it}: EN mirror missing at {rel_en}"
            )
            if allow_missing_en:
                warnings.append(
                    f"WARNING: {msg} (use --allow-missing-en to suppress until EN is written)"
                )
            else:
                errors.append(
                    f"{rel_it}: MISSING EN MIRROR at {rel_en}\n"
                    f"    Fix: create {rel_en} with matching H1 + first {MAX_H2_COMPARE} H2 headings"
                )
            continue

        # Extract headings from both files
        it_h1, it_h2 = extract_headings(it_path)
        en_h1, en_h2 = extract_headings(en_path)

        # Compare H1 count
        if len(it_h1) != len(en_h1):
            errors.append(
                f"{rel_it} <-> {rel_en}: H1 COUNT MISMATCH — IT has {len(it_h1)}, EN has {len(en_h1)}\n"
                f"    Fix: ensure both files have the same number of H1 headings"
            )

        # Compare total H2 count
        if len(it_h2) != len(en_h2):
            errors.append(
                f"{rel_it} <-> {rel_en}: H2 COUNT MISMATCH — IT has {len(it_h2)}, EN has {len(en_h2)}\n"
                f"    Fix: ensure both files have the same number of ## sections"
            )

        # Compare first MAX_H2_COMPARE H2 headings (structure match, NOT text match)
        it_h2_slice = it_h2[:MAX_H2_COMPARE]
        en_h2_slice = en_h2[:MAX_H2_COMPARE]
        if len(it_h2_slice) != len(en_h2_slice):
            errors.append(
                f"{rel_it} <-> {rel_en}: H2 STRUCTURE MISMATCH in first {MAX_H2_COMPARE} headings — "
                f"IT: {it_h2_slice}, EN: {en_h2_slice}\n"
                f"    Fix: ensure IT and EN have the same first {MAX_H2_COMPARE} H2 sections"
            )

    # Emit warnings to stdout
    for w in warnings:
        print(w)

    if errors:
        print(
            f"FAILED: {len(errors)} bilingual mirror error(s) across {len(it_pages)} IT page(s):",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return False

    print(
        f"OK: {len(it_pages)} IT page(s) validated — "
        f"all have matching EN mirror structure"
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate bilingual mirror structure: docs/docs/*.md <-> docs/docs/en/*.md.",
        epilog=(
            "Checks H1 + first 5 H2 headings match (structure, not text — translations differ). "
            "Use --allow-missing-en during IT-only phases. "
            "Excluded dirs: en, assets."
        ),
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=WORKSPACE_ROOT / "docs" / "docs",
        help="Path to the IT docs root directory (default: docs/docs)",
    )
    parser.add_argument(
        "--allow-missing-en",
        action="store_true",
        help=(
            "Demote missing EN mirrors from errors to warnings. "
            "Use during IT-only phases. Drop after EN pages are committed."
        ),
    )
    args = parser.parse_args()

    success = validate(args.docs_dir, args.allow_missing_en)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
