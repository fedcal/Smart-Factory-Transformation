"""Cross-cluster asyncpg aggregator for ShiftHandover (D-SH-02, TRN-03).

ShiftAggregator builds a structured HandoverReport by:
  1. Fetching all audit.actions rows in the shift window (cross-cluster).
  2. Fetching maintenance.downtime_events rows in the shift window.
  3. Deriving counts and citations DETERMINISTICALLY from these rows only.

D-SH-02 (resolved post-research):
    NO ops.alerts / ops.work_orders tables. Alerts derive from audit.actions
    WHERE action_type='ANOMALY_ALERT'. Work-order presence is inferred from
    DOWNTIME_VERDICT rows that carry a work_order_id in the evidence_panel.

Security (T-08-04 / Shared Pattern H):
    ALL SQL is stored as ClassVar string constants and uses asyncpg $1..$N
    parameterized placeholders ONLY. No f-string interpolation in SQL.

WR-03 fix (Phase 7):
    asyncpg TIMESTAMPTZ parameters MUST be Python datetime objects — never
    call .isoformat() before passing to conn.fetch(). The fetch_* methods
    accept and pass datetime objects directly.

Performance constraint (Pitfall §4):
    build_report() is LLM-free. Counts and citations are computed
    deterministically from the returned rows so the aggregation path stays
    under 30 seconds, protecting the <3 min SLA.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, ClassVar

import structlog

from trn_shift_handover.models import HandoverReport

logger = structlog.get_logger("agent.shift-handover.aggregator")

# Action type constants (mirrors sft_agents.models.enums.ActionType values)
_ANOMALY_ALERT = "ANOMALY_ALERT"
_QUALITY_VERDICT = "QUALITY_VERDICT"
_DOWNTIME_VERDICT = "DOWNTIME_VERDICT"


class ShiftAggregator:
    """Cross-cluster asyncpg aggregator for ShiftHandover (D-SH-02).

    Reads audit.actions across all clusters for the shift window plus
    maintenance.downtime_events. All SQL uses $N parameterized placeholders
    (T-08-04). ClassVar SQL constants enable meta-test inspection.

    WR-03 fix: pass datetime objects directly to asyncpg — never .isoformat().
    """

    # Cross-cluster audit query for shift window (D-SH-02).
    # WR-03 fix: pass datetime objects directly to asyncpg (never .isoformat()).
    _SQL_AUDIT_WINDOW: ClassVar[str] = (
        "SELECT ts, agent_id, cluster, action_type, thread_id, "
        "evidence_panel, decision "
        "FROM audit.actions "
        "WHERE ts BETWEEN $1 AND $2 "
        "ORDER BY ts ASC"
    )

    # Downtime events for the shift window (maintenance.downtime_events, migration 008).
    _SQL_DOWNTIME_WINDOW: ClassVar[str] = (
        "SELECT event_id, asset_id, reason_code, duration_min, severity, "
        "work_order_id, timestamp "
        "FROM maintenance.downtime_events "
        "WHERE timestamp BETWEEN $1 AND $2 "
        "ORDER BY timestamp ASC"
    )

    def __init__(self, *, pool: Any) -> None:
        """Bind asyncpg connection pool.

        Args:
            pool: asyncpg.Pool instance (keyword-only to prevent positional swaps).
        """
        self._pool = pool

    async def fetch_audit_window(
        self,
        shift_start: datetime,
        shift_end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch all audit.actions rows in the shift window.

        WR-03 fix: shift_start and shift_end are datetime objects passed
        directly to asyncpg — never call .isoformat() before passing.

        Args:
            shift_start: Inclusive window start (tz-aware datetime).
            shift_end:   Inclusive window end (tz-aware datetime).

        Returns:
            List of dicts (one per audit.actions row); empty list if none found.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                self._SQL_AUDIT_WINDOW,
                shift_start,   # datetime object — WR-03 fix
                shift_end,     # datetime object — WR-03 fix
            )
        result = [dict(row) for row in rows]
        logger.debug(
            "fetch_audit_window_complete",
            shift_start=shift_start.isoformat(),
            shift_end=shift_end.isoformat(),
            row_count=len(result),
        )
        return result

    async def fetch_downtime_events(
        self,
        shift_start: datetime,
        shift_end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch maintenance.downtime_events rows in the shift window.

        WR-03 fix: shift_start and shift_end are datetime objects passed
        directly to asyncpg — never call .isoformat() before passing.

        Args:
            shift_start: Inclusive window start (tz-aware datetime).
            shift_end:   Inclusive window end (tz-aware datetime).

        Returns:
            List of dicts (one per maintenance.downtime_events row); empty list if none.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                self._SQL_DOWNTIME_WINDOW,
                shift_start,   # datetime object — WR-03 fix
                shift_end,     # datetime object — WR-03 fix
            )
        result = [dict(row) for row in rows]
        logger.debug(
            "fetch_downtime_events_complete",
            shift_start=shift_start.isoformat(),
            shift_end=shift_end.isoformat(),
            row_count=len(result),
        )
        return result

    def build_report(
        self,
        audit_rows: list[dict[str, Any]],
        downtime_rows: list[dict[str, Any]],
        *,
        shift_start: datetime,
        shift_end: datetime,
        boundary_label: str = "",
    ) -> HandoverReport:
        """Build HandoverReport deterministically from audit + downtime rows.

        D-SH-02: ALL counts are derived from existing tables only:
            - open_alerts:            count of action_type='ANOMALY_ALERT' rows
            - completed_work_orders:  count of DOWNTIME_VERDICT rows with work_order_id
            - quality_events:         count of QUALITY_VERDICT rows
            - downtime_events:        count of maintenance.downtime_events rows

        TRN-05: RagCitations collected from evidence_panel JSONB rag_citations arrays.

        This method is LLM-free (Pitfall §4) — the narrative_summary is left empty
        and must be filled by the caller using an LLM (capped to 3-5 lines).

        Args:
            audit_rows:    Rows from fetch_audit_window().
            downtime_rows: Rows from fetch_downtime_events().
            shift_start:   Shift window start datetime.
            shift_end:     Shift window end datetime.
            boundary_label: Human-readable shift label.

        Returns:
            Frozen HandoverReport with derived counts and citations.
        """
        open_alerts = 0
        completed_work_orders = 0
        quality_events = 0
        equipment_status: dict[str, str] = {}
        citations: list[Any] = []
        source_events: list[dict[str, Any]] = []

        for row in audit_rows:
            action_type = row.get("action_type", "")
            source_events.append(row)

            # Count alerts (D-SH-02: derive from ANOMALY_ALERT action_type)
            if action_type == _ANOMALY_ALERT:
                open_alerts += 1

            # Count quality verdicts
            if action_type == _QUALITY_VERDICT:
                quality_events += 1

            # Count completed work orders from DOWNTIME_VERDICT rows with work_order_id
            if action_type == _DOWNTIME_VERDICT:
                evidence = row.get("evidence_panel")
                if evidence:
                    panel = _parse_jsonb(evidence)
                    if panel.get("work_order_id"):
                        completed_work_orders += 1

            # Track latest per-asset equipment status
            evidence = row.get("evidence_panel")
            if evidence:
                panel = _parse_jsonb(evidence)
                asset_id = panel.get("asset_id")
                status = panel.get("status") or panel.get("equipment_status")
                if asset_id and status:
                    equipment_status[str(asset_id)] = str(status)

            # TRN-05: collect RAG citations from evidence_panel.rag_citations
            if evidence:
                panel = _parse_jsonb(evidence)
                rag_citations = panel.get("rag_citations", [])
                if isinstance(rag_citations, list):
                    citations.extend(_parse_rag_citations(rag_citations))

        # Build verified RagCitation objects from raw dicts
        rag_citation_objects = _build_rag_citations(citations)

        return HandoverReport(
            shift_start=shift_start,
            shift_end=shift_end,
            boundary_label=boundary_label,
            open_alerts=open_alerts,
            completed_work_orders=completed_work_orders,
            downtime_events=len(downtime_rows),
            quality_events=quality_events,
            equipment_status=equipment_status,
            narrative_summary="",  # LLM-filled by caller (Pitfall §4 — keep this path LLM-free)
            source_events=source_events,
            citations=rag_citation_objects,
        )

    async def compile(
        self,
        window: "ShiftWindow",  # type: ignore[name-defined]  # noqa: F821
        pool: Any | None = None,
    ) -> HandoverReport:
        """Compile a HandoverReport for the given ShiftWindow.

        Convenience entry-point that fetches both audit and downtime rows then
        calls build_report(). The pool argument is accepted but ignored when
        ShiftAggregator is constructed with a pool (for test compatibility).

        Args:
            window: Validated ShiftWindow (tz-aware, end > start).
            pool:   Optional pool override (ignored if self._pool is set).

        Returns:
            Frozen HandoverReport with derived counts and citations.
        """
        effective_pool = pool if pool is not None else self._pool
        audit_rows = await _fetch_audit_window_from_pool(
            effective_pool,
            self._SQL_AUDIT_WINDOW,
            window.shift_start,
            window.shift_end,
        )
        downtime_rows = await _fetch_downtime_events_from_pool(
            effective_pool,
            self._SQL_DOWNTIME_WINDOW,
            window.shift_start,
            window.shift_end,
        )
        return self.build_report(
            audit_rows=audit_rows,
            downtime_rows=downtime_rows,
            shift_start=window.shift_start,
            shift_end=window.shift_end,
            boundary_label=window.boundary_label,
        )


# ---------------------------------------------------------------------------
# Module-level helpers (pure functions — no I/O)
# ---------------------------------------------------------------------------


def _parse_jsonb(value: Any) -> dict[str, Any]:
    """Parse asyncpg JSONB value to dict; return empty dict on error."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            result = json.loads(value)
            return result if isinstance(result, dict) else {}
        except (json.JSONDecodeError, ValueError):
            logger.warning("jsonb_parse_error", raw=value[:200])
            return {}
    return {}


