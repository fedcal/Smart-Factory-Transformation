"""Unit + integration tests for `sft_knowledge.chunking.semantic.SemanticChunker`.

Plan 05-07 Task 2 (unit) + Task 3 (integration on real SOP).

Covers KNW-04 (semantic chunking) per 05-VALIDATION.md.

Strategy:
    - Unit: mock both `_get_embed_model()` and `SemanticSplitterNodeParser` so we test
      pipeline wiring + heading_path recovery + metadata propagation WITHOUT loading
      real BGE-M3 (~2GB).
    - Integration (Task 3): `@pytest.mark.integration @pytest.mark.gpu` runs the full
      pipeline parse → chunk → embed on a real SOP file. Skipped by default on CPU CI.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from sft_knowledge.chunking.semantic import Chunk
from sft_knowledge.parsers.base import ParsedDoc, ParsedSection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_singleton() -> None:
    """Clear `_get_embed_model` cache so each test starts fresh."""
    from sft_knowledge.chunking import semantic as mod

    mod._get_embed_model.cache_clear()


@pytest.fixture(autouse=True)
def _clear_singleton():
    _reset_singleton()
    yield
    _reset_singleton()


def _build_parsed_doc(
    sections: list[tuple[list[str], str]],
    frontmatter: dict[str, Any] | None = None,
) -> ParsedDoc:
    """Build a `ParsedDoc` for tests with given (heading_path, text) sections."""
    fm = frontmatter or {
        "id": "SOP-TEST-001",
        "title": "Test SOP",
        "version": "1.0",
        "lang": "it",
        "acl_level": "internal",
        "asset_family": "weaving",
    }
    return ParsedDoc(
        source_uri="corpus://test/sop-test-001.md",
        frontmatter=fm,
        sections=[ParsedSection(heading_path=hp, text=t) for hp, t in sections],
        version=str(fm["version"]),
        lang=fm["lang"],
    )


def _make_text_node(text: str, start_char_idx: int, metadata: dict[str, Any]) -> Any:
    """Construct a TextNode-like MagicMock for patched splitter output."""
    node = MagicMock()
    node.text = text
    node.start_char_idx = start_char_idx
    node.metadata = metadata
    return node


def _patch_llama_index(
    monkeypatch: pytest.MonkeyPatch,
    splitter_nodes: list[Any],
) -> None:
    """Install fake `llama_index.core` + `.node_parser` + embed model into sys.modules.

    The fake splitter ignores the actual splitting algorithm and returns the
    pre-built `splitter_nodes` list. This keeps tests deterministic.
    """
    # 1. Patch embed model singleton.
    from sft_knowledge.chunking import semantic as mod

    monkeypatch.setattr(mod, "_get_embed_model", lambda: MagicMock(name="embed_model"))

    # 2. Build fake llama_index.core.Document.
    fake_core = types.ModuleType("llama_index.core")

    class _StubDocument:
        def __init__(self, text: str, metadata: dict, **kwargs: Any) -> None:
            self.text = text
            self.metadata = metadata
            self.excluded_embed_metadata_keys = kwargs.get(
                "excluded_embed_metadata_keys", []
            )

    fake_core.Document = _StubDocument  # type: ignore[attr-defined]

    # 3. Build fake llama_index.core.node_parser.SemanticSplitterNodeParser.
    fake_np = types.ModuleType("llama_index.core.node_parser")

    class _StubSplitter:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def get_nodes_from_documents(self, docs: list[Any]) -> list[Any]:
            # Copia Document.metadata su ciascun nodo (semantica reale di LlamaIndex).
            doc_meta = docs[0].metadata if docs else {}
            patched = []
            for n in splitter_nodes:
                merged = {**doc_meta, **(n.metadata or {})}
                n.metadata = merged
                patched.append(n)
            return patched

    fake_np.SemanticSplitterNodeParser = _StubSplitter  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "llama_index.core", fake_core)
    monkeypatch.setitem(sys.modules, "llama_index.core.node_parser", fake_np)


# ===========================================================================
# Task 2 — Unit tests
# ===========================================================================


def test_semantic_chunker_returns_text_nodes_with_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Builds a ParsedDoc with 5 sections; chunker returns ≥1 Chunk; metadata present."""
    parsed = _build_parsed_doc(
        sections=[
            (["H1 Intro"], "Intro body."),
            (["H1 Intro", "H2 A"], "Section A body."),
            (["H1 Intro", "H2 B"], "Section B body."),
            (["H1 Methods"], "Methods body."),
            (["H1 Methods", "H2 C"], "Section C body."),
        ],
    )
    nodes = [
        _make_text_node("Intro body.", 0, {}),
        _make_text_node("Section C body.", 60, {}),
    ]
    _patch_llama_index(monkeypatch, nodes)

    from sft_knowledge.chunking.semantic import SemanticChunker

    chunks = SemanticChunker().chunk(parsed)

    assert len(chunks) >= 1
    for chunk in chunks:
        # KNW-05 prerequisite: ogni chunk DEVE avere queste chiavi.
        for key in ("source_uri", "lang", "acl_level", "sop_id", "version", "asset_family"):
            assert key in chunk.metadata, f"Missing key {key} in chunk metadata"


