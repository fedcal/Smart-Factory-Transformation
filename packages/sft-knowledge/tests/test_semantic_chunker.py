# Covers KNW-04 (semantic chunking) per 05-VALIDATION.md
"""Wave 0 stub — implemented in Plan 05-07 (embedding + chunking)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-07")


def test_semantic_chunker_returns_text_nodes_with_metadata() -> None:
    """Stub: SemanticChunker.chunk(ParsedDoc) returns list[TextNode] with metadata propagated."""
    pass


def test_metadata_propagation_to_chunks() -> None:
    """Stub: heading_path + frontmatter (id, version, lang, acl_level) propagate to each chunk."""
    pass
