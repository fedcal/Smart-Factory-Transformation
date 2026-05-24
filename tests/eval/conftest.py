"""Pytest conftest for eval gate tests (Phase 11 — Plan 11-00, OBS-05/06).

Provides:
    MockDeepEvalLLM: LLM stub deterministico per CI gate senza GPU.
        Score varia in base al campo `expected_score` del fixture per
        permettere al gate di fallire (non sempre 1 — anti-pattern evitato).
    ground_truth_dataset: fixture che carica tests/eval/dataset/ground_truth.jsonl.

Ragas 0.4.3 compatibility patch:
    langchain_community 0.4.x ha rimosso ChatVertexAI. Questo conftest applica
    uno stub del modulo mancante PRIMA che ragas venga importato, permettendo
    l'uso delle metriche non-LLM senza dipendere da Google Cloud SDK.
    (RESEARCH Finding: ragas 0.4.3 + langchain-community 0.4.x compatibility bug)
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Ragas 0.4.3 compatibility patch (applicato prima di qualsiasi import ragas)
# langchain_community 0.4.x ha rimosso chat_models.vertexai — stub il modulo.
# ---------------------------------------------------------------------------
_vertexai_stub = types.ModuleType("langchain_community.chat_models.vertexai")


class _StubChatVertexAI:
    """Stub per ChatVertexAI rimosso in langchain-community 0.4.x."""

    pass


_vertexai_stub.ChatVertexAI = _StubChatVertexAI  # type: ignore[attr-defined]
sys.modules.setdefault(
    "langchain_community.chat_models.vertexai", _vertexai_stub
)

# ---------------------------------------------------------------------------
# MockDeepEvalLLM — LLM deterministico per CI gate (RESEARCH Pattern 4)
# ---------------------------------------------------------------------------

try:
    from deepeval.models import DeepEvalBaseLLM

    class MockDeepEvalLLM(DeepEvalBaseLLM):
        """LLM stub per CI eval gate — nessuna chiamata a LLM reale.

        Il metodo generate() restituisce uno score variabile basato sul campo
        `expected_score` del contesto (se presente nel fixture), garantendo
        che il gate possa effettivamente fallire su scenari negativi.

        Non restituisce sempre 1 (anti-pattern evitato — RESEARCH Pattern 4).
        """

        def __init__(self, default_score: float = 0.8) -> None:
            self._default_score = default_score

        def get_model_name(self) -> str:
            return "MockDeepEvalLLM-v1-deterministic"

        def load_model(self) -> Any:
            return None

        def generate(self, prompt: str, **kwargs: Any) -> str:  # type: ignore[override]
            """Restituisce una risposta JSON deterministica.

            Se il prompt contiene `expected_score`, usa quel valore.
            Altrimenti usa il default.
            """
            import re

            score_match = re.search(r'"expected_score"\s*:\s*([\d.]+)', prompt)
            score = float(score_match.group(1)) if score_match else self._default_score
            return json.dumps({"score": score, "reason": "mock-deterministic"})

        async def a_generate(self, prompt: str, **kwargs: Any) -> str:  # type: ignore[override]
            return self.generate(prompt, **kwargs)

except ImportError:
    # DeepEval non installato — skip graceful per ambienti senza eval deps

    class MockDeepEvalLLM:  # type: ignore[no-redef]
        """Placeholder se deepeval non è installato."""

        def __init__(self, default_score: float = 0.8) -> None:
            self._default_score = default_score

        def get_model_name(self) -> str:
            return "MockDeepEvalLLM-v1-deterministic"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_GROUND_TRUTH_PATH = (
    Path(__file__).parent / "dataset" / "ground_truth.jsonl"
)


@pytest.fixture(scope="session")
def ground_truth_dataset() -> list[dict[str, Any]]:
    """Carica il dataset di ground truth da tests/eval/dataset/ground_truth.jsonl.

    Returns:
        Lista di dict con chiavi: question, contexts, ground_truth, expected_score, cluster.
    """
    if not _GROUND_TRUTH_PATH.exists():
        pytest.skip(f"ground_truth.jsonl not found at {_GROUND_TRUTH_PATH}")

    rows = [
        json.loads(line)
        for line in _GROUND_TRUTH_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return rows