def test_metadata_propagation_to_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    """ALL chunks must have metadata['source_uri'] == ParsedDoc.source_uri (Risk 7)."""
    parsed = _build_parsed_doc(
        sections=[
            (["H1"], "Body one."),
            (["H1", "H2"], "Body two."),
        ],
    )
    nodes = [
        _make_text_node("Body one.", 0, {}),
        _make_text_node("Body two.", 11, {}),
    ]
    _patch_llama_index(monkeypatch, nodes)

    from sft_knowledge.chunking.semantic import SemanticChunker

    chunks = SemanticChunker().chunk(parsed)

    assert len(chunks) == 2
    for chunk in chunks:
        assert chunk.metadata["source_uri"] == "corpus://test/sop-test-001.md"
        assert chunk.metadata["acl_level"] == "internal"
        assert chunk.metadata["sop_id"] == "SOP-TEST-001"


def test_heading_path_recovered(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chunks across 3 sections: first has section-0 heading_path, last has section-2's."""
    s1 = "First section body for H1 Intro."
    s2 = "Second section body for H2 Setup."
    s3 = "Third section body for H3 Detail."
    parsed = _build_parsed_doc(
        sections=[
            (["H1 Intro"], s1),
            (["H1 Intro", "H2 Setup"], s2),
            (["H1 Intro", "H2 Setup", "H3 Detail"], s3),
        ],
    )

    # Compute exact section offsets in concatenated body.
    sep = "\n\n"
    off1 = 0
    off2 = len(s1) + len(sep)
    off3 = off2 + len(s2) + len(sep)

    nodes = [
        _make_text_node(s1, off1, {}),
        _make_text_node(s2, off2, {}),
        _make_text_node(s3, off3, {}),
    ]
    _patch_llama_index(monkeypatch, nodes)

    from sft_knowledge.chunking.semantic import SemanticChunker

    chunks = SemanticChunker().chunk(parsed)

    assert len(chunks) == 3
    assert chunks[0].heading_path == ["H1 Intro"]
    assert chunks[1].heading_path == ["H1 Intro", "H2 Setup"]
    assert chunks[2].heading_path == ["H1 Intro", "H2 Setup", "H3 Detail"]


def test_chunk_frozen() -> None:
    """Pydantic frozen → mutating a Chunk attribute raises ValidationError."""
    chunk = Chunk(
        text="hello",
        chunk_idx=0,
        heading_path=["H1"],
        metadata={"k": "v"},
    )
    with pytest.raises(ValidationError):
        chunk.text = "mutated"  # type: ignore[misc]


def test_chunk_idx_sequential(monkeypatch: pytest.MonkeyPatch) -> None:
    """chunk_idx must be a contiguous 0,1,2,... sequence over the returned chunks."""
    parsed = _build_parsed_doc(
        sections=[(["H1"], "A."), (["H1"], "B."), (["H1"], "C."), (["H1"], "D.")],
    )
    nodes = [
        _make_text_node("A.", 0, {}),
        _make_text_node("B.", 4, {}),
        _make_text_node("C.", 8, {}),
        _make_text_node("D.", 12, {}),
    ]
    _patch_llama_index(monkeypatch, nodes)

    from sft_knowledge.chunking.semantic import SemanticChunker

    chunks = SemanticChunker().chunk(parsed)

    assert [c.chunk_idx for c in chunks] == [0, 1, 2, 3]


# NOTE: Task 3 integration test (test_real_sop_end_to_end_chunk_and_embed) is added in a
# separate commit (Plan 05-07 Task 3) to keep this commit focused on unit-test coverage.
