#!/usr/bin/env python3
"""
scripts/validate-assumption-components.py

Validates that every component name in `affected_components[]` of
docs/assumptions/register.yaml references either a known Nx project or a known
infrastructure service.

Implements D-34 (dual-axis tagging: category + affected_components validated against
inventory) and RESEARCH.md Pitfall 6.

The allowlist is built as the union of:
  1. Nx project names from `npx nx show projects --json` (or pre-generated tmp/nx-projects.json
     when --no-nx is passed).
  2. Short-form aliases derived from Nx project names by stripping common service prefixes
     (svc-, ops-, mnt-, trn-, scm-, sft-, ui-, sim-). These aliases map e.g.
     `svc-orchestrator` -> `orchestrator`, `ops-anomaly-detector` -> `anomaly-detector`.
  3. INFRA_SERVICES: hardcoded set of infrastructure service names that are NOT Nx projects
     but are valid component references (deployed via docker-compose.yml / Helm values).

NOTE: The INFRA_SERVICES set must be kept in sync with docker-compose.yml and Helm values
as new services are added to the stack. Review this list when adding a new infrastructure
service (vide D-34 + RESEARCH.md Pitfall 6, Phase 2).

Usage:
    python3 scripts/validate-assumption-components.py [--register-file PATH] [--no-nx]

    --no-nx: skip `npx nx show projects` and use tmp/nx-projects.json instead.
             Caller must ensure tmp/nx-projects.json is pre-populated:
               npx nx show projects --json > tmp/nx-projects.json

Exit codes:
    0 - All affected_components references are in the allowlist
    1 - One or more entries reference an unknown component name
"""
import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path

import yaml

WORKSPACE_ROOT = Path(__file__).parent.parent

_DEFAULT_REGISTER = Path("docs/assumptions/register.yaml")
_NX_PROJECTS_CACHE = Path("tmp/nx-projects.json")

# Infrastructure services known to this project that are NOT Nx-managed Python/TS projects.
# These are deployed via docker-compose.yml (dev) or Helm charts (k8s).
# Keep this list in sync with infrastructure changes (D-34, RESEARCH Pitfall 6).
INFRA_SERVICES: frozenset[str] = frozenset({
    "langfuse",
    "qdrant",
    "postgresql",
    "timescaledb",
    "nats",
    "redis",
    "ollama",
    "vllm",
    "clickhouse",
    "minio",
    "hitl-queue",
    "audit-stream",
    "k8s",
    "sealed-secrets",
    "helm",
    # Cross-cutting infra aliases
    "ot-bridge",       # svc-ot-bridge Nx project; alias kept here for robustness
    "orchestrator",    # svc-orchestrator Nx project; alias kept here for robustness
})

# Common prefixes in Nx project names that map to short component aliases.
# E.g. "svc-ot-bridge" -> "ot-bridge", "ops-anomaly-detector" -> "anomaly-detector".
_NX_PREFIX_STRIP = (
    "svc-",
    "ops-",
    "mnt-",
    "trn-",
    "scm-",
    "sft-",
    "ui-",
    "sim-",
    "app-",
)


def _derive_alias(nx_name: str) -> str | None:
    """Strip a known service prefix from an Nx project name to get a short alias."""
    for prefix in _NX_PREFIX_STRIP:
        if nx_name.startswith(prefix):
            return nx_name[len(prefix):]
    return None


def _load_nx_projects(no_nx: bool) -> tuple[set[str], str | None]:
    """
    Return (nx_project_set, error_message).

    If no_nx is True, reads from tmp/nx-projects.json.
    Otherwise runs `npx nx show projects --json`.
    """
    if no_nx:
        cache = WORKSPACE_ROOT / _NX_PROJECTS_CACHE
        if not cache.exists():
            return set(), (
                f"ERROR: --no-nx specified but {cache.relative_to(WORKSPACE_ROOT)} does not exist.\n"
                "Fix: run `npx nx show projects --json > tmp/nx-projects.json` first."
            )
        try:
            raw = cache.read_text(encoding="utf-8")
            data = json.loads(raw)
            return set(data), None
        except (json.JSONDecodeError, OSError) as exc:
            return set(), f"ERROR: cannot parse {_NX_PROJECTS_CACHE}: {exc}"

    # Live Nx query
    try:
        result = subprocess.run(
            ["npx", "nx", "show", "projects", "--json"],
            check=True,
            timeout=30,
            capture_output=True,
            text=True,
        )
        data = json.loads(result.stdout)
        return set(data), None
    except FileNotFoundError:
        return set(), (
            "ERROR: `npx` not found — Node.js/npm is not installed or not on PATH.\n"
            "Fix: install Node.js 20+ (see .nvmrc) or pass --no-nx and pre-generate "
            "tmp/nx-projects.json manually."
        )
    except subprocess.CalledProcessError as exc:
        return set(), (
            f"ERROR: `npx nx show projects --json` exited with code {exc.returncode}.\n"
            f"  stderr: {exc.stderr.strip()}\n"
            "Fix: run `npx nx show projects` to diagnose the Nx workspace issue."
        )
    except subprocess.TimeoutExpired:
        return set(), (
            "ERROR: `npx nx show projects --json` timed out after 30 seconds.\n"
            "Fix: check that the Nx daemon is responsive (`npx nx reset` to restart)."
        )
    except json.JSONDecodeError as exc:
        return set(), f"ERROR: cannot parse `npx nx show projects --json` output: {exc}"


