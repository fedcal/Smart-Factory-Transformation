"""Post-translation validators for DocumentationSynthesizer (TRN-05, D-DS-01, Pitfall §1).

Validation contract
-------------------
SOPCitationValidator.validate(sop_draft) performs:

    1. **Citation provenance check (TRN-05):** raises ValidationError if any citation
       in sop_draft.citations is missing source_uri or retrieved_at (timestamp).
       Empty citations list is also rejected (uncited output is opaque output).

    2. **Anchor parity check (D-DS-01, Pitfall §1):** raises MissingAnchorError if
       any [SRC:N] anchor found in sections_it text is absent from sections_en text.
       Fail-fast: raises on the first missing anchor.

    3. **Anchor map coverage (CitationDriftError):** raises if an anchor found in
       sections_it has no entry in anchor_map. This prevents citation drift where
       the translation produces an anchor that cannot be traced back to a source.

Mirroring RCAChainValidator structure (same exception pattern, same fail-fast ordering).

SQL parameterization:
    No SQL in this module — pure in-memory validation.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trn_documentation_synthesizer.models import SOPDraft

# Regex to extract [SRC:N] anchors from text
_ANCHOR_RE = re.compile(r"\[SRC:\d+\]")


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class MissingAnchorError(Exception):
    """Raised when an [SRC:N] anchor from IT text is missing in EN text (Pitfall §1).

    This indicates the translation pass dropped a citation anchor, making
    the EN SOP non-traceable to its source document. TRN-04 enforcement.

    Attributes:
        anchor_id: The specific "[SRC:N]" marker that is absent from EN text.
    """

    def __init__(self, *, anchor_id: str) -> None:
        self.anchor_id = anchor_id
        super().__init__(
            f"Citation anchor {anchor_id!r} is present in IT SOP text but missing "
            f"from EN translation. Citation drift detected (Pitfall §1 violation). "
            f"The translation must preserve all [SRC:N] markers in place."
        )


class CitationDriftError(Exception):
    """Raised when anchor_map has no entry for an anchor found in IT text.

    This indicates the SOP builder produced an [SRC:N] anchor without a
    corresponding anchor_map entry — the anchor cannot be resolved to a source_uri.
    This is a Pitfall §1 violation in the IT generation phase.

    Attributes:
        anchor_id: The specific "[SRC:N]" marker that has no anchor_map entry.
    """

    def __init__(self, *, anchor_id: str) -> None:
        self.anchor_id = anchor_id
        super().__init__(
            f"Citation anchor {anchor_id!r} found in IT SOP text but has no entry "
            f"in anchor_map. The SOP builder must add every [SRC:N] anchor to the "
            f"anchor_map with its source_uri (Pitfall §1 mitigation)."
        )


class ValidationError(Exception):
    """Raised when TRN-05 citation provenance check fails.

    This indicates the SOP draft has citations missing source_uri or timestamp,
    or has an empty citations list (uncited output is opaque and rejected).

    Attributes:
        reason: Human-readable explanation of the validation failure.
    """

    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(
            f"SOP citation provenance validation failed (TRN-05): {reason}"
        )


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class SOPCitationValidator:
    """Post-translation validator for DocumentationSynthesizer output.

    Enforces:
        - TRN-05: every citation has non-empty source_uri + non-null retrieved_at
        - D-DS-01 + Pitfall §1: all [SRC:N] anchors from IT text survive in EN text
        - Anchor map coverage: every IT anchor has an anchor_map entry

    Usage::

        validator = SOPCitationValidator()
        validated = validator.validate(sop_draft)
        # raises ValidationError, MissingAnchorError, or CitationDriftError on failure

    Fail-fast: raises on the first violation found in each check category.
    """

    def validate(self, sop_draft: "SOPDraft", anchor_map: dict[str, str] | None = None) -> "SOPDraft":
        """Validate citation provenance and anchor parity.

        Performs checks in order:
            1. Empty citations list → ValidationError
            2. Missing source_uri on any citation → ValidationError
            3. Missing retrieved_at on any citation → ValidationError
            4. Anchor drift: IT anchor missing from EN → MissingAnchorError
            5. Anchor map drift: IT anchor not in anchor_map → CitationDriftError

        The anchor_map parameter takes priority over sop_draft.anchor_map when
        provided; otherwise falls back to sop_draft.anchor_map.

        Args:
            sop_draft:  The SOPDraft to validate.
            anchor_map: Optional explicit anchor_map override. When None, uses
                        sop_draft.anchor_map.

        Returns:
            The same sop_draft unchanged when all checks pass.

        Raises:
            ValidationError:    TRN-05 citation provenance failure.
            MissingAnchorError: IT anchor absent from EN (Pitfall §1).
            CitationDriftError: IT anchor has no anchor_map entry.
        """
        effective_anchor_map = anchor_map if anchor_map is not None else sop_draft.anchor_map

        # --- Check 1: empty citations list (TRN-05) ---
        if not sop_draft.citations:
            raise ValidationError(
                reason=(
                    "citations list is empty — uncited SOP output is opaque and rejected. "
                    "Every SOP draft must include at least one RAG citation with source_uri + timestamp."
                )
            )

        # --- Check 2+3: source_uri + retrieved_at on every citation (TRN-05) ---
        for idx, citation in enumerate(sop_draft.citations):
            if not citation.source_uri:
                raise ValidationError(
                    reason=(
                        f"citation[{idx}] has missing or empty source_uri. "
                        f"All citations must carry a non-empty source_uri (TRN-05)."
                    )
                )
            if citation.retrieved_at is None:
                raise ValidationError(
                    reason=(
                        f"citation[{idx}] has null retrieved_at (timestamp). "
                        f"All citations must carry a UTC-aware timestamp (TRN-05)."
                    )
                )

        # --- Check 4: anchor parity — IT anchors must survive in EN (Pitfall §1) ---
        it_text = " ".join(sop_draft.sections_it.values())
        en_text = " ".join(sop_draft.sections_en.values())

        it_anchors = set(_ANCHOR_RE.findall(it_text))
        en_anchors = set(_ANCHOR_RE.findall(en_text))

        for anchor in sorted(it_anchors):  # sorted for deterministic error messages
            if anchor not in en_anchors:
                raise MissingAnchorError(anchor_id=anchor)

        # --- Check 5: anchor map coverage — every IT anchor must have a map entry ---
        for anchor in sorted(it_anchors):
            if anchor not in effective_anchor_map:
                raise CitationDriftError(anchor_id=anchor)

        return sop_draft


__all__ = [
    "CitationDriftError",
    "MissingAnchorError",
    "SOPCitationValidator",
    "ValidationError",
]
