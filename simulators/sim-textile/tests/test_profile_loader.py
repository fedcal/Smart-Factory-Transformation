"""Test del profile loader YAML con caching LRU (Test 8-9).

Verifica: load_profile, load_all_profiles, cache behavior, error handling.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest
import yaml
from pydantic import ValidationError

from sft_assets._models import AssetFamily
from sim_textile.profile_loader import invalidate_cache, load_all_profiles, load_profile


class TestLoadProfile:
    """Test 8: load_profile carica correttamente il profilo loom."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_load_loom_returns_fault_profile(self) -> None:
        """load_profile("loom") ritorna FaultProfile con asset_family==LOOM (Test 8)."""
        profile = load_profile("loom")
        assert profile.asset_family == AssetFamily.LOOM

    def test_load_loom_jitter_enabled(self) -> None:
        """loom profile ha jitter.enabled==True (Test 8)."""
        profile = load_profile("loom")
        assert profile.fault_injection.jitter.enabled is True

    def test_load_loom_sample_rate(self) -> None:
        """loom profile ha sample_rate_hz=10."""
        profile = load_profile("loom")
        assert profile.sample_rate_hz == pytest.approx(10.0)

    def test_load_loom_has_baseline(self) -> None:
        """loom profile ha default_baseline con warp_tension."""
        profile = load_profile("loom")
        assert "warp_tension" in profile.default_baseline

    def test_load_spinning(self) -> None:
        """load_profile("spinning") ritorna FaultProfile con asset_family==SPINNING."""
        profile = load_profile("spinning")
        assert profile.asset_family == AssetFamily.SPINNING

    def test_missing_profile_raises_file_not_found(self, tmp_path: pathlib.Path) -> None:
        """Profilo inesistente solleva FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Profile non trovato"):
            # Patch temporaneo del _PROFILES_DIR per forzare errore
            import sim_textile.profile_loader as pl
            original = pl._PROFILES_DIR
            pl._PROFILES_DIR = tmp_path
            invalidate_cache()
            try:
                load_profile("loom")
            finally:
                pl._PROFILES_DIR = original
                invalidate_cache()


class TestLoadAllProfiles:
    """Test 9: load_all_profiles ritorna dict con 5 chiavi."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_load_all_returns_five_keys(self) -> None:
        """load_all_profiles() ritorna dict con 5 chiavi (Test 9)."""
        profiles = load_all_profiles()
        assert set(profiles.keys()) == {"loom", "spinning", "warping", "dyeing", "finishing"}

    def test_load_all_profiles_are_valid(self) -> None:
        """Tutti i profili caricati sono istanze di FaultProfile."""
        from sim_textile.models import FaultProfile

        profiles = load_all_profiles()
        for name, profile in profiles.items():
            assert isinstance(profile, FaultProfile), f"Profile {name} non e' FaultProfile"

    def test_load_all_profiles_correct_families(self) -> None:
        """Ogni profilo ha l'asset_family corrispondente al nome chiave."""
        profiles = load_all_profiles()
        for name, profile in profiles.items():
            assert profile.asset_family.value == name, (
                f"Profile {name} ha asset_family={profile.asset_family.value}"
            )


class TestProfileLoaderCache:
    """Test cache LRU del loader."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_cache_returns_same_object(self) -> None:
        """Chiamate successive ritornano lo stesso oggetto (cache hit)."""
        p1 = load_profile("loom")
        p2 = load_profile("loom")
        assert p1 is p2

    def test_invalidate_cache_clears_hits(self) -> None:
        """invalidate_cache() svuota la cache LRU."""
        load_profile("loom")
        info_before = load_profile.cache_info()
        assert info_before.currsize >= 1
        invalidate_cache()
        info_after = load_profile.cache_info()
        assert info_after.currsize == 0
