"""Contract tests for dynamic difficulty adaptation (TRN-02 / D-TC-02).

CONTRACT: DifficultyAdaptor adjusts difficulty within a session based on answers:
  - Correct answer: difficulty rises (easy → medium → hard)
  - Wrong answer: difficulty falls (hard → medium → easy)
  - Difficulty is capped at both ends (cannot go below easy or above hard)

Implementation target: trn_training_coach.difficulty.DifficultyAdaptor
(Wave 2-3 plan: 08-05)

Wave 0 scaffold: test functions fail explicitly with a message naming the
unimplemented contract. NOT module-level pytest.skip (Phase 6/7 Wave 0 decision).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Contract 1: difficulty rises on correct answer
# ---------------------------------------------------------------------------


def test_difficulty_rises_on_correct_answer() -> None:
    """DifficultyAdaptor.next_difficulty(current='easy', answer_correct=True) -> 'medium'.

    D-TC-02: difficulty rises based on correct answers within the session.
    easy → medium on correct, medium → hard on correct.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor.next_difficulty()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: difficulty rises on correct answer "
        "(easy->medium, medium->hard). D-TC-02 dynamic difficulty adaption. "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.difficulty"
    )


def test_difficulty_falls_on_wrong_answer() -> None:
    """DifficultyAdaptor.next_difficulty(current='hard', answer_correct=False) -> 'medium'.

    D-TC-02: difficulty falls based on incorrect answers within the session.
    hard → medium on wrong, medium → easy on wrong.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor.next_difficulty()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: difficulty falls on wrong answer "
        "(hard->medium, medium->easy). D-TC-02 dynamic difficulty adaption. "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.difficulty"
    )


def test_difficulty_capped_at_hard_ceiling() -> None:
    """DifficultyAdaptor does not exceed 'hard' on correct answer at max level.

    next_difficulty(current='hard', answer_correct=True) must stay 'hard'.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor.next_difficulty()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: difficulty capped at 'hard' ceiling; "
        "correct answer at hard level stays hard. "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.difficulty"
    )


def test_difficulty_capped_at_easy_floor() -> None:
    """DifficultyAdaptor does not fall below 'easy' on wrong answer at min level.

    next_difficulty(current='easy', answer_correct=False) must stay 'easy'.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor.next_difficulty()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: difficulty capped at 'easy' floor; "
        "wrong answer at easy level stays easy. "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.difficulty"
    )


def test_difficulty_sequence_across_session() -> None:
    """Full session: easy -correct-> medium -wrong-> easy -correct-> medium -correct-> hard.

    D-TC-02: difficulty adapts per-answer within the session.
    Verify the full sequence over 4 answers produces the expected trajectory.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: full session difficulty trajectory "
        "easy->medium->easy->medium->hard over 4 answers (correct,wrong,correct,correct). "
        "D-TC-02 per-session dynamic difficulty. "
        "Implement in plan 08-05 (training-coach agent). "
        "Module: trn_training_coach.difficulty"
    )
