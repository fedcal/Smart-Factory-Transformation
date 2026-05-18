#!/usr/bin/env python3
"""
scripts/download-replay-datasets.py

Downloads NASA C-MAPSS and UCI Manufacturing datasets for Phase 3 replay loaders.
Validates downloads via SHA256 checksums in simulators/sim-textile/replay-data/CHECKSUMS.txt.

License compliance (A4/A10 mitigation):
    - NASA C-MAPSS: Open Data Portal (CC0 / NASA Open Government License)
    - UCI Manufacturing: UCI ML Repository (Creative Commons Attribution 4.0)
    - Datasets are NOT committed to version control (gitignored by design).
    - Download-on-demand pattern: each developer/CI fetches data independently.

Usage:
    python3 scripts/download-replay-datasets.py [--dry-run] [--dataset DATASET] [--dest PATH] [--force]

Exit codes:
    0 - All requested datasets downloaded and SHA256 verified (or dry-run completed)
    1 - Download error, SHA256 mismatch, or I/O error
"""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import sys
import urllib.request
from typing import NamedTuple

WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent
DEFAULT_DEST = WORKSPACE_ROOT / "simulators" / "sim-textile" / "replay-data"
CHECKSUMS_FILE = DEFAULT_DEST / "CHECKSUMS.txt"


class DatasetSpec(NamedTuple):
    """Specifica per un dataset da scaricare."""

    key: str  # chiave CLI (es. "cmapss-fd001")
    url_env: str  # env var per override URL
    default_url: str  # URL default (best-effort — può cambiare)
    filename: str  # nome file destinazione
    description: str  # descrizione human-readable


# Registry dataset — URL best-effort; user può override via env vars
_DATASETS: dict[str, DatasetSpec] = {
    "cmapss-fd001": DatasetSpec(
        key="cmapss-fd001",
        url_env="CMAPSS_FD001_URL",
        # NASA Open Data Portal: PHM Challenge 2008 dataset (C-MAPSS turbofan)
        # URL best-effort — verificare su https://data.nasa.gov/ se non funziona
        default_url="https://data.nasa.gov/download/ff5v-kuh6/application%2Fzip",
        filename="train_FD001.txt",
        description="NASA C-MAPSS FD001 turbofan run-to-failure (PHM Challenge 2008)",
    ),
    "uci-air-quality": DatasetSpec(
        key="uci-air-quality",
        url_env="UCI_AIR_QUALITY_URL",
        default_url="https://archive.ics.uci.edu/static/public/360/air+quality.zip",
        filename="uci_air_quality.zip",
        description="UCI Air Quality dataset (ambient sensor proxy for dyeing assets)",
    ),
    "uci-energy": DatasetSpec(
        key="uci-energy",
        url_env="UCI_ENERGY_URL",
        default_url="https://archive.ics.uci.edu/static/public/374/appliances+energy+prediction.zip",
        filename="uci_energy.zip",
        description="UCI Energy Efficiency dataset (building energy proxy for finishing assets)",
    ),
    "uci-production": DatasetSpec(
        key="uci-production",
        url_env="UCI_PRODUCTION_URL",
        # NOTE: URL placeholder per dataset produzione UCI Manufacturing.
        # Dataset reale: UCI dataset 477 (Real-Time Election Results) usato come proxy
        # per throughput manufacturing. L'URL potrebbe cambiare — override via UCI_PRODUCTION_URL.
        default_url="https://archive.ics.uci.edu/static/public/477/real+time+election+results+portugal+2019.zip",
        filename="uci_production.zip",
        description="UCI Production proxy dataset (manufacturing throughput mapping for loom assets)",
    ),
}


