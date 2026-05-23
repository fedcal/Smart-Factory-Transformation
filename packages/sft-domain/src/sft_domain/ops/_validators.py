"""Validator condivisi per i modelli OPS."""

from __future__ import annotations

from datetime import datetime


def tz_aware(v: datetime) -> datetime:
    """Rifiuta datetime naive (Pitfall 7 — Phase 4 cross-cutting).

    Tutti i campi datetime nei modelli OPS devono essere tz-aware.
    Esempio valido: `datetime.now(timezone.utc)` o `datetime(..., tzinfo=UTC)`.
    """
    if v.tzinfo is None:
        raise ValueError(
            f"Datetime field must be tz-aware, got naive: {v!r}. "
            "Use datetime.now(timezone.utc) or datetime(..., tzinfo=timezone.utc)."
        )
    return v
