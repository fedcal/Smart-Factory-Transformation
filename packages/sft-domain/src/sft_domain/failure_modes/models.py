"""Modelli Pydantic v2 per il registro delle failure mode tessili.

FailureMode descrive una modalita' di guasto/difetto del processo tessile (D-65).
Ogni entry e' input per:
    - Plan 05-08 Neo4j graph builder (nodo FailureMode + edges DOCUMENTED_BY -> SOP)
    - Plan 05-09 traverse_graph tool (lookup SOP per failure mode)
    - Plan 06-04 Wave 1 OPS extension: hitl_tier + setup_minutes + severity_band
      (D-QI-03 severity bands, D-PP-01 scheduling setup time).
    - Plan 07-02 Wave 1 MNT extension: maintenance taxonomy (D-MNT-TAX)
      con reason_code + MTTR target + intervention SOP id + preventive check.

Tutti i modelli sono frozen=True, extra="forbid" per immutabilita' e validazione stretta
(RESEARCH.md Pattern 1, T-05-03-02 strict schema).

Le estensioni Phase 6 e Phase 7 sono backward-compatible: tutti i nuovi campi sono
optional con default (Pattern G non-breaking — vedi 07-PATTERNS.md Shared Pattern G).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class MaintenanceSpec(BaseModel):
    """Metadati di manutenzione associati a una FailureMode (D-MNT-TAX, Phase 7).

    Immutabile (frozen=True) + extra='forbid' per validazione stretta del YAML.

    Convenzioni:
        - reason_code: codice ISO 14224-style ``<MODULE>-<DEFECT_ABBR>-<NNN>``
          (es. ``WEAVING-BE-001``). Unico tra tutte le FailureMode (enforced
          dal validator ``scripts/validate-failure-modes.py``).
        - mttr_target_minutes: target Mean Time To Repair in minuti, range
          [0, 10080] (0..1 settimana). Usato dal downtime_event_generator
          (07-05) per simulazioni Pareto e da DowntimeAnalyzer (07-09).
        - intervention_steps_sop_id: id SOP del corpus Phase 5
          (regex ``^SOP-[A-Z0-9-]+$``). Il validator risolve il riferimento
          contro il SOP corpus (warn-only di default, ``--strict-sop`` per fail).
        - preventive_check_interval_hours: opzionale; intervallo PM in ore
          (>= 1 quando presente). None = nessuna manutenzione preventiva.

    Esempio:
        MaintenanceSpec(
            reason_code="WEAVING-BE-001",
            mttr_target_minutes=30,
            intervention_steps_sop_id="SOP-LOOM-001",
            preventive_check_interval_hours=168,
        )
    """

    model_config = {"frozen": True, "extra": "forbid"}

    reason_code: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^[A-Z][A-Z0-9-]+$",
            description=(
                "Codice motivazione ISO 14224-style "
                "(es. 'WEAVING-BE-001'); unico tra le FailureMode."
            ),
        ),
    ]
    mttr_target_minutes: Annotated[
        int,
        Field(
            ge=0,
            le=10080,
            description="Target Mean Time To Repair in minuti (0..10080 = 1 settimana).",
        ),
    ]
    intervention_steps_sop_id: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^SOP-[A-Z0-9-]+$",
            description=(
                "Id SOP intervento (es. 'SOP-LOOM-001'); deve esistere "
                "nel corpus Phase 5 (verificato da validate-failure-modes.py)."
            ),
        ),
    ]
    preventive_check_interval_hours: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description=(
                "Intervallo manutenzione preventiva in ore (>=1). "
                "None = nessuna manutenzione preventiva pianificata."
            ),
        ),
    ] = None


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

    # ------------------------------------------------------------------
    # Phase 7 (plan 07-02) extension — D-MNT-TAX maintenance taxonomy
    # backward-compatible (optional + default None — Pattern G non-breaking)
    # ------------------------------------------------------------------
    maintenance: Annotated[
        MaintenanceSpec | None,
        Field(
            default=None,
            description=(
                "Metadati manutenzione (D-MNT-TAX Phase 7, optional). "
                "Quando presente fornisce reason_code, MTTR target, "
                "intervention SOP id e intervallo preventive check."
            ),
        ),
    ] = None
