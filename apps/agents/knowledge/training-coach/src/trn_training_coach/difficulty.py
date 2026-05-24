"""Dynamic difficulty adaptation for TrainingCoach sessions (TRN-02 / D-TC-02).

DifficultyAdaptor wraps the pure next_difficulty function with an object interface
that mirrors the test contract surface (trn_training_coach.difficulty.DifficultyAdaptor).

Immutability: next_difficulty always returns a new string value — it never mutates
the input. The _DIFFICULTY_LEVELS tuple is immutable by design.

Cap behaviour:
    - Correct answer at 'hard': remains 'hard' (ceiling cap).
    - Wrong answer at 'easy': remains 'easy' (floor cap).
    - Unknown current value: treated as 'medium' (middle of scale).
"""

from __future__ import annotations

_DIFFICULTY_LEVELS: tuple[str, ...] = ("easy", "medium", "hard")

_DIFFICULTY_INDEX: dict[str, int] = {level: i for i, level in enumerate(_DIFFICULTY_LEVELS)}


def next_difficulty(current: str, *, answered_correctly: bool) -> str:
    """Compute next difficulty level (D-TC-02).

    Rise on correct answer (easy->medium->hard), fall on incorrect
    (hard->medium->easy). Capped at both extremes.

    Returns a new string — never mutates current (immutability rule).

    Args:
        current: Current difficulty level ("easy", "medium", or "hard").
                 Unknown values default to "medium".
        answered_correctly: True if the operator answered correctly.

    Returns:
        str: The new difficulty level.
    """
    idx = _DIFFICULTY_INDEX.get(current, 1)  # default to medium (index 1)
    if answered_correctly:
        new_idx = min(idx + 1, len(_DIFFICULTY_LEVELS) - 1)
    else:
        new_idx = max(idx - 1, 0)
    return _DIFFICULTY_LEVELS[new_idx]


class DifficultyAdaptor:
    """Stateless adaptor exposing next_difficulty as an object method.

    Tests reference trn_training_coach.difficulty.DifficultyAdaptor.next_difficulty().
    The method signature matches the module-level function for compatibility.
    """

    def next_difficulty(self, current: str, *, answer_correct: bool) -> str:
        """Adapt difficulty based on latest answer (D-TC-02).

        Args:
            current: Current difficulty level ("easy", "medium", or "hard").
            answer_correct: True if the operator answered correctly.

        Returns:
            str: The new difficulty level (new value, no mutation).
        """
        return next_difficulty(current, answered_correctly=answer_correct)


__all__ = ["DifficultyAdaptor", "_DIFFICULTY_LEVELS", "next_difficulty"]
