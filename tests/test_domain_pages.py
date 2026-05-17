"""
tests/test_domain_pages.py

Structural assertions for the Italian-language domain analysis pages
authored in Plan 02-02.

Tests verify:
  - index.md exists and has the correct H1
  - Each process page has all 4 required H2 sections
  - Each process page has exactly one Mermaid flowchart LR block with accDescr
  - Each process page has ≤8 Mermaid node identifiers (single source of truth for the
    D-22 constraint — no regex heuristic elsewhere)
  - Each role page has all 4 required H2 sections
  - Every domain page (process + role + index) has exactly one Mantis context admonition

All paths use pathlib.Path exclusively. No os.path usage (T-02-10 / security V12).
"""

import pathlib
import re

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROCESS_NAMES = [
    "weaving",
    "spinning",
    "warping",
    "dyeing",
    "finishing",
]

ROLE_NAMES = [
    "operator",
    "technician",
    "quality-manager",
    "shift-supervisor",
]

PROCESS_H2_SECTIONS = [
    "Process flow",
    "Asset coinvolti",
    "KPI",
    "Pain point",
]

ROLE_H2_SECTIONS = [
    "Responsabilità",
    "Interazione tipica con asset e processi",
    "Decisione critica giornaliera",
    "Pain point",
]

MANTIS_ADMONITION = '!!! note "Mantis context"'

# Max Mermaid node count per D-22
MAX_MERMAID_NODES = 8


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: pathlib.Path) -> str:
    """Read file content, emitting a clear message if the file is missing."""
    assert path.exists(), f"Expected file not found: {path}"
    return path.read_text(encoding="utf-8")


