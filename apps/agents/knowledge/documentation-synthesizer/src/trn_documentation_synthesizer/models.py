"""SOPDraft model for DocumentationSynthesizer (D-DS-01/02/03, TRN-04/05).

SOPDraft is the primary output model: a frozen bilingual SOP with Italian primary
text, English translation, citation anchors, and provenance metadata.

Fixed section keys (D-DS-01):
    Scopo, Prerequisiti, Passi, Sicurezza, Riferimenti

Citation anchor format (Pitfall §1):
    [SRC:N] markers embedded in section text; anchor_map maps them to source_uri.

TRN-05 provenance:
    Every citation in the citations list must have source_uri + timestamp.
    SOPCitationValidator enforces this post-translation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sft_agents.models.evidence import RagCitation

# ---------------------------------------------------------------------------
# Fixed section keys (D-DS-01)
# ---------------------------------------------------------------------------

SECTION_KEYS_IT: tuple[str, ...] = (
    "Scopo",
    "Prerequisiti",
    "Passi",
    "Sicurezza",
    "Riferimenti",
)

# Canonical mapping from IT section keys to EN equivalents (D-DS-01)
SECTION_KEY_MAP_IT_TO_EN: dict[str, str] = {
    "Scopo": "Purpose",
    "Prerequisiti": "Prerequisites",
    "Passi": "Steps",
    "Sicurezza": "Safety",
    "Riferimenti": "References",
}


# ---------------------------------------------------------------------------
# SOPDraft — frozen bilingual SOP (D-DS-01/02/03)
# ---------------------------------------------------------------------------


class SOPDraft(BaseModel):
    """Fixed-section SOP with IT primary + EN translation (D-DS-01/02/03).

    Frozen to prevent post-generation mutation (Shared Pattern D).
    All 5 SECTION_KEYS_IT must be present in both sections_it and sections_en;
    a missing section raises ValueError at construction time.

    Citation provenance (TRN-05):
        citations: every citation must have source_uri + retrieved_at.
        anchor_map: maps "[SRC:N]" to source_uri; used by SOPCitationValidator.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sop_id: str = Field(min_length=1, description="Unique SOP identifier (UUID or slug)")
    failure_mode: str = Field(min_length=1, description="Failure mode driving this SOP")
    asset_id: str = Field(min_length=1, description="Target asset identifier")
    title_it: str = Field(min_length=1, description="SOP title in Italian")
    title_en: str = Field(min_length=1, description="SOP title in English")
    lang_primary: Literal["it"] = Field(
        default="it",
        description="Primary language is always Italian (D-DS-01)",
    )
    sections_it: dict[str, str] = Field(
        description="IT section content; keys must include all SECTION_KEYS_IT with [SRC:N] anchors",
    )
    sections_en: dict[str, str] = Field(
        description="EN translated section content; anchor markers must be preserved",
    )
    citations: list[RagCitation] = Field(
        description="RAG citations; each must have source_uri + retrieved_at (TRN-05)",
    )
    anchor_map: dict[str, str] = Field(
        description='Mapping of "[SRC:N]" -> source_uri (Pitfall §1 mitigation)',
    )
    generated_at: datetime = Field(description="UTC-aware generation timestamp")
    approved: bool = Field(default=False, description="True after supervisor HITL approval")

    @field_validator("sections_it", "sections_en")
    @classmethod
    def _check_sections(cls, v: dict[str, str]) -> dict[str, str]:
        """Require all 5 fixed section keys (D-DS-01)."""
        missing = [k for k in SECTION_KEYS_IT if k not in v]
        if missing:
            raise ValueError(
                f"Missing required SOP sections: {missing}. "
                f"All 5 sections required: {list(SECTION_KEYS_IT)}"
            )
        return v


__all__ = [
    "SECTION_KEYS_IT",
    "SECTION_KEY_MAP_IT_TO_EN",
    "SOPDraft",
]
