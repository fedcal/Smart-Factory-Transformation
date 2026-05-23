"""MTTR computation helpers for MaintenanceCoach (MNT-03).

Two KPI helpers serve the maintenance reporting layer:
  - ``compute_mttr_minutes``: pause-inclusive elapsed time (MTTR proper)
  - ``compute_active_work_minutes``: active-only time (sum of step durations)

Both accept either a ``CoachThreadState`` Pydantic instance or a plain dict
(defensive — LangGraph checkpoint replay may deserialize to dict shape before
Pydantic re-validation in some LangGraph versions).

Threat mitigation (T-V7-coach-mttr-negative):
  ``compute_mttr_minutes`` raises ``ValueError`` if ``mttr_end < mttr_start``.
  This prevents silent KPI corruption from clock skew or out-of-order replay.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from mnt_maintenance_coach.models import CoachThreadState


def _extract_field(state: Union["CoachThreadState", dict[str, Any]], field: str) -> Any:
    """Extract a field from either a Pydantic model or a dict."""
    if isinstance(state, dict):
        return state[field]
    return getattr(state, field)


def compute_mttr_minutes(
    state: Union["CoachThreadState", dict[str, Any]],
) -> int | None:
    """Compute pause-inclusive MTTR in minutes.

    Returns:
        ``int`` MTTR in minutes if ``mttr_end`` is set.
        ``None`` if the intervention is still open (``mttr_end is None``).

    Raises:
        ValueError: if ``mttr_end < mttr_start`` (clock skew / replay corruption).
            This is a hard error — negative MTTR is invalid and must not silently
            corrupt the KPI (T-V7-coach-mttr-negative mitigation).

    Note:
        Uses ``int(total_seconds / 60)`` (floor division) — fractional minutes
        are truncated, not rounded. This is intentional: MTTR reporting errs
        on the side of slightly underreporting elapsed time, which is the
        conservative choice for SLO compliance checks.
    """
    mttr_start: datetime = _extract_field(state, "mttr_start")
    mttr_end: datetime | None = _extract_field(state, "mttr_end")

    if mttr_end is None:
        return None

    delta = mttr_end - mttr_start
    total_seconds = delta.total_seconds()

    if total_seconds < 0:
        raise ValueError(
            f"mttr_end {mttr_end!r} < mttr_start {mttr_start!r}: "
            "negative MTTR detected. This indicates clock skew or "
            "invalid state replay. Cannot compute KPI safely."
        )

    return int(total_seconds / 60)


def compute_active_work_minutes(
    state: Union["CoachThreadState", dict[str, Any]],
) -> int:
    """Compute active work time in minutes (exclusive of pauses).

    Sums ``StepReport.duration_minutes`` for all completed steps.
    This is the "hands-on" time only — it excludes shift handovers,
    technician pauses, and supervisor review windows.

    Returns:
        ``int``: total active work minutes; 0 if no steps completed yet.

    Note:
        For the cross-shift scenario, MTTR >> active_work is expected and
        correct (e.g. MTTR=1800, active_work=120 for an overnight repair).
        The gap represents waiting time tracked by Phase 11 TTL warnings.
    """
    completed_steps = _extract_field(state, "completed_steps")

    if not completed_steps:
        return 0

    total = 0
    for step in completed_steps:
        if isinstance(step, dict):
            total += step["duration_minutes"]
        else:
            total += step.duration_minutes

    return total


__all__ = ["compute_active_work_minutes", "compute_mttr_minutes"]
