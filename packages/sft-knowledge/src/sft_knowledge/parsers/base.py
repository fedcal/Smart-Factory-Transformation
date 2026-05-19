"""DocumentParser ABC + ParsedDoc/ParsedSection frozen models.

Wave-1 scaffold stub. Implementazione completa in Plan 05-01 Task 2.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class ParsedSection(BaseModel):
    """Una sezione del documento parsato (heading_path + testo)."""

    model_config = {"frozen": True, "extra": "forbid"}

    heading_path: list[str]
    text: str


class ParsedDoc(BaseModel):
    """Documento parsato in output da `DocumentParser.parse()` (D-67)."""

    model_config = {"frozen": True, "extra": "forbid"}

    source_uri: str
    frontmatter: dict
    sections: list[ParsedSection]
    version: str
    lang: Literal["it", "en"]


class DocumentParser(ABC):
    """ABC per parser di documenti — output uniforme `ParsedDoc`."""

    @abstractmethod
    async def parse(self, path: Path) -> ParsedDoc | None:
        """Parsa il file e ritorna `ParsedDoc`, oppure `None` se gate skip (es. status)."""

    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """Set di estensioni file gestite (es. {'.md'})."""
