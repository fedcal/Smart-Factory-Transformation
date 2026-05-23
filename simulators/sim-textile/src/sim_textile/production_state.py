"""ProductionState — dye_lot_id in-process state per asset (plan 06-09, D-QI-04).

Tiene traccia del lotto di tintura corrente di un asset; ruota a un nuovo lotto
ogni `rotation_interval` (default 60 min) di sim-time tramite
`secrets.token_hex(2)` per la parte sequenziale.

Nessuna persistenza Postgres in Fase 6 (D-QI-04): lo stato vive in-process nel
simulator. Il `dye_lot_id` ha forma `DL-<asset_id>-<YYYYMMDD>-<hex4>` e matcha
il regex `^DL-[A-Z0-9-]+-\\d{8}-[0-9a-f]+$` enforced da `QualityEvent`.

Sicurezza:
    - `secrets.token_hex` (CSPRNG) per evitare collisioni prevedibili (T-V6-injection).
    - `datetime.now(UTC)` SEMPRE tz-aware (Pattern S-6, T-V6-naive-datetime).

Nota stilistica: la dataclass NON e' `frozen` perche' rappresenta stato vivo
mutabile dell'asset (un "puntatore" al lotto corrente). L'immutabilita' globale
(coding-style.md) si applica ai modelli di dato condivisi (Pydantic
`QualityEvent`, `FaultProfile`, `EmitterState`); `ProductionState` e' invece
locale al loop dell'emitter ed e' incapsulata dietro `maybe_rotate`.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass
class ProductionState:
    """Stato in-process del lotto di tintura corrente per un singolo asset.

    Attributes:
        asset_id: Identificativo asset (es. "LOOM-01").
        current_dye_lot_id: Lotto corrente (formato `DL-<asset>-<YYYYMMDD>-<hex4>`).
        rotation_interval: Quanto sim-time deve passare prima di ruotare (default 60 min).
        _last_rotation: Timestamp UTC dell'ultima rotazione (per delta-check).
    """

    asset_id: str
    current_dye_lot_id: str
    rotation_interval: timedelta = timedelta(minutes=60)
    _last_rotation: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def bootstrap(cls, *, asset_id: str, now: datetime | None = None) -> ProductionState:
        """Crea uno stato iniziale con un primo dye_lot_id valido.

        Args:
            asset_id: Asset id (deve matchare il sotto-set di `[A-Z0-9-]+` per
                il regex di `dye_lot_id`).
            now: Istante di bootstrap (default `datetime.now(UTC)`).
        """
        if now is None:
            now = datetime.now(UTC)
        ymd = now.strftime("%Y%m%d")
        seq = secrets.token_hex(2)
        return cls(
            asset_id=asset_id,
            current_dye_lot_id=f"DL-{asset_id}-{ymd}-{seq}",
            _last_rotation=now,
        )

    def maybe_rotate(self, now: datetime) -> bool:
        """Ruota `current_dye_lot_id` se e' passato `rotation_interval` da `_last_rotation`.

        Args:
            now: Istante corrente (UTC tz-aware).

        Returns:
            True se la rotazione e' avvenuta, False altrimenti.
        """
        if (now - self._last_rotation) < self.rotation_interval:
            return False
        ymd = now.strftime("%Y%m%d")
        seq = secrets.token_hex(2)
        self.current_dye_lot_id = f"DL-{self.asset_id}-{ymd}-{seq}"
        self._last_rotation = now
        return True


__all__ = ["ProductionState"]
