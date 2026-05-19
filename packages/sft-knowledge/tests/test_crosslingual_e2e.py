# Covers SC#1 (cross-lingual retrieval IT↔EN) per 05-VALIDATION.md
"""Wave 0 stub — implemented in Plan 05-09 (retrieval + bge-m3 multilingual)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-09")


def test_it_query_returns_en_sop() -> None:
    """SC#1: an Italian query matches the same SOP in English when only EN version exists."""
    pass
