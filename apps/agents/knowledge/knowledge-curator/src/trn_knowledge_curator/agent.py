"""KnowledgeCurator LangGraph node — autonomous curation (Plan 08-06, D-KC-04).

Handles document ingest events: dedup detection + staleness flagging + reuse-rate KPI.
Mode: deterministic (no LLM). All computation is pure Python + Qdrant cosine + SQL.

Autonomous design (D-KC-04):
  - Fully autonomous: no human-in-the-loop gating mechanism anywhere in this module.
  - Audit rows (KNOWLEDGE_DEDUP + STALE_FLAG) are written IMMEDIATELY before return.
  - Decision is always Decision.AUTO.

Audit trail:
  - On duplicate detected: KNOWLEDGE_DEDUP audit row (D-KC-01).
  - On stale document: STALE_FLAG audit row (D-KC-02).
  - Reuse-rate is included in the CurationReport (D-KC-03).

Security:
  - T-08-11: threshold is server-side config (injected at construction, not from request body).
  - T-08-12: with_payload=False in Qdrant query (enforced in NearDedupChecker).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from sft_agents.audit.writer import AuditWriter
from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision
from sft_agents.models.evidence import EvidencePanel, TokenUsage, ToolCall

from trn_knowledge_curator.dedup import ExactDedupChecker, NearDedupChecker
from trn_knowledge_curator.metadata import AGENT_ID, CLUSTER
from trn_knowledge_curator.models import CurationReport, IngestRequest
from trn_knowledge_curator.reuse_rate import ReuseRateKPI
from trn_knowledge_curator.staleness import StalenessChecker

_log = structlog.get_logger("agent.knowledge-curator")

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Sentinel model string for deterministic (no-LLM) audit rows.
_NO_LLM_MODEL: str = "deterministic@knowledge-curator"

#: Sentinel prompt hash (no LLM prompt — all zeros).
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
# KnowledgeCurator
# ---------------------------------------------------------------------------


class KnowledgeCurator:
    """Autonomous KnowledgeCurator LangGraph node (D-KC-04 — no HITL).

    Dedup + stale flag are read/flag operations only (no irreversible writes).
    Audit rows written IMMEDIATELY (autonomous D-KC-04 — no HITL gating).

    Parameters
    ----------
    pool:
        asyncpg.Pool for ReuseRateKPI.
    audit_writer:
        AuditWriter instance for PG-first dual-write audit rows.
    exact_dedup:
        ExactDedupChecker instance (SHA-256 fast path). Constructed from default
        ExactDedupChecker() if not provided.
    near_dedup:
        NearDedupChecker instance (BGE-M3 cosine slow path). Optional — if not
        provided, only exact dedup is performed.
    staleness:
        StalenessChecker instance. Constructed from default StalenessChecker() if None.
    reuse_rate:
        ReuseRateKPI instance. Constructed from pool if not provided.
    known_hashes:
        Mutable set of known SHA-256 hashes (exact-dup corpus). Defaults to empty set.
    """

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: AuditWriter | Any,
        exact_dedup: ExactDedupChecker | None = None,
        near_dedup: NearDedupChecker | None = None,
        staleness: StalenessChecker | None = None,
        reuse_rate: ReuseRateKPI | None = None,
        known_hashes: set[str] | None = None,
    ) -> None:
        if pool is None:
            raise ValueError("pool must not be None")
        if audit_writer is None:
            raise ValueError("audit_writer must not be None")
        self._pool = pool
        self._audit = audit_writer
        self._exact_dedup = exact_dedup if exact_dedup is not None else ExactDedupChecker()
        self._near_dedup = near_dedup  # Optional — None means skip near-dup check.
        self._staleness = staleness if staleness is not None else StalenessChecker()
        self._reuse_rate = reuse_rate if reuse_rate is not None else ReuseRateKPI(pool=pool)
        self._known_hashes: set[str] = known_hashes if known_hashes is not None else set()

    # ------------------------------------------------------------------
    # LangGraph node entrypoint
    # ------------------------------------------------------------------

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """LangGraph node entrypoint for document curation.

        Reads IngestRequest-shaped fields from state and returns
        ``{"curation_report": CurationReport}``. NEVER mutates the input state.

        State keys read:
            - document_id (str, required)
            - document_text (str, required)
            - doc_type (str, required)
            - last_updated (datetime, required — UTC tz-aware)
            - source_uri (str, required)

        Returns:
            {"curation_report": CurationReport}
        """
        request = IngestRequest(
            document_id=state["document_id"],
            document_text=state["document_text"],
            doc_type=state["doc_type"],
            last_updated=state["last_updated"],
            source_uri=state["source_uri"],
        )
        report = await self.curate(request)
        return {"curation_report": report}

    # ------------------------------------------------------------------
    # Main curation logic
    # ------------------------------------------------------------------

    async def curate(self, request: IngestRequest) -> CurationReport:
        """Run dedup + staleness + reuse-rate; write audit immediately (D-KC-04).

        Steps:
            1. Exact dedup check (SHA-256 fast path).
            2. Near dedup check (BGE-M3 slow path) — only if not exact dup and near_dedup configured.
            3. Staleness check.
            4. Reuse-rate KPI.
            5. Write KNOWLEDGE_DEDUP audit row IMMEDIATELY if duplicate found.
            6. Write STALE_FLAG audit row IMMEDIATELY if stale.
            7. Return CurationReport.

        Args:
            request: Validated IngestRequest.

        Returns:
            CurationReport carrying all three KPI dimensions.
        """
        normalized = self._exact_dedup.normalize(request.document_text)

        # Step 1: Exact dedup (SHA-256 fast path).
        exact_result = self._exact_dedup.check(normalized, self._known_hashes)

        if exact_result.is_duplicate:
            dedup_result = exact_result
        elif self._near_dedup is not None:
            # Step 2: Near dedup (BGE-M3 slow path).
            dedup_result = await self._near_dedup.check(normalized)
        else:
            from trn_knowledge_curator.dedup import DedupResult
            dedup_result = DedupResult(is_duplicate=False)

        # Step 3: Staleness check.
        is_stale = self._staleness.is_stale(
            doc_type=request.doc_type,
            last_updated=request.last_updated,
        )

        # Step 4: Reuse-rate KPI.
        reuse_rate_value = await self._reuse_rate.compute()

        # Step 5: Write KNOWLEDGE_DEDUP audit IMMEDIATELY (D-KC-04 — autonomous, no HITL gating).
        if dedup_result.is_duplicate:
            await self._write_dedup_audit(request=request, dedup_result=dedup_result)

        # Step 6: Write STALE_FLAG audit IMMEDIATELY (D-KC-04 — autonomous, no HITL gating).
        if is_stale:
            await self._write_stale_audit(request=request)

        # Step 7: Build and return CurationReport (immutable).
        report = CurationReport(
            document_id=request.document_id,
            is_duplicate=dedup_result.is_duplicate,
            dup_type=dedup_result.dup_type,
            dup_source_uri=dedup_result.source_uri,
            dup_score=dedup_result.score,
            is_stale=is_stale,
            reuse_rate=reuse_rate_value,
            citations=[],
        )

        _log.info(
            "curation_complete",
            document_id=request.document_id,
            doc_type=request.doc_type,
            is_duplicate=report.is_duplicate,
            dup_type=report.dup_type,
            is_stale=report.is_stale,
            reuse_rate=report.reuse_rate,
        )
        return report

    # ------------------------------------------------------------------
    # Audit helpers
    # ------------------------------------------------------------------

    async def _write_dedup_audit(
        self,
        *,
        request: IngestRequest,
        dedup_result: Any,
    ) -> None:
        """Write a KNOWLEDGE_DEDUP audit row (D-KC-01, D-KC-04).

        Immediate write — fully autonomous (D-KC-04). Decision.AUTO always.
        """
        now = datetime.now(UTC)
        action_id = uuid4()
        synthetic_call = ToolCall(
            name="dedup_check",
            args={
                "document_id": request.document_id,
                "doc_type": request.doc_type,
                "source_uri": request.source_uri,
                "dup_type": dedup_result.dup_type,
            },
            result={
                "is_duplicate": dedup_result.is_duplicate,
                "dup_source_uri": dedup_result.source_uri,
                "score": dedup_result.score,
            },
            duration_ms=0,
            ts=now,
        )
        evidence_panel = EvidencePanel(
            input_summary=(
                f"dedup check document={request.document_id} "
                f"type={request.doc_type} dup_type={dedup_result.dup_type}"
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
            action_id=action_id,
            agent_id=AGENT_ID,
            thread_id=f"{CLUSTER}.{AGENT_ID}.{request.document_id}",
            cluster=CLUSTER,
            action_type=ActionType.KNOWLEDGE_DEDUP.value,
            evidence_panel=evidence_panel,
            decision=Decision.AUTO,
            decision_actor=None,
            motivation=None,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,
        )
        await self._audit.write(record)
        _log.info(
            "knowledge_dedup_audit_written",
            document_id=request.document_id,
            dup_type=dedup_result.dup_type,
            action_id=str(action_id),
        )

    async def _write_stale_audit(self, *, request: IngestRequest) -> None:
        """Write a STALE_FLAG audit row (D-KC-02, D-KC-04).

        Immediate write — fully autonomous (D-KC-04). Decision.AUTO always.
        """
        now = datetime.now(UTC)
        action_id = uuid4()
        synthetic_call = ToolCall(
            name="staleness_check",
            args={
                "document_id": request.document_id,
                "doc_type": request.doc_type,
                "last_updated": request.last_updated.isoformat(),
            },
            result={
                "is_stale": True,
                "doc_type": request.doc_type,
            },
            duration_ms=0,
            ts=now,
        )
        evidence_panel = EvidencePanel(
            input_summary=(
                f"staleness flag document={request.document_id} "
                f"type={request.doc_type} last_updated={request.last_updated.isoformat()}"
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
            action_id=action_id,
            agent_id=AGENT_ID,
            thread_id=f"{CLUSTER}.{AGENT_ID}.{request.document_id}",
            cluster=CLUSTER,
            action_type=ActionType.STALE_FLAG.value,
            evidence_panel=evidence_panel,
            decision=Decision.AUTO,
            decision_actor=None,
            motivation=None,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,
        )
        await self._audit.write(record)
        _log.info(
            "stale_flag_audit_written",
            document_id=request.document_id,
            doc_type=request.doc_type,
            action_id=str(action_id),
        )


__all__ = ["AGENT_ID", "CLUSTER", "KnowledgeCurator"]
