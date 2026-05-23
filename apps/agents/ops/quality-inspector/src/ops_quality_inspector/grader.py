"""LLM 4-point grading for QualityInspector (D-QI-02).

Sequence (Pattern 6 + Example 3 in RESEARCH.md):
    1. RAG search for SOP citations matching ``defect_type``.
    2. Build prompt: system = SYSTEM_PROMPT_4POINT, user = event JSON +
       citations block.
    3. Invoke LLM (BaseChatModel, async).
    4. Pydantic-validate the LLM JSON response into ``QualityVerdict``.
    5. On ``ValidationError``: return conservative fallback
       (``score=4``, ``severity="major"``, rationale flags "fallback")
       per Pitfall §7.

The grader never decides on HITL routing; that is the QualityInspector
agent's job (``agent.py``). The grader is a pure verdict function with
no side effects beyond the RAG search.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError
from sft_domain.ops.quality import QualityEvent, QualityVerdict

from ops_quality_inspector.prompts import RAG_QUERY_TEMPLATE, SYSTEM_PROMPT_4POINT

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

logger = structlog.get_logger("agent.quality-inspector.grader")


def _format_citations_block(citations: list[Any]) -> str:
    """Render citations as a fenced markdown block for the user prompt."""
    if not citations:
        return "(no SOP citations retrieved)"
    lines: list[str] = []
    for idx, cit in enumerate(citations, start=1):
        # RagCitation has source_uri + snippet; both schemas (sft-domain +
        # sft-knowledge) expose the same attribute names.
        source_uri = getattr(cit, "source_uri", "?")
        snippet = getattr(cit, "snippet", "")
        lines.append(f"[{idx}] {source_uri}\n    {snippet}")
    return "\n".join(lines)


async def grade_quality_event(
    event: QualityEvent,
    *,
    rag_pipeline: Any,
    model: "BaseChatModel | None" = None,
    user_roles: list[str] | None = None,
) -> QualityVerdict:
    """Grade a single QualityEvent via LLM + ASTM 4-point rules.

    Args:
        event: The QualityEvent to grade (Pydantic-validated upstream).
        rag_pipeline: A RetrievalPipeline-like object exposing
            ``async def search(*, query, user_roles, category, k, ...)``.
        model: Optional BaseChatModel; if None, build one from env
            (``build_chat_model(temperature=0.0, seed=42)``).
        user_roles: ACL roles for RAG (default ``["technician"]``).

    Returns:
        A QualityVerdict. On LLM-output validation failure, returns the
        conservative fallback verdict (score=4, severity="major", rationale
        contains the word "fallback").
    """
    roles = list(user_roles or ["technician"])
    query = RAG_QUERY_TEMPLATE.format(defect_type=event.defect_type)

    # Step 1: RAG citations. The pipeline returns a list of citation objects;
    # we attach them to the verdict regardless of LLM success/failure.
    citations = await rag_pipeline.search(
        query=query,
        user_roles=roles,
        category="sop",
        k=5,
    )
    citations_list = list(citations or [])

    # Step 2: build LLM model lazily if not injected.
    if model is None:
        from sft_agents.llm.factory import build_chat_model  # noqa: PLC0415

        model = build_chat_model(temperature=0.0, seed=42)

    # Step 3: prompt.
    citations_block = _format_citations_block(citations_list)
    user_content = (
        "Grade the following defect event using the 4-point system. "
        "Output JSON ONLY matching the schema.\n\n"
        "QUALITY_EVENT_JSON:\n"
        f"{event.model_dump_json(indent=2)}\n\n"
        "RAG_CITATIONS (informational, do not echo):\n"
        f"{citations_block}\n"
    )
    messages = [
        SystemMessage(content=SYSTEM_PROMPT_4POINT),
        HumanMessage(content=user_content),
    ]

    # Step 4: invoke + validate.
    raw = await model.ainvoke(messages)
    raw_content = _coerce_to_str(raw.content) if hasattr(raw, "content") else str(raw)

    try:
        # Parse the LLM JSON. We then re-build the verdict with the
        # ACL-filtered citations from the RAG pipeline so the LLM cannot
        # fabricate sources (T-V6-citation-hallucination mitigation).
        parsed = QualityVerdict.model_validate_json(raw_content)
        verdict = parsed.model_copy(update={"citations": citations_list})
    except ValidationError as exc:
        logger.warning(
            "quality_verdict_validation_error_fallback",
            defect_type=event.defect_type,
            event_id=str(event.event_id),
            raw_excerpt=(raw_content or "")[:200],
            error=str(exc),
        )
        verdict = QualityVerdict(
            score=4,
            severity="major",
            rationale_md=(
                "LLM produced invalid output; conservative fallback applied "
                "(score=4, severity=major). "
                f"Original (truncated): {(raw_content or '')[:200]}"
            ),
            citations=citations_list,
        )

    logger.info(
        "quality_verdict_emitted",
        event_id=str(event.event_id),
        asset_id=event.asset_id,
        dye_lot_id=event.dye_lot_id,
        defect_type=event.defect_type,
        score=verdict.score,
        severity=verdict.severity,
    )
    return verdict


def _coerce_to_str(content: Any) -> str:
    """LangChain content can be str or list-of-blocks; flatten to str."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Each block is dict-like with {"type": "text", "text": "..."} or a str.
        out: list[str] = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                out.append(str(block["text"]))
            else:
                out.append(str(block))
        return "".join(out)
    return str(content)


__all__ = ["grade_quality_event"]
