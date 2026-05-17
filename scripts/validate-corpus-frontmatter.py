#!/usr/bin/env python3
"""
scripts/validate-corpus-frontmatter.py

Validates YAML frontmatter and required H2 section structure of every SOP Markdown
file under simulators/synthetic-corpus/.

Checks performed per file:
  1. Frontmatter is present and parses as valid YAML.
  2. Frontmatter validates against packages/sft-domain/src/sft_domain/schemas/sop.schema.json
     using JSON Schema Draft 2020-12.
  3. H2 sections exist in exactly the fixed order required by D-26:
     Scope, Prerequisites, Tools and PPE, Step-by-step Procedure,
     Verification, Troubleshooting, References.
  4. Filename matches the convention ^SOP-[A-Z]+-[0-9]{3}-[a-z0-9-]+-(it|en)\\.md$
     and the lang suffix matches the frontmatter `lang` field (Pitfall 7 mitigation).

Graceful empty-corpus handling: if no *.md files are found under corpus-dir,
exits 0 with a notice message (safe to run before content is written).

Usage:
    python3 scripts/validate-corpus-frontmatter.py [--corpus-dir PATH] [--schema-file PATH]

Exit codes:
    0 - All SOPs valid (or corpus-dir is empty)
    1 - One or more validation errors found
"""
import argparse
import json
import re
import sys
from pathlib import Path

import frontmatter
import yaml  # noqa: F401  (imported to confirm safe_load is available)
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

WORKSPACE_ROOT = Path(__file__).parent.parent

REQUIRED_H2_SECTIONS = [
    "Scope",
    "Prerequisites",
    "Tools and PPE",
    "Step-by-step Procedure",
    "Verification",
    "Troubleshooting",
    "References",
]

H2_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

# Filename must match SOP-<ALPHA>-<NNN>-<slug>-<lang>.md
FILENAME_PATTERN = re.compile(r"^SOP-[A-Z]+-[0-9]{3}-[a-z0-9-]+-(it|en)\.md$")


def load_schema(schema_file: Path) -> dict:
    """Load and return the JSON Schema from disk."""
    if not schema_file.exists():
        print(f"ERROR: Schema file not found: {schema_file}", file=sys.stderr)
        sys.exit(1)
    with schema_file.open() as f:
        return json.load(f)


def validate_file(md_path: Path, validator: Draft202012Validator, corpus_root: Path) -> list[str]:
    """
    Validate a single SOP Markdown file.

    Returns a list of error strings (empty list means file is valid).
    """
    errors: list[str] = []
    rel = md_path.relative_to(WORKSPACE_ROOT)

    # 1. Parse frontmatter
    try:
        post = frontmatter.load(str(md_path))
    except Exception as exc:
        errors.append(f"{rel}: ERROR parsing frontmatter: {exc}")
        return errors

    # 2. Schema validation
    schema_errors = list(validator.iter_errors(dict(post.metadata)))
    for err in schema_errors:
        field = ".".join(str(p) for p in err.absolute_path) if err.absolute_path else err.validator_value
        errors.append(
            f"{rel}: SCHEMA ERROR — {err.message} (field: {field})\n"
            f"    Fix: correct the frontmatter field to match sop.schema.json"
        )

    # 3. H2 section check
    content = post.content
    found_h2 = H2_PATTERN.findall(content)
    # Strip whitespace from found headings
    found_h2 = [h.strip() for h in found_h2]

    if found_h2 != REQUIRED_H2_SECTIONS:
        errors.append(
            f"{rel}: H2 SECTION ERROR\n"
            f"    Expected: {REQUIRED_H2_SECTIONS}\n"
            f"    Found:    {found_h2}\n"
            f"    Fix: ensure H2 sections appear in fixed order per D-26 — "
            f"missing: {[h for h in REQUIRED_H2_SECTIONS if h not in found_h2]}"
        )
        # Provide per-missing-section guidance
        for required in REQUIRED_H2_SECTIONS:
            if required not in found_h2:
                errors.append(
                    f"    Fix: add ## {required} section to {rel.name}"
                )

    # 4. Filename convention + lang suffix match
    filename = md_path.name
    if not FILENAME_PATTERN.match(filename):
        errors.append(
            f"{rel}: FILENAME ERROR — '{filename}' does not match "
            f"^SOP-[A-Z]+-[0-9]{{3}}-[a-z0-9-]+-(it|en).md$\n"
            f"    Fix: rename file to match convention e.g. SOP-LOOM-001-broken-end-it.md"
        )
    else:
        # Extract lang suffix from filename and compare to frontmatter lang
        lang_suffix = FILENAME_PATTERN.match(filename).group(1)  # type: ignore[union-attr]
        fm_lang = post.metadata.get("lang", "")
        if lang_suffix != fm_lang:
            errors.append(
                f"{rel}: LANG MISMATCH — filename suffix '{lang_suffix}' != "
                f"frontmatter lang '{fm_lang}'\n"
                f"    Fix: rename file so the lang suffix matches the 'lang' frontmatter field"
            )

    return errors