def validate(register_file: Path, no_nx: bool = False) -> bool:
    """
    Build allowlist from Nx projects + INFRA_SERVICES, then validate every
    `affected_components` entry in register_file.

    Returns True on success, False on any validation error.
    """
    errors: list[str] = []

    # --- Build allowlist ---
    nx_projects, nx_error = _load_nx_projects(no_nx)
    if nx_error:
        print(nx_error, file=sys.stderr)
        return False

    # Derive short aliases from Nx project names
    aliases: set[str] = set()
    for nx_name in nx_projects:
        alias = _derive_alias(nx_name)
        if alias:
            aliases.add(alias)

    allowlist: set[str] = nx_projects | aliases | INFRA_SERVICES

    # --- Load register ---
    if not register_file.exists():
        print(
            f"ERROR: register file not found: {register_file.relative_to(WORKSPACE_ROOT)}",
            file=sys.stderr,
        )
        print(
            "Fix: create docs/assumptions/register.yaml or pass --register-file.",
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
        return False

    if not isinstance(data, list):
        print(
            f"ERROR: {register_file.relative_to(WORKSPACE_ROOT)} must be a list at top level.",
            file=sys.stderr,
        )
        return False

    # --- Validate each entry ---
    component_count = 0
    for entry in data:
        if not isinstance(entry, dict):
            continue
        entry_id = entry.get("id", "<unknown>")
        components = entry.get("affected_components", [])
        if not isinstance(components, list):
            errors.append(
                f"  [{entry_id}] affected_components is not a list (got {type(components).__name__}).\n"
                "    Fix: ensure affected_components is a YAML list."
            )
            continue
        for component in components:
            component_count += 1
            if component not in allowlist:
                close = difflib.get_close_matches(component, allowlist, n=3, cutoff=0.6)
                suggestion = f"Did you mean: {', '.join(close)}?" if close else "No close match found."
                errors.append(
                    f"  [{entry_id}] unknown component '{component}'. {suggestion}\n"
                    f"    Fix: use a name from the Nx project list or add '{component}' to "
                    "INFRA_SERVICES in scripts/validate-assumption-components.py if it is a "
                    "known infrastructure service."
                )

    # --- Report ---
    if errors:
        print(
            f"\nComponent validation FAILED for {register_file.relative_to(WORKSPACE_ROOT)} "
            f"({len(errors)} error(s)):",
            file=sys.stderr,
        )
        for err in errors:
            print(err, file=sys.stderr)
        return False

    nx_count = len(nx_projects)
    print(
        f"OK: all {component_count} component references valid "
        f"(allowlist: {nx_count} Nx projects + {len(aliases)} aliases + {len(INFRA_SERVICES)} infra services)."
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Cross-validate affected_components[] in docs/assumptions/register.yaml "
            "against the Nx project inventory and known infrastructure services. "
            "Implements D-34 (dual-axis tagging) and RESEARCH.md Pitfall 6."
        ),
        epilog=(
            "The allowlist = nx_projects U short_aliases U INFRA_SERVICES. "
            "Update INFRA_SERVICES in this script when new infra services are added."
        ),
    )
    parser.add_argument(
        "--register-file",
        type=Path,
        default=_DEFAULT_REGISTER,
        help=f"Path to the assumption register YAML (default: {_DEFAULT_REGISTER})",
    )
    parser.add_argument(
        "--no-nx",
        action="store_true",
        help=(
            "Skip `npx nx show projects` and read tmp/nx-projects.json instead. "
            "Use in CI environments where npx is unavailable after pre-generating the file."
        ),
    )
    args = parser.parse_args()

    register_path = (
        WORKSPACE_ROOT / args.register_file
        if not args.register_file.is_absolute()
        else args.register_file
    )

    success = validate(register_file=register_path, no_nx=args.no_nx)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
