"""Knowledge agent: personalized training coach for factory operators (TRN-02 / D-TC-01/02/03)."""

from __future__ import annotations

from trn_training_coach.agent import TrainingCoach
from trn_training_coach.difficulty import DifficultyAdaptor, next_difficulty
from trn_training_coach.models import CompetencyResult, TrainingSession
from trn_training_coach.quiz import MCQQuestion, MCQSession, score_session

__version__ = "0.1.0"

__all__ = [
    "CompetencyResult",
    "DifficultyAdaptor",
    "MCQQuestion",
    "MCQSession",
    "TrainingCoach",
    "TrainingSession",
    "next_difficulty",
    "score_session",
]
