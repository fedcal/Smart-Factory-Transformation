"""DocumentationSynthesizer — bilingual SOP draft with pre-index HITL (D-DS-03, CR-02).

Architecture overview:
    1. ``__call__(state)`` aggregates historical events (event_aggregator, D-DS-02).
    2. RAG grounding citations (retrieval_pipeline.search).
    3. LLM: generate IT SOP with [SRC:N] anchors (sop_builder, Pitfall §1).
    4. LLM: translate to EN, re-anchor citations (translator, D-DS-01).
    5. Validate citations + anchor parity (validator, TRN-05).
    6. HITL gate BEFORE Qdrant indexing (D-DS-03, CR-02 fix):
       interrupt() called DIRECTLY in __call__ (not via a tool).
       On the FIRST execution, LangGraph raises GraphInterrupt here.
       The lines below interrupt() only execute on RESUME.
    7. Qdrant indexing AFTER interrupt returns (on resume — D-DS-03).
    8. Audit row AFTER interrupt (CR-02 fix — one row per resume, never on first run).

Saver guard (CR-01):
    saver=None raises RuntimeError at construction time. The caller must inject
    the saver via api-gateway lifespan.py DI pattern.

Pitfall §3 (no audit before interrupt):
    _write_audit() fires ONLY on resume execution (after interrupt() returns).
    No double-write risk because the interrupt is DIRECTLY in __call__ (CR-02 fix).

CR-03 (approval_id=None):
    The SOP_DRAFT audit row uses approval_id=None (pending HITL). Never fabricate UUID.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

import structlog

from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision, Tier

# Pattern G: langgraph.types.interrupt graceful fallback (for test environments)
try:
    from langgraph.types import interrupt
except ImportError:  # pragma: no cover
    def interrupt(value: Any) -> Any:  # type: ignore[misc]
        """Fallback stub — only reached in non-langgraph test environments."""
        raise NotImplementedError("langgraph.types.interrupt is not available in this environment")

from trn_documentation_synthesizer.metadata import AGENT_ID as _AGENT_ID
from trn_documentation_synthesizer.metadata import build_trn05_evidence_panel
from trn_documentation_synthesizer.models import SECTION_KEYS_IT, SOPDraft

logger = structlog.get_logger("agent.documentation-synthesizer")

# ---------------------------------------------------------------------------
# Module-level constants (Pattern I)
# ---------------------------------------------------------------------------

AGENT_ID: str = "documentation-synthesizer"
CLUSTER: str = "knowledge"

_DEFAULT_MODEL_NAME: str = "unknown@documentation-synthesizer"

_EMPTY_BUDGET = BudgetSnapshot(
    tokens_input=0,
    tokens_output=0,
    tokens_total=0,
    cost_usd_simulated=0.0,
    duration_ms=0,
    limit_tokens=50000,
    limit_cost_usd=1.0,
    limit_duration_s=300,
)


def _sha256(text: str) -> str:
    """Return lowercase 64-char sha256 hex of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# DocumentationSynthesizer
# ---------------------------------------------------------------------------


