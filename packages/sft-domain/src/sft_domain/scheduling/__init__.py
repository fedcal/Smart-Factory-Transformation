"""Euristiche di scheduling pure-function (D-PP-03 + RESEARCH §Pattern 5).

Espone:
    schedule_spt(orders, capacity, failure_modes, horizon_start, horizon_end) -> ScheduleDraft
    schedule_edd(...)                                                          -> ScheduleDraft

Le funzioni sono PURE: nessun side effect, deterministiche su input identici.
Il rationale LLM (rationale_md) e' generato fuori da questo modulo
(production-planner agent post-scheduling, RESEARCH lines 656-666).
"""

from sft_domain.scheduling.heuristic import schedule_edd, schedule_spt

__all__ = ["schedule_edd", "schedule_spt"]
