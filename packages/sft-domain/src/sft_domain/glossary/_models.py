"""Modelli Pydantic v2 per il glossario bilingue IT/EN.

Tutti i modelli sono frozen=True, extra="forbid" per immutabilità e validazione stretta.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Category(str, Enum):
    """Categorie tassonomiche del glossario (D-30)."""

    TEXTILE_PROCESS = "textile-process"
    TEXTILE_ASSET = "textile-asset"
    TEXTILE_DEFECT = "textile-defect"
    TEXTILE_KPI = "textile-kpi"
    TEXTILE_TOOL_PPE = "textile-tool-ppe"
    TEXTILE_MATERIAL = "textile-material"
    AGENTIC_PLATFORM = "agentic-platform"
    AGENTIC_TOOL = "agentic-tool"
    REGULATORY = "regulatory"


class Source(str, Enum):
    """Fonte di autorita del termine."""

    INDUSTRY_STANDARD = "industry-standard"
    ISO_STANDARD = "iso-standard"
    PROJECT_SPECIFIC = "project-specific"
    AGENTIC_COMMUNITY = "agentic-community"


class Term(BaseModel):
    """Termine del glossario bilingue.

    Immutabile (frozen=True) — crea nuovi oggetti invece di mutare quelli esistenti.
    Extra fields sono vietati (extra="forbid") per validazione stretta del YAML.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    term: Annotated[str, Field(min_length=1, description="Nome canonico del termine")]
    definition: Annotated[
        str, Field(min_length=10, description="Definizione nel contesto textile/agentic")
    ]
    category: Annotated[Category, Field(description="Categoria tassonomica (D-30)")]
    related_terms: Annotated[
        list[str],
        Field(description="Termini correlati nel glossario"),
    ] = []
    examples: Annotated[
        list[str],
        Field(description="Esempi d'uso contestualizzati"),
    ] = []
    source: Annotated[
        Source,
        Field(description="Fonte di autorita"),
    ] = Source.INDUSTRY_STANDARD
    no_direct_equivalent: Annotated[
        bool,
        Field(
            description="True se il termine non ha equivalente diretto nell'altra lingua (D-31)",
        ),
    ] = False