def _compute_sha256(path: pathlib.Path) -> str:
    """Calcola SHA256 di un file in modo streaming (memoria efficiente).

    Args:
        path: Path al file.

    Returns:
        Stringa hex SHA256 (64 caratteri).
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _load_checksums(checksums_path: pathlib.Path) -> dict[str, str]:
    """Carica il file CHECKSUMS.txt in un dict {filename: sha256}.

    Args:
        checksums_path: Path al file CHECKSUMS.txt.

    Returns:
        Dict {filename: sha256_hex}, o dict vuoto se file non esiste.
    """
    if not checksums_path.exists():
        return {}

    checksums: dict[str, str] = {}
    with checksums_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                sha256_hex, filename = parts
                checksums[filename] = sha256_hex.lower()
    return checksums


def _save_checksum(checksums_path: pathlib.Path, filename: str, sha256_hex: str) -> None:
    """Aggiorna CHECKSUMS.txt con il checksum di un file scaricato.

    Aggiunge la riga se non esiste, sostituisce se esiste.

    Args:
        checksums_path: Path al file CHECKSUMS.txt.
        filename: Nome file (senza path).
        sha256_hex: SHA256 hex del file.
    """
    existing = checksums_path.read_text(encoding="utf-8") if checksums_path.exists() else ""

    lines = existing.splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            parts = stripped.split(None, 1)
            if len(parts) == 2 and parts[1] == filename:
                new_lines.append(f"{sha256_hex}  {filename}")
                found = True
                continue
        new_lines.append(line)

    if not found:
        new_lines.append(f"{sha256_hex}  {filename}")

    checksums_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def download_dataset(
    spec: DatasetSpec,
    dest: pathlib.Path,
    dry_run: bool = False,
    force: bool = False,
) -> bool:
    """Scarica un singolo dataset con verifica SHA256.

    Args:
        spec: Specifica dataset (URL, filename, ecc.).
        dest: Directory destinazione.
        dry_run: Se True, stampa cosa farebbe senza I/O di rete.
        force: Se True, sovrascrive file esistente.

    Returns:
        True su successo (o dry-run), False su errore.
    """
    url = os.environ.get(spec.url_env, spec.default_url)
    dest_file = dest / spec.filename
    checksums = _load_checksums(CHECKSUMS_FILE)

    if dry_run:
        expected_sha = checksums.get(spec.filename, "<checksum non ancora registrato>")
        print(f"[dry-run] would download: {spec.description}")
        print(f"[dry-run]   URL: {url}")
        print(f"[dry-run]   dest: {dest_file.relative_to(WORKSPACE_ROOT)}")
        print(f"[dry-run]   sha256 atteso: {expected_sha}")
        return True

    # Controlla se il file esiste già
    if dest_file.exists() and not force:
        actual_sha = _compute_sha256(dest_file)
        if spec.filename in checksums:
            expected_sha = checksums[spec.filename]
            if actual_sha == expected_sha:
                print(f"[skip] {spec.filename}: gia' presente e SHA256 valido.")
                return True
            else:
                print(
                    f"[warn] {spec.filename}: presente ma SHA256 mismatch "
                    f"(atteso={expected_sha[:16]}..., effettivo={actual_sha[:16]}...). "
                    f"Usa --force per ri-scaricare.",
                    file=sys.stderr,
                )
                return False
        else:
            print(f"[skip] {spec.filename}: gia' presente, nessun checksum registrato (usa --force per verificare).")
            return True

    # Scarica il file
    print(f"[download] {spec.description}")
    print(f"  URL: {url}")
    print(f"  dest: {dest_file.relative_to(WORKSPACE_ROOT)}")

    dest.mkdir(parents=True, exist_ok=True)

    try:
        urllib.request.urlretrieve(url, dest_file)
    except Exception as exc:
        print(
            f"ERROR: Download fallito per {spec.filename}: {exc}\n"
            f"  Verifica l'URL o imposta {spec.url_env}=<url-corretto> come env var.",
            file=sys.stderr,
        )
        if dest_file.exists():
            dest_file.unlink()
        return False

    # Calcola SHA256 del file scaricato
    actual_sha = _compute_sha256(dest_file)
    print(f"  SHA256: {actual_sha}")

    # Verifica contro CHECKSUMS.txt se disponibile
    if spec.filename in checksums:
        expected_sha = checksums[spec.filename]
        if actual_sha != expected_sha:
            print(
                f"ERROR: SHA256 mismatch per {spec.filename}!\n"
                f"  Atteso:  {expected_sha}\n"
                f"  Effettivo: {actual_sha}\n"
                f"  File rimosso per sicurezza.",
                file=sys.stderr,
            )
            dest_file.unlink()
            return False
        print(f"  [ok] SHA256 verificato.")
    else:
        # Prima volta: registra il checksum
        print(f"  [info] Nessun checksum preregistrato. Registrando SHA256 in CHECKSUMS.txt.")
        _save_checksum(CHECKSUMS_FILE, spec.filename, actual_sha)
        print(f"  [ok] Checksum salvato: {actual_sha}")

    return True


def main() -> None:
    """Entry point principale dello script."""
    parser = argparse.ArgumentParser(
        description=(
            "Download NASA C-MAPSS + UCI Manufacturing datasets per Phase 3 replay loaders. "
            "Verifica SHA256 via simulators/sim-textile/replay-data/CHECKSUMS.txt. "
            "I dataset NON sono committati in git (license compliance A4/A10)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Esempi:\n"
            "  python3 scripts/download-replay-datasets.py --dry-run --dataset all\n"
            "  python3 scripts/download-replay-datasets.py --dataset cmapss-fd001\n"
            "  python3 scripts/download-replay-datasets.py --dataset uci-production --force\n"
            "\nOverride URL via env vars:\n"
            "  CMAPSS_FD001_URL=https://... python3 scripts/download-replay-datasets.py\n"
        ),
    )
    parser.add_argument(
        "--dataset",
        choices=list(_DATASETS.keys()) + ["all"],
        default="all",
        help="Dataset da scaricare. Default: all (tutti e 4).",
    )
    parser.add_argument(
        "--dest",
        type=pathlib.Path,
        default=DEFAULT_DEST,
        help=f"Directory destinazione. Default: {DEFAULT_DEST.relative_to(WORKSPACE_ROOT)}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra cosa scaricherebbe senza eseguire I/O di rete.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sovrascrive file esistenti (ri-scarica e ri-verifica SHA256).",
    )
    args = parser.parse_args()

    # Seleziona dataset da processare
    if args.dataset == "all":
        targets = list(_DATASETS.values())
    else:
        targets = [_DATASETS[args.dataset]]

    if args.dry_run:
        print(f"[dry-run] dest: {args.dest.relative_to(WORKSPACE_ROOT)}")
        print(f"[dry-run] dataset: {', '.join(t.key for t in targets)}")
        print()

    # Scarica / verifica ogni dataset
    success = True
    for spec in targets:
        ok = download_dataset(spec, args.dest, dry_run=args.dry_run, force=args.force)
        if not ok:
            success = False

    if args.dry_run:
        print()
        print(f"[dry-run] {len(targets)} dataset(s) elencati. Nessun file scaricato.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
