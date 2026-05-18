"""CLI entry point per sim-textile (Pattern S-4, D-50).

Argparse + env fallback + --dry-run (Pattern S-4: argparse + exit codes documentati).

Usage:
    uv run sim-textile [--profile FAMILY] [--time-scale FLOAT] [--metrics-port INT] [--dry-run]

Exit codes:
    0 - Success (o --dry-run completato)
    1 - Errore configurazione / runtime
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys


_ALL_FAMILIES = ["loom", "spinning", "warping", "dyeing", "finishing"]


def main() -> None:
    """Entry point CLI per sim-textile.

    Legge configurazione da argparse con fallback env (Pattern S-4):
    - --profile: SIM_PROFILES (csv, default tutti 5)
    - --time-scale: SIM_TIME_SCALE (float, default 1.0)
    - --metrics-port: METRICS_PORT (int, default 8080)
    - --dry-run: stampa config risolto + exit 0
    """
    parser = argparse.ArgumentParser(
        description="Textile factory simulator: emette stream sensore OPC-UA per 5 asset family (D-50).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--profile",
        action="append",
        metavar="FAMILY",
        dest="profiles",
        help=(
            "Family da abilitare (può essere ripetuto). "
            "Default: env SIM_PROFILES o tutti e 5."
        ),
    )
    parser.add_argument(
        "--time-scale",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Fattore accelerazione tempo (1.0 = realtime). Default: env SIM_TIME_SCALE o 1.0.",
    )
    parser.add_argument(
        "--metrics-port",
        type=int,
        default=None,
        metavar="INT",
        help="Porta Prometheus /metrics. Default: env METRICS_PORT o 8080.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stampa configurazione risolta ed esce (exit 0) senza avviare il simulatore.",
    )

    args = parser.parse_args()

    # Risolvi profiles: --profile > env SIM_PROFILES > tutti 5
    if args.profiles is not None:
        profiles = args.profiles
    else:
        env_profiles = os.environ.get("SIM_PROFILES", "")
        if env_profiles:
            profiles = [p.strip() for p in env_profiles.split(",") if p.strip()]
        else:
            profiles = list(_ALL_FAMILIES)

    # Risolvi time_scale: --time-scale > env SIM_TIME_SCALE > 1.0
    if args.time_scale is not None:
        time_scale = args.time_scale
    else:
        env_ts = os.environ.get("SIM_TIME_SCALE", "")
        try:
            time_scale = float(env_ts) if env_ts else 1.0
        except ValueError:
            print(f"ERROR: SIM_TIME_SCALE non valido: {env_ts!r}", file=sys.stderr)
            sys.exit(1)

    # Risolvi metrics_port: --metrics-port > env METRICS_PORT > 8080
    if args.metrics_port is not None:
        metrics_port = args.metrics_port
    else:
        env_mp = os.environ.get("METRICS_PORT", "")
        try:
            metrics_port = int(env_mp) if env_mp else 8080
        except ValueError:
            print(f"ERROR: METRICS_PORT non valido: {env_mp!r}", file=sys.stderr)
            sys.exit(1)

    if args.dry_run:
        print(
            f"Resolved config: profiles={profiles}, "
            f"time_scale={time_scale}, "
            f"metrics_port={metrics_port}"
        )
        sys.exit(0)

    # Avvia simulatore
    from sim_textile.main import run

    asyncio.run(run(profiles, time_scale, metrics_port))
