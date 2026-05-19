"""Unit tests for MarkdownParser (Plan 05-01 Task 3).

Coverage:
    - test_parse_all_41_sops:           parses every SOP under simulators/synthetic-corpus/
                                        without raising (returns ParsedDoc or None)
    - test_extracts_heading_path:       H1/H2/H3 state-machine produces nested heading_path
    - test_status_draft_returns_none:   status != "reviewed" gates the doc (D-25)
    - test_missing_acl_level_defaults_internal: missing acl_level → "internal" (D-67/D-72)
    - test_required_field_missing_raises: missing id/title/version/lang raises ValueError
    - test_supported_extensions_returns_md: contract on supported_extensions()

NO mocks for filesystem I/O — uses real fixtures via tmp_path + the synthetic-corpus.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from sft_knowledge.parsers.base import ParsedDoc
from sft_knowledge.parsers.markdown import MarkdownParser

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SYNTHETIC_CORPUS = WORKSPACE_ROOT / "simulators" / "synthetic-corpus"


def _write_sop(tmp_path: Path, frontmatter_yaml: str, body: str = "## Scope\nbody") -> Path:
    p = tmp_path / "SOP-TEST-001-fixture-en.md"
    p.write_text(f"---\n{frontmatter_yaml}\n---\n\n{body}\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


def test_supported_extensions_returns_md() -> None:
    assert MarkdownParser().supported_extensions() == {".md"}


# ---------------------------------------------------------------------------
# Status gate (D-25)
# ---------------------------------------------------------------------------


async def test_status_draft_returns_none(tmp_path: Path) -> None:
    p = _write_sop(
        tmp_path,
        dedent(
            """\
            id: SOP-X-001
            title: Draft fixture
            version: "1.0"
            lang: en
            status: draft
            """
        ).strip(),
    )
    result = await MarkdownParser().parse(p)
    assert result is None


async def test_status_reviewed_returns_parsed_doc(tmp_path: Path) -> None:
    p = _write_sop(
        tmp_path,
        dedent(
            """\
            id: SOP-X-002
            title: Reviewed fixture
            version: "1.0"
            lang: en
            status: reviewed
            """
        ).strip(),
    )
    result = await MarkdownParser().parse(p)
    assert isinstance(result, ParsedDoc)
    assert result.lang == "en"


# ---------------------------------------------------------------------------
# ACL default fallback (D-67/D-72)
# ---------------------------------------------------------------------------


async def test_missing_acl_level_defaults_internal(tmp_path: Path) -> None:
    p = _write_sop(
        tmp_path,
        dedent(
            """\
            id: SOP-X-003
            title: Missing ACL fixture
            version: "1.0"
            lang: en
            status: reviewed
            """
        ).strip(),
    )
    doc = await MarkdownParser().parse(p)
    assert doc is not None
    assert doc.frontmatter["acl_level"] == "internal"


async def test_explicit_acl_level_preserved(tmp_path: Path) -> None:
    p = _write_sop(
        tmp_path,
        dedent(
            """\
            id: SOP-X-004
            title: Explicit ACL fixture
            version: "1.0"
            lang: en
            status: reviewed
            acl_level: restricted
            """
        ).strip(),
    )
    doc = await MarkdownParser().parse(p)
    assert doc is not None
    assert doc.frontmatter["acl_level"] == "restricted"


# ---------------------------------------------------------------------------
# Required-field enforcement
# ---------------------------------------------------------------------------


async def test_required_field_missing_raises(tmp_path: Path) -> None:
    p = _write_sop(
        tmp_path,
        dedent(
            """\
            title: No id fixture
            version: "1.0"
            lang: en
            status: reviewed
            """
        ).strip(),
    )
    with pytest.raises(ValueError, match="id"):
        await MarkdownParser().parse(p)


# ---------------------------------------------------------------------------
# heading_path extraction
# ---------------------------------------------------------------------------


async def test_extracts_heading_path(tmp_path: Path) -> None:
    body = dedent(
        """\
        # Top
        intro
        ## Scope
        scope body
        ### Sub-scope
        nested body
        ## Prerequisites
        prereq body
        """
    )
    p = _write_sop(
        tmp_path,
        dedent(
            """\
            id: SOP-X-005
            title: Heading path fixture
            version: "1.0"
            lang: en
            status: reviewed
            """
        ).strip(),
        body=body,
    )
    doc = await MarkdownParser().parse(p)
    assert doc is not None
    paths = [s.heading_path for s in doc.sections]
    assert ["Top"] in paths
    assert ["Top", "Scope"] in paths
    assert ["Top", "Scope", "Sub-scope"] in paths
    assert ["Top", "Prerequisites"] in paths


async def test_section_text_excludes_heading_line(tmp_path: Path) -> None:
    body = "## Only\nbody-only-text"
    p = _write_sop(
        tmp_path,
        dedent(
            """\
            id: SOP-X-006
            title: Section text fixture
            version: "1.0"
            lang: en
            status: reviewed
            """
        ).strip(),
        body=body,
    )
    doc = await MarkdownParser().parse(p)
    assert doc is not None
    only = [s for s in doc.sections if s.heading_path == ["Only"]]
    assert len(only) == 1
    assert only[0].text == "body-only-text"


# ---------------------------------------------------------------------------
# Full corpus pass (41 SOPs)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not SYNTHETIC_CORPUS.exists(),
    reason="simulators/synthetic-corpus/ not present in this checkout",
)
async def test_parse_all_41_sops() -> None:
    """Parses every SOP markdown file under synthetic-corpus without exception.

    Before Plan 05-02 ACL migration: ≥40 of 41 must parse to ParsedDoc, the rest
    may legitimately be skipped (status != reviewed). After 05-02, all 41 parse.
    """
    parser = MarkdownParser()
    paths = sorted(SYNTHETIC_CORPUS.rglob("SOP-*.md"))
    # Plan 05-01 spec quotes "41 SOPs"; actual checkout has 40 *.md SOPs under
    # synthetic-corpus/{en,it}/ (the 41st .md is the corpus README, not an SOP).
    # We assert ≥40 to remain robust to corpus growth in Plan 05-02 (ACL migration
    # does not change file count).
    assert len(paths) >= 40, f"expected ≥40 SOPs, found {len(paths)}"

    parsed: list[ParsedDoc] = []
    for p in paths:
        result = await parser.parse(p)
        # Must NOT raise. Either ParsedDoc or None (status-gated).
        if result is not None:
            assert isinstance(result, ParsedDoc)
            parsed.append(result)
    # Every SOP currently has status: reviewed → all should parse.
    assert len(parsed) == len(paths), (
        f"expected all {len(paths)} SOPs to parse to ParsedDoc; got {len(parsed)}"
    )
