#!/usr/bin/env python3
"""
scripts/validate-nx-graph.py

Validates that all required Python->TypeScript dependency edges are present
in the Nx dep graph JSON. Run after `nx graph --file=tmp/graph.json`.

Usage:
    nx graph --file=tmp/graph.json
    python3 scripts/validate-nx-graph.py [--graph-file PATH]

Exit codes:
    0 - All required edges are present
    1 - One or more required edges are missing
"""
import argparse
import json
import sys
from pathlib import Path

# Required edges: (source_project, target_project)
# These declare Python->TypeScript or Python->Python dependencies that Nx
# cannot infer automatically and must be set via implicitDependencies.
REQUIRED_EDGES = [
    ("ui-factory", "sft-contracts"),
    ("svc-api-gateway", "sft-contracts"),
    ("svc-api-gateway", "sft-agents"),
    ("svc-api-gateway", "sft-domain"),
    ("svc-orchestrator", "sft-agents"),
]


def validate(graph_file: Path) -> bool:
    """
    Parse the Nx graph JSON and check that all REQUIRED_EDGES are present.

    Returns True if all edges are found, False if any are missing.
    """
    if not graph_file.exists():
        print(f"ERROR: Graph file not found: {graph_file}", file=sys.stderr)
        print("Run: nx graph --file=tmp/graph.json", file=sys.stderr)
        return False

    with graph_file.open() as f:
        data = json.load(f)

    dependencies: dict = data.get("graph", {}).get("dependencies", {})

    missing: list[str] = []
    for source, target in REQUIRED_EDGES:
        targets = [d["target"] for d in dependencies.get(source, [])]
        if target not in targets:
            missing.append(f"  MISSING: {source} -> {target}")

    if missing:
        print("Dependency graph validation FAILED. Missing edges:")
        for m in missing:
            print(m)
        print(
            "\nFix: add the target to 'implicitDependencies' in the source project's project.json"
        )
        return False

    print(f"OK: All {len(REQUIRED_EDGES)} required dependency edges are present.")
    for source, target in REQUIRED_EDGES:
        print(f"  {source} -> {target}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Nx dep graph edges for Python->TypeScript links.",
        epilog="Run 'nx graph --file=tmp/graph.json' first.",
    )
    parser.add_argument(
        "--graph-file",
        type=Path,
        default=Path("tmp/graph.json"),
        help="Path to the Nx graph JSON file (default: tmp/graph.json)",
    )
    args = parser.parse_args()

    success = validate(args.graph_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
