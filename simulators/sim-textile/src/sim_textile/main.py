"""Entry point asyncio per sim-textile (D-50, IOT-01).

Singolo processo asyncio che coordina:
- Server OPC-UA multi-namespace (server.py)
- Per-asset emitter tasks (emitter.py)
- Prometheus metrics endpoint (metrics.py)
- Profile loader (profile_loader.py)

RESEARCH §Pattern 1 lines 460-465: asyncio.gather per tutti i task.
"""

from __future__ import annotations

import asyncio

import structlog

from sft_assets import load_assets

from sim_textile.emitter import asset_emitter
from sim_textile.metrics import start_metrics
from sim_textile.profile_loader import load_all_profiles
from sim_textile.server import setup_server

logger = structlog.get_logger("sim-textile")


async def run(
    profiles_enabled: list[str],
    time_scale: float = 1.0,
    metrics_port: int = 8080,
) -> None:
    """Avvia il simulatore completo.

    Coordina: metrics endpoint + OPC-UA server + emitter tasks per ogni asset.

    Args:
        profiles_enabled: Lista nomi family abilitati (es. ["loom", "spinning"]).
        time_scale: Fattore accelerazione tempo (1.0 = realtime, >1.0 = accelerato).
        metrics_port: Porta HTTP per Prometheus /metrics.
    """
    logger.info(
        "sim_textile_starting",
        profiles_enabled=profiles_enabled,
        time_scale=time_scale,
        metrics_port=metrics_port,
    )

    # Avvia Prometheus metrics endpoint
    start_metrics(metrics_port)
    logger.info("metrics_started", port=metrics_port)

    # Setup OPC-UA server
    server, vars_map = await setup_server()
    logger.info("opcua_server_created")

    # Carica profiles e filtra per quelli abilitati
    profile_dict = load_all_profiles()
    profile_dict_enabled = {
        f: profile_dict[f] for f in profiles_enabled if f in profile_dict
    }

    if not profile_dict_enabled:
        logger.warning("no_profiles_enabled", profiles_enabled=profiles_enabled)

    # Filtra assets per family abilitata
    assets = [
        a for a in load_assets() if a.asset_family.value in profile_dict_enabled
    ]

    logger.info(
        "assets_loaded",
        count=len(assets),
        families=list(profile_dict_enabled.keys()),
    )

    # Avvia server + emitter tasks (RESEARCH §Pattern 1 lines 460-465)
    async with server:
        tasks = [
            asyncio.create_task(
                asset_emitter(
                    a,
                    profile_dict_enabled[a.asset_family.value],
                    vars_map,
                    time_scale=time_scale,
                )
            )
            for a in assets
        ]
        await asyncio.gather(*tasks)
