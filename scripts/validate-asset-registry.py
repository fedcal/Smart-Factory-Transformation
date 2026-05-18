#!/usr/bin/env python3
"""
scripts/validate-asset-registry.py

Validates packages/sft-assets/src/sft_assets/registry.yaml against
the JSON Schema Draft 2020-12 definition in
packages/sft-assets/src/sft_assets/schemas/asset.schema.json.

Implements D-45 (asset registry schema enforcement) and T-03-01-yaml
(yaml.safe_load mandatory — CWE-502 prevention), T-03-01-asset (asset_id uniqueness).

Additional constraints beyond JSON Schema:
  - Top-level YAML must be a list
  - `asset_id` field must be unique (case-sensitive)

Uses yaml.safe_load exclusively (never yaml.load or Loader= parameter).

Usage:
    python3 scripts/validate-asset-registry.py [--registry PATH] [--schema PATH] [--dry-run]

Exit codes:
    0 - registry.yaml is schema-valid with unique asset_ids (or dry-run completed)
    1 - One or more validation errors (schema violations or duplicate asset_ids)
"""
import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema.validators import Draft202012Validator

WORKSPACE_ROOT = Path(__file__).parent.parent

_DEFAULT_REGISTRY = Path(
    "packages/sft-assets/src/sft_assets/registry.yaml"
)
_DEFAULT_SCHEMA = Path(
    "packages/sft-assets/src/sft_assets/schemas/asset.schema.json"
)


def validate_registry(
    registry_path: Path,
    schema_file: Path,
    *,
    dry_run: bool = False,
) -> bool:
    """Validate registry.yaml against asset.schema.json.

    Returns True if the registry is valid, False otherwise.
    Prints errors to stderr. Prints OK summary to stdout.
    """
    if dry_run:
        print(
            f"[dry-run] Would validate {registry_path.relative_to(WORKSPACE_ROOT)} "
            f"against {schema_file.relative_to(WORKSPACE_ROOT)}"
        )
        return True

    # --- Load schema ---
    if not schema_file.exists():
        print(
            f"ERROR: schema file not found: {schema_file.relative_to(WORKSPACE_ROOT)}",
            file=sys.stderr,
        )
        print(
            "Fix: run Task 1 of Phase 3 Plan 01 to generate asset.schema.json.",
            file=sys.stderr,
        )
        return False

    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot read schema file: {exc}", file=sys.stderr)
        return False

    validator = Draft202012Validator(schema)

    # --- Load registry ---
    if not registry_path.exists():
        print(
            f"ERROR: registry file not found: {registry_path.relative_to(WORKSPACE_ROOT)}",
            file=sys.stderr,
        )
        print(
            "Fix: ensure registry.yaml exists at the expected path.",
            file=sys.stderr,
        )
        return False

    try:
        with registry_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)  # SEMPRE safe_load, mai yaml.load (T-03-01-yaml)
    except yaml.YAMLError as exc:
        print(
            f"ERROR: cannot parse {registry_path.relative_to(WORKSPACE_ROOT)}: {exc}",
            file=sys.stderr,
        )
        print("Fix: correct the YAML syntax error shown above.", file=sys.stderr)
        return False

    # --- Top-level structure ---
    if not isinstance(data, list):
        print(
            f"ERROR: {registry_path.relative_to(WORKSPACE_ROOT)} must be a YAML list at "
            f"top level, got {type(data).__name__}.",
            file=sys.stderr,
        )
        print(
            "Fix: ensure the file starts with `- asset_id: ...` (list of mapping entries).",
            file=sys.stderr,
        )
        return False

    if len(data) == 0:
        print(
            f"ERROR: {registry_path.relative_to(WORKSPACE_ROOT)} is empty (0 assets).",
            file=sys.stderr,
        )
        print("Fix: add at least one asset entry.", file=sys.stderr)
        return False

    errors: list[str] = []

    # --- Per-entry schema validation ---
    for idx, entry in enumerate(data):
        asset_id = (
            entry.get("asset_id", f"<entry #{idx + 1}>")
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
                f"  [asset '{asset_id}'] field '{field_path}': {schema_error.message}\n"
                f"    Fix: correct the value for field '{field_path}' in "
                f"{registry_path.relative_to(WORKSPACE_ROOT)} entry '{asset_id}'."
            )

    # --- asset_id uniqueness (case-sensitive, T-03-01-asset) ---
    asset_ids: list[str] = []
    id_positions: dict[str, list[int]] = {}
    for idx, entry in enumerate(data):
        if isinstance(entry, dict) and "asset_id" in entry:
            aid = str(entry["asset_id"])
            asset_ids.append(aid)
            id_positions.setdefault(aid, []).append(idx + 1)

    for aid, positions in id_positions.items():
        if len(positions) > 1:
            errors.append(
                f"  [REGISTRY] duplicate asset_id '{aid}' at entries {positions}.\n"
                f"    Fix: ensure each asset_id appears exactly once in "
                f"{registry_path.relative_to(WORKSPACE_ROOT)}."
            )

    # --- Report ---
    if errors:
        print(
            f"\nValidation FAILED for {registry_path.relative_to(WORKSPACE_ROOT)} "
            f"({len(errors)} error(s)):",
            file=sys.stderr,
        )
        for err in errors:
            print(err, file=sys.stderr)
        return False

    print(
        f"OK [{registry_path.relative_to(WORKSPACE_ROOT)}]: {len(data)} assets valid"
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate registry.yaml asset file against asset.schema.json "
            "(Draft 2020-12). Checks schema validity and asset_id uniqueness."
        ),
        epilog=(
            "Schema source: packages/sft-assets/src/sft_assets/schemas/asset.schema.json "
            "(D-45). Run after editing registry.yaml."
        ),
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=_DEFAULT_REGISTRY,
        help=(
            f"Path to the registry YAML file "
            f"(default: {_DEFAULT_REGISTRY})"
        ),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=_DEFAULT_SCHEMA,
        help=(
            f"Path to the JSON Schema file for asset entries "
            f"(default: {_DEFAULT_SCHEMA})"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be validated without actually loading files. Exit 0.",
    )
    args = parser.parse_args()

    registry_path = (
        WORKSPACE_ROOT / args.registry
        if not args.registry.is_absolute()
        else args.registry
    )
    schema_file = (
        WORKSPACE_ROOT / args.schema
        if not args.schema.is_absolute()
        else args.schema
    )

    success = validate_registry(registry_path, schema_file, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
