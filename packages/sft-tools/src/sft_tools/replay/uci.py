"""ReplayUCITool — UCI Manufacturing dataset replay loader.

LangChain BaseTool (langchain-core 1.x, Pydantic v2 native).
Async-first: _arun e' il metodo primario; _run solleva NotImplementedError.

CRITICAL: SOLO import da `pydantic` v2 native (Pitfall 5 — compat shim vietato).
CRITICAL: NESSUN f-string SQL (T-03-02-sql, Security check 1).

Decisioni implementate:
    D-46 (ReplayRecord schema unificato: 7 colonne canoniche)
    D-47 (sft-tools location)
    IOT-08 (replay_uci esposto come LangChain Tool)
"""

from __future__ import annotations

import pathlib
from datetime import datetime, timezone
from typing import Literal

import pandas as pd
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from sft_tools.replay.models import ReplayUCIArgs

UTC = timezone.utc

# Path workspace root per trovare i dataset
_WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent.parent.parent.parent.parent

# Fixtures directory per dev/test
_FIXTURES_DIR = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / "tests" / "fixtures"
)


def _get_uci_path(dataset: str) -> pathlib.Path:
    """Risolve il path al file CSV UCI Manufacturing.

    Priorita':
    1. simulators/sim-textile/replay-data/uci_<dataset>.csv (prod path)
    2. packages/sft-tools/tests/fixtures/uci_<dataset>_sample.csv (dev/test fallback)

    Args:
        dataset: Variant UCI dataset ("air_quality", "energy", "production").

    Returns:
        pathlib.Path al file dataset.

    Raises:
        FileNotFoundError: Se nessun path e' disponibile.
    """
    prod_path = _WORKSPACE_ROOT / "simulators" / "sim-textile" / "replay-data" / f"uci_{dataset}.csv"
    if prod_path.exists():
        return prod_path

    # Fallback fixture per dev/test
    fixture_path = _FIXTURES_DIR / f"uci_{dataset}_sample.csv"
    if fixture_path.exists():
        return fixture_path

    raise FileNotFoundError(
        f"UCI dataset '{dataset}' non trovato. "
        f"Prova: python3 scripts/download-replay-datasets.py --dataset uci-{dataset.replace('_', '-')}. "
        f"Path cercati: {prod_path}, {fixture_path}"
    )


class ReplayUCITool(BaseTool):
    """Replay UCI Manufacturing dataset come LangChain Tool.

    Supporta 3 varianti: air_quality, energy, production.
    asset_id e' richiesto esplicitamente (nessun auto-mapping UCI).
    Output: pandas DataFrame con 7 colonne canoniche (schema D-46).

    Async-first: usa await tool.ainvoke({...}) o await tool._arun(...).
    _run() e' disabilitato (solleva NotImplementedError).

    Decisioni: D-46, D-47, IOT-08.
    """

    name: str = "replay_uci"
    description: str = (
        "Replay UCI Manufacturing dataset variants as unified ReplayRecord schema. "
        "Supports: 'air_quality' (ambient sensors mapped to dyeing assets), "
        "'energy' (building energy mapped to finishing assets), "
        "'production' (manufacturing process mapped to loom throughput proxy). "
        "Output columns: asset_id, timestamp (UTC), sensor_id, value, unit, "
        "source_dataset, source_unit. Requires explicit asset_id parameter."
    )
    args_schema: type[BaseModel] = ReplayUCIArgs

    def _run(
        self,
        dataset: str,
        asset_id: str,
        time_range: tuple[datetime, datetime] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Sync _run e' disabilitato — usa async _arun."""
        raise NotImplementedError(
            "ReplayUCITool e' async-only. "
            "Usa `await tool.ainvoke({...})` o `await tool._arun(...)` invece di _run."
        )

    async def _arun(
        self,
        dataset: str,
        asset_id: str,
        time_range: tuple[datetime, datetime] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Replay UCI dataset come DataFrame unificato.

        Args:
            dataset: Variant UCI ("air_quality", "energy", "production").
            asset_id: Asset ID di destinazione (es. "LOOM-01").
            time_range: Intervallo UTC opzionale. None = tutti i record.

        Returns:
            pandas.DataFrame con colonne canoniche:
            ["asset_id", "timestamp", "sensor_id", "value", "unit", "source_dataset", "source_unit"]

        Raises:
            FileNotFoundError: Se il dataset non e' disponibile.
        """
        csv_path = _get_uci_path(dataset)
        df_raw = pd.read_csv(csv_path)

        records = []
        for idx, row in df_raw.iterrows():
            # Parsing timestamp dalla colonna 'timestamp' (ISO 8601 con timezone)
            ts_raw = row["timestamp"]
            if isinstance(ts_raw, str):
                ts = datetime.fromisoformat(ts_raw)
                # Assicura tz-aware UTC
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
            elif isinstance(ts_raw, datetime):
                ts = ts_raw if ts_raw.tzinfo is not None else ts_raw.replace(tzinfo=UTC)
            else:
                # Fallback: usa indice come offset in secondi da epoch 2026-01-01
                ts = datetime(2026, 1, 1, tzinfo=UTC)

            # Filtra per time_range se specificato
            if time_range is not None:
                start, end = time_range
                if not (start <= ts <= end):
                    continue

            sensor_id = str(row.get("sensor_id", f"sensor_{idx}"))
            value = float(row.get("value", 0.0))
            unit = str(row.get("unit", "raw"))

            records.append({
                "asset_id": asset_id,
                "timestamp": ts,
                "sensor_id": sensor_id,
                "value": value,
                "unit": unit,
                "source_dataset": "uci",
                "source_unit": f"uci_{dataset}#row{idx}",
            })

        result_df = pd.DataFrame(
            records,
            columns=["asset_id", "timestamp", "sensor_id", "value", "unit", "source_dataset", "source_unit"],
        )
        return result_df
