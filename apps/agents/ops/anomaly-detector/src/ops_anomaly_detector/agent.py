"""AnomalyDetector LangGraph node (D-AD-01 / D-AD-02 / D-AD-03).

First of the 4 OPS agents to ship. Fully deterministic — no LLM call,
no NATS consumer, no JetStream subscription. The node body:

    1. Pulls a ``window_minutes`` slice of sensor history from TimescaleDB
       (per-asset via ``QueryTimescaleTool._arun``).
    2. Compares each sample to its baseline band from
       ``anomaly_baselines.yaml`` (per-asset-family with optional per-machine
       override via ``select_baseline``).
    3. For every out-of-band sample, asks the ``RateLimiter`` whether the
       agent's 12-alerts/hour quota is exhausted.
    4. Writes a single ``audit.actions`` row per anomaly via ``AuditWriter``:

         * ``Decision.AUTO`` + ``ActionType.ANOMALY_ALERT`` when allowed;
         * ``Decision.SUPPRESSED`` + ``ActionType.ANOMALY_ALERT`` when
           dropped — payload carries the original anomaly fields so audit
           consumers can reconstruct the suppressed event.

    5. Returns a state delta dict ``{"anomalies": [Anomaly, ...]}`` — the
       agent NEVER mutates the input state (LangGraph reducer convention).

Design analogues:
    * ``packages/sft-agents/src/sft_agents/runtime/governor.py`` — class
      init pattern + audit-record builder shape.
    * ``packages/sft-agents/src/sft_agents/tools/audit.py`` — synthetic
      ``ToolCall`` shape inside ``EvidencePanel`` for queryability without
      a JSONB ad-hoc scan.

Security / threat-model notes:
    * T-V6-naive-datetime — ``datetime.now(timezone.utc)`` mandatory; we
      pass tz-aware UTC datetimes to ``QueryTimescaleTool._arun`` and into
      the ``AuditRecord.ts`` field. The ``EvidencePanel`` validator rejects
      naive datetimes; ``AuditRecord.ts`` does the same.
    * T-V6-throttle — the 12/h cap is enforced via ``RateLimiter``; excess
      anomalies still write a ``Decision.SUPPRESSED`` audit row for forensic
      retention (no silent drop).
    * T-V6-audit-double-write — AnomalyDetector is invoked on-demand only
      (no NATS consumer / no retry path), so the Pitfall §3 idempotency
      concern does not apply.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import structlog
from sft_agents.audit.writer import AuditWriter
from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision
from sft_agents.models.evidence import EvidencePanel, TokenUsage, ToolCall
from sft_agents.runtime.rate_limit import RateLimiter
from sft_assets.models import Asset
from sft_domain.ops.anomaly import Anomaly
from sft_tools.timescale.query import QueryTimescaleTool

from ops_anomaly_detector.baseline import BaselineRegistry, select_baseline

_log = structlog.get_logger("agent.anomaly-detector")

#: Logical agent identifier shared with ``RateLimiter`` (matches
#: ``audit.actions.agent_id``) and the audit row's ``agent_id`` column.
AGENT_ID: str = "anomaly-detector"

#: Cluster the agent belongs to — written verbatim to ``audit.actions.cluster``.
CLUSTER: str = "ops"

#: Sentinel model / prompt-hash for deterministic (no-LLM) audit rows.
#: ``EvidencePanel.model`` requires ``name@runtime`` regex; the sentinel
#: documents the audit consumer that no LLM was invoked.
_NO_LLM_MODEL: str = "deterministic@anomaly-detector"
_NO_PROMPT_HASH: str = "0" * 64

#: Default ``window_minutes`` when state omits the key (Plan 06-06 contract).
_DEFAULT_WINDOW_MINUTES: int = 15

#: Default rate-limit ceiling (D-AD-03 — 12 alerts per agent per hour).
_DEFAULT_RATE_LIMIT: int = 12

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


class AnomalyDetector:
    """Deterministic anomaly-detection LangGraph node.

    Constructor uses keyword-only arguments so callers / tests can not
    accidentally swap collaborators positionally.

    Parameters
    ----------
    pool:
        Live ``asyncpg.Pool`` against the audit database. Used to build the
        default ``RateLimiter`` and is otherwise opaque to the agent. Must
        not be ``None``.
    baselines:
        Immutable registry as returned by
        ``sft_domain.ops.anomaly.load_anomaly_baselines``. May be extended
        with ``(machine_id, sensor_id)`` keys for per-machine overrides
        (``select_baseline`` consumes both shapes).
    asset_registry:
        Iterable of ``Asset`` instances (``sft-assets`` registry) — every
        scan iterates over each asset and queries its sensor history.
    audit_writer:
        ``AuditWriter`` instance (PG-first dual-write). Mandatory — there
        is no sane default for an audit-log writer.
    query_tool:
        Optional ``QueryTimescaleTool``. When omitted, the default
        ``QueryTimescaleTool()`` is constructed at init time. Inject a
        mock in tests.
    rate_limiter:
        Optional ``RateLimiter``. When omitted, constructed at init time
        bound to ``pool`` with ``agent_id="anomaly-detector"`` and the
        12/h ceiling.
    """

    def __init__(
        self,
        *,
        pool: Any,
        baselines: BaselineRegistry,
        asset_registry: Sequence[Asset],
        audit_writer: AuditWriter | Any,
        query_tool: QueryTimescaleTool | Any | None = None,
        rate_limiter: RateLimiter | Any | None = None,
    ) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        if audit_writer is None:
            raise ValueError("audit_writer must not be None")
        if asset_registry is None:
            raise ValueError("asset_registry must not be None")
        self._pool = pool
        self._baselines = baselines
        self._assets: tuple[Asset, ...] = tuple(asset_registry)
        self._audit = audit_writer
        self._query = query_tool if query_tool is not None else QueryTimescaleTool()
        self._limiter = rate_limiter if rate_limiter is not None else RateLimiter(
            pool=pool,
            agent_id=AGENT_ID,
            limit=_DEFAULT_RATE_LIMIT,
        )

    # ------------------------------------------------------------------
    # LangGraph node entrypoint
    # ------------------------------------------------------------------

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """Run one anomaly scan tick — see module docstring for the full flow.

        Returns
        -------
        dict
            A LangGraph state delta containing exactly one key,
            ``"anomalies": list[Anomaly]``. NEVER mutates ``state``.
        """
        window_minutes = int(state.get("window_minutes", _DEFAULT_WINDOW_MINUTES))
        now = datetime.now(UTC)
        time_range = (now - timedelta(minutes=window_minutes), now)

        emitted: list[Anomaly] = []
        suppressed = 0

        for asset in self._assets:
            df = await self._query._arun(asset_id=asset.asset_id, time_range=time_range)
            # Defensive: pandas .empty avoids iterating an empty DataFrame.
            if df is None or getattr(df, "empty", False):
                continue
            for row in df.itertuples(index=False):
                # Map DataFrame row to canonical (sensor_id, value, timestamp)
                # using getattr so this works against either a fully-typed
                # DataFrame or a mock-returned one.
                sensor_id = getattr(row, "sensor_id", None)
                value = getattr(row, "value", None)
                ts = getattr(row, "timestamp", now)
                if sensor_id is None or value is None:
                    continue

                baseline = select_baseline(
                    self._baselines,
                    asset_family=asset.asset_family.value,
                    sensor_id=str(sensor_id),
                    machine_id=asset.asset_id,
                )
                if baseline is None:
                    _log.warning(
                        "missing_baseline",
                        asset_id=asset.asset_id,
                        asset_family=asset.asset_family.value,
                        sensor_id=str(sensor_id),
                    )
                    continue
                if baseline.is_within_band(float(value)):
                    continue

                anomaly = Anomaly(
                    asset_id=asset.asset_id,
                    sensor_id=str(sensor_id),
                    value=float(value),
                    baseline_low=baseline.low,
                    baseline_high=baseline.high,
                    timestamp=_ensure_utc(ts, fallback=now),
                    severity=baseline.severity_for(float(value)),
                )

                allowed, count = await self._limiter.check_and_emit(
                    ActionType.ANOMALY_ALERT.value
                )
                if not allowed:
                    suppressed += 1
                    _log.info(
                        "anomaly_suppressed",
                        anomaly_id=str(anomaly.id),
                        asset_id=anomaly.asset_id,
                        sensor_id=anomaly.sensor_id,
                        rate_count=count,
                    )
                    await self._write_audit(
                        anomaly=anomaly, decision=Decision.SUPPRESSED, rate_count=count
                    )
                    continue

                await self._write_audit(
                    anomaly=anomaly, decision=Decision.AUTO, rate_count=count
                )
                emitted.append(anomaly)

        _log.info(
            "anomaly_scan_complete",
            emitted=len(emitted),
            suppressed=suppressed,
            window_minutes=window_minutes,
        )
        return {"anomalies": emitted}

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    async def _write_audit(
        self,
        *,
        anomaly: Anomaly,
        decision: Decision,
        rate_count: int,
    ) -> None:
        """Persist one ``AuditRecord`` (PG + NATS via the injected writer).

        The original anomaly fields are stashed inside ``EvidencePanel``
        as a synthetic ``ToolCall`` so downstream consumers can query the
        suppressed payload without a JSONB ad-hoc scan (mirrors the
        ``LogEventTool`` convention from Plan 06-05).
        """
        now = datetime.now(UTC)

        synthetic_call = ToolCall(
            name="anomaly_detect",
            args={
                "asset_id": anomaly.asset_id,
                "sensor_id": anomaly.sensor_id,
                "value": anomaly.value,
                "baseline_low": anomaly.baseline_low,
                "baseline_high": anomaly.baseline_high,
                "severity": anomaly.severity,
                "rate_count": rate_count,
            },
            result={"anomaly_id": str(anomaly.id), "decision": decision.value},
            duration_ms=0,
            ts=now,
        )

        decision_label = "emit" if decision is Decision.AUTO else "suppress"
        input_summary = (
            f"anomaly {decision_label}: asset={anomaly.asset_id} "
            f"sensor={anomaly.sensor_id} value={anomaly.value} "
            f"band=[{anomaly.baseline_low}, {anomaly.baseline_high}] "
            f"severity={anomaly.severity}"
        )[:500]

        evidence = EvidencePanel(
            input_summary=input_summary,
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
            action_id=uuid4(),
            agent_id=AGENT_ID,
            thread_id=f"{CLUSTER}.{AGENT_ID}.{anomaly.id}",
            cluster=CLUSTER,
            action_type=ActionType.ANOMALY_ALERT.value,
            evidence_panel=evidence,
            decision=decision,
            decision_actor=None,
            motivation=None,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,
        )

        await self._audit.write(record)


def _ensure_utc(value: Any, *, fallback: datetime) -> datetime:
    """Coerce a (possibly naive) datetime to UTC tz-aware; use ``fallback`` on type mismatch.

    ``Anomaly.timestamp`` rejects naive datetimes (Pitfall 7 / T-V6-naive-datetime).
    The DataFrame may carry pandas Timestamps or naive datetimes depending on
    the upstream driver; this helper normalises to UTC tz-aware without raising.
    """
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    # pandas Timestamp / other date-like → try .to_pydatetime() then fall back.
    to_py = getattr(value, "to_pydatetime", None)
    if callable(to_py):
        py = to_py()
        if isinstance(py, datetime):
            return py if py.tzinfo is not None else py.replace(tzinfo=UTC)
    return fallback


__all__ = ["AGENT_ID", "CLUSTER", "AnomalyDetector"]
