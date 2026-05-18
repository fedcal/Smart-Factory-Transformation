"""ReplayCMAPSSTool — NASA C-MAPSS turbofan run-to-failure replay loader.

LangChain BaseTool (langchain-core 1.x, Pydantic v2 native).
Async-first: _arun e' il metodo primario; _run solleva NotImplementedError.

CRITICAL: SOLO import da `pydantic` v2 native (Pitfall 5 — compat shim vietato).
CRITICAL: NESSUN f-string SQL o string interpolation SQL (T-03-02-sql, Security check 1).

Decisioni implementate:
    D-46 (ReplayRecord schema unificato: 7 colonne canoniche)
    D-47 (sft-tools location)
    OQ5 (target_asset_id optional + deterministic hash unit_id → asset_id)
    IOT-07 (replay_cmapss esposto come LangChain Tool)
"""

from __future__ import annotations

import hashlib
import pathlib
from datetime import datetime, timedelta, timezone
from typing import Literal

import pandas as pd
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from sft_tools.replay.models import ReplayCMAPSSArgs

UTC = timezone.utc

# Path workspace root per trovare i dataset
_WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent.parent.parent.parent.parent

# Colonne C-MAPSS (26 colonne: unit_id, cycle, 3 op_settings, 21 sensors)
_CMAPSS_COLUMNS = (
    ["unit_id", "cycle", "op_setting_1", "op_setting_2", "op_setting_3"]
    + [f"sensor_{i}" for i in range(1, 22)]
)

# Lista deterministica fallback di asset IDs (usata se sft-assets non disponibile)
_FALLBACK_ASSET_LIST = [
    "LOOM-01", "LOOM-02", "LOOM-03", "LOOM-04", "LOOM-05",
    "LOOM-06", "LOOM-07", "LOOM-08", "LOOM-09", "LOOM-10",
    "LOOM-11", "LOOM-12", "SPIN-01", "SPIN-02", "SPIN-03",
    "SPIN-04", "SPIN-05", "SPIN-06", "SPIN-07", "SPIN-08",
    "WARP-01", "WARP-02", "WARP-03", "WARP-04",
    "DYE-01", "DYE-02", "DYE-03", "DYE-04",
    "STEN-01", "STEN-02",
]


def _get_cmapss_path(dataset: str = "FD001") -> pathlib.Path:
    """Risolve il path al file CSV C-MAPSS.

    Priorita':
    1. simulators/sim-textile/replay-data/train_<dataset>.txt (prod path)
    2. packages/sft-tools/tests/fixtures/cmapss_fd001_sample.txt (dev/test fallback)

    Args:
        dataset: Sub-dataset C-MAPSS (es. "FD001").

    Returns:
        pathlib.Path al file dataset.

    Raises:
        FileNotFoundError: Se nessun path e' disponibile.
    """
    prod_path = _WORKSPACE_ROOT / "simulators" / "sim-textile" / "replay-data" / f"train_{dataset}.txt"
    if prod_path.exists():
        return prod_path

    # Fallback path per dev/test (fixtures)
    fixture_path = (
        pathlib.Path(__file__).parent.parent.parent.parent
        / "tests" / "fixtures" / "cmapss_fd001_sample.txt"
    )
    if fixture_path.exists():
        return fixture_path

    raise FileNotFoundError(
        f"C-MAPSS dataset '{dataset}' non trovato. "
        f"Prova: python3 scripts/download-replay-datasets.py --dataset cmapss-fd001. "
        f"Path cercati: {prod_path}, {fixture_path}"
    )


def _load_asset_list() -> list[str]:
    """Carica la lista di asset IDs da sft-assets registry, con fallback.

    Prova a importare sft_assets; se non disponibile (sft-assets non ancora
    nel workspace), usa la lista fallback deterministica.

    Returns:
        Lista di asset_id strings.
    """
    try:
        from sft_assets import load_assets  # type: ignore[import-untyped]
        assets = load_assets()
        return [a.asset_id for a in assets]
    except ImportError:
        # sft-assets non ancora installato (parallel Wave 1 build)
        return list(_FALLBACK_ASSET_LIST)


def _deterministic_asset_for_unit(unit_id: int) -> str:
    """Mappa deterministicamente unit_id → asset_id via hash SHA256.

    Il mapping e' stabile: stesso unit_id → stesso asset_id, sempre.
    Usa SHA256 per distribuzione uniforme sulla lista asset.

    Args:
        unit_id: C-MAPSS engine unit identifier.

    Returns:
        asset_id stringa (es. "LOOM-03").
    """
    asset_list = _load_asset_list()
    # SHA256 del unit_id per distribuzione uniforme deterministica
    hash_bytes = hashlib.sha256(str(unit_id).encode()).digest()
    index = int.from_bytes(hash_bytes[:4], "big") % len(asset_list)
    return asset_list[index]