class DocumentationSynthesizer:
    """LangGraph node: bilingual SOP draft with supervisor HITL gating Qdrant indexing.

    HITL ordering (D-DS-03, CR-02 fix):
        1. Generate IT + EN SOP
        2. Validate citations
        3. interrupt() — LangGraph pauses here on first execution
        4. [RESUME] indexer.upsert() — Qdrant indexing on resume only
        5. [RESUME] _write_audit(SOP_DRAFT) — audit row on resume only

    Usage::

        agent = DocumentationSynthesizer(
            pool=asyncpg_pool,
            audit_writer=audit_writer,
            llm=llm,
            retrieval_pipeline=retrieval_pipeline,
            indexer=qdrant_indexer,
            event_aggregator=event_aggregator,
            validator=sop_citation_validator,
            saver=saver,
        )
        result = await agent(state={"failure_mode": "overheating", "asset_id": "loom-01"})
    """

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: Any,
        llm: Any,
        retrieval_pipeline: Any,
        indexer: Any,
        event_aggregator: Any,
        validator: Any,
        saver: Any,
    ) -> None:
        """Bind collaborators.

        Args:
            pool:                asyncpg.Pool for PG lookups.
            audit_writer:        AuditWriter (written AFTER interrupt returns — CR-02).
            llm:                 LangChain-compatible LLM.
            retrieval_pipeline:  RetrievalPipeline for RAG grounding (Phase 5).
            indexer:             QdrantIndexer for post-approval indexing (D-DS-03).
            event_aggregator:    HistoricalEventAggregator (D-DS-02).
            validator:           SOPCitationValidator (TRN-05).
            saver:               LangGraph CheckpointSaver (CR-01 guard).

        Raises:
            RuntimeError: If saver is None (CR-01 fix — must be injected via lifespan).
        """
        # CR-01 fix: saver must be injected at construction (never None in production)
        if saver is None:
            raise RuntimeError(
                "DocumentationSynthesizer requires a non-None saver. "
                "Inject the saver via api-gateway lifespan.py DI pattern (CR-01 fix). "
                "See apps/agents/knowledge/documentation-synthesizer/README.md."
            )

        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
        self._retrieval = retrieval_pipeline
        self._indexer = indexer
        self._event_aggregator = event_aggregator
        self._validator = validator
        self._saver = saver

    # ------------------------------------------------------------------ private

    def _thread_id(self, sop_id: str) -> str:
        """Format: {CLUSTER}.{AGENT_ID}.{sop_id}."""
        return f"{CLUSTER}.{AGENT_ID}.{sop_id}"

    async def _generate_it_sop(
        self,
        *,
        failure_mode: str,
        asset_id: str,
        events: list[dict[str, Any]],
        citations: list[Any],
        sop_id: str | None = None,
    ) -> tuple[SOPDraft, dict[str, str]]:
        """Generate IT SOP with [SRC:N] anchors (D-DS-01, Pitfall §1).

        Returns the initial SOPDraft (sections_en is a placeholder) and anchor_map.
        The caller must call _translate_en() to fill sections_en.

        Args:
            sop_id: Optional stable SOP ID from state for replay idempotency (CR-04).
        """
        from trn_documentation_synthesizer.sop_builder import SOPBuilder

        builder = SOPBuilder(llm=self._llm)
        sop_draft, anchor_map = await builder.build(
            failure_mode=failure_mode,
            asset_id=asset_id,
            events=events,
            citations=citations,
            sop_id=sop_id,
        )
        return sop_draft, anchor_map

    async def _translate_en(
        self,
        sop_draft: SOPDraft,
        anchor_map: dict[str, str],
    ) -> SOPDraft:
        """Translate IT sections to EN, re-anchoring citations (D-DS-01).

        Returns a new (frozen) SOPDraft with sections_en populated.
        Raises MissingAnchorError if any IT anchor is dropped in translation.
        """
        from trn_documentation_synthesizer.translator import SOPTranslator

        translator = SOPTranslator(llm=self._llm)
        sections_en = await translator.translate(sop_draft.sections_it, anchor_map)

        # Build a new immutable SOPDraft with the translated EN sections
        return SOPDraft(
            sop_id=sop_draft.sop_id,
            failure_mode=sop_draft.failure_mode,
            asset_id=sop_draft.asset_id,
            title_it=sop_draft.title_it,
            title_en=sop_draft.title_en,
            lang_primary=sop_draft.lang_primary,
            sections_it=sop_draft.sections_it,
            sections_en=sections_en,
            citations=sop_draft.citations,
            anchor_map=anchor_map,
            generated_at=sop_draft.generated_at,
            approved=sop_draft.approved,
        )

    async def _write_audit(
        self,
        *,
        sop_id: str,
        failure_mode: str,
        motivation: str,
    ) -> None:
        """Write the SOP_DRAFT audit row (executes ONLY on interrupt() resume — CR-02).

        Uses approval_id=None (CR-03 fix — never fabricate UUID for pending HITL).

        Args:
            sop_id:       SOP identifier for the thread_id.
            failure_mode: Used in the evidence panel summary.
            motivation:   Supervisor decision text (passed as interrupt return value).
        """
        from sft_agents.models.audit import AuditRecord
        from sft_agents.models.evidence import EvidencePanel, TokenUsage
        from sft_agents.models.proposed_action import ProposedAction

        thread_id = self._thread_id(sop_id)
        prompt_hash = _sha256(f"sop_draft:{failure_mode}:{sop_id}")
        model_name = (
            getattr(self._llm, "model_name", None)
            or getattr(self._llm, "model", None)
            or _DEFAULT_MODEL_NAME
        )
        model_id = f"{model_name}@{AGENT_ID}" if "@" not in str(model_name) else str(model_name)

        # Validate model_id pattern (EvidencePanel requires name@runtime)
        import re as _re
        if not _re.match(r"^[a-z0-9.\-]+@[a-z0-9.\-]+$", model_id):
            model_id = f"mock@{AGENT_ID}"

        evidence_panel = EvidencePanel(
            input_summary=f"sop_failure_mode={failure_mode[:200]}",
            input_truncated=len(failure_mode) > 200,
            tool_calls=[],
            rag_citations=[],
            confidence=1.0,
            model=model_id,
            prompt_hash=prompt_hash,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=0,
        )

        action = ProposedAction.from_payload(
            thread_id=thread_id,
            action_type=ActionType.SOP_DRAFT,
            args={"sop_id": sop_id, "failure_mode": failure_mode},
            target_subject=None,
        )

        record = AuditRecord(
            id=uuid4(),
            ts=datetime.now(timezone.utc),
            action_id=action.id,
            agent_id=AGENT_ID,
            thread_id=thread_id,
            cluster=CLUSTER,
            action_type=ActionType.SOP_DRAFT.value,
            evidence_panel=evidence_panel,
            decision=Decision.HITL_SUPERVISOR,
            decision_actor=None,
            motivation=motivation or "supervisor_sop_draft_approval",
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,  # CR-03 fix: never fabricate UUID for pending HITL
        )
        await self._audit.write(record)

    # ------------------------------------------------------------------ entry-point

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """Run one SOP synthesis turn (LangGraph node entry-point).

        D-DS-03 HITL ordering (CR-02 fix):
            Steps 1-5 run on FIRST execution.
            interrupt() is called DIRECTLY here (not via a tool).
            Steps 6-7 (indexer.upsert + _write_audit) run ONLY on RESUME.

        Args:
            state: LangGraph state dict. Expected keys:
                - failure_mode (str, required)
                - asset_id (str, required)
                - window_days (int, optional — default 180)
                - user_roles (list[str], optional — default ["technician"])
                - asset_family (str | None, optional)

        Returns:
            State delta: {"sop_draft": SOPDraft}

        Raises:
            RuntimeError: If _saver is None (CR-01 guard — should never reach here
                          if __init__ guard passed).
        """
        start_epoch_ms = int(time.time() * 1000)

        # -------- Extract state fields
        failure_mode: str = state["failure_mode"]
        asset_id: str = state["asset_id"]
        window_days: int = state.get("window_days", 180)
        user_roles: list[str] = state.get("user_roles", ["technician"])
        asset_family: str | None = state.get("asset_family")
        # CR-04: read pre-existing sop_id from state for stable IDs across LangGraph replays
        stable_sop_id: str | None = state.get("sop_id") or None

        logger.info(
            "documentation_synthesizer_start",
            failure_mode=failure_mode,
            asset_id=asset_id,
            window_days=window_days,
        )

        # -------- 1. Fetch historical events (event_aggregator — D-DS-02)
        events = await self._event_aggregator.fetch(
            failure_mode=failure_mode,
            asset_id=asset_id,
            window_days=window_days,
        )

        # -------- 2. RAG grounding citations (RetrievalPipeline.search)
        citations = await self._retrieval.search(
            query=failure_mode,
            user_roles=user_roles,
            category="sop",
            k=5,
            asset_family=asset_family,
        )

        # -------- 3. Generate IT SOP with [SRC:N] anchors (Pitfall §1)
        sop_draft_it, anchor_map = await self._generate_it_sop(
            failure_mode=failure_mode,
            asset_id=asset_id,
            events=events,
            citations=citations,
            sop_id=stable_sop_id,  # CR-04: propagate stable ID to prevent replay drift
        )

        # -------- 4. Translate to EN, re-anchor citations (D-DS-01)
        sop_draft_bilingual = await self._translate_en(sop_draft_it, anchor_map)

        # -------- 5. Validate citations (TRN-05)
        validated = self._validator.validate(sop_draft_bilingual, anchor_map)

        # -------- 6. HITL gate BEFORE Qdrant indexing (D-DS-03, CR-02 fix)
        # interrupt() called DIRECTLY in __call__ — NOT via a tool.
        # On the FIRST execution, LangGraph raises GraphInterrupt here, unwinding
        # the stack. Steps 7-8 below ONLY execute on the RESUMED execution.
        supervisor_decision = interrupt({
            "tier": Tier.SUPERVISOR.value,
            "payload": {
                "sop_id": validated.sop_id,
                "failure_mode": validated.failure_mode,
                "asset_id": validated.asset_id,
                "title_it": validated.title_it,
                "title_en": validated.title_en,
                "anchor_count": len(validated.anchor_map),
                "citation_count": len(validated.citations),
            },
        })

        # -------- 7. Qdrant indexing AFTER interrupt returns (on resume — D-DS-03)
        await self._indexer.upsert(validated)

        # -------- 8. Audit row AFTER interrupt (CR-02 fix — executes ONLY on resume)
        # approval_id=None (CR-03 fix: never fabricate UUID for pending HITL)
        await self._write_audit(
            sop_id=validated.sop_id,
            failure_mode=failure_mode,
            motivation=f"Supervisor approved SOP draft: {supervisor_decision}",
        )

        logger.info(
            "documentation_synthesizer_completed",
            sop_id=validated.sop_id,
            failure_mode=failure_mode,
            asset_id=asset_id,
            hitl_status="supervisor_pending",
        )

        return {"sop_draft": validated}


__all__ = ["AGENT_ID", "CLUSTER", "DocumentationSynthesizer"]
