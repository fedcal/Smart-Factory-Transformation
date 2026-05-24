"""Deterministic multiple-choice quiz models and scoring (TRN-02 / D-TC-01).

MCQQuestion and MCQSession are frozen Pydantic models — generated at session start
and never mutated (RESEARCH Open Q2). score_session is a pure function: no LLM call,
no async, no side effects. Scoring is strictly operator_answer_index == correct_answer_index
comparison (Pitfall §3 avoidance).

Trust boundary mitigation (T-08-09):
    Scoring is index-comparison only. LLM is never called in the scoring path.
    correct_answer_index is frozen at generation time and cannot be overwritten.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MCQQuestion(BaseModel):
    """Multiple-choice question with frozen correct answer index (D-TC-01).

    correct_answer_index is set once at generation time and frozen.
    options length is constrained to [2, 6].
    source_uri carries the citation link per question (TRN-05).
    difficulty labels the adaptive level ("easy" | "medium" | "hard") (D-TC-02).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    question_text: str = Field(min_length=1, description="Question text presented to operator.")
    options: list[str] = Field(min_length=2, max_length=6, description="Answer options (2..6).")
    correct_answer_index: int = Field(ge=0, description="Index into options of the correct answer.")
    source_uri: str = Field(min_length=1, description="URI of the source SOP/document (TRN-05).")
    difficulty: str = Field(description='Difficulty level: "easy", "medium", or "hard" (D-TC-02).')


class MCQSession(BaseModel):
    """Frozen quiz session — no LLM in scoring path (D-TC-01).

    questions is frozen at session start (generate-at-session-start, RESEARCH Open Q2).
    answers is the list of operator_answer_index values, one per question.
    answers default is empty list (session not yet answered).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1, description="UUID session identifier.")
    persona_role: str = Field(min_length=1, description="SOP frontmatter role (D-X-03).")
    questions: list[MCQQuestion] = Field(description="Frozen question bank for this session.")
    answers: list[int] = Field(
        default_factory=list,
        description="Operator answer indices (one per question, submitted after quiz delivery).",
    )


def score_session(session: MCQSession) -> float:
    """Deterministic score: correct_answers / total_questions (D-TC-01).

    Scoring is operator_answer_index == correct_answer_index comparison only.
    No LLM judge in this path (Pitfall §3 avoidance, T-08-09 mitigation).

    Returns:
        float in [0.0, 1.0].
        0.0 when questions list is empty.

    This function is pure: no async, no LLM import, no side effects.
    """
    if not session.questions:
        return 0.0
    correct = sum(
        1
        for q, a in zip(session.questions, session.answers)
        if a == q.correct_answer_index
    )
    return correct / len(session.questions)


__all__ = ["MCQQuestion", "MCQSession", "score_session"]
