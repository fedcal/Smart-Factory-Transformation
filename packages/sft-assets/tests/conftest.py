"""Shared pytest fixtures per i test di sft-assets.

Fornisce:
    sample_asset_dict        — dict valido per Asset (LOOM-01 con 2 tag)
    sample_tag_dict          — dict valido per Tag (warp_tension)
    sample_registry_minimal  — lista YAML con 1 asset valido per loader test
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def sample_tag_dict() -> dict:
    """Restituisce un dizionario valido per un Tag (warp_tension)."""
    return {
        "tag_id": "warp_tension",
        "unit": "N",
        "sample_rate_hz": 10.0,
        "semantic_type": "tension",
    }


@pytest.fixture(scope="module")
def sample_asset_dict() -> dict:
    """Restituisce un dizionario valido per un Asset (LOOM-01 con 2 tag)."""
    return {
        "asset_id": "LOOM-01",
        "asset_family": "loom",
        "line_id": "weaving-line-1",
        "opcua_namespace": "urn:mantis:loom:LOOM-01",
        "tags": [
            {
                "tag_id": "warp_tension",
                "unit": "N",
                "sample_rate_hz": 10.0,
                "semantic_type": "tension",
            },
            {
                "tag_id": "pick_density",
                "unit": "picks_per_cm",
                "sample_rate_hz": 1.0,
                "semantic_type": "density",
            },
        ],
        "status": "active",
    }


@pytest.fixture(scope="module")
def sample_registry_minimal() -> list:
    """Restituisce una lista con 1 asset valido per loader test."""
    return [
        {
            "asset_id": "LOOM-01",
            "asset_family": "loom",
            "line_id": "weaving-line-1",
            "opcua_namespace": "urn:mantis:loom:LOOM-01",
            "tags": [
                {
                    "tag_id": "warp_tension",
                    "unit": "N",
                    "sample_rate_hz": 10.0,
                    "semantic_type": "tension",
                }
            ],
            "status": "active",
        }
    ]
