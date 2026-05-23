"""Test dell'estensione FailureMode con hitl_tier + setup_minutes + severity_band.

Riferimenti:
    D-QI-03 (severity tiers)
    D-PP-01 (setup_minutes nelle decisioni di scheduling)
    Phase 2 textile defect taxonomy (7 difetti principali)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sft_domain.failure_modes import (
    FailureMode,
    invalidate_cache,
    load_failure_modes,
    load_failure_modes_dict,
)


TEXTILE_DEFECT_IDS = {
    "broken_end",
    "mispick",
    "slub",
    "neppy",
    "selvage_fault",
    "shade_deviation",
    "unlevel_dyeing",
}


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    invalidate_cache()
    yield
    invalidate_cache()


class TestFailureModeExtension:
    """L'estensione e' backward-compatible: i campi sono optional con default."""

    def _baseline_kwargs(self) -> dict:
        return dict(
            id="broken_end",
            name_it="rottura filo ordito",
            name_en="broken end",
            asset_families=["weaving"],
            parts=["warp"],
        )

    def test_default_hitl_tier_supervisor(self) -> None:
        fm = FailureMode(**self._baseline_kwargs())
        assert fm.hitl_tier == "supervisor"

    def test_default_setup_minutes_zero(self) -> None:
        fm = FailureMode(**self._baseline_kwargs())
        assert fm.setup_minutes == 0

    def test_default_severity_band_empty(self) -> None:
        fm = FailureMode(**self._baseline_kwargs())
        assert fm.severity_band == {}

    def test_hitl_tier_literal_enforced(self) -> None:
        kwargs = self._baseline_kwargs()
        kwargs["hitl_tier"] = "ceo"
        with pytest.raises(ValidationError):
            FailureMode(**kwargs)

    def test_hitl_tier_auto_log_accepted(self) -> None:
        kwargs = self._baseline_kwargs()
        kwargs["hitl_tier"] = "auto-log"
        fm = FailureMode(**kwargs)
        assert fm.hitl_tier == "auto-log"

    def test_hitl_tier_manager_safety_accepted(self) -> None:
        kwargs = self._baseline_kwargs()
        kwargs["hitl_tier"] = "manager+safety"
        fm = FailureMode(**kwargs)
        assert fm.hitl_tier == "manager+safety"

    def test_setup_minutes_non_negative(self) -> None:
        kwargs = self._baseline_kwargs()
        kwargs["setup_minutes"] = -1
        with pytest.raises(ValidationError):
            FailureMode(**kwargs)

    def test_severity_band_dict_accepted(self) -> None:
        kwargs = self._baseline_kwargs()
        kwargs["severity_band"] = {
            "minor": {"max_frequency_per_meter": 5},
            "critical": {"safety_risk": True},
        }
        fm = FailureMode(**kwargs)
        assert fm.severity_band["critical"]["safety_risk"] is True

    def test_still_frozen_after_extension(self) -> None:
        fm = FailureMode(**self._baseline_kwargs())
        with pytest.raises(ValidationError):
            fm.hitl_tier = "auto-log"  # type: ignore[misc]


class TestFailureModesYamlBackwardCompat:
    """Le entries esistenti continuano a caricare correttamente."""

    def test_load_succeeds(self) -> None:
        fms = load_failure_modes()
        assert len(fms) >= 30

    def test_existing_entries_still_valid(self) -> None:
        fms = load_failure_modes()
        for fm in fms:
            # backward-compat fields hold default or yaml-provided values
            assert fm.hitl_tier in {"auto-log", "supervisor", "manager+safety"}
            assert fm.setup_minutes >= 0


class TestSevenTextileDefectsCovered:
    """Tutti e 7 i difetti textile core devono essere presenti in YAML."""

    def test_all_seven_textile_defects_present(self) -> None:
        d = load_failure_modes_dict()
        missing = TEXTILE_DEFECT_IDS - set(d.keys())
        assert not missing, f"Missing textile defects in failure_modes.yaml: {missing}"

    def test_each_textile_defect_has_hitl_tier_mapping(self) -> None:
        d = load_failure_modes_dict()
        for defect_id in TEXTILE_DEFECT_IDS:
            fm = d[defect_id]
            assert fm.hitl_tier in {"auto-log", "supervisor", "manager+safety"}, (
                f"{defect_id} has invalid hitl_tier: {fm.hitl_tier}"
            )
