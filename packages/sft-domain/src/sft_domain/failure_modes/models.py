"""Modelli Pydantic v2 per il registro delle failure mode tessili.

FailureMode descrive una modalita' di guasto/difetto del processo tessile (D-65).
Ogni entry e' input per:
    - Plan 05-08 Neo4j graph builder (nodo FailureMode + edges DOCUMENTED_BY -> SOP)
    - Plan 05-09 traverse_graph tool (lookup SOP per failure mode)
    - Plan 06-04 Wave 1 OPS extension: hitl_tier + setup_minutes + severity_band
      (D-QI-03 severity bands, D-PP-01 scheduling setup time).

Tutti i modelli sono frozen=True, extra="forbid" per immutabilita' e validazione stretta
(RESEARCH.md Pattern 1, T-05-03-02 strict schema).

L'estensione Phase 6 e' backward-compatible: tutti i nuovi campi sono optional con default.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

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
            hitl_tier="supervisor",
            setup_minutes=15,
            severity_band={"critical": {"safety_risk": True}},
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

    # ------------------------------------------------------------------
    # Phase 6 (plan 06-04) extension — backward-compatible (optional + default)
    # ------------------------------------------------------------------
    hitl_tier: Annotated[
        Literal["auto-log", "supervisor", "manager+safety"],
        Field(
            default="supervisor",
            description=(
                "HITL routing tier per OPS agents (D-QI-03): "
                "auto-log = nessuna escalation, "
                "supervisor = approvazione supervisore, "
                "manager+safety = approvazione manager + safety interlock."
            ),
        ),
    ] = "supervisor"

    setup_minutes: Annotated[
        int,
        Field(
            default=0,
            ge=0,
            description=(
                "Minuti di setup aggiuntivi (D-PP-01) imposti dall'occorrenza di "
                "questa failure mode (usati dallo scheduler per il sequencing)."
            ),
        ),
    ] = 0

    severity_band: Annotated[
        dict[str, Any],
        Field(
            default_factory=dict,
            description=(
                "Override per banda di severity (minor|major|critical) — es. "
                "{'minor': {'max_frequency_per_meter': 5}, 'critical': {'safety_risk': True}}."
            ),
        ),
    ]
