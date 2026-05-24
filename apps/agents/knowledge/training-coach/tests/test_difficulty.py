"""Contract tests for dynamic difficulty adaptation (TRN-02 / D-TC-02).

CONTRACT: DifficultyAdaptor adjusts difficulty within a session based on answers:
  - Correct answer: difficulty rises (easy → medium → hard)
  - Wrong answer: difficulty falls (hard → medium → easy)
  - Difficulty is capped at both ends (cannot go below easy or above hard)

Implementation target: trn_training_coach.difficulty.DifficultyAdaptor
(Wave 2-3 plan: 08-05)
"""

from __future__ import annotations

import pytest

from trn_training_coach.difficulty import DifficultyAdaptor


# ---------------------------------------------------------------------------
# Contract 1: difficulty rises on correct answer
# ---------------------------------------------------------------------------


def test_difficulty_rises_on_correct_answer() -> None:
    """DifficultyAdaptor.next_difficulty(current='easy', answer_correct=True) -> 'medium'.

    D-TC-02: difficulty rises based on correct answers within the session.
    easy → medium on correct, medium → hard on correct.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor.next_difficulty()
    """
    adaptor = DifficultyAdaptor()

    result_easy_to_medium = adaptor.next_difficulty("easy", answer_correct=True)
    assert result_easy_to_medium == "medium", (
        f"Expected 'medium' after correct at 'easy', got '{result_easy_to_medium}'"
    )

    result_medium_to_hard = adaptor.next_difficulty("medium", answer_correct=True)
    assert result_medium_to_hard == "hard", (
        f"Expected 'hard' after correct at 'medium', got '{result_medium_to_hard}'"
    )


def test_difficulty_falls_on_wrong_answer() -> None:
    """DifficultyAdaptor.next_difficulty(current='hard', answer_correct=False) -> 'medium'.

    D-TC-02: difficulty falls based on incorrect answers within the session.
    hard → medium on wrong, medium → easy on wrong.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor.next_difficulty()
    """
    adaptor = DifficultyAdaptor()

    result_hard_to_medium = adaptor.next_difficulty("hard", answer_correct=False)
    assert result_hard_to_medium == "medium", (
        f"Expected 'medium' after wrong at 'hard', got '{result_hard_to_medium}'"
    )

    result_medium_to_easy = adaptor.next_difficulty("medium", answer_correct=False)
    assert result_medium_to_easy == "easy", (
        f"Expected 'easy' after wrong at 'medium', got '{result_medium_to_easy}'"
    )


def test_difficulty_capped_at_hard_ceiling() -> None:
    """DifficultyAdaptor does not exceed 'hard' on correct answer at max level.

    next_difficulty(current='hard', answer_correct=True) must stay 'hard'.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor.next_difficulty()
    """
    adaptor = DifficultyAdaptor()

    result = adaptor.next_difficulty("hard", answer_correct=True)
    assert result == "hard", (
        f"Expected 'hard' (ceiling cap) after correct at 'hard', got '{result}'"
    )


def test_difficulty_capped_at_easy_floor() -> None:
    """DifficultyAdaptor does not fall below 'easy' on wrong answer at min level.

    next_difficulty(current='easy', answer_correct=False) must stay 'easy'.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor.next_difficulty()
    """
    adaptor = DifficultyAdaptor()

    result = adaptor.next_difficulty("easy", answer_correct=False)
    assert result == "easy", (
        f"Expected 'easy' (floor cap) after wrong at 'easy', got '{result}'"
    )


def test_difficulty_sequence_across_session() -> None:
    """Full session: easy -correct-> medium -wrong-> easy -correct-> medium -correct-> hard.

    D-TC-02: difficulty adapts per-answer within the session.
    Verify the full sequence over 4 answers produces the expected trajectory.

    Implementation target: trn_training_coach.difficulty.DifficultyAdaptor
    """
    adaptor = DifficultyAdaptor()

    # Start at easy
    current = "easy"
    answers = [True, False, True, True]
    expected_trajectory = ["medium", "easy", "medium", "hard"]

    for i, (answer, expected) in enumerate(zip(answers, expected_trajectory)):
        current = adaptor.next_difficulty(current, answer_correct=answer)
        assert current == expected, (
            f"Step {i}: after answer_correct={answer}, expected '{expected}', got '{current}'. "
            f"Full expected trajectory: {expected_trajectory}"
        )
