"""Sanitizer deterministico anti prompt-injection per il pipeline ingest (SEC-04).

Applica due strati di sanitizzazione sul testo PLAIN estratto dal parser:
    1. Denylist regex: strip dei pattern injection noti → sostituisce con [REDACTED].
    2. bleach.clean(tags=[], strip=True): rimuove HTML residuo (es. da PDF con embedding HTML).
    3. Normalizzazione whitespace eccessivo.

Design rationale:
    - Deterministico, NO LLM — CI-testabile e riproducibile (CONTEXT locked decision 3).
    - Applicato sul testo PLAIN post-parse, MAI sul Markdown grezzo (Pitfall 6 in RESEARCH):
      bleach su Markdown strutturato può strip sintassi legittima.
    - Ritorna sempre str (mai None) — validazione input al boundary.

Threat mitigation:
    T-11-03-02 (Tampering via prompt injection): denylist + bleach bloccano i pattern
    injection noti prima che il testo raggiunga l'embedder e Qdrant.

SC-3: il test crafted-PDF in tests/security/test_prompt_injection.py dimostra che
nessuna istruzione imperativa sopravvive alla sanitizzazione.

RESEARCH Pattern 6 — services/knowledge-ingest/sanitizer.py
"""

from __future__ import annotations

import re

import bleach

# Pattern per rimuovere tag script/style con il CONTENUTO interno (WR-02).
# bleach.clean(strip=True) rimuove i tag ma lascia il testo interno visibile:
# "<script>alert('xss')</script>" → "alert('xss')" — il payload XSS sopravvive.
# Questi pattern eliminano sia il tag che il contenuto (DOTALL per multi-linea).
_SCRIPT_CONTENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL),
)

# ---------------------------------------------------------------------------
# Denylist regex per pattern injection noti (deterministic, IGNORECASE)
# ---------------------------------------------------------------------------
# Ogni pattern cattura una famiglia di istruzioni injection note:
#   1. "ignore (all) previous instructions" — prompt override classico
#   2. "you are now a" — persona override
#   3. "system :" + varianti — system prompt injection
#   4. Token speciali modello: [INST], [/INST], <|im_start|>, <|im_end|> — Llama/Mistral delimiters
#   5. "### Human:", "### Assistant:", "### System:" — ChatML/Alpaca style delimiters
#   6. "<system>" / "</system>" — tag XML system
#   7. "disregard (all) previous" — variante override
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>", re.IGNORECASE),
    re.compile(r"###\s*(Human|Assistant|System)\s*:", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous", re.IGNORECASE),
)

# Limit whitespace normalization: 3+ consecutive whitespace/newlines → double newline
_EXCESS_WHITESPACE = re.compile(r"\s{3,}")


def sanitize_document(text: str) -> str:
    """Applica sanitizzazione deterministica anti-injection sul testo plain post-parse.

    Pipeline:
        1. Valida input (stringa — fail fast se non str).
        2. Rimuove tag script/style con il loro contenuto (WR-02: prevenzione XSS payload).
        3. Applica ogni pattern della denylist con .sub("[REDACTED]", ...).
        4. Applica bleach.clean(tags=[], strip=True) per rimuovere HTML residuo.
        5. Normalizza whitespace eccessivo (3+ → doppio newline).
        6. Strip finale e ritorna stringa (mai None).

    Args:
        text: Testo plain estratto dal parser (post-parse, prima dell'embedding).
              Deve essere testo plain, NON Markdown grezzo (Pitfall 6).

    Returns:
        Testo sanitizzato — sempre str, mai None.

    Raises:
        TypeError: se text non è una stringa (violazione del contratto al boundary).
    """
    # Validazione input al boundary (CODING-STYLE: fail fast con messaggio chiaro)
    if not isinstance(text, str):
        raise TypeError(
            f"sanitize_document() richiede str, ricevuto {type(text).__name__!r}"
        )

    # Stringa vuota o solo whitespace — ritorna stringa vuota (immutabilità: nuova str)
    if not text.strip():
        return ""

    # 1. Rimozione tag script/style con contenuto (WR-02: prevenzione XSS payload nel testo).
    # Deve avvenire PRIMA del bleach pass perché bleach rimuove i tag ma lascia il contenuto:
    # "<script>alert('xss')</script>" → bleach → "alert('xss')" — payload sopravvive.
    result: str = text
    for pattern in _SCRIPT_CONTENT_PATTERNS:
        result = pattern.sub("", result)

    # 2. Denylist regex — ogni pattern sostituisce con [REDACTED]
    for pattern in _INJECTION_PATTERNS:
        result = pattern.sub("[REDACTED]", result)

    # 3. bleach.clean() — strip HTML residuo (tags=[] = whitelist vuota, nessun tag permesso)
    # strip=True rimuove i tag invece di escaping, producendo testo plain leggibile.
    result = bleach.clean(result, tags=[], strip=True)

    # 3. Normalizzazione whitespace eccessivo (3+ → doppio newline)
    result = _EXCESS_WHITESPACE.sub("\n\n", result)

    return result.strip()


__all__ = ["sanitize_document"]
