"""Anomaly + AnomalyBaseline (D-AD-02 — anomaly detector domain).

`Anomaly` rappresenta un evento out-of-band rilevato dal AnomalyDetector
agent. `AnomalyBaseline` rappresenta i confini operativi normali
(per `(asset_family, sensor_id)`) caricati da `anomaly_baselines.yaml`.

Tutti i modelli sono frozen=True, extra='forbid', tz-aware datetime.
Loader `load_anomaly_baselines()` e' lru_cached + yaml.safe_load only
(T-V6-yaml-injection / T-05-03-01).
"""

from __future__ import annotations

import pathlib
from datetime import datetime
from functools import lru_cache
from typing import Annotated, Literal
from uuid import UUID, uuid4

import yaml
from pydantic import BaseModel, Field, field_validator

from sft_domain.ops._validators import tz_aware

_YAML_PATH = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "anomaly_baselines.yaml"


Severity = Literal["minor", "major", "critical"]
"""Severity bands shared with QualityVerdict (D-QI-03)."""


class AnomalyBaseline(BaseModel):
    """Banda di normalita' per `(asset_family, sensor_id)`.

    `severity_mapping` mappa il livello di deviazione (in unita' della
    misura) alla severity. Le chiavi devono essere `minor`, `major`,
    `critical`; i valori sono soglie di deviazione cumulativa rispetto
    al limite della banda piu' vicino.

    Esempio:
        ```yaml
        asset_family: loom
        sensor_id: warp_tension
        low: 0.0
        high: 0.8
        unit: g
        severity_mapping:
          minor: 0.1
          major: 0.3
          critical: 0.6
        ```
    """

    model_config = {"frozen": True, "extra": "forbid"}

    asset_family: Annotated[str, Field(min_length=1, description="Famiglia asset (loom, spinning, dyeing, ...)")]
    sensor_id: Annotated[str, Field(min_length=1, description="Identificatore del tag/sensor")]
    low: Annotated[float, Field(description="Estremo inferiore della banda di normalita'")]
    high: Annotated[float, Field(description="Estremo superiore della banda di normalita'")]
    unit: Annotated[str, Field(min_length=1, description="Unita' di misura (es. 'g', 'degC', 'rpm')")]
    severity_mapping: Annotated[
        dict[str, float],
        Field(
            description="Mapping severity → soglia di deviazione (oltre il band edge). "
            "Chiavi: minor|major|critical; valori monotonicamente crescenti.",
        ),
    ]

    @field_validator("severity_mapping")
    @classmethod
    def _check_keys(cls, v: dict[str, float]) -> dict[str, float]:
        allowed = {"minor", "major", "critical"}
        bad = set(v.keys()) - allowed
        if bad:
            raise ValueError(f"severity_mapping keys must be subset of {allowed}, got extra: {bad}")
        return v

    def is_within_band(self, value: float) -> bool:
        """True se `value ∈ [low, high]`."""
        return self.low <= value <= self.high

    def severity_for(self, value: float) -> Severity:
        """Restituisce la severity (minor|major|critical) per un valore fuori banda.

        Calcola la deviazione rispetto al bordo della banda piu' vicino,
        poi confronta con `severity_mapping` in ordine decrescente di soglia.

        Per valori dentro banda → minor (chiamante dovrebbe controllare
        `is_within_band` prima per evitare falsi allarmi).
        """
        if value < self.low:
            deviation = self.low - value
        elif value > self.high:
            deviation = value - self.high
        else:
            deviation = 0.0

        # Threshold attesi: minor < major < critical
        thresholds = sorted(self.severity_mapping.items(), key=lambda kv: kv[1])
        chosen: Severity = "minor"
        for label, threshold in thresholds:
            if deviation >= threshold:
                chosen = label  # type: ignore[assignment]
        return chosen


class Anomaly(BaseModel):
    """Anomalia rilevata su un sensor di un asset (D-AD-02)."""

    model_config = {"frozen": True, "extra": "forbid"}

    id: Annotated[UUID, Field(default_factory=uuid4, description="Identificatore univoco evento")]
    asset_id: Annotated[str, Field(min_length=1, description="Asset coinvolto (es. LOOM-01)")]
    sensor_id: Annotated[str, Field(min_length=1, description="Sensor/tag identifier")]
    value: Annotated[float, Field(description="Valore osservato fuori banda")]
    baseline_low: Annotated[float, Field(description="Estremo inferiore baseline applicata")]
    baseline_high: Annotated[float, Field(description="Estremo superiore baseline applicata")]
    timestamp: Annotated[datetime, Field(description="UTC tz-aware timestamp dell'osservazione")]
    severity: Annotated[Severity, Field(description="Severity bucket: minor|major|critical")]

    @field_validator("timestamp")
    @classmethod
    def _tz(cls, v: datetime) -> datetime:
        return tz_aware(v)


@lru_cache(maxsize=1)
def load_anomaly_baselines(
    path: pathlib.Path | None = None,
) -> dict[tuple[str, str], AnomalyBaseline]:
    """Carica anomaly_baselines.yaml restituendo dict keyed da (asset_family, sensor_id).

    Args:
        path: Override path per test; default punta a `packages/sft-domain/anomaly_baselines.yaml`.

    Returns:
        Dict immutabile in pratica: chiamate ripetute restituiscono lo stesso oggetto (lru_cache).

    Raises:
        FileNotFoundError: Se il YAML non esiste.
        ValueError: Se la chiave 'anomaly_baselines' manca o non e' una lista.
        ValidationError: Se un entry non rispetta lo schema AnomalyBaseline.
    """
    yaml_path = path or _YAML_PATH
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"anomaly_baselines.yaml non trovato: {yaml_path}. "
            f"Assicurati che il file esista in {yaml_path.parent}."
        )
    raw_text = yaml_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load (T-V6-yaml-injection)
    if not isinstance(raw_data, dict) or "anomaly_baselines" not in raw_data:
        raise ValueError(
            f"anomaly_baselines.yaml deve contenere un dict con chiave 'anomaly_baselines', "
            f"trovato: {type(raw_data).__name__}"
        )
    entries = raw_data["anomaly_baselines"]
    if not isinstance(entries, list):
        raise ValueError(
            f"La chiave 'anomaly_baselines' deve contenere una lista, "
            f"trovato: {type(entries).__name__}"
        )
    result: dict[tuple[str, str], AnomalyBaseline] = {}
    for entry in entries:
        baseline = AnomalyBaseline.model_validate(entry)
        result[(baseline.asset_family, baseline.sensor_id)] = baseline
    return result


def invalidate_anomaly_baselines_cache() -> None:
    """Svuota la cache del loader (utile nei test)."""
    load_anomaly_baselines.cache_clear()
