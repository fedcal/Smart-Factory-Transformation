"""Test della MaintenanceSpec extension (Plan 07-02, D-MNT-TAX, MNT-05).

Riferimenti:
    .planning/phases/07-agents-maintenance-reliability/07-CONTEXT.md (D-MNT-TAX)
    .planning/phases/07-agents-maintenance-reliability/07-PATTERNS.md (Section 16-17)
    Phase 6 analog: tests/test_failure_modes_hitl_tier.py

Schema invariants:
    - MaintenanceSpec frozen + extra=forbid
    - reason_code regex ^[A-Z][A-Z0-9-]+$
    - mttr_target_minutes in [0, 10080] (1 week)
    - intervention_steps_sop_id regex ^SOP-[A-Z0-9-]+$
    - preventive_check_interval_hours optional, >=1 quando presente
    - FailureMode.maintenance optional (default None, backward-compat)
    - YAML round-trip: 7 textile defects con maintenance populated
    - reason_code uniqueness across all entries
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
from sft_domain.failure_modes.models import MaintenanceSpec


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


# ---------------------------------------------------------------------------
# MaintenanceSpec — schema invariants
# ---------------------------------------------------------------------------


class TestMaintenanceSpecBasics:
    """Invariants strutturali del modello MaintenanceSpec."""

    def test_instantiable_with_valid_fields(self) -> None:
        spec = MaintenanceSpec(
            reason_code="WEAVING-BE-001",
            mttr_target_minutes=30,
            intervention_steps_sop_id="SOP-LOOM-001",
            preventive_check_interval_hours=168,
        )
        assert spec.reason_code == "WEAVING-BE-001"
        assert spec.mttr_target_minutes == 30
        assert spec.intervention_steps_sop_id == "SOP-LOOM-001"
        assert spec.preventive_check_interval_hours == 168

    def test_preventive_check_interval_optional_default_none(self) -> None:
        spec = MaintenanceSpec(
            reason_code="WEAVING-BE-001",
            mttr_target_minutes=30,
            intervention_steps_sop_id="SOP-LOOM-001",
        )
        assert spec.preventive_check_interval_hours is None

    def test_frozen_mutation_raises(self) -> None:
        spec = MaintenanceSpec(
            reason_code="WEAVING-BE-001",
            mttr_target_minutes=30,
            intervention_steps_sop_id="SOP-LOOM-001",
        )
        with pytest.raises(ValidationError):
            spec.reason_code = "OTHER"  # type: ignore[misc]

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(
                reason_code="WEAVING-BE-001",
                mttr_target_minutes=30,
                intervention_steps_sop_id="SOP-LOOM-001",
                unknown_extra_field="boom",  # type: ignore[call-arg]
            )


class TestMaintenanceSpecReasonCodeRegex:
    """reason_code DEVE rispettare ^[A-Z][A-Z0-9-]+$."""

    def _kwargs(self, code: str) -> dict:
        return dict(
            reason_code=code,
            mttr_target_minutes=10,
            intervention_steps_sop_id="SOP-LOOM-001",
        )

    def test_valid_uppercase_alpha_numeric_hyphen(self) -> None:
        spec = MaintenanceSpec(**self._kwargs("WEAVING-BE-001"))
        assert spec.reason_code == "WEAVING-BE-001"

    def test_valid_min_two_chars(self) -> None:
        # ^[A-Z][A-Z0-9-]+$ requires at least 2 chars (first letter + 1+ continuation)
        spec = MaintenanceSpec(**self._kwargs("XX"))
        assert spec.reason_code == "XX"

    def test_invalid_single_char(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs("X"))

    def test_invalid_lowercase(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs("weaving-be-001"))

    def test_invalid_empty_string(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs(""))

    def test_invalid_leading_digit(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs("123-FOO"))

    def test_invalid_underscore(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs("WEAVING_BE_001"))


class TestMaintenanceSpecMttrBounds:
    """mttr_target_minutes DEVE essere in [0, 10080]."""

    def _kwargs(self, mttr: int) -> dict:
        return dict(
            reason_code="WEAVING-BE-001",
            mttr_target_minutes=mttr,
            intervention_steps_sop_id="SOP-LOOM-001",
        )

    def test_zero_valid(self) -> None:
        spec = MaintenanceSpec(**self._kwargs(0))
        assert spec.mttr_target_minutes == 0

    def test_max_valid(self) -> None:
        spec = MaintenanceSpec(**self._kwargs(10080))
        assert spec.mttr_target_minutes == 10080

    def test_negative_invalid(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs(-1))

    def test_above_max_invalid(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs(10081))


class TestMaintenanceSpecSopIdRegex:
    """intervention_steps_sop_id DEVE rispettare ^SOP-[A-Z0-9-]+$."""

    def _kwargs(self, sop: str) -> dict:
        return dict(
            reason_code="WEAVING-BE-001",
            mttr_target_minutes=15,
            intervention_steps_sop_id=sop,
        )

    def test_valid_sop_loom_001(self) -> None:
        spec = MaintenanceSpec(**self._kwargs("SOP-LOOM-001"))
        assert spec.intervention_steps_sop_id == "SOP-LOOM-001"

    def test_valid_sop_dye_001(self) -> None:
        spec = MaintenanceSpec(**self._kwargs("SOP-DYE-001"))
        assert spec.intervention_steps_sop_id == "SOP-DYE-001"

    def test_invalid_no_prefix(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs("LOOM-001"))

    def test_invalid_too_short(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs("SOP-"))

    def test_invalid_lowercase_prefix(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs("sop-LOOM-001"))


class TestMaintenanceSpecPreventiveCheck:
    """preventive_check_interval_hours optional + >=1."""

    def _kwargs(self, hours: int | None) -> dict:
        return dict(
            reason_code="WEAVING-BE-001",
            mttr_target_minutes=15,
            intervention_steps_sop_id="SOP-LOOM-001",
            preventive_check_interval_hours=hours,
        )

    def test_one_hour_valid(self) -> None:
        spec = MaintenanceSpec(**self._kwargs(1))
        assert spec.preventive_check_interval_hours == 1

    def test_ten_years_valid(self) -> None:
        spec = MaintenanceSpec(**self._kwargs(24 * 365 * 10))
        assert spec.preventive_check_interval_hours == 24 * 365 * 10

    def test_zero_invalid(self) -> None:
        with pytest.raises(ValidationError):
            MaintenanceSpec(**self._kwargs(0))

    def test_none_explicit_valid(self) -> None:
        spec = MaintenanceSpec(**self._kwargs(None))
        assert spec.preventive_check_interval_hours is None


# ---------------------------------------------------------------------------
# FailureMode.maintenance — optional field, backward-compat
# ---------------------------------------------------------------------------


class TestFailureModeMaintenanceField:
    """FailureMode acquires an optional `maintenance` field (additive)."""

    def _baseline_kwargs(self) -> dict:
        return dict(
            id="broken_end",
            name_it="rottura filo ordito",
            name_en="broken end",
            asset_families=["weaving"],
            parts=["warp"],
        )

    def test_default_maintenance_none(self) -> None:
        fm = FailureMode(**self._baseline_kwargs())
        assert fm.maintenance is None

    def test_maintenance_can_be_assigned(self) -> None:
        spec = MaintenanceSpec(
            reason_code="WEAVING-BE-001",
            mttr_target_minutes=30,
            intervention_steps_sop_id="SOP-LOOM-001",
        )
        kwargs = self._baseline_kwargs()
        kwargs["maintenance"] = spec
        fm = FailureMode(**kwargs)
        assert fm.maintenance is not None
        assert fm.maintenance.reason_code == "WEAVING-BE-001"

    def test_maintenance_explicit_none_accepted(self) -> None:
        kwargs = self._baseline_kwargs()
        kwargs["maintenance"] = None
        fm = FailureMode(**kwargs)
        assert fm.maintenance is None

    def test_failure_mode_still_frozen(self) -> None:
        fm = FailureMode(**self._baseline_kwargs())
        with pytest.raises(ValidationError):
            fm.maintenance = MaintenanceSpec(  # type: ignore[misc]
                reason_code="X1",
                mttr_target_minutes=10,
                intervention_steps_sop_id="SOP-X-1",
            )


# ---------------------------------------------------------------------------
# YAML round-trip — loader integration
# ---------------------------------------------------------------------------


class TestFailureModesYamlMaintenanceRoundTrip:
    """failure_modes.yaml extension: 7 textile defects have maintenance subkey."""

    def test_loader_succeeds_after_extension(self) -> None:
        fms = load_failure_modes()
        assert len(fms) >= 30, "backward-compat: existing entries continue to load"

    def test_all_seven_textile_defects_have_maintenance(self) -> None:
        d = load_failure_modes_dict()
        missing = TEXTILE_DEFECT_IDS - set(d.keys())
        assert not missing, f"Missing textile defects in YAML: {missing}"
        for defect_id in TEXTILE_DEFECT_IDS:
            fm = d[defect_id]
            assert fm.maintenance is not None, (
                f"{defect_id} missing required 'maintenance' subkey"
            )
            assert fm.maintenance.reason_code, (
                f"{defect_id}.maintenance.reason_code must be non-empty"
            )
            assert fm.maintenance.mttr_target_minutes >= 0, (
                f"{defect_id}.maintenance.mttr_target_minutes invalid"
            )
            assert fm.maintenance.intervention_steps_sop_id.startswith("SOP-"), (
                f"{defect_id}.maintenance.intervention_steps_sop_id invalid"
            )

    def test_non_textile_entries_load_with_maintenance_none(self) -> None:
        """Backward-compat: entries WITHOUT maintenance subkey → maintenance=None."""
        d = load_failure_modes_dict()
        # rottura_filo is a non-textile-defect entry without maintenance subkey
        assert "rottura_filo" in d
        assert d["rottura_filo"].maintenance is None

    def test_reason_codes_unique_across_all_entries(self) -> None:
        fms = load_failure_modes()
        codes = [
            fm.maintenance.reason_code
            for fm in fms
            if fm.maintenance is not None
        ]
        assert codes, "expected at least one entry with maintenance metadata"
        assert len(codes) == len(set(codes)), (
            f"duplicate reason_codes found: "
            f"{[c for c in codes if codes.count(c) > 1]}"
        )

    def test_sop_ids_well_formed(self) -> None:
        fms = load_failure_modes()
        for fm in fms:
            if fm.maintenance is None:
                continue
            sop = fm.maintenance.intervention_steps_sop_id
            assert sop.startswith("SOP-"), f"{fm.id}: bad SOP id {sop!r}"
