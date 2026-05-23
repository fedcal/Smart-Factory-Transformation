"""Registro delle failure mode (modalita' di guasto/difetto) del processo tessile.

Espone:
    FailureMode                                  — modello Pydantic frozen (D-65)
    MaintenanceSpec                              — metadati manutenzione (D-MNT-TAX)
    load_failure_modes() -> tuple[FailureMode]   — loader lru_cache singleton
    load_failure_modes_dict() -> dict[str, FailureMode] — lookup O(1) per id
    invalidate_cache()                           — utility test per resettare la cache
"""

from sft_domain.failure_modes._loader import (
    invalidate_cache,
    load_failure_modes,
    load_failure_modes_dict,
)
from sft_domain.failure_modes.models import FailureMode, MaintenanceSpec

__all__ = [
    "FailureMode",
    "MaintenanceSpec",
    "load_failure_modes",
    "load_failure_modes_dict",
    "invalidate_cache",
]
