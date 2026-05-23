"""DowntimeAnalyzer LangGraph node — on-demand /report generation (plan 07-09, D-DA-03).

Handles on-demand POST /report invocation from the api-gateway (07-10).
The reactive (NATS consumer) path is handled by consumer.py / run_da_consumer.

Mode: deterministic (no LLM). All computation is pure SQL + Python arithmetic.

Audit trail:
    - Per-event: DOWNTIME_VERDICT + Decision.AUTO (via _write_event_audit callback,
      called by consumer.py when write_event_audit is wired at startup 07-10).
    - Per-report: OEE_REPORT + Decision.AUTO (via _write_audit in generate_report).

Evidence panel:
    The OEE_REPORT audit row includes a synthetic ToolCall named 'oee_report_generate'
    with args capturing the request parameters and result capturing the OEE summary +
    top-3 Pareto reason codes. This enables forensic reconstruction of every report
    without scanning raw tables (audit-friendly design from D-DA-03).

Security:
    T-V7-da-naive-datetime: all datetime.now() calls use datetime.now(UTC).
    T-V7-da-asset-spoof: validate_asset_exists called via repository on asset_registry.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

import structlog
from sft_agents.audit.writer import AuditWriter
from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision
from sft_agents.models.evidence import EvidencePanel, TokenUsage, ToolCall

from mnt_downtime_analyzer.models import (
    DowntimeEvent,
    OEEMetrics,
    OEEReport,
    ParetoEntry,
    ReportRequest,
)
from mnt_downtime_analyzer.oee import (
    compute_oee,
    compute_pareto,
    compute_quality_cross_cluster,
)
from mnt_downtime_analyzer.repository import DowntimeEventRepository, QualityVerdictReader

_log = structlog.get_logger("agent.downtime-analyzer")

# ---------------------------------------------------------------------------
# Module-level constants (Shared Pattern A — mirrors anomaly-detector)
# ---------------------------------------------------------------------------

#: Logical agent identifier (matches audit.actions.agent_id).
AGENT_ID: str = "downtime-analyzer"

#: Cluster the agent belongs to (matches audit.actions.cluster).
CLUSTER: str = "maintenance"

#: Sentinel model string for deterministic (no-LLM) audit rows.
_NO_LLM_MODEL: str = "deterministic@downtime-analyzer"

#: Sentinel prompt hash (no LLM prompt hash — all zeros).
_NO_PROMPT_HASH: str = "0" * 64

#: Empty budget snapshot for deterministic agents.
_EMPTY_BUDGET = BudgetSnapshot(
    tokens_input=0,
    tokens_output=0,
    tokens_total=0,
    cost_usd_simulated=0.0,
    duration_ms=0,
    limit_tokens=0,
    limit_cost_usd=0.0,
    limit_duration_s=0,
)

# ---------------------------------------------------------------------------
# DowntimeAnalyzer
# ---------------------------------------------------------------------------


class DowntimeAnalyzer:
    """Deterministic DowntimeAnalyzer LangGraph node.

    Handles on-demand OEE report generation. The reactive NATS consumer path
    is handled by consumer.py (run_da_consumer).

    All collaborators are injected at construction (no PrivateAttr — not Pydantic).

    Parameters
    ----------
    pool:
        asyncpg.Pool for DowntimeEventRepository and QualityVerdictReader.
    audit_writer:
        AuditWriter instance for PG-first dual-write audit rows.
    repository:
        Optional DowntimeEventRepository. When None, constructed from pool.
    quality_reader:
        Optional QualityVerdictReader. When None, constructed from pool.
    asset_registry:
        Iterable of Asset instances (sft-assets registry). Used for by_asset breakdown.
    production_state_reader:
        Optional async callable returning (good, target) for OEE.P + OEE.Q fallback.
        Signature: async def reader(asset_id, window_start, window_end) -> tuple[int, int].
    """

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: AuditWriter | Any,
        repository: DowntimeEventRepository | None = None,
        quality_reader: QualityVerdictReader | None = None,
        asset_registry: Any = None,
        production_state_reader: Callable | None = None,
    ) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        if audit_writer is None:
            raise ValueError("audit_writer must not be None")
        self._pool = pool
        self._audit = audit_writer
        self._repository = repository if repository is not None else DowntimeEventRepository(pool=pool)
        self._quality_reader = quality_reader if quality_reader is not None else QualityVerdictReader(pool=pool)
        self._asset_registry = asset_registry
        self._production_state_reader = production_state_reader

    # ------------------------------------------------------------------
    # LangGraph node entrypoint
    # ------------------------------------------------------------------

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """LangGraph node entrypoint for on-demand report generation.

        Reads ReportRequest-shaped fields from state and returns
        ``{"oee_report": OEEReport}``. NEVER mutates the input state.

        State keys read:
            - window_start (datetime, required)
            - window_end (datetime, required)
            - by_asset (bool, default False)
            - top_n_pareto (int, default 10)
        """
        window_start = state["window_start"]
        window_end = state["window_end"]
        by_asset = bool(state.get("by_asset", False))
        top_n_pareto = int(state.get("top_n_pareto", 10))

        report = await self.generate_report(
            window_start=window_start,
            window_end=window_end,
            by_asset=by_asset,
            top_n_pareto=top_n_pareto,
        )
        return {"oee_report": report}

    # ------------------------------------------------------------------
    # On-demand report generation
    # ------------------------------------------------------------------

    async def generate_report(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        by_asset: bool = False,
        top_n_pareto: int = 10,
    ) -> OEEReport:
        """Generate an OEEReport for the given window.

        Steps:
            1. Validate window order.
            2. Compute aggregate OEE (A, P, Q) via compute_oee.
            3. Compute Pareto top-N.
            4. If by_asset=True, compute per-asset OEEMetrics.
            5. Build OEEReport Pydantic.
            6. Write OEE_REPORT audit row.

        Args:
            window_start: Window start (tz-aware UTC).
            window_end: Window end (tz-aware UTC, must be > window_start).
            by_asset: Include per-asset OEEMetrics breakdown.
            top_n_pareto: Maximum Pareto entries (1..100).

        Returns:
            OEEReport Pydantic (frozen+extra=forbid).

        Raises:
            ValueError: If window_end <= window_start.
        """
        # Step 1: Validate window order.
        if window_end <= window_start:
            raise ValueError(
                f"window_end ({window_end}) must be strictly after window_start ({window_start})"
            )

        # Step 2: Compute aggregate OEE.
        availability, performance, quality, oee, total_downtime, event_count = await compute_oee(
            asset_id=None,  # aggregate across all assets
            window_start=window_start,
            window_end=window_end,
            repository=self._repository,
            quality_reader=self._quality_reader,
            production_state_reader=self._production_state_reader,
            sim_fallback_reader=self._production_state_reader,
        )

        # Get quality source for audit row (call compute_quality_cross_cluster separately).
        _, quality_source = await compute_quality_cross_cluster(
            asset_id=None,
            window_start=window_start,
            window_end=window_end,
            quality_reader=self._quality_reader,
            sim_fallback_reader=self._production_state_reader,
        )

        # Step 3: Compute Pareto.
        raw_pareto = await self._repository.pareto(window_start, window_end, top_n=top_n_pareto)
        pareto_entries = compute_pareto(raw_pareto, top_n=top_n_pareto)

        # Step 4: Per-asset breakdown (optional).
        by_asset_dict: dict[str, OEEMetrics] | None = None
        if by_asset and self._asset_registry is not None:
            by_asset_dict = {}
            assets = list(self._asset_registry)
            for asset in assets:
                asset_id = getattr(asset, "asset_id", None)
                if asset_id is None:
                    continue
                a_avail, a_perf, a_qual, a_oee, a_dt, a_cnt = await compute_oee(
                    asset_id=asset_id,
                    window_start=window_start,
                    window_end=window_end,
                    repository=self._repository,
                    quality_reader=self._quality_reader,
                    production_state_reader=self._production_state_reader,
                    sim_fallback_reader=self._production_state_reader,
                )
                by_asset_dict[asset_id] = OEEMetrics(
                    asset_id=asset_id,
                    availability=a_avail,
                    performance=a_perf,
                    quality=a_qual,
                    oee=a_oee,
                    total_downtime_min=a_dt,
                    event_count=a_cnt,
                )

        # Step 5: Build OEEReport.
        now = datetime.now(UTC)
        report_id = str(uuid4())
        report = OEEReport(
            window_start=window_start,
            window_end=window_end,
            availability=availability,
            performance=performance,
            quality=quality,
            oee=availability * performance * quality,
            by_asset=by_asset_dict,
            pareto=pareto_entries,
            report_id=report_id,
            generated_at=now,
        )

        # Step 6: Write audit row.
        await self._write_audit(report=report, quality_source=quality_source)

        _log.info(
            "oee_report_generated",
            report_id=report_id,
            availability=availability,
            performance=performance,
            quality=quality,
            oee=oee,
            quality_source=quality_source,
            pareto_count=len(pareto_entries),
        )
        return report

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    async def _write_audit(
        self,
        *,
        report: OEEReport,
        quality_source: str,
    ) -> None:
        """Write an OEE_REPORT audit row (D-DA-03).

        The EvidencePanel ToolCall captures request params + OEE summary for
        forensic reconstruction without scanning raw tables.
        """
        now = datetime.now(UTC)
        synthetic_call = ToolCall(
            name="oee_report_generate",
            args={
                "window_start": report.window_start.isoformat(),
                "window_end": report.window_end.isoformat(),
                "by_asset": report.by_asset is not None,
                "pareto_count": len(report.pareto),
                "quality_source": quality_source,
            },
            result={
                "availability": report.availability,
                "performance": report.performance,
                "quality": report.quality,
                "oee": report.oee,
                "pareto_top": [e.reason_code for e in report.pareto[:3]],
            },
            duration_ms=0,
            ts=now,
        )
        evidence_panel = EvidencePanel(
            input_summary=(
                f"OEE report {report.report_id} "
                f"window={report.window_start.isoformat()}/{report.window_end.isoformat()}"
            )[:500],
            input_truncated=False,
            tool_calls=[synthetic_call],
            rag_citations=[],
            confidence=1.0,
            model=_NO_LLM_MODEL,
            prompt_hash=_NO_PROMPT_HASH,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=0,
        )
        record = AuditRecord(
            id=uuid4(),
            ts=now,
            action_id=UUID(report.report_id),
            agent_id=AGENT_ID,
            thread_id=f"{CLUSTER}.{AGENT_ID}.{report.report_id}",
            cluster=CLUSTER,
            action_type=ActionType.OEE_REPORT.value,
            evidence_panel=evidence_panel,
            decision=Decision.AUTO,
            decision_actor=None,
            motivation=None,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,
        )
        await self._audit.write(record)

    async def _write_event_audit(self, event: DowntimeEvent) -> None:
        """Write a DOWNTIME_VERDICT audit row for a single DowntimeEvent.

        Called by consumer.py via the write_event_audit callback in production
        wiring (07-10 api-gateway). Writes per-event DOWNTIME_VERDICT + Decision.AUTO.

        thread_id format: maintenance.downtime-analyzer.<event_id>
        """
        now = datetime.now(UTC)
        synthetic_call = ToolCall(
            name="downtime_event_ingest",
            args={
                "asset_id": event.asset_id,
                "reason_code": event.reason_code,
                "severity": event.severity,
                "duration_min": event.duration_min,
                "source": event.source,
            },
            result={
                "event_id": event.event_id,
                "persisted_at": now.isoformat(),
            },
            duration_ms=0,
            ts=now,
        )
        evidence_panel = EvidencePanel(
            input_summary=(
                f"downtime event={event.event_id} asset={event.asset_id} "
                f"reason={event.reason_code}"
            )[:500],
            input_truncated=False,
            tool_calls=[synthetic_call],
            rag_citations=[],
            confidence=1.0,
            model=_NO_LLM_MODEL,
            prompt_hash=_NO_PROMPT_HASH,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=0,
        )
        record = AuditRecord(
            id=uuid4(),
            ts=now,
            action_id=UUID(event.event_id),
            agent_id=AGENT_ID,
            thread_id=f"{CLUSTER}.{AGENT_ID}.{event.event_id}",
            cluster=CLUSTER,
            action_type=ActionType.DOWNTIME_VERDICT.value,
            evidence_panel=evidence_panel,
            decision=Decision.AUTO,
            decision_actor=None,
            motivation=None,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,
        )
        await self._audit.write(record)


__all__ = ["AGENT_ID", "CLUSTER", "DowntimeAnalyzer"]
