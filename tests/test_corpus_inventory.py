"""
tests/test_corpus_inventory.py

Inventory tests for the synthetic SOP corpus (KNW-10, D-26, D-27).

Purpose:
  - Verify the corpus directory and file structure exist after Task 2 populates it.
  - Check distribution: at least 1 IT SOP per asset family (relaxed for Plan 02-04;
    Plan 02-05 tightens to ==5 per family).
  - Verify frontmatter status values are within the allowed enum.
  - Verify filename-frontmatter lang consistency (Pitfall 7 mitigation).

Bootstrap behavior: when run BEFORE Task 2 (corpus empty or dir absent),
tests that depend on corpus content skip gracefully via pytest.mark.skipif
or explicit skip inside the test body. They pass automatically once the
5 IT SOPs are written by Task 2.

Asset family → subdirectory mapping:
  weaving     → it/loom/
  dyeing      → it/dyeing/
  spinning    → it/spinning/
  quality_grading → it/quality_grading/

Note: directory names reflect the *asset* (e.g. loom), not the asset_family
(weaving). The mapping is documented in the synthetic-corpus README.md.
"""
import re
from pathlib import Path

import frontmatter
import pytest

WORKSPACE_ROOT = Path(__file__).parent.parent
CORPUS_ROOT = WORKSPACE_ROOT / "simulators" / "synthetic-corpus"
IT_ROOT = CORPUS_ROOT / "it"

# Map of asset_family value -> IT subdirectory name
# (D-27 distribution: 4 families in Phase 2 corpus)
FAMILY_SUBDIR_MAP = {
    "weaving": "loom",
    "dyeing": "dyeing",
    "spinning": "spinning",
    "quality_grading": "quality_grading",
}

VALID_STATUS_VALUES = {"reviewed", "draft-unreviewed", "deprecated"}

FILENAME_PATTERN = re.compile(r"^SOP-[A-Z]+-[0-9]{3}-[a-z0-9-]+-(it|en)\.md$")


def _corpus_has_files() -> bool:
    """Return True if at least one IT SOP file exists in the corpus."""
    if not IT_ROOT.exists():
        return False
    return any(IT_ROOT.rglob("*.md"))


def _all_it_sop_files() -> list[Path]:
    """Return sorted list of all IT SOP .md files."""
    if not IT_ROOT.exists():
        return []
    return sorted(IT_ROOT.rglob("*.md"))


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: corpus directory structure exists
# ─────────────────────────────────────────────────────────────────────────────


def test_corpus_dir_exists() -> None:
    """Assert simulators/synthetic-corpus directory exists (populated by Task 2)."""
    if not CORPUS_ROOT.exists():
        pytest.skip("Corpus directory not yet created — run Task 2 first")
    assert CORPUS_ROOT.is_dir(), f"Expected directory at {CORPUS_ROOT}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: distribution by asset family (Plan 02-04 relaxed: ≥1 per family)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("asset_family,subdir", list(FAMILY_SUBDIR_MAP.items()))
def test_distribution_phase04(asset_family: str, subdir: str) -> None:
    """For each asset family, assert ≥1 IT SOP file exists (relaxed for Plan 02-04)."""
    if not _corpus_has_files():
        pytest.skip(f"No IT SOP files yet — task 2 must run first (checking {asset_family})")

    family_dir = IT_ROOT / subdir
    if not family_dir.exists():
        pytest.fail(
            f"Directory {family_dir.relative_to(WORKSPACE_ROOT)} does not exist; "
            f"expected at least 1 SOP for asset_family '{asset_family}'"
        )

    sop_files = list(family_dir.glob("*.md"))
    assert len(sop_files) >= 1, (
        f"Expected ≥1 IT SOP for asset_family '{asset_family}' "
        f"under {family_dir.relative_to(WORKSPACE_ROOT)}, found 0"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: all frontmatter status values are within allowed enum
# ─────────────────────────────────────────────────────────────────────────────


def test_all_status_draft_unreviewed_or_reviewed() -> None:
    """Frontmatter status field must be one of {reviewed, draft-unreviewed, deprecated}."""
    sop_files = _all_it_sop_files()
    if not sop_files:
        pytest.skip("No IT SOP files yet — task 2 must run first")

    violations: list[str] = []
    for md_path in sop_files:
        try:
            post = frontmatter.load(str(md_path))
        except Exception as exc:
            violations.append(f"{md_path.relative_to(WORKSPACE_ROOT)}: parse error: {exc}")
            continue

        status = post.metadata.get("status", "")
        if status not in VALID_STATUS_VALUES:
            violations.append(
                f"{md_path.relative_to(WORKSPACE_ROOT)}: "
                f"invalid status '{status}' — must be one of {VALID_STATUS_VALUES}"
            )

    assert not violations, (
        f"{len(violations)} SOP(s) have invalid status values:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: filename lang suffix matches frontmatter lang field
# ─────────────────────────────────────────────────────────────────────────────


def test_filename_matches_frontmatter_lang() -> None:
    """Filename lang suffix must match frontmatter lang field (D-26 + Pitfall 7)."""
    sop_files = _all_it_sop_files()
    if not sop_files:
        pytest.skip("No IT SOP files yet — task 2 must run first")

    violations: list[str] = []
    for md_path in sop_files:
        filename = md_path.name
        rel = md_path.relative_to(WORKSPACE_ROOT)

        # Check filename convention
        match = FILENAME_PATTERN.match(filename)
        if not match:
            violations.append(
                f"{rel}: filename does not match convention "
                f"SOP-ASSET-NNN-slug-lang.md"
            )
            continue

        lang_suffix = match.group(1)

        try:
            post = frontmatter.load(str(md_path))
        except Exception as exc:
            violations.append(f"{rel}: parse error: {exc}")
            continue

        fm_lang = post.metadata.get("lang", "")
        if lang_suffix != fm_lang:
            violations.append(
                f"{rel}: filename suffix '{lang_suffix}' != frontmatter lang '{fm_lang}'"
            )

    assert not violations, (
        f"{len(violations)} SOP(s) have filename/frontmatter lang mismatch:\n"
        + "\n".join(f"  {v}" for v in violations)
    )
