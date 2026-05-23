"""Pydantic frozen schema for a single C-MAPSS record (26 columns).

Used as a typed validator at the model input boundary (V5 input validation).
Mirrors the canonical NASA C-MAPSS column layout — see Pattern 1 in
07-RESEARCH.md (`CMAPSS_COLUMNS`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CMAPSSRecord(BaseModel):
    """Frozen Pydantic model for one C-MAPSS row (26 columns).

    Per coding-style: immutable (frozen=True) + extra='forbid' to fail-fast on
    typos and slop input. All sensor fields are float; identifiers are int.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_number: int
    time_cycles: int
    op_setting_1: float
    op_setting_2: float
    op_setting_3: float
    s1: float
    s2: float
    s3: float
    s4: float
    s5: float
    s6: float
    s7: float
    s8: float
    s9: float
    s10: float
    s11: float
    s12: float
    s13: float
    s14: float
    s15: float
    s16: float
    s17: float
    s18: float
    s19: float
    s20: float
    s21: float
