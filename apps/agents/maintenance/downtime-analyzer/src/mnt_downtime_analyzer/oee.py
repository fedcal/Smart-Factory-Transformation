"""OEE decomposition stub (plan 07-09, D-DA-02/03).

Full implementation in Task 3. This stub satisfies imports during Task 2.
"""

from __future__ import annotations

__all__ = [
    "compute_availability",
    "compute_oee",
    "compute_pareto",
    "compute_performance",
    "compute_quality_cross_cluster",
]


def compute_availability(
    *,
    window_start: object,
    window_end: object,
    downtime_minutes: int,
    planned_production_minutes: int | None = None,
) -> float:
    raise NotImplementedError("compute_availability stub — Task 3 implements this.")


async def compute_performance(
    *,
    asset_id: str | None,
    window_start: object,
    window_end: object,
    production_state_reader: object = None,
) -> float:
    raise NotImplementedError("compute_performance stub — Task 3 implements this.")


async def compute_quality_cross_cluster(
    *,
    asset_id: str | None,
    window_start: object,
    window_end: object,
    quality_reader: object,
    sim_fallback_reader: object = None,
) -> tuple[float, str]:
    raise NotImplementedError("compute_quality_cross_cluster stub — Task 3 implements this.")


async def compute_oee(
    *,
    asset_id: str | None,
    window_start: object,
    window_end: object,
    repository: object,
    quality_reader: object,
    production_state_reader: object = None,
    sim_fallback_reader: object = None,
    planned_production_minutes: int | None = None,
) -> tuple[float, float, float, float, int, int]:
    raise NotImplementedError("compute_oee stub — Task 3 implements this.")


def compute_pareto(
    rows: list[tuple[str, int, int]],
    top_n: int = 10,
) -> list:  # type: ignore[type-arg]
    raise NotImplementedError("compute_pareto stub — Task 3 implements this.")
