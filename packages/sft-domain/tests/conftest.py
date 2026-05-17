"""Shared pytest fixtures per i test di sft-domain.

Fornisce:
    sample_term_dict        — dict valido per Term (textile-kpi)
    sample_sop_frontmatter  — dict valido per SOP frontmatter (SOP-LOOM-001 da D-26)
    sample_assumption_dict  — dict valido per Assumption register entry (A-001 da D-33)
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def sample_term_dict() -> dict:
    """Restituisce un dizionario valido per un Term del glossario (textile-kpi)."""
    return {
        "term": "pick density",
        "definition": "Number of weft picks per centimeter of fabric, determining fabric density and weight.",
        "category": "textile-kpi",
        "related_terms": ["warp_tension", "weft_yarn"],
        "examples": [
            "Pick density of 22-28 picks/cm is typical for cotton shirting fabrics."
        ],
        "source": "industry-standard",
    }


@pytest.fixture(scope="module")
def sample_sop_frontmatter() -> dict:
    """Restituisce un dizionario valido per il frontmatter SOP (SOP-LOOM-001 da D-26)."""
    return {
        "id": "SOP-LOOM-001",
        "title": "Sostituzione rapida del subbio di ordito",
        "version": "1.0",
        "lang": "it",
        "asset": "loom",
        "asset_family": "weaving",
        "role": "technician",
        "hazard_level": "medium",
        "estimated_duration_min": 45,
        "prerequisites": ["SOP-LOOM-000"],
        "related_glossary": ["warp_beam", "heddle_frame", "pick_density"],
        "tags": ["maintenance", "mechanical", "weaving"],
        "audience": "operations",
        "status": "reviewed",
        "created_in_phase": 2,
    }


@pytest.fixture(scope="module")
def sample_assumption_dict() -> dict:
    """Restituisce un dizionario valido per una Assumption register entry (A-001 da D-33)."""
    return {
        "id": "A-001",
        "statement": "TimescaleDB hypertables ingest sensor events with p99 latency < 200ms at 5,000 msg/s",
        "category": "data-quality",
        "affected_components": ["timescaledb", "ot-bridge", "anomaly-detector"],
        "rationale": (
            "Phase 3 success criterion #3 requires this; "
            "based on Timescale benchmarks 2.18.x with chunk_interval=1day"
        ),
        "validation_method": (
            "Phase 3 integration test: 5min load injection at 5k msg/s, "
            "measure pg_stat_io tail latency"
        ),
        "risk_if_wrong": (
            "AnomalyDetector and PredictiveMaintenance produce stale insights; "
            "HITL queue floods"
        ),
        "status": "active",
        "created_in_phase": 2,
        "last_reviewed_in_phase": 2,
        "superseded_by": None,
    }
