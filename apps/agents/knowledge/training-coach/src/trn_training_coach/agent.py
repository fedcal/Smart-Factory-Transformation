"""TrainingCoach async LangGraph node agent (TRN-02 / D-TC-01/02/03).

Architecture (D-TC-01/02/03):
  - Single interrupt() for competency sign-off on pass path (supervisor HITL).
  - Quiz questions generated at session start via LLM (RESEARCH Open Q2 — frozen).
  - Scoring is DETERMINISTIC index comparison only — LLM never called in scoring path
    (Pitfall §3, T-08-09 mitigation).

W4/CR-02 audit ordering (CRITICAL — prevents double-write on LangGraph replay):
  ON PASS (score >= threshold):
    1. Score quiz deterministically (score_session).
    2. interrupt(SUPERVISOR) — raises GraphInterrupt on FIRST call.
    3. On resume (interrupt() returns): write TRAINING_SESSION row.
    4. Then: write TRAINING_SIGNOFF row.
    Both writes happen AFTER interrupt() returns — never before.
    This prevents the replay double-write: LangGraph re-executes the node
    on resume, so any write before interrupt() fires twice.

  ON FAIL (score < threshold):
    1. Score quiz deterministically.
    2. Write TRAINING_SESSION row immediately (no interrupt).
    3. Return. No TRAINING_SIGNOFF, no interrupt.

CR-03: approval_id=None on TRAINING_SIGNOFF (pending HITL — supervisor assigns real ID).

D-X-03: persona_role comes from SOP frontmatter role field.
TRN-05: every MCQQuestion carries source_uri from RAG citation.

ImportError fallback shim for langgraph.types.interrupt (Pattern G):
  In test environments without LangGraph installed, we shim interrupt().
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

import structlog

try:
    from langgraph.types import interrupt
except ImportError:  # Pattern G — test shim
    def interrupt(value: Any) -> Any:  # type: ignore[misc]
        """Fallback stub — only in non-langgraph test environments."""
        raise NotImplementedError(
            "langgraph.types.interrupt non disponibile. "
            "Usare patch('trn_training_coach.agent.interrupt', ...) nei test HITL."
        )

from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision, Tier
from sft_agents.models.evidence import EvidencePanel, TokenUsage

from trn_training_coach.difficulty import next_difficulty
from trn_training_coach.metadata import AGENT_ID, CLUSTER, DEFAULT_PASS_THRESHOLD
from trn_training_coach.models import CompetencyResult, TrainingSession
from trn_training_coach.quiz import MCQQuestion, MCQSession, score_session

UTC = timezone.utc
logger = structlog.get_logger("agent.training-coach")

# ---------------------------------------------------------------------------
# Empty budget snapshot for training-coach (deterministic scoring path).
# ---------------------------------------------------------------------------

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
# Valid persona roles from SOP frontmatter (D-X-03)
# ---------------------------------------------------------------------------

VALID_PERSONA_ROLES: frozenset[str] = frozenset({
    "tessitore",
    "tintore",
    "manutentore",
    "operatore",
    "supervisore",
    "quality_inspector",
})

# ---------------------------------------------------------------------------
# Default quiz settings
# ---------------------------------------------------------------------------

_DEFAULT_N_QUESTIONS: int = 5
_DEFAULT_DIFFICULTY: str = "medium"
_DEFAULT_RAG_CATEGORY: str = "training"
_DEFAULT_RAG_K: int = 5


class TrainingCoach:
    """TrainingCoach: delivers adaptive MCQ quiz with supervisor HITL sign-off on pass.

    Constructor is collaborator-injected for test-friendly dependency injection
    (pool, audit_writer, llm, retrieval_pipeline, escalate_tool).

    LLM usage: ONLY for quiz question generation (never in scoring path — Pitfall §3).
    Scoring: deterministic via trn_training_coach.quiz.score_session() (index comparison).
    HITL: single interrupt() for supervisor sign-off (D-TC-03, CR-02 ordering).
    """

    def __init__(
        self,
        *,
        pool: Any,
        audit_writer: Any,
        llm: Any,
        retrieval_pipeline: Any,
        escalate_tool: Any,
        pass_threshold: float = DEFAULT_PASS_THRESHOLD,
    ) -> None:
        """Initialize TrainingCoach with injected collaborators.

        Args:
            pool: asyncpg connection pool (for future DB queries).
            audit_writer: AuditWriter with async write() method.
            llm: LangChain BaseChatModel (Qwen2.5 or mock in tests).
                 Used ONLY for quiz generation — never scoring.
            retrieval_pipeline: RetrievalPipeline (Phase 5) for RAG.
            escalate_tool: EscalateToSupervisorTool for HITL routing.
            pass_threshold: Competency pass threshold (default 0.80, D-TC-03).
        """
        self._pool = pool
        self._audit = audit_writer
        self._llm = llm
        self._retrieval = retrieval_pipeline
        self._escalate = escalate_tool
        self._pass_threshold = pass_threshold

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """Execute a training session for the operator.

        W4/CR-02 audit ordering:
          - PASSING: interrupt() FIRST, then TRAINING_SESSION + TRAINING_SIGNOFF after resume.
          - FAILING: TRAINING_SESSION immediately after scoring, no interrupt, no TRAINING_SIGNOFF.

        Args:
            state: LangGraph state dict. Expected keys:
                - persona_role (str): Operator role from SOP frontmatter (D-X-03).
                - user_roles (list[str]): RBAC roles for RAG ACL filter.
                - asset_family (str | None): Optional asset context for retrieval.
                - n_questions (int | None): Override quiz size (default 5).
                - session_id (str | None): Override session ID (default UUID4).

        Returns:
            dict with keys:
                - training_session: TrainingSession with final score.
                - competency_result: CompetencyResult summary.
                - hitl_status: "supervisor_pending" | "approved" | "none".
        """
        # 1. Extract and validate session parameters
        persona_role = str(state.get("persona_role", "operatore"))
        if persona_role not in VALID_PERSONA_ROLES:
            logger.warning(
                "training_coach_unknown_persona_role",
                persona_role=persona_role,
                valid_roles=sorted(VALID_PERSONA_ROLES),
            )
            # Graceful degradation: use as-is (D-X-03 — roles from SOP frontmatter, not a registry)

        user_roles: list[str] = list(state.get("user_roles", [persona_role]))
        asset_family: str | None = state.get("asset_family")
        n_questions: int = int(state.get("n_questions", _DEFAULT_N_QUESTIONS))
        session_id: str = str(state.get("session_id") or str(uuid.uuid4()))

        logger.info(
            "training_coach_session_start",
            session_id=session_id,
            persona_role=persona_role,
            n_questions=n_questions,
        )

        # 2. RAG retrieval for SOP content (used for quiz generation only)
        citations = await self._retrieve_sop_content(
            persona_role=persona_role,
            user_roles=user_roles,
            asset_family=asset_family,
            k=_DEFAULT_RAG_K,
        )

        # 3. Generate and freeze quiz questions via LLM (LLM only here — not in scoring)
        questions = await self._generate_quiz_questions(
            persona_role=persona_role,
            citations=citations,
            n_questions=n_questions,
        )

        # 4. Build frozen MCQSession (generate-at-session-start, RESEARCH Open Q2)
        mcq_session = MCQSession(
            session_id=session_id,
            persona_role=persona_role,
            questions=questions,
            answers=[],  # Operator answers are injected from state in real flow
        )

        # Extract operator answers from state if provided (quiz delivery step)
        operator_answers: list[int] = list(state.get("answers", []))
        if operator_answers:
            # Replace frozen session answers by creating a new MCQSession (immutability)
            mcq_session = MCQSession(
                session_id=session_id,
                persona_role=persona_role,
                questions=questions,
                answers=operator_answers,
            )

        # 5. Score deterministically — NO LLM call (Pitfall §3, T-08-09)
        score = score_session(mcq_session)
        passed = score >= self._pass_threshold

        logger.info(
            "training_coach_scored",
            session_id=session_id,
            score=score,
            passed=passed,
            threshold=self._pass_threshold,
        )

        now = datetime.now(UTC)
        training_session = TrainingSession(
            session_id=session_id,
            persona_role=persona_role,
            score=score,
            passed=passed,
            threshold=self._pass_threshold,
            completed_at=now,
            citations=citations,
        )
        competency_result = CompetencyResult(
            persona_role=persona_role,
            score=score,
            passed=passed,
            threshold=self._pass_threshold,
            citations=citations,
        )

        # 6. Audit write ordering: W4/CR-02 compliant
        if passed:
            # PASSING PATH: interrupt() FIRST, writes AFTER resume.
            # On first execution, interrupt() raises GraphInterrupt — no writes fire.
            # On resume, interrupt() returns the supervisor's decision — writes fire once.
            decision = interrupt({  # noqa: F841  # CR-02 pattern: directly in __call__
                "type": "competency_signoff",
                "tier": Tier.SUPERVISOR.value,
                "session_id": session_id,
                "persona_role": persona_role,
                "score": score,
                "threshold": self._pass_threshold,
                "payload": training_session.model_dump(mode="json"),
            })

            # AFTER interrupt() returns (resume): write both rows exactly once.
            # TRAINING_SESSION written here (not before) to prevent double-write on replay.
            _thread_id = f"knowledge.training-coach.{session_id}"
            _now = datetime.now(UTC)
            _session_evidence = EvidencePanel(
                input_summary=f"session={session_id} role={persona_role} score={score:.2f}"[:500],
                input_truncated=False,
                tool_calls=[],
                rag_citations=[],
                confidence=1.0,
                model="deterministic@training-coach",
                prompt_hash="0" * 64,
                tokens=TokenUsage(input=0, output=0, total=0),
                duration_ms=0,
            )
            await self._audit.write(AuditRecord(
                id=uuid.uuid4(),
                ts=_now,
                action_id=uuid.uuid4(),
                agent_id=AGENT_ID,
                thread_id=_thread_id,
                cluster=CLUSTER,
                action_type=ActionType.TRAINING_SESSION.value,
                evidence_panel=_session_evidence,
                decision=Decision.HITL_SUPERVISOR,
                decision_actor=None,
                motivation=f"Training session completed: score={score:.2f} >= threshold={self._pass_threshold}",
                budget_snapshot=_EMPTY_BUDGET,
                approval_id=None,  # CR-03: pending HITL — supervisor assigns real ID
            ))
            await self._audit.write(AuditRecord(
                id=uuid.uuid4(),
                ts=_now,
                action_id=uuid.uuid4(),
                agent_id=AGENT_ID,
                thread_id=_thread_id,
                cluster=CLUSTER,
                action_type=ActionType.TRAINING_SIGNOFF.value,
                evidence_panel=_session_evidence,
                decision=Decision.HITL_SUPERVISOR,
                decision_actor=None,
                motivation=f"Supervisor competency sign-off: score={score:.2f} >= threshold={self._pass_threshold}",
                budget_snapshot=_EMPTY_BUDGET,
                approval_id=None,  # CR-03: never fabricate UUID for pending HITL
            ))
            hitl_status = "supervisor_pending"

        else:
            # FAILING PATH: write TRAINING_SESSION immediately, no interrupt, no TRAINING_SIGNOFF.
            _thread_id = f"knowledge.training-coach.{session_id}"
            _now = datetime.now(UTC)
            _fail_evidence = EvidencePanel(
                input_summary=f"session={session_id} role={persona_role} score={score:.2f} FAILED"[:500],
                input_truncated=False,
                tool_calls=[],
                rag_citations=[],
                confidence=1.0,
                model="deterministic@training-coach",
                prompt_hash="0" * 64,
                tokens=TokenUsage(input=0, output=0, total=0),
                duration_ms=0,
            )
            await self._audit.write(AuditRecord(
                id=uuid.uuid4(),
                ts=_now,
                action_id=uuid.uuid4(),
                agent_id=AGENT_ID,
                thread_id=_thread_id,
                cluster=CLUSTER,
                action_type=ActionType.TRAINING_SESSION.value,
                evidence_panel=_fail_evidence,
                decision=Decision.AUTO,
                decision_actor=None,
                motivation=None,
                budget_snapshot=_EMPTY_BUDGET,
                approval_id=None,
            ))
            hitl_status = "none"

        logger.info(
            "training_coach_session_complete",
            session_id=session_id,
            hitl_status=hitl_status,
        )

        return {
            "training_session": training_session,
            "competency_result": competency_result,
            "hitl_status": hitl_status,
        }

    async def _retrieve_sop_content(
        self,
        *,
        persona_role: str,
        user_roles: list[str],
        asset_family: str | None,
        k: int,
    ) -> list[Any]:
        """Retrieve SOP content via RAG pipeline for quiz generation.

        Returns list of RagCitation objects (sft_agents.models.evidence.RagCitation).
        Empty list if retrieval_pipeline is None or raises.
        """
        if self._retrieval is None:
            return []
        try:
            kwargs: dict[str, Any] = {
                "query": f"procedure operativa {persona_role}",
                "user_roles": user_roles,
                "category": _DEFAULT_RAG_CATEGORY,
                "k": k,
            }
            if asset_family is not None:
                kwargs["asset_family"] = asset_family
            results = await self._retrieval.search(**kwargs)
            return list(results) if results else []
        except Exception as exc:
            logger.warning(
                "training_coach_retrieval_failed",
                persona_role=persona_role,
                error=str(exc),
            )
            return []

    async def _generate_quiz_questions(
        self,
        *,
        persona_role: str,
        citations: list[Any],
        n_questions: int,
    ) -> list[MCQQuestion]:
        """Generate quiz questions via LLM from SOP citations (LLM used ONLY here).

        Each question carries source_uri from the citation (TRN-05).
        If LLM generation fails, returns a minimal fallback question set.
        correct_answer_index is frozen at generation time (immutable).

        NOTE: This is the ONLY point where LLM is called — never in scoring.
        """
        if self._llm is None or not citations:
            return self._fallback_questions(persona_role=persona_role, n=n_questions)

        try:
            from trn_training_coach.prompts import build_quiz_generation_prompt

            # Build SOP content from citations
            sop_chunks = []
            source_uri = "sop://unknown"
            for citation in citations[:3]:  # use top-3 citations for context
                snippet = getattr(citation, "snippet", str(citation))
                uri = getattr(citation, "source_uri", "sop://unknown")
                sop_chunks.append(f"[{uri}]\n{snippet}")
                source_uri = uri  # use last URI as primary

            sop_content = "\n\n---\n\n".join(sop_chunks)

            system_prompt, user_message = build_quiz_generation_prompt(
                persona_role=persona_role,
                sop_content=sop_content,
                source_uri=source_uri,
                n_questions=n_questions,
                difficulty=_DEFAULT_DIFFICULTY,
            )

            from langchain_core.messages import HumanMessage, SystemMessage
            response = await self._llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ])

            # Parse LLM response JSON
            content = response.content if hasattr(response, "content") else str(response)
            parsed = json.loads(content)
            raw_questions = parsed.get("questions", [])

            questions: list[MCQQuestion] = []
            difficulty = _DEFAULT_DIFFICULTY
            for i, rq in enumerate(raw_questions[:n_questions]):
                # Dynamic difficulty: adapt across questions (D-TC-02)
                if i > 0 and questions:
                    # In generation phase, we start medium and vary by index
                    # Real adaptation is based on answers (delivered per-question)
                    pass
                questions.append(
                    MCQQuestion(
                        question_text=str(rq.get("question_text", f"Domanda {i + 1}")),
                        options=list(rq.get("options", ["A", "B", "C", "D"])),
                        correct_answer_index=int(rq.get("correct_option_index", 0)),
                        source_uri=str(rq.get("source_uri", source_uri)),
                        difficulty=str(rq.get("difficulty", difficulty)),
                    )
                )
            if questions:
                return questions

        except Exception as exc:
            logger.warning(
                "training_coach_quiz_generation_failed",
                persona_role=persona_role,
                error=str(exc),
            )

        return self._fallback_questions(persona_role=persona_role, n=n_questions)

    def _fallback_questions(
        self,
        *,
        persona_role: str,
        n: int,
    ) -> list[MCQQuestion]:
        """Minimal fallback questions when LLM generation fails or is unavailable.

        Returns deterministic questions with source_uri so the quiz session
        can proceed (TRN-05 always satisfied, even in degraded mode).
        """
        difficulty = _DEFAULT_DIFFICULTY
        questions = []
        for i in range(n):
            if i > 0:
                # Vary difficulty across fallback questions for test coverage
                difficulty = next_difficulty(difficulty, answered_correctly=(i % 2 == 0))
            questions.append(
                MCQQuestion(
                    question_text=f"[Modalità degrado] Domanda {i + 1} per {persona_role}: procedure standard?",
                    options=[
                        "Rispettare le procedure SOP",
                        "Procedere senza consultare il supervisore",
                        "Ignorare le istruzioni di sicurezza",
                        "Non documentare l'intervento",
                    ],
                    correct_answer_index=0,  # always first option in fallback
                    source_uri=f"sop://fallback/{persona_role}/question-{i + 1}",
                    difficulty=difficulty,
                )
            )
        return questions


__all__ = ["TrainingCoach", "VALID_PERSONA_ROLES"]
