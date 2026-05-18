#!/usr/bin/env python3
"""
scripts/validate-glossary-schema.py

Validates packages/sft-domain/src/sft_domain/glossary/it.yaml and en.yaml against
the JSON Schema Draft 2020-12 definition in
packages/sft-domain/src/sft_domain/schemas/glossary.schema.json.

Implements D-29 (dual-channel YAML + MkDocs render) schema enforcement and T-02-27
(yaml.safe_load mandatory — CWE-502 prevention).

Additional constraints beyond JSON Schema:
  - Top-level YAML must be a list
  - `term` field must be unique per language (case-insensitive)

Uses yaml.safe_load exclusively (never yaml.load or Loader= parameter).

Usage:
    python3 scripts/validate-glossary-schema.py [--glossary-dir PATH] [--schema-file PATH]

Exit codes:
    0 - Both it.yaml and en.yaml are schema-valid with unique terms
    1 - One or more validation errors (schema violations or duplicate terms)
"""
import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema.validators import Draft202012Validator

WORKSPACE_ROOT = Path(__file__).parent.parent

_DEFAULT_GLOSSARY_DIR = Path("packages/sft-domain/src/sft_domain/glossary")
_DEFAULT_SCHEMA_FILE = Path(
    "packages/sft-domain/src/sft_domain/schemas/glossary.schema.json"
)


def validate_language(
    yaml_path: Path,
    validator: Draft202012Validator,
    lang: str,
) -> tuple[bool, int]:
    """Validate a single glossary YAML file.

    Returns (success, term_count).
    Prints errors to stderr.
    """
    errors: list[str] = []

    if not yaml_path.exists():
        print(
            f"ERROR: glossary file not found: {yaml_path.relative_to(WORKSPACE_ROOT)}",
            file=sys.stderr,
        )
        print(
            "Fix: ensure the glossary YAML file exists (run Plan 02-01 to bootstrap).",
            file=sys.stderr,
        )
        return False, 0

    try:
        with yaml_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)  # SEMPRE safe_load, mai yaml.load
    except yaml.YAMLError as exc:
        print(
            f"ERROR: cannot parse {yaml_path.relative_to(WORKSPACE_ROOT)}: {exc}",
            file=sys.stderr,
        )
        print("Fix: correct the YAML syntax error shown above.", file=sys.stderr)
        return False, 0

    # --- Top-level structure ---
    if not isinstance(data, list):
        print(
            f"ERROR: {yaml_path.relative_to(WORKSPACE_ROOT)} must be a YAML list at "
            f"top level, got {type(data).__name__}.",
            file=sys.stderr,
        )
        print(
            "Fix: ensure the file starts with `- term: ...` (list of mapping entries).",
            file=sys.stderr,
        )
        return False, 0

    if len(data) == 0:
        print(
            f"ERROR: {yaml_path.relative_to(WORKSPACE_ROOT)} is empty (0 terms).",
            file=sys.stderr,
        )
        print("Fix: add at least one glossary term entry.", file=sys.stderr)
        return False, 0

    # --- Per-entry schema validation ---
    for idx, entry in enumerate(data):
        entry_term = (
            entry.get("term", f"<entry #{idx + 1}>")
            if isinstance(entry, dict)
            else f"<entry #{idx + 1}>"
        )
        for schema_error in sorted(
            validator.iter_errors(entry), key=lambda e: list(e.path)
        ):
            field_path = (
                " -> ".join(str(p) for p in schema_error.path)
                if schema_error.path
                else "(root)"
            )
            errors.append(
                f"  [{lang}: '{entry_term}'] field '{field_path}': {schema_error.message}\n"
                f"    Fix: correct the value for field '{field_path}' in "
                f"{yaml_path.relative_to(WORKSPACE_ROOT)} entry '{entry_term}'."
            )

    # --- Term uniqueness (case-insensitive) ---
    term_values: list[str] = []
    for entry in data:
        if isinstance(entry, dict) and "term" in entry:
            term_values.append(str(entry["term"]).lower())

    seen: set[str] = set()
    duplicates: list[str] = []
    for term_lower in term_values:
        if term_lower in seen:
            duplicates.append(term_lower)
        seen.add(term_lower)

    for dup in sorted(set(duplicates)):
        errors.append(
            f"  [{lang}] Duplicate term '{dup}' (case-insensitive) found more than once.\n"
            f"    Fix: ensure each term appears exactly once in "
            f"{yaml_path.relative_to(WORKSPACE_ROOT)}."
        )

    # --- Report ---
    if errors:
        print(
            f"\nValidation FAILED for {yaml_path.relative_to(WORKSPACE_ROOT)} "
            f"({len(errors)} error(s)):",
            file=sys.stderr,
        )
        for err in errors:
            print(err, file=sys.stderr)
        return False, len(data)

    return True, len(data)


def validate(glossary_dir: Path, schema_file: Path) -> bool:
    """Validate both it.yaml and en.yaml against the glossary schema.

    Returns True if both files are valid, False otherwise.
    """
    # --- Load schema ---
    if not schema_file.exists():
        print(
            f"ERROR: schema file not found: {schema_file.relative_to(WORKSPACE_ROOT)}",
            file=sys.stderr,
        )
        print(
            "Fix: run `git status` to confirm Plan 02-01 schema artifacts are committed.",
            file=sys.stderr,
        )
        return False

    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read schema file: {exc}", file=sys.stderr)
        return False

    validator = Draft202012Validator(schema)

    all_ok = True
    total_it = 0
    total_en = 0

    # Validate IT glossary
    it_path = glossary_dir / "it.yaml"
    ok_it, total_it = validate_language(it_path, validator, "it")
    if not ok_it:
        all_ok = False

    # Validate EN glossary
    en_path = glossary_dir / "en.yaml"
    ok_en, total_en = validate_language(en_path, validator, "en")
    if not ok_en:
        all_ok = False

    if all_ok:
        print(
            f"OK: validated {total_it} IT terms + {total_en} EN terms "
            f"in {glossary_dir.relative_to(WORKSPACE_ROOT)}."
        )

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate it.yaml and en.yaml glossary files against the glossary JSON Schema "
            "(Draft 2020-12). Checks schema validity and term uniqueness per language."
        ),
        epilog=(
            "Schema source: packages/sft-domain/src/sft_domain/schemas/glossary.schema.json "
            "(D-29). Run after editing glossary YAML files."
        ),
    )
    parser.add_argument(
        "--glossary-dir",
        type=Path,
        default=_DEFAULT_GLOSSARY_DIR,
        help=(
            f"Path to the glossary directory containing it.yaml and en.yaml "
            f"(default: {_DEFAULT_GLOSSARY_DIR})"
        ),
    )
    parser.add_argument(
        "--schema-file",
        type=Path,
        default=_DEFAULT_SCHEMA_FILE,
        help=(
            f"Path to the JSON Schema file for glossary entries "
            f"(default: {_DEFAULT_SCHEMA_FILE})"
        ),
    )
    args = parser.parse_args()

    glossary_dir = (
        WORKSPACE_ROOT / args.glossary_dir
        if not args.glossary_dir.is_absolute()
        else args.glossary_dir
    )
    schema_file = (
        WORKSPACE_ROOT / args.schema_file
        if not args.schema_file.is_absolute()
        else args.schema_file
    )

    success = validate(glossary_dir=glossary_dir, schema_file=schema_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
