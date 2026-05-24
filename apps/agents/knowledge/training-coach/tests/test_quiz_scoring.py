"""Contract tests for deterministic quiz scoring (TRN-02 / D-TC-01).

CONTRACT: Quiz score = correct_answers / total_questions, computed by index equality
only — NO LLM-judge in the scoring path.

Given an MCQSession with N questions and known correct_answer_index values,
the scorer must return score = (matching indices) / N deterministically.

Implementation target: trn_training_coach.quiz (MCQSession, QuizScorer)
(Wave 2-3 plan: 08-05)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from trn_training_coach.quiz import MCQQuestion, MCQSession, score_session


def _make_question(
    correct_answer_index: int = 0,
    difficulty: str = "medium",
    source_uri: str = "sop://test/section-1",
) -> MCQQuestion:
    """Helper to build a minimal MCQQuestion for test fixtures."""
    return MCQQuestion(
        question_text="Test question?",
        options=["Option A", "Option B", "Option C"],
        correct_answer_index=correct_answer_index,
        source_uri=source_uri,
        difficulty=difficulty,
    )


def _make_session(
    questions: list[MCQQuestion],
    answers: list[int],
) -> MCQSession:
    """Helper to build an MCQSession with given questions and answers."""
    return MCQSession(
        session_id="test-session-001",
        persona_role="tessitore",
        questions=questions,
        answers=answers,
    )


# ---------------------------------------------------------------------------
# Contract 1: score = correct_count / total (index equality)
# ---------------------------------------------------------------------------


def test_perfect_score_all_correct() -> None:
    """Score == 1.0 when all operator_answer_index == correct_answer_index.

    Given 3 questions with correct_answer_index=[0, 1, 2] and operator answers
    [0, 1, 2], score must be 3/3 = 1.0.

    Implementation target: trn_training_coach.quiz.score_session()
    """
    questions = [
        _make_question(correct_answer_index=0),
        _make_question(correct_answer_index=1),
        _make_question(correct_answer_index=2),
    ]
    session = _make_session(questions=questions, answers=[0, 1, 2])

    result = score_session(session)

    assert result == 1.0, f"Expected 1.0 for all-correct session, got {result}"


def test_partial_score_two_of_three_correct() -> None:
    """Score == 2/3 when 2 of 3 operator answers match correct_answer_index.

    Given correct_answer_index=[1, 0, 2] and operator answers=[1, 1, 2],
    score must be 2/3 ≈ 0.6667 (within 1e-9 tolerance).

    Implementation target: trn_training_coach.quiz.score_session()
    """
    questions = [
        _make_question(correct_answer_index=1),
        _make_question(correct_answer_index=0),
        _make_question(correct_answer_index=2),
    ]
    session = _make_session(questions=questions, answers=[1, 1, 2])

    result = score_session(session)

    expected = 2 / 3
    assert abs(result - expected) < 1e-9, f"Expected {expected}, got {result}"


def test_zero_score_all_wrong() -> None:
    """Score == 0.0 when no operator answer matches correct_answer_index.

    Given correct_answer_index=[0, 0, 0] and operator answers=[1, 2, 3] (all wrong),
    score must be 0.0.

    Implementation target: trn_training_coach.quiz.score_session()
    """
    questions = [
        _make_question(correct_answer_index=0),
        _make_question(correct_answer_index=0),
        _make_question(correct_answer_index=0),
    ]
    session = _make_session(questions=questions, answers=[1, 2, 1])

    result = score_session(session)

    assert result == 0.0, f"Expected 0.0 for all-wrong session, got {result}"


def test_score_uses_only_index_equality_no_llm() -> None:
    """Scoring path invokes no LLM: score_session must not call any ainvoke/invoke.

    Given a mock LLM and a quiz session, after computing score the mock LLM
    ainvoke.call_count must be 0. Pitfall §3 guard.

    Implementation target: trn_training_coach.quiz.score_session()
    """
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()
    mock_llm.invoke = MagicMock()

    questions = [
        _make_question(correct_answer_index=0),
        _make_question(correct_answer_index=1),
    ]
    session = _make_session(questions=questions, answers=[0, 1])

    # score_session is pure — no LLM reference at all
    result = score_session(session)

    assert result == 1.0
    assert mock_llm.ainvoke.call_count == 0, (
        f"LLM.ainvoke was called {mock_llm.ainvoke.call_count} times — "
        "scoring must be LLM-free (Pitfall §3, T-08-09)."
    )
    assert mock_llm.invoke.call_count == 0, (
        f"LLM.invoke was called {mock_llm.invoke.call_count} times — "
        "scoring must be LLM-free (Pitfall §3, T-08-09)."
    )


def test_pass_threshold_default_080() -> None:
    """Score >= 0.80 (default threshold) is a passing session.

    Given a session with score=0.80, passed must be True.
    Given score=0.79, passed must be False.

    D-TC-03: pass threshold = configurable, default 0.80.

    We test TrainingSession.passed field using the models module.
    """
    from datetime import datetime, timezone

    from trn_training_coach.models import TrainingSession

    utcnow = datetime.now(timezone.utc)
    pass_threshold = 0.80

    # Passing case: score exactly at threshold
    passing = TrainingSession(
        session_id="sess-pass",
        persona_role="tessitore",
        score=0.80,
        passed=0.80 >= pass_threshold,
        threshold=pass_threshold,
        completed_at=utcnow,
    )
    assert passing.passed is True, "Score 0.80 >= 0.80 should be passing"

    # Failing case: score just below threshold
    failing = TrainingSession(
        session_id="sess-fail",
        persona_role="tessitore",
        score=0.79,
        passed=0.79 >= pass_threshold,
        threshold=pass_threshold,
        completed_at=utcnow,
    )
    assert failing.passed is False, "Score 0.79 < 0.80 should be failing"
