# Covers KNW-06 SC#2 (ACL operator gate) per 05-VALIDATION.md
"""Wave 0 stub — implemented in Plan 05-09 (retrieval ACL filter)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-09")


def test_operator_cannot_see_restricted() -> None:
    """KNW-06 SC#2: retrieval filtered by user role excludes acl_level=restricted for operators."""
    pass
