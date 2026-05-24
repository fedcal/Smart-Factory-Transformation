"""Contract tests for deterministic quiz scoring (TRN-02 / D-TC-01).

CONTRACT: Quiz score = correct_answers / total_questions, computed by index equality
only — NO LLM-judge in the scoring path.

Given an MCQSession with N questions and known correct_answer_index values,
the scorer must return score = (matching indices) / N deterministically.

Implementation target: trn_training_coach.quiz (MCQSession, QuizScorer)
(Wave 2-3 plan: 08-05)

Wave 0 scaffold: test functions fail explicitly with a message naming the
unimplemented contract. NOT module-level pytest.skip (Phase 6/7 Wave 0 decision).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Contract 1: score = correct_count / total (index equality)
# ---------------------------------------------------------------------------


def test_perfect_score_all_correct() -> None:
    """Score == 1.0 when all operator_answer_index == correct_answer_index.

    Given 3 questions with correct_answer_index=[0, 1, 2] and operator answers
    [0, 1, 2], score must be 3/3 = 1.0.

    Implementation target: trn_training_coach.quiz.QuizScorer.score()
    or trn_training_coach.quiz.MCQSession.compute_score()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: score = correct / total by index equality. "
        "Score == 1.0 when all answers match correct_answer_index. "
        "No LLM call in scoring path (D-TC-01 / Pitfall §3). "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.quiz"
    )


def test_partial_score_two_of_three_correct() -> None:
    """Score == 2/3 when 2 of 3 operator answers match correct_answer_index.

    Given correct_answer_index=[1, 0, 2] and operator answers=[1, 1, 2],
    score must be 2/3 ≈ 0.6667 (within 1e-9 tolerance).

    Implementation target: trn_training_coach.quiz.QuizScorer.score()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: partial score = 2/3 for 2 correct out of 3. "
        "Deterministic index equality, no LLM involvement. "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.quiz"
    )


def test_zero_score_all_wrong() -> None:
    """Score == 0.0 when no operator answer matches correct_answer_index.

    Given correct_answer_index=[0, 0, 0] and operator answers=[1, 2, 3],
    score must be 0.0.

    Implementation target: trn_training_coach.quiz.QuizScorer.score()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: score == 0.0 when no answers match. "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.quiz"
    )


def test_score_uses_only_index_equality_no_llm() -> None:
    """Scoring path invokes no LLM: QuizScorer must not call any ainvoke/invoke.

    Given a mock LLM and a QuizScorer, after computing score the mock LLM
    ainvoke.call_count must be 0. Pitfall §3 guard.

    Implementation target: trn_training_coach.quiz.QuizScorer.score()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: scoring must NOT call any LLM method "
        "(ainvoke, invoke, stream). LLM mock.ainvoke.call_count must be 0 "
        "after score computation (Pitfall §3 guard, D-TC-01). "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.quiz"
    )


def test_pass_threshold_default_080() -> None:
    """Score >= 0.80 (default threshold) is a passing session.

    Given a session with score=0.80, session.passed must be True.
    Given score=0.79, session.passed must be False.

    D-TC-03: pass threshold = configurable, default 0.80.

    Implementation target: trn_training_coach.quiz.MCQSession
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: score >= 0.80 (default) -> session.passed=True; "
        "score < 0.80 -> session.passed=False. "
        "D-TC-03: configurable threshold, default 0.80. "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.quiz"
    )
