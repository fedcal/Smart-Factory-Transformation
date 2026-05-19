# Covers KNW-01 (collection bootstrap) + KNW-05 (provenance fields) per 05-VALIDATION.md
"""Wave 0 stub — implemented in Plan 05-04 (bootstrap) + 05-08 (indexer)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-04 + 05-08")


def test_collection_bootstrap_idempotent() -> None:
    """KNW-01: bootstrap script creates collection on first run, no-op on subsequent runs."""
    pass


def test_provenance_fields_complete() -> None:
    """KNW-05: every upserted point carries source_uri, version, lang, acl_level, retrieved_at."""
    pass
