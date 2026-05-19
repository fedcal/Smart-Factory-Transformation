"""sft_knowledge.parsers — DocumentParser ABC + concrete parsers.

Esporta:
    DocumentParser     — ABC (parse async + supported_extensions)
    ParsedDoc          — frozen Pydantic v2 (frontmatter, sections, version, lang)
    ParsedSection      — heading_path + text
    MarkdownParser     — implementazione concreta per *.md con YAML frontmatter
"""

from sft_knowledge.parsers.base import DocumentParser, ParsedDoc, ParsedSection
from sft_knowledge.parsers.markdown import MarkdownParser

__all__ = [
    "DocumentParser",
    "MarkdownParser",
    "ParsedDoc",
    "ParsedSection",
]
