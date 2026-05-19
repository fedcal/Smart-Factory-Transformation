"""Unit tests for sft_knowledge models + DocumentParser ABC invariants.

Covers Plan 05-01 Task 2 acceptance:
    - ParsedDoc / ParsedSection / GraphNode frozen + extra=forbid
    - DocumentParser is ABC (cannot instantiate; subclass must override abstract methods)
    - RagCitation re-export from sft_agents.models.evidence (no redefine per D-59)
"""

from __future__ import annotations

from inspect import isabstract

import pytest
from pydantic import ValidationError
from sft_knowledge.models import GraphNode, RagCitation
from sft_knowledge.parsers.base import DocumentParser, ParsedDoc, ParsedSection

# ---------------------------------------------------------------------------
# ParsedSection
# ---------------------------------------------------------------------------


def test_parsed_section_frozen_rejects_mutation() -> None:
    sec = ParsedSection(heading_path=["H1", "H2"], text="body")
    with pytest.raises(ValidationError):
        sec.text = "mutated"  # type: ignore[misc]


def test_parsed_section_extra_forbid_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        ParsedSection(heading_path=["A"], text="x", unknown_field="boom")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# ParsedDoc
# ---------------------------------------------------------------------------


def _sample_parsed_doc() -> ParsedDoc:
    return ParsedDoc(
        source_uri="corpus://demo.md",
        frontmatter={"id": "SOP-DEMO-001", "title": "Demo", "version": "1.0", "lang": "it"},
        sections=[ParsedSection(heading_path=["Scope"], text="hello")],
        version="1.0",
        lang="it",
    )


def test_parsed_doc_constructs_with_valid_fields() -> None:
    doc = _sample_parsed_doc()
    assert doc.source_uri == "corpus://demo.md"
    assert doc.lang == "it"
    assert len(doc.sections) == 1


def test_parsed_doc_frozen_rejects_mutation() -> None:
    doc = _sample_parsed_doc()
    with pytest.raises(ValidationError):
        doc.source_uri = "corpus://other.md"  # type: ignore[misc]


def test_parsed_doc_extra_forbid_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        ParsedDoc(  # type: ignore[call-arg]
            source_uri="corpus://x.md",
            frontmatter={},
            sections=[],
            version="1.0",
            lang="it",
            unknown="boom",
        )


def test_parsed_doc_lang_literal_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        ParsedDoc(
            source_uri="corpus://x.md",
            frontmatter={},
            sections=[],
            version="1.0",
            lang="fr",  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# DocumentParser ABC
# ---------------------------------------------------------------------------


def test_document_parser_is_abstract() -> None:
    assert isabstract(DocumentParser)
    with pytest.raises(TypeError):
        DocumentParser()  # type: ignore[abstract]


def test_document_parser_subclass_must_implement_both_methods() -> None:
    class Partial(DocumentParser):
        def supported_extensions(self) -> set[str]:
            return {".x"}

    # missing parse() -> still abstract
    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# GraphNode
# ---------------------------------------------------------------------------


def test_graph_node_constructs_with_valid_label() -> None:
    node = GraphNode(label="SOP", node_id="SOP-DEMO-001", properties={"version": "1.0"})
    assert node.label == "SOP"
    assert node.properties == {"version": "1.0"}


def test_graph_node_label_literal_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        GraphNode(label="Operator", node_id="X")  # type: ignore[arg-type]


def test_graph_node_frozen_rejects_mutation() -> None:
    node = GraphNode(label="SOP", node_id="X")
    with pytest.raises(ValidationError):
        node.node_id = "Y"  # type: ignore[misc]


def test_graph_node_extra_forbid_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        GraphNode(label="SOP", node_id="X", unknown=1)  # type: ignore[call-arg]


def test_graph_node_properties_defaults_empty_dict() -> None:
    node = GraphNode(label="Part", node_id="P-001")
    assert node.properties == {}


# ---------------------------------------------------------------------------
# RagCitation re-export (D-59: import, do NOT redefine)
# ---------------------------------------------------------------------------


def test_rag_citation_reexport_is_same_class_as_sft_agents() -> None:
    from sft_agents.models.evidence import RagCitation as AgentsRagCitation

    assert RagCitation is AgentsRagCitation
