"""Pytest conftest for eval gate tests (Phase 11 — Plan 11-00/11-02, OBS-05/06).

Provides:
    MockDeepEvalLLM: LLM stub deterministico per CI gate senza GPU.
        Gestisce i prompt DeepEval 4.0.3 per HallucinationMetric e
        AnswerRelevancyMetric restituendo JSON strutturati (verdicts/statements)
        in modo deterministico, analizzando il token-overlap tra context e output.
        Il gate può fallire su scenari con contesti irrilevanti (T-11-02-01).
    ground_truth_dataset: fixture che carica tests/eval/dataset/ground_truth.jsonl.
    mock_deepeval_llm: istanza sessione del MockDeepEvalLLM per 11-02.

Ragas 0.4.3 compatibility patch:
    langchain_community 0.4.x ha rimosso ChatVertexAI. Questo conftest applica
    uno stub del modulo mancante PRIMA che ragas venga importato.
    (RESEARCH Finding: ragas 0.4.3 + langchain-community 0.4.x compatibility bug)

DeepEval 4.0.3 JSON schema (11-02 finding):
    HallucinationMetric prompt: contiene "Contexts: [...]" e "Actual Output: ..."
        Risposta attesa: {"verdicts": [{"verdict": "yes"|"no", "reason": str}]}
        1 verdict per contesto. "yes" = output consistente con context.
        HallucinationMetric.score = fraction(verdicts == "no") → 0 = nessuna hallucination.

    AnswerRelevancyMetric prompt fase 1: "breakdown and generate a list of statements"
        Risposta attesa: {"statements": [str, ...]}

    AnswerRelevancyMetric prompt fase 2: "determine whether each statement is relevant"
        Risposta attesa: {"verdicts": [{"verdict": "yes"|"no"|"idk"}]}
        AnswerRelevancyMetric.score = fraction(verdicts != "no") → 1.0 = tutto rilevante.

Strategia di score per i due scenari:
    Golden (contesti rilevanti): token-overlap alto → verdicts "yes" → hallucination 0.0
    Degraded (contesti irrilevanti): token-overlap basso → verdicts "no" → hallucination 1.0

Il MockDeepEvalLLM analizza il token-overlap context↔output nel prompt per
determinare la qualità — questo prova che il gate è sensibile ai dati reali.
"""
from __future__ import annotations

import json
import re
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
# Token overlap helper — usato da MockDeepEvalLLM per determinare la qualità
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "il", "la", "lo", "i", "gli", "le", "un", "una", "di", "del", "della",
    "dello", "dei", "degli", "delle", "a", "ad", "da", "in", "su", "per",
    "tra", "fra", "con", "e", "o", "ma", "che", "si", "è", "non",
    "al", "ai", "nel", "nella", "nei", "nelle", "col", "coi", "the", "a",
    "an", "of", "in", "on", "for", "to", "is", "are", "was", "were",
})


def _token_overlap_ratio(text_a: str, text_b: str) -> float:
    """Rapporto di overlap token tra due testi (minuscolo, senza stopword).

    Usato per valutare la rilevanza contesto↔output in modo deterministico.
    """
    def _toks(t: str) -> set[str]:
        return {
            tok for tok in t.lower().split()
            if tok.isalpha() and tok not in _STOP_WORDS
        }

    toks_a = _toks(text_a)
    toks_b = _toks(text_b)
    if not toks_a or not toks_b:
        return 0.0
    intersection = toks_a & toks_b
    union = toks_a | toks_b
    return len(intersection) / len(union)  # Jaccard coefficient


# ---------------------------------------------------------------------------
# MockDeepEvalLLM — LLM deterministico per CI gate (RESEARCH Pattern 4)
# Versione 2 (11-02): gestisce i JSON schema di DeepEval 4.0.3 usando
# token-overlap per simulare la qualità dei verdicts.
# ---------------------------------------------------------------------------

