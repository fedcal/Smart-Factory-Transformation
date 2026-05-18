"""Test del server OPC-UA, emitter e CLI (IOT-01, IOT-02, Task 2).

Test:
    test_emitter_uses_tz_aware_now    — emitter usa datetime.now(UTC), mai naive
    test_main_dry_run_resolves_5_families — CLI --dry-run mostra 5 family names
    test_all_families_emit            — IOT-01 coverage con mock server
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEmitterTzAware:
    """Test: emitter usa datetime.now(UTC) — Pattern S-6 enforcement."""

    @pytest.mark.asyncio
    async def test_emitter_uses_tz_aware_now(self) -> None:
        """asset_emitter usa datetime.now(UTC) con kwarg UTC — non naive (Pattern S-6)."""
        from sft_assets import load_assets
        from sim_textile.models import EmitterState

        # Prendi un asset loom
        assets = [a for a in load_assets() if a.asset_family.value == "loom"]
        assert assets, "Nessun asset loom trovato in registry"
        asset = assets[0]

        from sim_textile.profile_loader import invalidate_cache, load_profile
        invalidate_cache()
        profile = load_profile("loom")

        now_calls: list[tuple] = []

        original_datetime = datetime

        class MockDatetime:
            @staticmethod
            def now(tz=None):
                now_calls.append((tz,))
                return original_datetime.now(tz)

        # Patch datetime nel modulo emitter
        vars_map: dict = {}
        for tag_ref in asset.tags:
            mock_node = AsyncMock()
            mock_node.write_value = AsyncMock()
            vars_map[(asset.asset_id, tag_ref.tag_id)] = mock_node

        with patch("sim_textile.emitter.datetime", MockDatetime):
            try:
                await asyncio.wait_for(
                    __import__(
                        "sim_textile.emitter", fromlist=["asset_emitter"]
                    ).asset_emitter(asset, profile, vars_map, time_scale=1000.0),
                    timeout=0.2,
                )
            except (asyncio.TimeoutError, Exception):
                pass  # Timeout atteso

        # Verifica che datetime.now sia sempre stato chiamato con UTC
        assert len(now_calls) > 0, "datetime.now non e' stato chiamato"
        for call_args in now_calls:
            assert call_args[0] is UTC, (
                f"datetime.now chiamato senza UTC: {call_args[0]!r} — Pattern S-6 violation"
            )


class TestCliDryRun:
    """Test: CLI --dry-run con 5 family names."""

    def test_main_dry_run_resolves_5_families(self) -> None:
        """CLI --dry-run con tutti i profili mostra 5 family names (Test smoke CLI)."""
        import pathlib
        worktree_root = pathlib.Path("/media/federicocalo/D1/prj/Smart Factory Transformation/.claude/worktrees/agent-ac9a517ea1a59bad4")
        cmd = [
            "uv", "run", "--project", "simulators/sim-textile",
            "sim-textile",
            "--dry-run",
            "--profile", "loom",
            "--profile", "spinning",
            "--profile", "warping",
            "--profile", "dyeing",
            "--profile", "finishing",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(worktree_root),
            timeout=30,
        )
        assert result.returncode == 0, (
            f"CLI --dry-run fallita con exit {result.returncode}:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        stdout = result.stdout
        assert "Resolved config: profiles=" in stdout, f"Output atteso mancante: {stdout!r}"
        # Verifica che tutti e 5 i nomi family siano presenti
        for family in ("loom", "spinning", "warping", "dyeing", "finishing"):
            assert family in stdout, f"Family {family!r} mancante nell'output: {stdout!r}"


class TestAllFamiliesEmit:
    """Test: IOT-01 — tutte 5 le family emettono eventi."""

    @pytest.mark.asyncio
    async def test_all_families_emit(self) -> None:
        """Tutte e 5 le family emettono almeno un evento (IOT-01 coverage)."""
        from sft_assets import load_assets
        from sim_textile.metrics import sim_events_emitted_total
        from sim_textile.profile_loader import invalidate_cache, load_all_profiles

        invalidate_cache()
        profiles = load_all_profiles()
        all_assets = load_assets()

        # Mock vars_map con nodi OPC-UA fittizi
        vars_map: dict = {}
        for asset in all_assets:
            for tag_ref in asset.tags:
                mock_node = AsyncMock()
                mock_node.write_value = AsyncMock()
                vars_map[(asset.asset_id, tag_ref.tag_id)] = mock_node

        # Avvia 1 emitter per family con time_scale alto per completare velocemente
        families = ["loom", "spinning", "warping", "dyeing", "finishing"]
        sample_assets = {}
        for family in families:
            family_assets = [a for a in all_assets if a.asset_family.value == family]
            if family_assets:
                sample_assets[family] = family_assets[0]

        tasks = []
        for family, asset in sample_assets.items():
            task = asyncio.create_task(
                __import__(
                    "sim_textile.emitter", fromlist=["asset_emitter"]
                ).asset_emitter(asset, profiles[family], vars_map, time_scale=1000.0)
            )
            tasks.append(task)

        # Attendi brevemente per permettere almeno un ciclo
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=0.3)
        except (asyncio.TimeoutError, Exception):
            pass

        # Cancella tasks rimasti
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verifica che ci siano entries per tutte e 5 le family nel counter
        # prometheus_client Counter._metrics e' un dict con tuple-chiavi (label_values)
        emitted_families: set[str] = set()
        for label_key in sim_events_emitted_total._metrics:
            # label_key e' una tupla di label values nell'ordine dei labelnames
            # labelnames = ["asset_family", "asset_id", "tag_id"]
            if isinstance(label_key, tuple) and len(label_key) >= 1:
                emitted_families.add(label_key[0])

        assert len(emitted_families) == 5, (
            f"Solo {len(emitted_families)} family hanno emesso: {sorted(emitted_families)}"
        )
        for family in families:
            assert family in emitted_families, (
                f"Family {family!r} non ha emesso eventi"
            )
