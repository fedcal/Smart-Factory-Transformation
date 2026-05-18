"""Modelli Pydantic v2 per il registro asset della piattaforma IT/OT.

Tutti i modelli sono frozen=True, extra="forbid" per immutabilita' e validazione stretta.
Vedi: RESEARCH.md Pattern 1, T-03-01-pydantic (immutabilita' + strict schema), D-45.

Sicurezza:
    - Asset.opcua_namespace deve iniziare con "urn:mantis:" (T-03-01-pydantic, RESEARCH §Security checks 2)
    - extra="forbid" su Asset e Tag previene injection di campi arbitrari
    - yaml.safe_load obbligatorio nel loader (T-03-01-yaml, RESEARCH §Pitfall Tampering)
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class AssetFamily(str, Enum):
    """Famiglie di asset tessili (D-21 + D-44) — 5 valori."""

    LOOM = "loom"
    SPINNING = "spinning"
    WARPING = "warping"
    DYEING = "dyeing"
    FINISHING = "finishing"


class SemanticType(str, Enum):
    """Tipo semantico del tag sensore — 10 valori canonici."""

    TENSION = "tension"
    DENSITY = "density"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    VIBRATION = "vibration"
    SPEED = "speed"
    PRESSURE = "pressure"
    FLOW = "flow"
    PH = "ph"
    LEVEL = "level"


class Tag(BaseModel):
    """Definizione di un tag sensore su un asset tessile.

    Immutabile (frozen=True) — crea nuovi oggetti invece di mutare quelli esistenti.
    Extra fields sono vietati (extra="forbid") per validazione stretta del YAML (T-03-01-pydantic).
    """

    model_config = {"frozen": True, "extra": "forbid"}  # immutable, strict schema

    tag_id: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^[a-z][a-z0-9_]+$",
            description="Identificativo canonico del tag (snake_case, lowercase)",
        ),
    ]
    unit: Annotated[
        str,
        Field(min_length=1, description="Unita' di misura (es. N, picks_per_cm, degC)"),
    ]
    sample_rate_hz: Annotated[
        float,
        Field(gt=0, le=1000, description="Frequenza di campionamento in Hz (0 < rate <= 1000)"),
    ]
    semantic_type: Annotated[
        SemanticType,
        Field(description="Tipo semantico del tag (D-44 vocabulary)"),
    ]


class Asset(BaseModel):
    """Metadata di un asset fisico della piattaforma tessile IT/OT.

    Immutabile (frozen=True) — crea nuovi oggetti invece di mutare quelli esistenti.
    Extra fields sono vietati (extra="forbid") per validazione stretta del YAML (T-03-01-pydantic).
    opcua_namespace deve iniziare con "urn:mantis:" per allineamento al namespace OPC-UA del progetto.
    """

    model_config = {"frozen": True, "extra": "forbid"}  # immutable, strict schema

    asset_id: Annotated[
        str,
        Field(
            min_length=1,
            pattern=r"^[A-Z]+-\d{2}$",
            description="Identificativo canonico dell'asset (es. LOOM-01, SPIN-08)",
        ),
    ]
    asset_family: Annotated[
        AssetFamily,
        Field(description="Famiglia dell'asset (D-21 + D-44)"),
    ]
    line_id: Annotated[
        str,
        Field(min_length=1, description="Identificativo della linea produttiva"),
    ]
    opcua_namespace: Annotated[
        str,
        Field(
            min_length=1,
            description="Namespace OPC-UA dell'asset — deve iniziare con urn:mantis: (T-03-01-pydantic)",
        ),
    ]
    tags: Annotated[
        tuple[Tag, ...],
        Field(description="Definizioni dei tag sensore associati all'asset"),
    ] = ()
    status: Annotated[
        str,
        Field(
            pattern=r"^(active|inactive|maintenance)$",
            description="Stato operativo dell'asset (active|inactive|maintenance)",
        ),
    ] = "active"

    @field_validator("opcua_namespace")
    @classmethod
    def validate_opcua_namespace(cls, v: str) -> str:
        """Impone il prefisso urn:mantis: sul namespace OPC-UA (T-03-01-pydantic, RESEARCH §Security checks 2)."""
        if not v.startswith("urn:mantis:"):
            raise ValueError(
                f"opcua_namespace deve iniziare con 'urn:mantis:', "
                f"trovato: {v!r}. Usa il formato 'urn:mantis:<family>:<asset_id>'."
            )
        return v
