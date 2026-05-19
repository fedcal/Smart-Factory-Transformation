"""MarkdownParser — Wave-1 scaffold placeholder.

Implementazione completa in Plan 05-01 Task 3 (status/ACL gates + heading_path).
"""

from __future__ import annotations

from pathlib import Path

from sft_knowledge.parsers.base import DocumentParser, ParsedDoc


class MarkdownParser(DocumentParser):
    """Parser SOP markdown — implementazione in Task 3."""

    def supported_extensions(self) -> set[str]:
        return {".md"}

    async def parse(self, path: Path) -> ParsedDoc | None:  # pragma: no cover - stub
        raise NotImplementedError(
            "MarkdownParser.parse() is implemented in Plan 05-01 Task 3"
        )