def _parse_rag_citations(raw_list: list[Any]) -> list[dict[str, Any]]:
    """Return list of dicts from raw rag_citations JSONB array."""
    result = []
    for item in raw_list:
        if isinstance(item, dict):
            result.append(item)
        elif isinstance(item, str):
            try:
                parsed = json.loads(item)
                if isinstance(parsed, dict):
                    result.append(parsed)
            except (json.JSONDecodeError, ValueError):
                pass
    return result


def _build_rag_citations(raw_dicts: list[dict[str, Any]]) -> list[Any]:
    """Build RagCitation objects from raw dicts; skip malformed entries."""
    from sft_agents.models.evidence import RagCitation

    citations = []
    for raw in raw_dicts:
        try:
            citation = RagCitation(**raw)
            citations.append(citation)
        except Exception:  # noqa: BLE001
            logger.debug("rag_citation_parse_skip", raw_keys=list(raw.keys()))
    return citations


async def _fetch_audit_window_from_pool(
    pool: Any,
    sql: str,
    shift_start: datetime,
    shift_end: datetime,
) -> list[dict[str, Any]]:
    """Internal helper: fetch audit rows via pool.acquire() context manager."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, shift_start, shift_end)
    return [dict(row) for row in rows]


async def _fetch_downtime_events_from_pool(
    pool: Any,
    sql: str,
    shift_start: datetime,
    shift_end: datetime,
) -> list[dict[str, Any]]:
    """Internal helper: fetch downtime rows via pool.acquire() context manager."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, shift_start, shift_end)
    return [dict(row) for row in rows]


# Import ShiftWindow after class definition to avoid circular imports
from trn_shift_handover.models import ShiftWindow  # noqa: E402


__all__ = [
    "ShiftAggregator",
]