def validate(corpus_dir: Path, schema_file: Path) -> bool:
    """
    Validate all *.md files under corpus_dir.

    Returns True if all files pass (or corpus is empty), False otherwise.
    """
    # Resolve relative paths against workspace root
    if not corpus_dir.is_absolute():
        corpus_dir = WORKSPACE_ROOT / corpus_dir
    if not schema_file.is_absolute():
        schema_file = WORKSPACE_ROOT / schema_file

    if not corpus_dir.exists():
        corpus_rel = corpus_dir.relative_to(WORKSPACE_ROOT) if corpus_dir.is_relative_to(WORKSPACE_ROOT) else corpus_dir
        print(f"OK: no SOPs found yet (corpus-dir does not exist: {corpus_rel})")
        return True

    # Only process files matching the SOP naming convention (skip README.md, etc.)
    all_md = sorted(corpus_dir.rglob("*.md"))
    md_files = [f for f in all_md if FILENAME_PATTERN.match(f.name)]
    if not md_files:
        corpus_rel = corpus_dir.relative_to(WORKSPACE_ROOT) if corpus_dir.is_relative_to(WORKSPACE_ROOT) else corpus_dir
        print(f"OK: no SOPs found yet (corpus-dir empty: {corpus_rel})")
        return True

    schema = load_schema(schema_file)

    # Validate schema itself before using it
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        print(f"ERROR: Invalid JSON Schema in {schema_file}: {exc}", file=sys.stderr)
        return False

    validator = Draft202012Validator(schema)

    all_errors: list[str] = []
    for md_path in md_files:
        file_errors = validate_file(md_path, validator, corpus_dir)
        all_errors.extend(file_errors)

    if all_errors:
        print(f"FAILED: {len(all_errors)} validation error(s) in {len(md_files)} SOP(s):", file=sys.stderr)
        for err in all_errors:
            print(f"  {err}", file=sys.stderr)
        return False

    print(f"OK: validated {len(md_files)} SOP(s) — 0 errors")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate SOP frontmatter schema + required H2 sections in synthetic-corpus.",
        epilog="Run from workspace root. Schema defaults to packages/sft-domain/src/sft_domain/schemas/sop.schema.json.",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=WORKSPACE_ROOT / "simulators" / "synthetic-corpus",
        help="Path to the synthetic-corpus directory (default: simulators/synthetic-corpus)",
    )
    parser.add_argument(
        "--schema-file",
        type=Path,
        default=WORKSPACE_ROOT / "packages" / "sft-domain" / "src" / "sft_domain" / "schemas" / "sop.schema.json",
        help="Path to the SOP JSON Schema file (default: packages/sft-domain/src/sft_domain/schemas/sop.schema.json)",
    )
    args = parser.parse_args()

    success = validate(args.corpus_dir, args.schema_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
