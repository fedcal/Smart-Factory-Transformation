"""Tests for ``ops_operator_assistant.lang_detect`` (Plan 06-10 — D-OA-03).

Covers:
    - Module-level ``DetectorFactory.seed = 42`` at import time (Pitfall §6).
    - ``detect_language(text)`` returns Literal["it","en"] with IT/EN bias.
    - Exception fallback returns "en".
    - Determinism: 100 sequential detects of same text -> same result.
"""

from __future__ import annotations

import pytest

from ops_operator_assistant.lang_detect import detect_language


# ---------------------------------------------------------------------------
# Module-level seed assertion (Pitfall §6 — seed must be 42 at import time)
# ---------------------------------------------------------------------------


def test_detector_factory_seed_is_42_at_import_time() -> None:
    """Importing ``lang_detect`` must have already seeded DetectorFactory=42."""
    from langdetect import DetectorFactory  # noqa: PLC0415

    assert DetectorFactory.seed == 42, (
        "DetectorFactory.seed must be 42 at module import time — Pitfall §6 "
        "guards against flaky CI from random langdetect seed."
    )


# ---------------------------------------------------------------------------
# Parametric IT/EN detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Italian — textile factory operator phrasing
        ("Il telaio LOOM-01 ha un problema di rottura del filo di ordito.", "it"),
        ("Come posso risolvere lo scarto di colore sul lotto di tintura?", "it"),
        ("Procedura per sostituire il subbio del telaio.", "it"),
        # English — same domain
        ("The loom LOOM-01 has a broken warp end on shaft three.", "en"),
        ("How do I troubleshoot a shade deviation on the dye lot?", "en"),
        ("Procedure for replacing the warp beam on the loom.", "en"),
    ],
)
def test_detect_language_picks_correct_iso(text: str, expected: str) -> None:
    assert detect_language(text) == expected


# ---------------------------------------------------------------------------
# Edge cases: empty / whitespace / mixed -> fallback "en"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["", "   ", "\n\t  ", "123 456 789", "??!!"])
def test_detect_language_unparseable_falls_back_to_en(text: str) -> None:
    """langdetect raises LangDetectException on empty / numeric text; we return 'en'."""
    assert detect_language(text) == "en"


# ---------------------------------------------------------------------------
# Determinism: 100 sequential detects produce the same result
# ---------------------------------------------------------------------------


def test_detect_language_is_deterministic_across_100_calls() -> None:
    """With seed=42, repeated calls on the same input must yield identical output."""
    text = "Il telaio ha bisogno di manutenzione preventiva sul subbio."
    first = detect_language(text)
    for _ in range(100):
        assert detect_language(text) == first, (
            "langdetect must be deterministic with DetectorFactory.seed=42; "
            "got a different result mid-loop — module-level seed lost?"
        )


def test_detect_language_returns_literal_it_or_en_only() -> None:
    """Even on languages outside it/en (Spanish), we must collapse to 'en'."""
    spanish = "El telar tiene un problema con la urdimbre rota."
    portuguese = "O tear tem um problema com o fio quebrado."
    german = "Der Webstuhl hat ein Problem mit dem Kettfaden."
    for text in (spanish, portuguese, german):
        assert detect_language(text) in {"it", "en"}, (
            f"detect_language must return only 'it' or 'en'; "
            f"got something else for {text!r}"
        )
