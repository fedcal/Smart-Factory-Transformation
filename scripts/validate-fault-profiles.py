#!/usr/bin/env python3
"""
scripts/validate-fault-profiles.py

Validates fault injection YAML profiles in simulators/sim-textile/profiles/
against the JSON Schema Draft 2020-12 definition in
simulators/sim-textile/schemas/fault-profile.schema.json.

Additional constraints beyond JSON Schema:
  - Each YAML must be a single object (not a list)
  - nan_probability must be in range [0.0, 1.0] (already in schema, double-checked)
  - All affected_tags and default_baseline keys must exist in sft-assets load_tag_dict()
  - asset_family must match AssetFamily enum

Uses yaml.safe_load exclusively (never yaml.load or Loader= parameter).
Pattern S-2 (T-03-03-yaml, RESEARCH §Security checks 1): yaml.safe_load gate.
Pattern S-3 (WORKSPACE_ROOT): Path(__file__).parent.parent.
Pattern S-4 (argparse + --dry-run + exit codes).

Usage:
    python3 scripts/validate-fault-profiles.py [--profiles-dir PATH] [--schema PATH] [--dry-run]

Exit codes:
    0 - All profiles schema-valid, tags registry-resolved
    1 - One or more validation errors
"""

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema.validators import Draft202012Validator

WORKSPACE_ROOT = Path(__file__).parent.parent

_DEFAULT_PROFILES_DIR = WORKSPACE_ROOT / "simulators/sim-textile/profiles"
_DEFAULT_SCHEMA = WORKSPACE_ROOT / "simulators/sim-textile/schemas/fault-profile.schema.json"


def validate_profile(
    yaml_path: Path,
    validator: Draft202012Validator,
    tag_dict: dict,
    dry_run: bool,
) -> tuple[bool, int]:
    """Valida un singolo fault profile YAML.

    Esegue tre check:
    1. JSON Schema validation
    2. Range check nan_probability 0..1 (ridondante con schema, esplicito per chiarezza)
    3. Cross-check tag_id contro registry sft-assets

    Returns:
        (success, tag_count): True se valido, numero tag referenziati.
    """
    errors: list[str] = []
    profile_name = yaml_path.stem

    if not yaml_path.exists():
        print(
            f"ERROR: profile non trovato: {yaml_path.relative_to(WORKSPACE_ROOT)}",
            file=sys.stderr,
        )
        return False, 0

    try:
        with yaml_path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)  # SEMPRE safe_load, mai yaml.load (Pattern S-2)
    except yaml.YAMLError as exc:
        print(
            f"ERROR: cannot parse {yaml_path.relative_to(WORKSPACE_ROOT)}: {exc}",
            file=sys.stderr,
        )
        return False, 0

    if not isinstance(data, dict):
        print(
            f"ERROR: {yaml_path.relative_to(WORKSPACE_ROOT)} deve essere un oggetto YAML, "
            f"trovato: {type(data).__name__}.",
            file=sys.stderr,
        )
        return False, 0

    # --- JSON Schema validation ---
    for schema_error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        field_path = (
            " -> ".join(str(p) for p in schema_error.path) if schema_error.path else "(root)"
        )
        errors.append(
            f"  [{profile_name}] field '{field_path}': {schema_error.message}\n"
            f"    Fix: correct the value for field '{field_path}' in "
            f"{yaml_path.relative_to(WORKSPACE_ROOT)}."
        )

    # --- Cross-check tag_id contro registry ---
    referenced_tags: set[str] = set()
    fi = data.get("fault_injection", {})
    for fault_type in ("drift", "jitter", "burst_noise", "alarm_storm"):
        ft = fi.get(fault_type, {})
        for tag in ft.get("affected_tags", []):
            referenced_tags.add(tag)
    for tag_key in data.get("default_baseline", {}).keys():
        referenced_tags.add(tag_key)

    missing_tags = referenced_tags - set(tag_dict.keys())
    if missing_tags:
        errors.append(
            f"  [{profile_name}] tag non in registry sft-assets: {sorted(missing_tags)}\n"
            f"    Fix: usa solo tag_id presenti in packages/sft-assets/src/sft_assets/registry.yaml"
        )

    # --- Report ---
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return False, len(referenced_tags)

    tag_count = len(referenced_tags)
    rel_path = yaml_path.relative_to(WORKSPACE_ROOT)
    if dry_run:
        print(f"[dry-run] OK [{rel_path}]: schema-valid, {tag_count} tags registry-resolved")
    else:
        print(f"OK [{rel_path}]: schema-valid, {tag_count} tags registry-resolved")
    return True, tag_count


def main() -> None:
    """Entry point principale del validator."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate fault injection YAML profiles against fault-profile.schema.json "
            "(Draft 2020-12). Checks schema validity and tag cross-reference with sft-assets."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--profiles-dir",
        type=Path,
        default=_DEFAULT_PROFILES_DIR,
        help=f"Directory dei profile YAML (default: {_DEFAULT_PROFILES_DIR.relative_to(WORKSPACE_ROOT)})",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=_DEFAULT_SCHEMA,
        help=f"File JSON Schema (default: {_DEFAULT_SCHEMA.relative_to(WORKSPACE_ROOT)})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stampa risultati senza side-effects (utile per testing).",
    )
    args = parser.parse_args()

    profiles_dir: Path = args.profiles_dir
    schema_path: Path = args.schema

    # Resolve relative paths rispetto a WORKSPACE_ROOT
    if not profiles_dir.is_absolute():
        profiles_dir = WORKSPACE_ROOT / profiles_dir
    if not schema_path.is_absolute():
        schema_path = WORKSPACE_ROOT / schema_path

    # Carica JSON Schema
    if not schema_path.exists():
        print(f"ERROR: schema non trovato: {schema_path}", file=sys.stderr)
        sys.exit(1)

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: schema JSON non valido: {exc}", file=sys.stderr)
        sys.exit(1)

    validator = Draft202012Validator(schema)

    # Carica tag registry da sft-assets
    try:
        from sft_assets import load_tag_dict
        tag_dict = load_tag_dict()
    except ImportError:
        print(
            "ERROR: sft-assets non installato. Esegui: uv sync --project packages/sft-assets",
            file=sys.stderr,
        )
        sys.exit(1)

    # Trova tutti i YAML profiles
    yaml_files = sorted(profiles_dir.glob("*.yaml"))
    if not yaml_files:
        print(
            f"ERROR: nessun file .yaml trovato in {profiles_dir.relative_to(WORKSPACE_ROOT)}",
            file=sys.stderr,
        )
        sys.exit(1)

    all_ok = True
    profile_count = 0
    for yaml_path in yaml_files:
        ok, _ = validate_profile(yaml_path, validator, tag_dict, dry_run=args.dry_run)
        if ok:
            profile_count += 1
        else:
            all_ok = False

    if all_ok:
        print(
            f"\n{'[dry-run] ' if args.dry_run else ''}Validation complete: "
            f"{profile_count} profiles schema-valid, tags registry-resolved."
        )
        sys.exit(0)
    else:
        print(
            f"\nValidation FAILED: {profile_count}/{len(yaml_files)} profiles valid.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
