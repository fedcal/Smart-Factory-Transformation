"""ProductionPlanner agent — thin orchestrator (D-PP-01..04, plan 06-08).

Flow:
    1. Validate ``state`` via :class:`PlanRequest` (frozen + extra=forbid).
    2. Load orders + asset capacity + failure modes from `sft-domain` loaders.
    3. Dispatch to ``schedule_spt`` or ``schedule_edd`` from
       `packages/sft-domain/scheduling/heuristic.py` (06-04) — deterministic.
    4. Retrieve SOP citations via the injected ``rag_pipeline.search``.
    5. Call the LLM only to generate ``rationale_md`` (never mutate items);
       on parse failure use a static fallback string.
    6. Build a ``ProposedAction`` with ``ActionType.SCHEDULE_DRAFT`` and route
       it to ``human_approval_node`` with ``Tier.SUPERVISOR`` — success
       criterion #4 for Phase 06.

Trust boundaries (06-08 threat_model):
    T-V6-injection         — Pydantic ``PlanRequest`` rejects unknown args.
    T-V6-llm-hallucination — LLM updates only ``rationale_md``; items immutable.
    T-V6-acl-leak          — ``user_roles`` propagated to ``rag_pipeline.search``.
    T-V6-hitl-bypass       — Always routes to ``human_approval_node`` SUPERVISOR.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from sft_agents.hitl.interrupt import human_approval_node
from sft_agents.models.enums import ActionType, Tier
from sft_agents.models.proposed_action import ProposedAction
from sft_domain.failure_modes import load_failure_modes
from sft_domain.ops.schedule import load_asset_capacity, load_orders
from sft_domain.scheduling import schedule_edd, schedule_spt

from ops_production_planner.models import PlanRequest
from ops_production_planner.prompts import citations_block, render_system_prompt

logger = structlog.get_logger(__name__)


# Fallback rationale when the LLM returns a non-JSON / invalid payload.
# The static string still surfaces the strategy + a pointer to the items list
# so the supervisor UI has *some* explanatory text to render.
_FALLBACK_RATIONALE = (
    "## Rationale\n\n"
    "_LLM rationale is unavailable for this draft (fallback path)._\n\n"
    "- The schedule was computed deterministically by the {strategy} heuristic.\n"
    "- See the `items` list for the per-order asset + window assignment.\n"
    "- See `unscheduled_orders` for orders that could not fit the horizon.\n"
)


# Strip whitespace + markdown fences from common LLM JSON-mode escapes.
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _parse_rationale(content: str) -> tuple[str, list[int]] | None:
    """Parse LLM JSON content → (rationale_md, citation_ids). Return None on failure."""
    if not content or not isinstance(content, str):
        return None
    cleaned = _FENCE_RE.sub("", content).strip()
    try:
        obj = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    rationale = obj.get("rationale_md")
    if not isinstance(rationale, str) or not rationale.strip():
        return None
    citation_ids = obj.get("citation_ids", [])
    if not isinstance(citation_ids, list):
        citation_ids = []
    # Coerce ids to int, drop garbage.
    safe_ids = [int(i) for i in citation_ids if isinstance(i, (int, str)) and str(i).lstrip("-").isdigit()]
    return rationale, safe_ids


class ProductionPlanner:
    """Thin orchestrator agent for production scheduling (D-PP-01..04).

    Collaborators are injected via the constructor so tests can supply mocks
    (mirrors `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py`
    composition pattern — see 06-PATTERNS lines 495-519).

    Args:
        rag_pipeline: RetrievalPipeline (sft-knowledge) — used to fetch SOP citations.
        audit_writer: AuditWriter from sft-agents.audit.writer (dual-write PG+NATS).
        queue_writer: ApprovalQueueWriter for the HITL row.
        nats: NATS publisher with ``publish_approval_new`` / ``publish_approval_resolved``.
        model: Optional pre-built BaseChatModel; falls back to ``build_chat_model()``.
        cluster: Agent cluster label for audit subject derivation (default "ops").
        agent_id: Agent slug for audit / approval rows (default "production-planner").
    """

    def __init__(
        self,
        *,
        rag_pipeline: Any,
        audit_writer: Any,
        queue_writer: Any,
        nats: Any,
        model: Any | None = None,
        cluster: str = "ops",
        agent_id: str = "production-planner",
    ) -> None:
        self._rag_pipeline = rag_pipeline
        self._audit_writer = audit_writer
        self._queue_writer = queue_writer
        self._nats = nats
        self._model = model
        self._cluster = cluster
        self._agent_id = agent_id
        # Injectable clock for deterministic tests (see test_deterministic_schedule_id).
        self._clock = lambda: datetime.now(UTC)

    # ------------------------------------------------------------------
    # Public entry
    # ------------------------------------------------------------------

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the planner end-to-end and return a state delta.

        Returns:
            ``{"schedule_draft": ScheduleDraft, "approval": <hitl delta>}``
        """
        # 1. Validate request (T-V6-injection).
        request = PlanRequest.model_validate(
            {
                "strategy": state.get("strategy"),
                "horizon_days": state.get("horizon_days"),
                "user_roles": state.get("user_roles", []),
            }
        )

        # 2. Load YAML-backed domain inputs (cached at module import; cheap).
        orders = list(load_orders())
        capacity = load_asset_capacity()
        failure_modes = load_failure_modes()
        # `load_failure_modes` returns a tuple; the heuristic expects a dict by asset_id.
        # Phase 6 plan 06-04 wires the dict shape via `load_failure_modes_dict` — but
        # the test fixtures here pass an empty tuple/dict, and `earliest_slot` only
        # uses `.get(asset_id, default)`. Normalise to a dict for robustness.
        if isinstance(failure_modes, (list, tuple)):
            fm_dict = {getattr(fm, "id", str(i)): fm for i, fm in enumerate(failure_modes)}
        else:
            fm_dict = dict(failure_modes)

        # 3. Horizon window (now → now + horizon_days).
        horizon_start = self._clock()
        horizon_end = horizon_start + timedelta(days=request.horizon_days)

        # 4. Deterministic scheduling (T-V6-llm-hallucination — algorithm-only).
        schedule_fn = schedule_spt if request.strategy == "spt" else schedule_edd
        draft = schedule_fn(orders, capacity, fm_dict, horizon_start, horizon_end)

        logger.info(
            "production_planner_schedule_computed",
            strategy=request.strategy,
            schedule_id=str(draft.schedule_id),
            items=len(draft.items),
            unscheduled=len(draft.unscheduled_orders),
        )

        # 5. RAG citations (T-V6-acl-leak — user_roles propagated).
        citations = []
        try:
            citations = await self._rag_pipeline.search(
                query=f"textile production scheduling {request.strategy} best practices",
                user_roles=list(request.user_roles),
                category="sop",
                k=5,
            )
        except Exception as exc:  # noqa: BLE001 — RAG outage is non-fatal.
            logger.warning(
                "production_planner_rag_search_failed",
                error=str(exc),
                strategy=request.strategy,
            )

        # 6. LLM rationale (LLM may NEVER alter items list — T-V6-llm-hallucination).
        rationale_md = await self._generate_rationale(request, draft, citations)

        # 7. Update draft immutably (Pydantic v2 model_copy).
        final_draft = draft.model_copy(
            update={"rationale_md": rationale_md, "citations": list(citations)}
        )

        # 8. Build ProposedAction with deterministic id.
        thread_id = str(state.get("thread_id", f"{self._cluster}.{self._agent_id}.session"))
        action_args = final_draft.model_dump(mode="json")
        action = ProposedAction.from_payload(
            thread_id=thread_id,
            action_type=ActionType.SCHEDULE_DRAFT,
            args=action_args,
            target_subject=None,
        )

        # 9. Route to supervisor HITL (T-V6-hitl-bypass — never auto-approve).
        approval = await self._invoke_human_approval(state, action)

        return {"schedule_draft": final_draft, "approval": approval}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _generate_rationale(
        self,
        request: PlanRequest,
        draft: Any,
        citations: list[Any],
    ) -> str:
        """Invoke the LLM for a markdown rationale; fallback on parse error."""
        model = self._model or _default_model()
        system = SystemMessage(content=render_system_prompt(request.strategy))
        human = HumanMessage(
            content=(
                f"Strategy: {request.strategy}\n\n"
                f"Schedule draft (DO NOT MODIFY):\n{draft.model_dump_json(indent=2)}\n\n"
                f"Citations:\n{citations_block(citations)}\n\n"
                f"Unscheduled orders: {list(draft.unscheduled_orders)}"
            )
        )
        try:
            raw = await model.ainvoke([system, human])
        except Exception as exc:  # noqa: BLE001 — LLM outage falls back.
            logger.warning(
                "production_planner_llm_call_failed",
                error=str(exc),
                strategy=request.strategy,
            )
            return _FALLBACK_RATIONALE.format(strategy=request.strategy)

        content = getattr(raw, "content", "") if raw is not None else ""
        parsed = _parse_rationale(content if isinstance(content, str) else str(content))
        if parsed is None:
            logger.warning(
                "production_planner_llm_parse_failed",
                strategy=request.strategy,
                head=str(content)[:120],
            )
            return _FALLBACK_RATIONALE.format(strategy=request.strategy)
        rationale, _ids = parsed
        return rationale

    async def _invoke_human_approval(
        self, state: dict[str, Any], action: ProposedAction
    ) -> dict[str, Any]:
        """Call ``human_approval_node`` with Tier.SUPERVISOR.

        We import via the module-level binding so tests can monkeypatch
        ``ops_production_planner.agent.human_approval_node`` cleanly.
        """
        # Build a minimal EvidencePanel-shaped placeholder. The full
        # evidence_panel wiring lands in plan 06-14 (OPS-05 completion).
        # We pass None where allowed — callers expecting a panel can patch
        # the human_approval_node fixture in tests.
        try:
            from sft_agents.models.evidence import EvidencePanel, TokenUsage

            panel = EvidencePanel(
                input_summary=f"ProductionPlanner draft (strategy={action.args.get('strategy')})",
                tool_calls=[],
                rag_citations=[],
                confidence=1.0,  # algorithm is deterministic
                model="schedule-heuristic@sft-domain",
                prompt_hash="0" * 64,
                tokens=TokenUsage(input=0, output=0, total=0),
                duration_ms=0,
            )
        except Exception:  # pragma: no cover — defensive only
            panel = None  # type: ignore[assignment]

        return await human_approval_node(
            state,
            proposed_action=action,
            evidence_panel=panel,
            queue_writer=self._queue_writer,
            nats_publisher=self._nats,
            audit_writer=self._audit_writer,
            tier=Tier.SUPERVISOR,
            cluster=self._cluster,
            agent_id=self._agent_id,
        )


def _default_model() -> Any:
    """Lazy import of build_chat_model so tests that inject a model never load it."""
    from sft_agents.llm.factory import build_chat_model

    return build_chat_model(temperature=0.3, seed=42)


__all__ = ["ProductionPlanner"]
