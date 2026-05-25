"""Test Nyquist scaffold — Wave 1 (12-01) implementerà i calcoli effettivi.

Questi test sono skipped intenzionalmente: esistono come placeholder strutturale
(Nyquist scaffold) per garantire che Wave 1 abbia un target chiaro.
"""

from __future__ import annotations

import os

import pytest


@pytest.mark.skip(reason="Nyquist scaffold — implemented in Wave 1 (12-01)")
def test_tco_table_csv_exists() -> None:
    """Verifica che lo script economico produca tco_table.csv."""
    output_path = os.path.join(os.path.dirname(__file__), "..", "tco_table.csv")
    assert os.path.exists(output_path), (
        f"tco_table.csv non trovato in {output_path} — "
        "eseguire tco_oepv.py prima del test"
    )


@pytest.mark.skip(reason="Nyquist scaffold — implemented in Wave 1 (12-01)")
def test_oepv_table_csv_exists() -> None:
    """Verifica che lo script economico produca oepv_table.csv."""
    output_path = os.path.join(os.path.dirname(__file__), "..", "oepv_table.csv")
    assert os.path.exists(output_path), (
        f"oepv_table.csv non trovato in {output_path} — "
        "eseguire tco_oepv.py prima del test"
    )
