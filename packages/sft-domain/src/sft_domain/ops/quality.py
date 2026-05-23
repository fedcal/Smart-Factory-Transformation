"""QualityEvent + QualityVerdict (D-QI-01..04 — quality inspector domain).

`QualityEvent` rappresenta un'osservazione di difetto su un rotolo di tessuto
(emessa da simulator o operator). `QualityVerdict` e' l'output strutturato
dell'agent QualityInspector secondo le regole ASTM D5430 four-point grading.

Tutti i modelli sono frozen=True, extra='forbid', tz-aware datetime.
`dye_lot_id` segue il pattern D-QI-04: ^DL-[A-Z0-9-]+-\\d{8}-[0-9a-f]+$.
`score` e' vincolato in [0..4] (T-V6-injection-score).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from sft_domain.ops._validators import tz_aware
from sft_domain.ops.citation import RagCitation

DefectType = Literal[
    "broken_end",
    "mispick",
    "slub",
    "neppy",
    "selvage_fault",
    "shade_deviation",
    "unlevel_dyeing",
]
"""I 7 tipi di difetto core della tassonomia textile di Fase 2."""

Severity = Literal["minor", "major", "critical"]
"""Severity tiers D-QI-03 (shared with Anomaly.severity)."""


class QualityEvent(BaseModel):
    """Difetto osservato su un rotolo di tessuto (input QualityInspector)."""

    model_config = {"frozen": True, "extra": "forbid"}

    event_id: Annotated[UUID, Field(default_factory=uuid4, description="Identificatore evento")]
    asset_id: Annotated[str, Field(min_length=1, description="Asset che ha generato il difetto")]
    dye_lot_id: Annotated[
        str,
        Field(
            pattern=r"^DL-[A-Z0-9-]+-\d{8}-[0-9a-f]+$",
            description="Dye-lot identifier (D-QI-04 regex).",
        ),
    ]
    defect_type: Annotated[DefectType, Field(description="Tipo difetto (7-defect taxonomy)")]
    defect_length_inches: Annotated[float, Field(ge=0.0, description="Lunghezza difetto in inches (>=0)")]
    full_width: Annotated[bool, Field(default=False, description="Difetto a tutta larghezza (selvedge-to-selvedge)")]
    position_meters: Annotated[float, Field(description="Posizione metro lineare sul rotolo")]
    timestamp: Annotated[datetime, Field(description="UTC tz-aware osservazione")]
    source: Annotated[
        Literal["simulator", "operator"],
        Field(description="Sorgente dell'evento: simulator o operator"),
    ]

    @field_validator("timestamp")
    @classmethod
    def _tz(cls, v: datetime) -> datetime:
        return tz_aware(v)


class QualityVerdict(BaseModel):
    """Verdetto strutturato del QualityInspector (D-QI-01..03).

    `score` ∈ [0..4] secondo ASTM D5430 (T-V6-injection-score — Pydantic enforce).
    `citations` lista di RagCitation a SOP/glossary che giustificano lo score.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    score: Annotated[int, Field(ge=0, le=4, description="ASTM D5430 four-point score 0..4")]
    severity: Annotated[Severity, Field(description="Severity bucket: minor|major|critical (D-QI-03)")]
    rationale_md: Annotated[str, Field(description="Markdown rationale dell'agent")]
    citations: Annotated[
        list[RagCitation],
        Field(default_factory=list, description="Citazioni RAG a SOP/glossary"),
    ]
