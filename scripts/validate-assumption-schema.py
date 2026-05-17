#!/usr/bin/env python3
"""
scripts/validate-assumption-schema.py

Validates every entry in docs/assumptions/register.yaml against the JSON Schema
Draft 2020-12 definition in packages/sft-domain/src/sft_domain/schemas/assumption.schema.json.

Implements D-33 (YAML structured assumption register) and D-35 (schema-enforced living doc).
Each entry is individually validated; all errors are accumulated and reported grouped at the
end to stderr with a Fix: suggestion for each violation.

Additional constraints beyond JSON Schema:
  - All ids match the pattern ^A-[0-9]{3}$ (enforced by schema)
  - All ids are unique (no duplicate A-NNN)
  - Ids form a contiguous range starting at A-001 (no gaps)

Usage:
    python3 scripts/validate-assumption-schema.py [--register-file PATH] [--schema-file PATH]

Exit codes:
    0 - All entries are schema-valid, ids unique, and range contiguous
    1 - One or more validation errors (schema violations, duplicate ids, gaps in range)
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema.validators import Draft202012Validator

WORKSPACE_ROOT = Path(__file__).parent.parent

_DEFAULT_REGISTER = Path("docs/assumptions/register.yaml")
_DEFAULT_SCHEMA = Path(
    "packages/sft-domain/src/sft_domain/schemas/assumption.schema.json"
)


def validate(
    register_file: Path,
    schema_file: Path,
) -> bool:
    """
    Load and validate register_file against schema_file.

    Returns True if all entries are valid and ids are unique + contiguous.
    Returns False (after printing grouped errors to stderr) if any violation found.
    """
    errors: list[str] = []

    # --- Load schema ---
    if not schema_file.exists():
        print(
            f"ERROR: schema file not found: {schema_file.relative_to(WORKSPACE_ROOT)}",
            file=sys.stderr,
        )
        print("Fix: run `git status` to confirm Plan 02-01 artifacts are committed.", file=sys.stderr)
        return False

    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read schema file: {exc}", file=sys.stderr)
        return False

    validator = Draft202012Validator(schema)

    # --- Load register ---
    if not register_file.exists():
        print(
            f"ERROR: register file not found: {register_file.relative_to(WORKSPACE_ROOT)}",
            file=sys.stderr,
        )
        print(
            "Fix: create docs/assumptions/register.yaml with at least one entry.",
            file=sys.stderr,
        )
        return False

    try:
        with register_file.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        print(
            f"ERROR: cannot parse {register_file.relative_to(WORKSPACE_ROOT)}: {exc}",
            file=sys.stderr,
        )
        print("Fix: correct the YAML syntax error shown above.", file=sys.stderr)
        return False

    # --- Top-level structure ---
    if not isinstance(data, list):
        print(
            f"ERROR: {register_file.relative_to(WORKSPACE_ROOT)} must be a YAML list at top level, got {type(data).__name__}.",
            file=sys.stderr,
        )
        print(
            "Fix: ensure the file starts with `- id: A-001` (list of mapping entries).",
            file=sys.stderr,
        )
        return False

    if len(data) == 0:
        print(
            f"ERROR: {register_file.relative_to(WORKSPACE_ROOT)} is empty (0 entries).",
            file=sys.stderr,
        )
        print("Fix: add at least one assumption entry.", file=sys.stderr)
        return False

    # --- Per-entry schema validation ---
    for idx, entry in enumerate(data):
        entry_id = entry.get("id", f"<entry #{idx + 1}>") if isinstance(entry, dict) else f"<entry #{idx + 1}>"
        for schema_error in sorted(validator.iter_errors(entry), key=lambda e: list(e.path)):
            field_path = " -> ".join(str(p) for p in schema_error.path) if schema_error.path else "(root)"
            errors.append(
                f"  [{entry_id}] field '{field_path}': {schema_error.message}\n"
                f"    Fix: correct the value for field '{field_path}' in "
                f"{register_file.relative_to(WORKSPACE_ROOT)} entry {entry_id}."
            )

    # --- Id uniqueness ---
    id_values: list[str] = []
    for entry in data:
        if isinstance(entry, dict) and "id" in entry:
            id_values.append(str(entry["id"]))

    seen: set[str] = set()
    duplicates: list[str] = []
    for entry_id in id_values:
        if entry_id in seen:
            duplicates.append(entry_id)
        seen.add(entry_id)

    for dup in sorted(set(duplicates)):
        errors.append(
            f"  Duplicate id '{dup}' found more than once.\n"
            f"    Fix: ensure each id appears exactly once in {register_file.relative_to(WORKSPACE_ROOT)}."
        )

    # --- Id pattern + contiguous range from A-001 ---
    id_pattern = re.compile(r"^A-([0-9]{3})$")
    valid_ids: list[int] = []
    for entry_id in id_values:
        match = id_pattern.match(entry_id)
        if match:
            valid_ids.append(int(match.group(1)))

    if valid_ids:
        valid_ids_sorted = sorted(valid_ids)
        expected = list(range(1, len(valid_ids_sorted) + 1))
        if valid_ids_sorted != expected:
            missing = sorted(set(expected) - set(valid_ids_sorted))
            extra = sorted(set(valid_ids_sorted) - set(expected))
            if missing:
                errors.append(
                    f"  Id range gap: ids {[f'A-{n:03d}' for n in missing]} are missing.\n"
                    f"    Fix: add entries for {[f'A-{n:03d}' for n in missing]} or renumber the register to fill the gap."
                )
            if extra:
                errors.append(
                    f"  Id range has unexpected entries {[f'A-{n:03d}' for n in extra]} "
                    f"(expected contiguous range A-001..A-{len(valid_ids_sorted):03d}).\n"
                    f"    Fix: renumber entries so they form a contiguous range starting at A-001."
                )

    # --- Report ---
    if errors:
        print(
            f"\nValidation FAILED for {register_file.relative_to(WORKSPACE_ROOT)} "
            f"({len(errors)} error(s)):",
            file=sys.stderr,
        )
        for err in errors:
            print(err, file=sys.stderr)
        return False

    print(f"OK: validated {len(data)} entries in {register_file.relative_to(WORKSPACE_ROOT)}.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate docs/assumptions/register.yaml against the assumption JSON Schema "
            "(Draft 2020-12). Checks schema validity, id uniqueness, and contiguous id range."
        ),
        epilog=(
            "Schema source: packages/sft-domain/src/sft_domain/schemas/assumption.schema.json "
            "(D-33/D-35). Run after editing register.yaml or adding new entries."
        ),
    )
    parser.add_argument(
        "--register-file",
        type=Path,
        default=_DEFAULT_REGISTER,
        help=(
            f"Path to the assumption register YAML file "
            f"(default: {_DEFAULT_REGISTER})"
        ),
    )
    parser.add_argument(
        "--schema-file",
        type=Path,
        default=_DEFAULT_SCHEMA,
        help=(
            f"Path to the JSON Schema file for assumption entries "
            f"(default: {_DEFAULT_SCHEMA})"
        ),
    )
    args = parser.parse_args()

    success = validate(
        register_file=WORKSPACE_ROOT / args.register_file
        if not args.register_file.is_absolute()
        else args.register_file,
        schema_file=WORKSPACE_ROOT / args.schema_file
        if not args.schema_file.is_absolute()
        else args.schema_file,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