class ReplayCMAPSSTool(BaseTool):
    """Replay NASA C-MAPSS turbofan run-to-failure data come LangChain Tool.

    Mappa unit_id → asset_id via sft-assets registry (deterministic hash).
    Output: pandas DataFrame con 7 colonne canoniche (schema D-46).

    Async-first: usa await tool.ainvoke({...}) o await tool._arun(...).
    _run() e' disabilitato (solleva NotImplementedError).

    Decisioni: D-46, D-47, OQ5, IOT-07.
    """

    name: str = "replay_cmapss"
    description: str = (
        "Replay NASA C-MAPSS turbofan run-to-failure data, mapped to a Mantis textile asset "
        "via sft-assets registry. Emits unified ReplayRecord schema: "
        "asset_id, timestamp (UTC), sensor_id, value, unit, source_dataset, source_unit. "
        "Use for training PredictiveMaintenance agents (Phase 7) or historical sensor analysis. "
        "Phase 3: FD001 only (100 train trajectories, 1 fault mode HPC Degradation). "
        "Optional target_asset_id overrides the automatic deterministic mapping (OQ5)."
    )
    args_schema: type[BaseModel] = ReplayCMAPSSArgs

    def _run(
        self,
        unit_id: int,
        dataset: str = "FD001",
        time_range: tuple[datetime, datetime] | None = None,
        sensor_subset: list[str] | None = None,
        target_asset_id: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Sync _run e' disabilitato — usa async _arun."""
        raise NotImplementedError(
            "ReplayCMAPSSTool e' async-only. "
            "Usa `await tool.ainvoke({...})` o `await tool._arun(...)` invece di _run."
        )

    async def _arun(
        self,
        unit_id: int,
        dataset: str = "FD001",
        time_range: tuple[datetime, datetime] | None = None,
        sensor_subset: list[str] | None = None,
        target_asset_id: str | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Replay C-MAPSS FD001 trajectory per unit_id come DataFrame unificato.

        Args:
            unit_id: C-MAPSS engine unit ID (1..260).
            dataset: Sub-dataset (default "FD001"; Phase 3 supporta solo FD001).
            time_range: Intervallo UTC opzionale (filtra per cycle timestamp). None = tutto.
            sensor_subset: Sottoinsieme sensori (es. ["sensor_2", "sensor_7"]). None = tutti 21.
            target_asset_id: Override asset_id output (OQ5). None = deterministic hash.

        Returns:
            pandas.DataFrame con colonne canoniche:
            ["asset_id", "timestamp", "sensor_id", "value", "unit", "source_dataset", "source_unit"]

        Raises:
            FileNotFoundError: Se il dataset non e' disponibile.
        """
        # Risolve asset_id: override esplicito o deterministic hash
        resolved_asset_id = target_asset_id or _deterministic_asset_for_unit(unit_id)

        # Carica CSV C-MAPSS
        csv_path = _get_cmapss_path(dataset)
        df_raw = pd.read_csv(
            csv_path,
            sep=r"\s+",
            header=None,
            names=_CMAPSS_COLUMNS,
        )

        # Filtra per unit_id
        df_unit = df_raw[df_raw["unit_id"] == unit_id].copy()

        # Pivot da wide a long: (unit_id, cycle) × 21 sensors → righe
        sensor_cols = [f"sensor_{i}" for i in range(1, 22)]

        # Applica subset se specificato
        if sensor_subset is not None:
            sensor_cols = [s for s in sensor_cols if s in sensor_subset]

        records = []
        for _, row in df_unit.iterrows():
            cycle = int(row["cycle"])
            # Mapping cycle → UTC timestamp: datetime(2026,1,1, UTC) + cycle * 60s (A-002)
            ts = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=cycle * 60)

            # Filtra per time_range se specificato
            if time_range is not None:
                start, end = time_range
                if not (start <= ts <= end):
                    continue

            for sensor_col in sensor_cols:
                records.append({
                    "asset_id": resolved_asset_id,
                    "timestamp": ts,
                    "sensor_id": sensor_col,
                    "value": float(row[sensor_col]),
                    "unit": "raw",
                    "source_dataset": "cmapss",
                    "source_unit": f"{dataset}#unit{unit_id}#cycle{cycle}",
                })

        # Crea DataFrame con schema canonico (7 colonne D-46)
        result_df = pd.DataFrame(
            records,
            columns=["asset_id", "timestamp", "sensor_id", "value", "unit", "source_dataset", "source_unit"],
        )
        return result_df
