"""ISO 50001 EnPI computation — pure function (EnergyOptimizer SCM-02, Plan 09-03).

Implements compute_enpi() as a deterministic pure function:
    enpi_actual = sum(kwh_valid) / sum(kg_valid)  (slots with kg > 0 only)
    deviation_pct = (enpi_actual - baseline) / baseline * 100
    is_above_baseline = enpi_actual > baseline
    off_peak_kwh_pct = off_peak_kwh / total_kwh * 100  (ALL slots, not just valid)

No LLM, no asyncpg, fully synchronous.

Pattern source: 09-RESEARCH.md Pattern 7 (verbatim + frozen dataclass).

Security note (T-09-14): compute_enpi guards kg > 0 and raises ValueError when no
valid slot exists. The EnpiReport is a frozen dataclass — post-construction mutation
is impossible (CR-05 clamp discipline: callers clamp before calling compute_enpi).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnpiReport:
    """ISO 50001 Energy Performance Indicator report (frozen dataclass).

    Fields:
        process:           Process name (e.g. 'dyeing', 'finishing').
        kwh_total:         Sum of kWh for valid slots (kg > 0).
        kg_total:          Sum of kg for valid slots (kg > 0).
        enpi_actual:       kWh/kg measured in the period (rounded to 4dp).
        enpi_baseline:     kWh/kg target from scm.enpi_baseline (ISO 50001).
        deviation_pct:     (actual - baseline) / baseline * 100 (rounded to 2dp).
        is_above_baseline: True when enpi_actual > enpi_baseline.
        off_peak_kwh_pct:  Fraction of total kWh in off-peak hours (rounded to 2dp).
                           Uses ALL kwh_readings (not just valid kg>0 slots).
    """

    process: str
    kwh_total: float
    kg_total: float
    enpi_actual: float
    enpi_baseline: float
    deviation_pct: float
    is_above_baseline: bool
    off_peak_kwh_pct: float


def compute_enpi(
    kwh_readings: list[float],
    kg_readings: list[float],
    enpi_baseline_kwh_per_kg: float,
    is_peak_hour_flags: list[bool],
    *,
    process: str = "computed",
) -> EnpiReport:
    """Compute ISO 50001 Energy Performance Indicator (pure function).

    Args:
        kwh_readings:             List of kWh measurements for each time slot.
        kg_readings:              List of kg processed in each slot. Slots with
                                  kg <= 0 or None are excluded from EnPI computation.
        enpi_baseline_kwh_per_kg: ISO 50001 target kWh/kg (from scm.enpi_baseline).
        is_peak_hour_flags:       True when slot was during peak tariff hours.
                                  Used to compute off_peak_kwh_pct over ALL slots.
        process:                  Process label for the report (default "computed").

    Returns:
        EnpiReport with actual vs baseline comparison.

    Raises:
        ValueError: When no slot with kg > 0 exists — an EnPI with no valid
                    production data is meaningless; callers must handle this.

    Notes:
        - off_peak_kwh_pct is computed over ALL kwh_readings, not only valid slots.
        - Rounding: enpi_actual to 4dp; deviation_pct and off_peak_kwh_pct to 2dp.
        - This is LLM-free and fully deterministic given the same inputs.
    """
    # Filter slots where kg_processed is known and positive (skip kg=0 or None).
    valid_pairs = [
        (kwh, kg)
        for kwh, kg in zip(kwh_readings, kg_readings)
        if kg and kg > 0
    ]

    if not valid_pairs:
        raise ValueError("Nessun dato valido (kg > 0) nei readings forniti")

    kwh_total = sum(k for k, _ in valid_pairs)
    kg_total = sum(g for _, g in valid_pairs)

    # CR-05: kg_total > 0 is guaranteed by the filter above; guard for safety.
    enpi_actual = kwh_total / kg_total if kg_total > 0 else float("inf")

    deviation_pct = (
        (enpi_actual - enpi_baseline_kwh_per_kg) / enpi_baseline_kwh_per_kg * 100
    )

    # off_peak_kwh_pct uses ALL kwh_readings (not just valid kg>0 slots).
    total_kwh_all = sum(kwh_readings)
    off_peak_kwh = sum(
        k for k, flag in zip(kwh_readings, is_peak_hour_flags) if not flag
    )
    off_peak_pct = off_peak_kwh / total_kwh_all * 100 if total_kwh_all > 0 else 0.0

    return EnpiReport(
        process=process,
        kwh_total=kwh_total,
        kg_total=kg_total,
        enpi_actual=round(enpi_actual, 4),
        enpi_baseline=enpi_baseline_kwh_per_kg,
        deviation_pct=round(deviation_pct, 2),
        is_above_baseline=enpi_actual > enpi_baseline_kwh_per_kg,
        off_peak_kwh_pct=round(off_peak_pct, 2),
    )


__all__ = ["EnpiReport", "compute_enpi"]