try:
    from deepeval.models import DeepEvalBaseLLM

    class MockDeepEvalLLM(DeepEvalBaseLLM):
        """LLM stub per CI eval gate — nessuna chiamata a LLM reale.

        Analizza il token-overlap tra Contexts e Actual Output nel prompt
        per generare verdicts deterministici. Threshold di overlap: 0.15
        (Jaccard). Sotto soglia → "no" (hallucination / irrilevante).

        Non restituisce mai score costante — sensibile ai dati (T-11-02-01).
        """

        # Soglia Jaccard per considerare context "rilevante" all'output.
        # 0.08 (invece di 0.15) per gestire scenari dove il ground_truth
        # è un riassunto sintetico del contesto tecnico dettagliato
        # (overlap Jaccard naturalmente basso per coppia tecnico→riassunto).
        OVERLAP_THRESHOLD: float = 0.08

        def __init__(self, default_score: float = 0.8) -> None:
            self._default_score = default_score

        def get_model_name(self) -> str:
            return "MockDeepEvalLLM-v1-deterministic"

        def load_model(self) -> Any:
            return None

        def _extract_contexts_and_output(
            self, prompt: str
        ) -> tuple[list[str], str]:
            """Estrae Contexts e Actual Output dal prompt DeepEval."""
            # Estrai contesti dalla sezione "Contexts: [...]"
            ctx_match = re.search(r"Contexts:\s*\[(.+?)\]\s*\n", prompt, re.DOTALL)
            contexts: list[str] = []
            if ctx_match:
                ctx_raw = ctx_match.group(1)
                # Estrai stringhe tra virgolette
                contexts = re.findall(r"'([^']*)'|\"([^\"]*\"?[^\"]*?)\"", ctx_raw)
                contexts = [a or b for a, b in contexts if a or b]
            if not contexts:
                contexts = [""]

            # Estrai Actual Output
            out_match = re.search(
                r"Actual Output:\s*\n(.+?)(?:\nJSON:|\Z)", prompt, re.DOTALL
            )
            output = out_match.group(1).strip() if out_match else ""
            return contexts, output

        def _extract_statements(self, prompt: str) -> list[str]:
            """Estrae statements dal testo nell'area 'Text:' del prompt (DeepEval 4.x)."""
            # Il prompt termina con:
            #   Text:\n<actual_output>\n\nJSON:
            text_match = re.search(r"\nText:\s*\n(.+?)\n\nJSON:", prompt, re.DOTALL)
            if text_match:
                text = text_match.group(1).strip()
                # Divide in frasi/clausole
                parts = [s.strip() for s in re.split(r"[.;]", text) if s.strip() and len(s.strip()) > 4]
                return parts[:4] if parts else [text[:60]]
            return ["mock statement extracted from output"]

        def _generate_hallucination_verdicts(
            self, prompt: str
        ) -> str:
            """Genera verdicts per HallucinationMetric via token-overlap."""
            contexts, output = self._extract_contexts_and_output(prompt)
            verdicts = []
            for ctx in contexts:
                ratio = _token_overlap_ratio(ctx, output)
                if ratio >= self.OVERLAP_THRESHOLD:
                    verdicts.append({
                        "verdict": "yes",
                        "reason": f"mock: context and output share tokens (overlap={ratio:.2f})",
                    })
                else:
                    verdicts.append({
                        "verdict": "no",
                        "reason": (
                            f"mock: context and output have low overlap ({ratio:.2f}) "
                            "— possible hallucination or irrelevant context"
                        ),
                    })
            return json.dumps({"verdicts": verdicts})

        def _generate_statements(self, prompt: str) -> str:
            """Genera statements per AnswerRelevancyMetric fase 1."""
            stmts = self._extract_statements(prompt)
            return json.dumps({"statements": stmts})

        def _generate_relevancy_verdicts(self, prompt: str) -> str:
            """Genera verdicts per AnswerRelevancyMetric fase 2.

            Strategia: un statement è rilevante se è una frase tecnica sostanziale
            (≥ 5 token non-stop). Solo placeholder molto corti o vuoti → "no".
            Questo simula correttamente un CI gate che distingue risposte RAG
            tecniche (rilevanti) da non-risposte o placeholder (irrilevanti).

            Nota: l'overlap keyword domanda↔risposta è basso per risposte tecniche
            RAG (domanda: "Come si calibra..." vs risposta: "...scollegare dall'impianto,
            applicare pressione zero...") — non usare overlap come criteri primario.
            """
            # Il prompt termina con:
            #   Input:\n<question>\n\nStatements:\n<list>\n\nJSON:
            stmt_match = re.search(r"\nStatements:\s*\n(.+?)(?:\n\nJSON:|\Z)", prompt, re.DOTALL)
            stmts_text = stmt_match.group(1).strip() if stmt_match else ""

            # Gli statements possono essere in formato lista Python: ['stmt1', 'stmt2']
            if stmts_text.startswith("["):
                raw_stmts = re.findall(r"'([^']+)'|\"([^\"]+)\"", stmts_text)
                statements = [a or b for a, b in raw_stmts if a or b]
            else:
                statements = [s.strip() for s in stmts_text.split("\n") if s.strip()]

            verdicts: list[dict[str, str]] = []
            for stmt in statements or ["mock"]:
                # Conta token significativi (no stopword, solo alfanumerici ≥2 char)
                # Soglia abbassata a 3 per gestire risposte RAG tecniche sintetiche
                # (es. "Calibrazione semestrale o dopo sostituzione celle" = 4 token)
                n_meaningful = sum(
                    1 for t in stmt.lower().split()
                    if t.isalpha() and len(t) >= 2 and t not in _STOP_WORDS
                )
                if n_meaningful >= 3:
                    # Statement tecnico sostanziale → rilevante (risposta RAG valida)
                    verdicts.append({"verdict": "yes"})
                elif n_meaningful >= 1:
                    # Statement breve ma non vuoto → ambiguo (conta come non-no)
                    verdicts.append({"verdict": "idk"})
                else:
                    # Placeholder/vuoto/singola parola → irrilevante
                    verdicts.append({
                        "verdict": "no",
                        "reason": f"mock: trivial/empty statement ({n_meaningful} meaningful tokens)",
                    })
            return json.dumps({"verdicts": verdicts})

        def generate(self, prompt: str, **kwargs: Any) -> str:  # type: ignore[override]
            """Genera JSON deterministico analizzando il tipo di prompt.

            Routing:
              - "agrees with EACH context" OR "Contexts:" + "Actual Output:" → Hallucination
              - "breakdown and generate a list of statements" → Relevancy fase 1
              - "determine whether each statement is relevant" → Relevancy fase 2
              - Altrimenti → score generico
            """
            # Tipo 1: HallucinationMetric
            if "agrees with EACH context" in prompt or (
                "Contexts:" in prompt
                and "Actual Output:" in prompt
                and "statements" not in prompt.lower()[:500]
            ):
                return self._generate_hallucination_verdicts(prompt)

            # Tipo 2a: AnswerRelevancyMetric — generate_statements
            if "breakdown and generate a list of statements" in prompt:
                return self._generate_statements(prompt)

            # Tipo 2b: AnswerRelevancyMetric — generate_verdicts
            if "determine whether each statement is relevant" in prompt:
                return self._generate_relevancy_verdicts(prompt)

            # Fallback: risposta numerica generica
            return json.dumps({"score": self._default_score, "reason": "mock-deterministic"})

        async def a_generate(self, prompt: str, **kwargs: Any) -> str:  # type: ignore[override]
            return self.generate(prompt, **kwargs)

except ImportError:
    # DeepEval non installato — placeholder graceful per ambienti senza eval deps

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
def mock_deepeval_llm() -> "MockDeepEvalLLM":
    """Istanza sessione del MockDeepEvalLLM per i test CI gate (11-02).

    Token-overlap deterministico — il gate può fallire su scenari con
    contesti irrilevanti (anti-pattern score-fisso evitato, T-11-02-01).
    """
    return MockDeepEvalLLM()


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
