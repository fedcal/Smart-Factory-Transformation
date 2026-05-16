#!/usr/bin/env python3
"""
scripts/sync-python-versions.py

Synchronizes Python package versions from package.json to __version__.py.

Used in the Changesets release workflow: after `changeset version` bumps
package.json files, this script propagates the version to the corresponding
Python __version__.py so that `sft_agents.__version__` etc. stay in sync.

Usage:
    python3 scripts/sync-python-versions.py [--dry-run]

Exit codes:
    0 - All versions synced (or dry-run completed)
    1 - Error reading a file
"""
import argparse
import json
import pathlib
import sys

WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent


def sync_versions(dry_run: bool = False) -> bool:
    """
    Scan packages/ for package.json files and update the corresponding
    __version__.py in src/<module_name>/.

    Returns True on success, False if any error occurred.
    """
    packages_dir = WORKSPACE_ROOT / "packages"
    if not packages_dir.exists():
        print(f"ERROR: packages/ directory not found at {packages_dir}", file=sys.stderr)
        return False

    updated: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for pkg_dir in sorted(packages_dir.iterdir()):
        if not pkg_dir.is_dir():
            continue

        pkg_json_path = pkg_dir / "package.json"
        if not pkg_json_path.exists():
            skipped.append(str(pkg_dir.name))
            continue

        try:
            version = json.loads(pkg_json_path.read_text())["version"]
        except (json.JSONDecodeError, KeyError) as exc:
            errors.append(f"{pkg_dir.name}: failed to read version from package.json ({exc})")
            continue

        # Derive Python module name: kebab-case -> snake_case
        module_name = pkg_dir.name.replace("-", "_")
        py_version_file = pkg_dir / "src" / module_name / "__version__.py"

        if not py_version_file.exists():
            skipped.append(f"{pkg_dir.name} (__version__.py not found at {py_version_file})")
            continue

        new_content = f'__version__ = "{version}"\n'

        if dry_run:
            current = py_version_file.read_text()
            if current == new_content:
                print(f"[dry-run] {py_version_file.relative_to(WORKSPACE_ROOT)}: already {version!r}")
            else:
                print(f"[dry-run] WOULD update {py_version_file.relative_to(WORKSPACE_ROOT)}: -> {version!r}")
        else:
            py_version_file.write_text(new_content)
            print(f"Updated {py_version_file.relative_to(WORKSPACE_ROOT)} -> {version!r}")
        updated.append(pkg_dir.name)

    if skipped:
        print(f"\nSkipped (no package.json or __version__.py): {', '.join(skipped)}")
    if errors:
        print("\nErrors:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return False

    print(f"\nDone. Updated: {len(updated)} package(s).")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync Python __version__.py from package.json (Changesets integration).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be changed without writing files.",
    )
    args = parser.parse_args()

    success = sync_versions(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
