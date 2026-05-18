"""GDPRRedactor — strip PII from EvidencePanel.input_summary (T-04-Checkpoint-PII).

Defense-in-depth rationale (PLAN.md <interfaces> note):
    Regex patterns live as **module-level Python constants**, NOT in a YAML
    policy file. An attacker who edits a YAML on disk could silently disable
    redaction; forcing the regexes through code+PR review provides tamper-
    evidence at the boundary where PII flows into the LangGraph checkpointer.

Patterns covered:
    - International phone numbers (E.164-ish)
    - Email addresses (RFC-5322 simplified)
    - Italian Codice Fiscale (16-char alphanumeric)

Output replacement tokens:
    [REDACTED-PHONE], [REDACTED-EMAIL], [REDACTED-CF]
"""

from __future__ import annotations

import re

from sft_agents.models.evidence import EvidencePanel

# Module-level compiled regex constants. These are the ONLY place redaction
# rules are encoded — Python-source-as-source-of-truth.
# Phone: optional leading +, then 8..17 digits with separators.
_PHONE_RE: re.Pattern[str] = re.compile(r"\+?\d[\d\s().-]{7,15}\d")

# Email: RFC-5322 simplified (good enough for the EvidencePanel 500-char cap).
_EMAIL_RE: re.Pattern[str] = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

# Italian Codice Fiscale: 6 letters + 2 digits + letter + 2 digits + letter +
# 3 digits + letter, all uppercase ASCII.
_CF_RE: re.Pattern[str] = re.compile(
    r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b"
)


def redact_str(s: str) -> str:
    """Apply phone/email/CF redaction in deterministic order.

    Order matters: CF is checked BEFORE phone (a CF contains digits that the
    phone regex could otherwise greedy-match into).
    """
    if not isinstance(s, str):
        return s
    out = _CF_RE.sub("[REDACTED-CF]", s)
    out = _EMAIL_RE.sub("[REDACTED-EMAIL]", out)
    out = _PHONE_RE.sub("[REDACTED-PHONE]", out)
    return out


def redact_evidence(panel: EvidencePanel) -> EvidencePanel:
    """Return a new EvidencePanel with input_summary redacted.

    The model is frozen + extra=forbid so we use ``model_copy(update=...)``
    rather than mutating in place.
    """
    return panel.model_copy(
        update={"input_summary": redact_str(panel.input_summary)}
    )


class GDPRRedactor:
    """Stateless façade exposing redact() at the EvidencePanel boundary.

    Usage::

        redactor = GDPRRedactor()
        clean_panel = redactor.redact(panel)
    """

    def redact(self, panel: EvidencePanel) -> EvidencePanel:
        return redact_evidence(panel)

    @staticmethod
    def redact_text(text: str) -> str:
        return redact_str(text)