def _count_mermaid_nodes(mermaid_block: str) -> int:
    """Count distinct node identifiers in a Mermaid flowchart block.

    A node identifier is an alphanumeric token (with optional underscores)
    that appears on the LEFT side of a '-->' edge, on its own as a standalone
    node declaration, or inside square/round/curly brackets `[ ]`, `( )`, `{ }`.

    Heuristic: extract all tokens from bracket labels AND standalone left-hand
    identifiers from edge definitions, deduplicate, and count.
    """
    # Collect node IDs from bracket declarations: A[label], B(label), C{label}
    bracket_ids = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*[\[\(\{]', mermaid_block)
    # Collect left-hand side of edges: A --> B
    lhs_ids = re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*-->', mermaid_block)
    # Collect right-hand side of edges: A --> B
    rhs_ids = re.findall(r'-->\s*([A-Za-z_][A-Za-z0-9_]*)\b', mermaid_block)
    # Union of all found IDs
    all_ids = set(bracket_ids) | set(lhs_ids) | set(rhs_ids)
    # Filter out Mermaid keywords that are not node IDs
    mermaid_keywords = {
        "flowchart", "graph", "LR", "TD", "RL", "BT",
        "subgraph", "end", "accDescr", "accTitle",
    }
    node_ids = all_ids - mermaid_keywords
    return len(node_ids)


def _extract_mermaid_blocks(content: str) -> list[str]:
    """Extract the content of all ```mermaid fenced blocks from Markdown content."""
    return re.findall(r'```mermaid\s*(.*?)```', content, re.DOTALL)


# ---------------------------------------------------------------------------
# Test: index page
# ---------------------------------------------------------------------------

class TestIndexPage:
    """Assertions for docs/docs/domain/index.md."""

    def test_index_exists(self, domain_dir: pathlib.Path) -> None:
        """index.md must exist and start with the correct H1."""
        index_path = domain_dir / "index.md"
        content = _read(index_path)
        assert content.startswith("# Dominio:"), (
            f"Expected index.md H1 to start with '# Dominio:' but got: "
            f"{content.splitlines()[0]!r}"
        )

    def test_index_links_processes(self, domain_dir: pathlib.Path) -> None:
        """index.md must contain links to all 5 process pages."""
        content = _read(domain_dir / "index.md")
        for name in PROCESS_NAMES:
            assert name in content, (
                f"index.md does not link to process page '{name}'"
            )

    def test_index_links_roles(self, domain_dir: pathlib.Path) -> None:
        """index.md must contain links to all 4 role pages."""
        content = _read(domain_dir / "index.md")
        for name in ROLE_NAMES:
            assert name in content, (
                f"index.md does not link to role page '{name}'"
            )


# ---------------------------------------------------------------------------
# Test: process pages — sections
# ---------------------------------------------------------------------------

class TestProcessSections:
    """Structural section assertions for the 5 process pages."""

    @pytest.mark.parametrize("process_name", PROCESS_NAMES)
    def test_process_sections(
        self, processes_dir: pathlib.Path, process_name: str
    ) -> None:
        """Each process page must have all 4 required H2 sections (D-22 contract)."""
        page_path = processes_dir / f"{process_name}.md"
        content = _read(page_path)
        for section in PROCESS_H2_SECTIONS:
            pattern = rf"^## {re.escape(section)}\s*$"
            assert re.search(pattern, content, re.MULTILINE), (
                f"Process page '{process_name}.md' is missing H2 section "
                f"'## {section}'"
            )


# ---------------------------------------------------------------------------
# Test: process pages — Mermaid
# ---------------------------------------------------------------------------

class TestProcessMermaid:
    """Mermaid diagram assertions for the 5 process pages."""

    @pytest.mark.parametrize("process_name", PROCESS_NAMES)
    def test_process_has_mermaid(
        self, processes_dir: pathlib.Path, process_name: str
    ) -> None:
        """Each process page must have exactly one ```mermaid block with accDescr."""
        page_path = processes_dir / f"{process_name}.md"
        content = _read(page_path)
        blocks = _extract_mermaid_blocks(content)
        assert len(blocks) == 1, (
            f"Process page '{process_name}.md' must have exactly 1 mermaid block; "
            f"found {len(blocks)}"
        )
        block = blocks[0]
        assert "accDescr" in block, (
            f"Mermaid block in '{process_name}.md' is missing 'accDescr' "
            "(required for accessibility — RESEARCH Pitfall 2 / T-02-07)"
        )

    @pytest.mark.parametrize("process_name", PROCESS_NAMES)
    def test_process_mermaid_node_count(
        self, processes_dir: pathlib.Path, process_name: str
    ) -> None:
        """Each process page Mermaid diagram must have ≤8 node identifiers (D-22).

        This test is the single source of truth for the ≤8-node constraint.
        No regex heuristic in Task 1 acceptance criteria — only this test.
        """
        page_path = processes_dir / f"{process_name}.md"
        content = _read(page_path)
        blocks = _extract_mermaid_blocks(content)
        assert len(blocks) >= 1, (
            f"Process page '{process_name}.md' has no mermaid block"
        )
        node_count = _count_mermaid_nodes(blocks[0])
        assert node_count <= MAX_MERMAID_NODES, (
            f"Mermaid diagram in '{process_name}.md' has {node_count} node(s) "
            f"but D-22 mandates ≤{MAX_MERMAID_NODES}. "
            "Split the diagram or reduce nodes."
        )


# ---------------------------------------------------------------------------
# Test: role pages — sections
# ---------------------------------------------------------------------------

class TestRoleSections:
    """Structural section assertions for the 4 role pages."""

    @pytest.mark.parametrize("role_name", ROLE_NAMES)
    def test_role_sections(
        self, roles_dir: pathlib.Path, role_name: str
    ) -> None:
        """Each role page must have all 4 required H2 sections (D-22 role contract)."""
        page_path = roles_dir / f"{role_name}.md"
        content = _read(page_path)
        for section in ROLE_H2_SECTIONS:
            pattern = rf"^## {re.escape(section)}\s*$"
            assert re.search(pattern, content, re.MULTILINE), (
                f"Role page '{role_name}.md' is missing H2 section "
                f"'## {section}'"
            )


# ---------------------------------------------------------------------------
# Test: Mantis context admonition — all pages
# ---------------------------------------------------------------------------

class TestMantisAdmonition:
    """Every domain page must have exactly one Mantis context admonition (D-23)."""

    @pytest.mark.parametrize("process_name", PROCESS_NAMES)
    def test_mantis_admonition_process(
        self, processes_dir: pathlib.Path, process_name: str
    ) -> None:
        """Each process page must have exactly one Mantis context admonition."""
        page_path = processes_dir / f"{process_name}.md"
        content = _read(page_path)
        count = content.count(MANTIS_ADMONITION)
        assert count == 1, (
            f"Process page '{process_name}.md' must have exactly 1 "
            f"'{MANTIS_ADMONITION}' line; found {count} (D-23)"
        )

    @pytest.mark.parametrize("role_name", ROLE_NAMES)
    def test_mantis_admonition_role(
        self, roles_dir: pathlib.Path, role_name: str
    ) -> None:
        """Each role page must have exactly one Mantis context admonition."""
        page_path = roles_dir / f"{role_name}.md"
        content = _read(page_path)
        count = content.count(MANTIS_ADMONITION)
        assert count == 1, (
            f"Role page '{role_name}.md' must have exactly 1 "
            f"'{MANTIS_ADMONITION}' line; found {count} (D-23)"
        )

    def test_mantis_admonition_index(self, domain_dir: pathlib.Path) -> None:
        """index.md must have exactly one Mantis context admonition."""
        content = _read(domain_dir / "index.md")
        count = content.count(MANTIS_ADMONITION)
        assert count == 1, (
            f"index.md must have exactly 1 '{MANTIS_ADMONITION}' line; "
            f"found {count} (D-23)"
        )
