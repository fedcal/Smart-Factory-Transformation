"""Postgres-backed sliding-window rate limiter (D-AD-03, Phase 6 Plan 06-02).

Implements OPS-04: a per-agent global limit of N actions per rolling window
derived from ``audit.actions`` rather than per-process state. This is the
caller-side companion used by ``AnomalyDetector`` (Plan 06-06) to enforce
12 ANOMALY_ALERTs/hour without flooding the HITL queue.

Why query audit instead of Redis/in-memory state?
    * Restart resilience — a freshly-started container reads the same count
      from the source of truth.
    * Audit-as-evidence — every counted action is already a forensic record;
      no separate eventually-consistent counter to drift.
    * Zero new infra — reuses the asyncpg pool already provisioned for the
      audit writer (Plan 04-02), no Redis dependency to add.

Concurrency note (D-AD-03 documented intent — T-V6-throttle accepted):
    Two parallel callers can both observe ``count == limit-1`` and both
    proceed, briefly exceeding the limit under MVCC. The semantic is
    "approximately ``limit``" — not strictly bounded. Phase 11 may upgrade
    to ``SELECT ... FOR UPDATE`` or a sequence-based counter if telemetry
    shows >13/hour spikes in production.

Pitfall §3 / scope:
    This module is **read-only** against ``audit.actions``. Writing the
    ``Decision.SUPPRESSED`` audit row when the limit is hit is the caller's
    responsibility (the rate limiter does not know which AuditRecord shape
    or AuditWriter instance to use — keeping concerns separated).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

# T-V5-sql / T-V6-sql-injection: SQL constants only. Window value is computed
# in Python and passed as $3 — never f-string interpolated.
_COUNT_RECENT_SQL: str = (
    "SELECT COUNT(*) FROM audit.actions "
    "WHERE agent_id = $1 AND action_type = $2 AND ts >= $3"
)

_log = structlog.get_logger("runtime.rate_limit")


class RateLimiter:
    """Per-agent sliding-window rate limiter backed by ``audit.actions``.

    Parameters
    ----------
    pool:
        Live ``asyncpg.Pool`` bound to the audit database. Must not be
        ``None`` — connection lifecycle is the caller's responsibility.
    agent_id:
        Logical agent identifier matching ``audit.actions.agent_id``
        (e.g. ``"anomaly-detector"``). Empty strings rejected.
    limit:
        Maximum permitted actions in the window. Default 12 (D-AD-03).
    window_minutes:
        Sliding window length in minutes. Default 60 (D-AD-03).

    Raises
    ------
    ValueError
        When ``pool`` is ``None`` or ``agent_id`` is empty.
    """

    def __init__(
        self,
        *,
        pool: Any,
        agent_id: str,
        limit: int = 12,
        window_minutes: int = 60,
    ) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        if not agent_id:
            raise ValueError("agent_id must not be empty")
        self._pool = pool
        self._agent_id = agent_id
        self._limit = int(limit)
        self._window = timedelta(minutes=int(window_minutes))

    async def check_and_emit(self, action_type: str) -> tuple[bool, int]:
        """Return ``(allowed, current_count)`` for ``action_type``.

        ``allowed`` is ``True`` iff fewer than ``self._limit`` audit rows
        match (``agent_id``, ``action_type``) inside the current sliding
        window. ``current_count`` is the raw COUNT(*) — the caller can log
        it, attach it to an emitted ``Decision.SUPPRESSED`` evidence panel,
        or surface it via metrics.

        The SQL uses three positional placeholders ($1 agent_id, $2
        action_type, $3 cutoff timestamp); the cutoff is always tz-aware
        UTC (Pitfall 7 / T-V6-naive-datetime mitigation).

        Note:
            This method does **not** write any audit row. When ``allowed``
            is ``False`` the caller is expected to emit a
            ``Decision.SUPPRESSED`` ``AuditRecord`` via its ``AuditWriter``
            (see Plan 06-06 AnomalyDetector).
        """
        cutoff = datetime.now(UTC) - self._window
        async with self._pool.acquire() as conn:
            raw = await conn.fetchval(
                _COUNT_RECENT_SQL, self._agent_id, action_type, cutoff
            )
        count = int(raw) if raw is not None else 0
        allowed = count < self._limit
        _log.debug(
            "rate_limit_check",
            agent_id=self._agent_id,
            action_type=action_type,
            count=count,
            limit=self._limit,
            allowed=allowed,
        )
        return allowed, count
