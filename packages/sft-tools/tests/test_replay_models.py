"""Test 1-3: Pydantic models ReplayRecord, ReplayCMAPSSArgs, ReplayUCIArgs.

Verifica:
    - ReplayRecord frozen immutabile
    - Timestamp tz-aware obbligatorio (naive datetime solleva ValidationError)
    - ReplayCMAPSSArgs range unit_id 1..260
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

UTC = timezone.utc


class TestReplayRecord:
    """Test 1-2: ReplayRecord frozen + tz-aware timestamp."""

    def test_valid_replay_record_instantiation(self, sample_replay_record_dict: dict) -> None:
        """Test 1: ReplayRecord valido si istanzia correttamente."""
        from sft_tools.replay.models import ReplayRecord

        record = ReplayRecord(**sample_replay_record_dict)
        assert record.asset_id == "LOOM-01"
        assert record.sensor_id == "sensor_2"
        assert record.value == 1.23
        assert record.unit == "raw"
        assert record.source_dataset == "cmapss"
        assert record.source_unit == "FD001#unit1#cycle1"

    def test_replay_record_frozen_raises_on_mutation(self, sample_replay_record_dict: dict) -> None:
        """Test 1: ReplayRecord frozen — mutazione diretta (record.field = value) solleva ValidationError."""
        from sft_tools.replay.models import ReplayRecord

        record = ReplayRecord(**sample_replay_record_dict)
        # Pydantic frozen models sollevano ValidationError su assignment diretto
        with pytest.raises((ValidationError, TypeError)):
            record.asset_id = "LOOM-99"  # type: ignore[misc]

    def test_naive_timestamp_raises_validation_error(self, sample_replay_record_dict: dict) -> None:
        """Test 2: timestamp naive (senza tzinfo) solleva ValidationError."""
        from sft_tools.replay.models import ReplayRecord

        invalid_dict = dict(sample_replay_record_dict)
        invalid_dict["timestamp"] = datetime(2026, 5, 18)  # naive — no tzinfo
        with pytest.raises(ValidationError, match="timezone"):
            ReplayRecord(**invalid_dict)

    def test_extra_field_raises_validation_error(self, sample_replay_record_dict: dict) -> None:
        """ReplayRecord con extra='forbid' — campo extra solleva ValidationError."""
        from sft_tools.replay.models import ReplayRecord

        invalid_dict = dict(sample_replay_record_dict)
        invalid_dict["unexpected_field"] = "should_fail"
        with pytest.raises(ValidationError):
            ReplayRecord(**invalid_dict)


class TestReplayCMAPSSArgs:
    """Test 3: ReplayCMAPSSArgs range unit_id."""

    def test_unit_id_above_max_raises_validation_error(self) -> None:
        """Test 3: unit_id=261 solleva ValidationError (range 1..260)."""
        from sft_tools.replay.models import ReplayCMAPSSArgs

        with pytest.raises(ValidationError):
            ReplayCMAPSSArgs(unit_id=261)

    def test_unit_id_below_min_raises_validation_error(self) -> None:
        """unit_id=0 solleva ValidationError (range 1..260)."""
        from sft_tools.replay.models import ReplayCMAPSSArgs

        with pytest.raises(ValidationError):
            ReplayCMAPSSArgs(unit_id=0)

    def test_valid_unit_id_boundary_values(self) -> None:
        """unit_id=1 e unit_id=260 sono validi (boundary values)."""
        from sft_tools.replay.models import ReplayCMAPSSArgs

        args_min = ReplayCMAPSSArgs(unit_id=1)
        assert args_min.unit_id == 1

        args_max = ReplayCMAPSSArgs(unit_id=260)
        assert args_max.unit_id == 260

    def test_optional_target_asset_id_defaults_none(self) -> None:
        """target_asset_id è opzionale (OQ5 resolution) — default None."""
        from sft_tools.replay.models import ReplayCMAPSSArgs

        args = ReplayCMAPSSArgs(unit_id=1)
        assert args.target_asset_id is None

    def test_target_asset_id_can_be_set(self) -> None:
        """target_asset_id può essere impostato esplicitamente."""
        from sft_tools.replay.models import ReplayCMAPSSArgs

        args = ReplayCMAPSSArgs(unit_id=1, target_asset_id="LOOM-05")
        assert args.target_asset_id == "LOOM-05"
