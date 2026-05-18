"""Modelli Pydantic v2 per sim-textile: fault injection profiles + emitter state.

Tutti i modelli Pydantic sono frozen=True, extra="forbid" per immutabilita' e
validazione stretta (Pattern S-1, T-03-03-pydantic).

EmitterState e' un dataclass frozen con mutazione via dataclasses.replace
(Pattern S-1 immutability, IOT-03).

Sicurezza:
    - FaultProfile.fault_injection.nan_probability validato 0..1 (T-03-03-pydantic)
    - FaultInjection.jitter.band_pct validato 0..100
    - FaultProfile.sample_rate_hz validato > 0 e <= 1000 (T-03-03-dos-emit)
    - extra="forbid" previene injection di campi arbitrari da YAML esterno
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from sft_assets._models import AssetFamily


class BaselineValue(BaseModel):
    """Valore baseline per un tag sensore in condizioni nominali."""

    model_config = {"frozen": True, "extra": "forbid"}

    value: float
    unit: str


class DriftConfig(BaseModel):
    """Configurazione fault drift — deriva incrementale nel tempo."""

    model_config = {"frozen": True, "extra": "forbid"}

    enabled: bool
    rate_per_hour: Annotated[float, Field(ge=0, description="Tasso drift per ora")] = 0.0
    affected_tags: tuple[str, ...] = ()


class JitterConfig(BaseModel):
    """Configurazione fault jitter — rumore casuale attorno al valore nominale."""

    model_config = {"frozen": True, "extra": "forbid"}

    enabled: bool
    band_pct: Annotated[
        float, Field(ge=0, le=100, description="Ampiezza jitter in % del valore nominale")
    ] = 0.0
    affected_tags: tuple[str, ...] = ()


class BurstNoiseConfig(BaseModel):
    """Configurazione fault burst noise — picco temporaneo di rumore."""

    model_config = {"frozen": True, "extra": "forbid"}

    enabled: bool
    magnitude_pct: float = 0.0
    duration_s: float = 0.0
    period_s: float = 0.0
    affected_tags: tuple[str, ...] = ()


class AlarmStormConfig(BaseModel):
    """Configurazione fault alarm storm — valanga di allarmi entro finestra temporale."""

    model_config = {"frozen": True, "extra": "forbid"}

    enabled: bool
    threshold_events: Annotated[
        int, Field(ge=1, description="Numero minimo eventi per scatenare alarm storm")
    ] = 50
    window_s: float = 30.0
    affected_tags: tuple[str, ...] = ()


class FaultInjection(BaseModel):
    """Configurazione completa di fault injection per un asset_family."""

    model_config = {"frozen": True, "extra": "forbid"}

    nan_probability: Annotated[
        float,
        Field(ge=0, le=1, description="Probabilita' di NaN per disconnessione sensore (0..1)"),
    ] = 0.0
    drift: DriftConfig
    jitter: JitterConfig
    burst_noise: BurstNoiseConfig
    alarm_storm: AlarmStormConfig


class FaultProfile(BaseModel):
    """Profilo fault injection completo per un asset_family.

    Caricato da profiles/{family}.yaml tramite profile_loader.load_profile().
    Immutabile (frozen=True) — crea nuovi oggetti invece di mutare quelli esistenti.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    asset_family: AssetFamily
    sample_rate_hz: Annotated[
        float,
        Field(gt=0, le=1000, description="Frequenza di campionamento Hz (0 < rate <= 1000)"),
    ]
    fault_injection: FaultInjection
    default_baseline: dict[str, BaselineValue]


@dataclass(frozen=True)
class EmitterState:
    """Stato immutabile dell'emitter per un asset.

    Mutazione via dataclasses.replace() — mai in-place (Pattern S-1, IOT-03).
    RESEARCH §Pattern 2 (lines 482-485): replace-based mutation.

    Attributes:
        drift_accumulated: Deriva cumulata dal valore nominale.
        recent_alarms: Tuple di timestamp allarmi recenti per alarm storm detection.
        burst_t_started: Timestamp inizio burst noise attivo, None se non in burst.
    """

    drift_accumulated: float = 0.0
    recent_alarms: tuple[datetime, ...] = ()
    burst_t_started: datetime | None = None
