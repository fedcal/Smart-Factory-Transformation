"""Modelli Pydantic v2 per il registro delle failure mode tessili.

FailureMode descrive una modalita' di guasto/difetto del processo tessile (D-65).
Ogni entry e' input per:
    - Plan 05-08 Neo4j graph builder (nodo FailureMode + edges DOCUMENTED_BY -> SOP)
    - Plan 05-09 traverse_graph tool (lookup SOP per failure mode)

Tutti i modelli sono frozen=True, extra="forbid" per immutabilita' e validazione stretta
(RESEARCH.md Pattern 1, T-05-03-02 strict schema).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class FailureMode(BaseModel):
    """Modalita' di guasto/difetto del processo tessile.

    Immutabile (frozen=True) — crea nuovi oggetti invece di mutare quelli esistenti.
    Extra fields sono vietati (extra="forbid") per validazione stretta del YAML.

    Esempio:
        FailureMode(
            id="broken_end",
            name_it="rottura filo ordito",
            name_en="broken end",
            asset_families=["weaving"],
            parts=["warp", "heddle"],
            severity="medium",
        )
    """

    model_config = {"frozen": True, "extra": "forbid"}  # immutable, strict schema

    id: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^[a-z][a-z0-9_]*$",
            description="Identificatore snake_case lowercase (es. 'broken_end')",
        ),
    ]
    name_it: Annotated[
        str,
        Field(min_length=1, description="Nome italiano del difetto (es. 'rottura filo ordito')"),
    ]
    name_en: Annotated[
        str,
        Field(min_length=1, description="Nome inglese del difetto (es. 'broken end')"),
    ]
    asset_families: Annotated[
        list[str],
        Field(
            min_length=1,
            description="Famiglie di asset coinvolte (es. ['weaving'])",
        ),
    ]
    parts: Annotated[
        list[str],
        Field(
            min_length=1,
            description="Parti/componenti coinvolte (es. ['warp', 'heddle'])",
        ),
    ]
    severity: Annotated[
        Literal["low", "medium", "high"],
        Field(description="Severita': low | medium | high (high = safety-critical)"),
    ] = "medium"
