"""Script economico TCO + OEPV — Phase 12, Wave 1 stub.

Questo file è uno STUB: i calcoli effettivi vengono implementati in Wave 1 (12-01).
L'import del vendor è validato qui per garantire che _oepv_vendor sia importabile
in CI prima che Wave 1 inizi la sua implementazione.

Usage (Wave 1):
    python tco_oepv.py          # legge params.toml, scrive tco_table.csv + oepv_table.csv
"""

from __future__ import annotations

from _oepv_vendor import OepvConfig, build_sensitivity_table, compute_oepv  # noqa: F401

# TODO (Wave 1 — 12-01): implementare le seguenti funzioni:
#   - load_params(path: str) -> dict   (legge params.toml via tomllib)
#   - compute_tco(params: dict) -> dict
#   - write_tco_csv(tco: dict, out_path: str) -> None
#   - write_oepv_csv(rows: list, out_path: str) -> None
#   - main() entry point


if __name__ == "__main__":
    pass  # TODO Wave 1: implementare main()
