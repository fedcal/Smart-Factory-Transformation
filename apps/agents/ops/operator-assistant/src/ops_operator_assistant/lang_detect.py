"""Deterministic IT/EN language detection (D-OA-03, Pitfall §6).

Wraps the third-party ``langdetect`` package (Mimino/MIT, ~25M downloads/month,
https://github.com/Mimino666/langdetect) and pins ``DetectorFactory.seed = 42``
once at module import. The seed is a module-level global; resetting it from
multiple call sites is a race condition (Pitfall §6) — we seed exactly once,
here, and never again.

Why a tiny wrapper instead of calling ``langdetect.detect`` directly:
    1. Collapse the open-set ISO 639-1 output to a closed ``Literal["it","en"]``
       so downstream prompts / responses can statically assume one of two
       templates (the OperatorAssistant currently ships only IT + EN prompts).
    2. Swallow ``langdetect.lang_detect_exception.LangDetectException`` on empty
       / numeric / pure-punctuation input and fall back to "en" — the safer
       default for a factory-floor agent (English SOPs are the original
       authoritative copy; Italian is the translation).
    3. Keep the import + seed side effect localized to one file so audit /
       review can verify Pitfall §6 with a single grep.
"""

from __future__ import annotations

from typing import Literal

from langdetect import DetectorFactory, detect
from langdetect.lang_detect_exception import LangDetectException

# Pitfall §6 — seed the global DetectorFactory exactly once, at module import.
# asyncio is single-threaded so concurrent tasks cannot race the seed; the
# remaining hazard is *resetting* the seed from another module, which we
# avoid by centralizing all langdetect usage in this file.
DetectorFactory.seed = 42


def detect_language(text: str) -> Literal["it", "en"]:
    """Return ``"it"`` for Italian-looking text, else ``"en"``.

    Args:
        text: Free-form user query (typically an operator chat message).

    Returns:
        ``"it"`` when ``langdetect.detect(text)`` returns an Italian ISO code
        (starts with ``"it"``); ``"en"`` otherwise (including all fallback
        cases — exceptions, empty input, non-IT/EN languages such as Spanish
        or Portuguese which collapse to the safer English template).
    """
    try:
        detected = detect(text)
    except LangDetectException:
        # Empty / whitespace-only / numeric input raises LangDetectException
        # ("No features in text."). Falling back to "en" is conservative.
        return "en"
    return "it" if detected.startswith("it") else "en"


__all__ = ["detect_language"]
