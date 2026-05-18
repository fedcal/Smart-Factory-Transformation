"""Textile line simulator: loom, spinning, warping machine event generation (Fase 3).

Espone i modelli principali e i loader per l'utilizzo esterno.
"""

from sim_textile.models import (
    BaselineValue,
    EmitterState,
    FaultInjection,
    FaultProfile,
)
from sim_textile.profile_loader import load_all_profiles, load_profile

__version__ = "0.1.0"

__all__ = [
    "BaselineValue",
    "EmitterState",
    "FaultInjection",
    "FaultProfile",
    "load_all_profiles",
    "load_profile",
]
