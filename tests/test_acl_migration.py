"""
tests/test_acl_migration.py

Unit tests for scripts/migrate-sop-acl.py (Plan 05-02 ACL migration).

Tests cover:
1. Pure mapping function `map_audience_to_acl` against D-72 table.
2. Idempotency of `migrate_file` (second run is a no-op).
3. Immutable update pattern (dry-run does not write).
4. (Task 3) Extended frontmatter validator rejects missing/invalid acl_level.

All tests run in tmp_path — no real corpus files are touched.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable

import pytest

WORKSPACE_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"


def _load_module(module_name: str, script_path: Path):
    """Import a Python file by path so test does not depend on PYTHONPATH layout.

    Required because the migration script is `scripts/migrate-sop-acl.py` (hyphen
    in the filename) and is therefore not importable via regular `import`.
    """
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def migrate_module():
    """Load scripts/migrate-sop-acl.py as a Python module."""
    return _load_module("migrate_sop_acl", SCRIPTS_DIR / "migrate-sop-acl.py")


@pytest.fixture(scope="module")
def validator_module():
    """Load scripts/validate-corpus-frontmatter.py as a Python module."""
    return _load_module(
        "validate_corpus_frontmatter", SCRIPTS_DIR / "validate-corpus-frontmatter.py"
    )


# ---------------------------------------------------------------------------
# 1. Pure mapping function tests (D-72 table)
# ---------------------------------------------------------------------------


def test_map_operations_to_public(migrate_module):
    assert migrate_module.map_audience_to_acl("operations") == "public"


def test_map_maintenance_to_internal(migrate_module):
    assert migrate_module.map_audience_to_acl("maintenance") == "internal"


def test_map_quality_to_internal(migrate_module):
    assert migrate_module.map_audience_to_acl("quality") == "internal"


def test_map_engineering_to_internal(migrate_module):
    assert migrate_module.map_audience_to_acl("engineering") == "internal"


def test_map_management_to_restricted(migrate_module):
    assert migrate_module.map_audience_to_acl("management") == "restricted"


def test_map_safety_to_restricted(migrate_module):
    assert migrate_module.map_audience_to_acl("safety") == "restricted"


def test_map_missing_defaults_internal(migrate_module):
    """Missing/None audience → conservative fallback 'internal' per D-72."""
    assert migrate_module.map_audience_to_acl(None) == "internal"


def test_map_unknown_defaults_internal(migrate_module):
    """Unknown audience value → conservative fallback 'internal' per D-72."""
    assert migrate_module.map_audience_to_acl("rocketscience") == "internal"


# ---------------------------------------------------------------------------
# 2. migrate_file behavior tests
# ---------------------------------------------------------------------------


def _write_sample_sop(
    tmp_path: Path,
    *,
    audience: str | None = "maintenance",
    include_acl: bool = False,
    filename: str = "SOP-LOOM-001-broken-end-it.md",
) -> Path:
    """Helper: write a minimal SOP markdown with valid frontmatter to tmp_path."""
    lines = ["---"]
    lines.append("id: SOP-LOOM-001")
    lines.append("title: Test SOP")
    lines.append('version: "1.0"')
    lines.append("lang: it")
    lines.append("asset: loom")
    lines.append("asset_family: weaving")
    lines.append("role: technician")
    lines.append("hazard_level: medium")
    lines.append("estimated_duration_min: 30")
    if audience is not None:
        lines.append(f"audience: {audience}")
    if include_acl:
        lines.append("acl_level: internal")
    lines.append("status: reviewed")
    lines.append("created_in_phase: 2")
    lines.append("---")
    lines.append("")
    lines.append("# Test SOP")
    lines.append("")
    lines.append("## Scope")
    lines.append("Body content.")
    path = tmp_path / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_migrate_file_adds_acl_level(migrate_module, tmp_path: Path):
    """First migration on a SOP without acl_level adds it correctly."""
    path = _write_sample_sop(tmp_path, audience="maintenance")
    result = migrate_module.migrate_file(path, dry_run=False)
    assert result == "migrated"

    import frontmatter

    post = frontmatter.load(str(path))
    assert post.metadata["acl_level"] == "internal"
    # Original fields preserved
    assert post.metadata["audience"] == "maintenance"
    assert post.metadata["id"] == "SOP-LOOM-001"


def test_migrate_file_idempotent(migrate_module, tmp_path: Path):
    """Re-running migrate_file on an already-migrated SOP is a no-op (skipped)."""
    path = _write_sample_sop(tmp_path, audience="maintenance")

    first = migrate_module.migrate_file(path, dry_run=False)
    assert first == "migrated"

    second = migrate_module.migrate_file(path, dry_run=False)
    assert second == "skipped"

    import frontmatter

    post = frontmatter.load(str(path))
    assert post.metadata["acl_level"] == "internal"


def test_migrate_file_dry_run_does_not_write(migrate_module, tmp_path: Path):
    """dry_run=True must not modify the file byte-for-byte (immutability check)."""
    path = _write_sample_sop(tmp_path, audience="operations")
    original_bytes = path.read_bytes()

    result = migrate_module.migrate_file(path, dry_run=True)
    assert result == "migrated"

    after_bytes = path.read_bytes()
    assert after_bytes == original_bytes, (
        "dry_run must not write to disk — file changed byte-for-byte"
    )


def test_migrate_file_missing_audience_uses_fallback(migrate_module, tmp_path: Path):
    """SOP without audience field → acl_level='internal' (conservative)."""
    path = _write_sample_sop(tmp_path, audience=None)
    result = migrate_module.migrate_file(path, dry_run=False)
    assert result == "migrated"

    import frontmatter

    post = frontmatter.load(str(path))
    assert post.metadata["acl_level"] == "internal"


def test_migrate_file_skips_when_acl_already_present(migrate_module, tmp_path: Path):
    """Pre-existing acl_level field → file is skipped, value preserved."""
    path = _write_sample_sop(tmp_path, audience="operations", include_acl=True)
    result = migrate_module.migrate_file(path, dry_run=False)
    assert result == "skipped"

    import frontmatter

    post = frontmatter.load(str(path))
    # Value preserved as originally written (internal), NOT remapped from audience
    assert post.metadata["acl_level"] == "internal"


def test_migrate_file_returns_error_on_invalid_yaml(migrate_module, tmp_path: Path):
    """Malformed frontmatter → returns 'error'."""
    path = tmp_path / "SOP-LOOM-999-malformed-it.md"
    path.write_text("---\nthis: is: not: valid: yaml\n---\nBody", encoding="utf-8")
    result = migrate_module.migrate_file(path, dry_run=False)
    assert result == "error"


# ---------------------------------------------------------------------------
# 3. Validator extension tests (Task 3 — exercised after acl_level added to required)
# ---------------------------------------------------------------------------


def _write_validator_test_sop(
    corpus_dir: Path,
    *,
    acl_level: str | None = "internal",
    filename: str = "SOP-LOOM-001-test-it.md",
) -> Path:
    """Write a SOP under corpus_dir/it/loom/ with all required H2 sections."""
    sop_dir = corpus_dir / "it" / "loom"
    sop_dir.mkdir(parents=True, exist_ok=True)

    fm_lines = [
        "---",
        "id: SOP-LOOM-001",
        "title: Validator Test SOP",
        'version: "1.0"',
        "lang: it",
        "asset: loom",
        "asset_family: weaving",
        "role: technician",
        "hazard_level: medium",
        "estimated_duration_min: 30",
        "audience: maintenance",
        "status: reviewed",
        "created_in_phase: 5",
    ]
    if acl_level is not None:
        fm_lines.append(f"acl_level: {acl_level}")
    fm_lines.append("---")

    body = [
        "",
        "# Validator Test SOP",
        "",
        "## Scope",
        "Body.",
        "",
        "## Prerequisites",
        "None.",
        "",
        "## Tools and PPE",
        "None.",
        "",
        "## Step-by-step Procedure",
        "1. Do thing.",
        "",
        "## Verification",
        "Check.",
        "",
        "## Troubleshooting",
        "None.",
        "",
        "## References",
        "None.",
        "",
    ]
    path = sop_dir / filename
    path.write_text("\n".join(fm_lines + body), encoding="utf-8")
    return path


def test_validator_rejects_missing_acl_level(validator_module, tmp_path: Path):
    """A SOP missing acl_level must cause validator to return False."""
    corpus_dir = tmp_path / "corpus"
    _write_validator_test_sop(corpus_dir, acl_level=None)

    schema_file = (
        WORKSPACE_ROOT
        / "packages"
        / "sft-domain"
        / "src"
        / "sft_domain"
        / "schemas"
        / "sop.schema.json"
    )
    success = validator_module.validate(corpus_dir, schema_file)
    assert success is False, "validator must reject SOP missing acl_level"


def test_validator_rejects_invalid_acl_value(validator_module, tmp_path: Path):
    """A SOP with acl_level outside {public, internal, restricted} must fail."""
    corpus_dir = tmp_path / "corpus"
    _write_validator_test_sop(corpus_dir, acl_level="top_secret")

    schema_file = (
        WORKSPACE_ROOT
        / "packages"
        / "sft-domain"
        / "src"
        / "sft_domain"
        / "schemas"
        / "sop.schema.json"
    )
    success = validator_module.validate(corpus_dir, schema_file)
    assert success is False, "validator must reject invalid acl_level value"


def test_validator_accepts_valid_corpus(validator_module):
    """Real corpus (post-Task-2 migration) must pass the extended validator."""
    corpus_dir = WORKSPACE_ROOT / "simulators" / "synthetic-corpus"
    schema_file = (
        WORKSPACE_ROOT
        / "packages"
        / "sft-domain"
        / "src"
        / "sft_domain"
        / "schemas"
        / "sop.schema.json"
    )
    success = validator_module.validate(corpus_dir, schema_file)
    assert success is True, "real migrated corpus must pass validator"
