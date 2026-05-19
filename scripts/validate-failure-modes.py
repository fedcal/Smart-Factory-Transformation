#!/usr/bin/env python3
"""
scripts/validate-failure-modes.py

CI validator (D-65) — verifica che ogni FailureMode definita in
packages/sft-domain/src/sft_domain/failure_modes.yaml abbia
almeno una SOP del corpus che la referenzia.

Logica di matching (ogni FailureMode e' "referenced" se almeno UNA delle
seguenti e' true in almeno una SOP):

  - fm.id appare (exact o normalizzato '-'/'_') in tags / related_glossary
  - fm.name_it.lower() o fm.name_en.lower() appaiono come token o substring
    in tags / related_glossary / asset_family / title
  - Una parola lunga >= 4 caratteri estratta dai nomi/id appare in qualsiasi
    token o nel title (case-insensitive)

Output:
    FAILURE_MODES: total=X referenced=Y orphans=Z

Exit codes:
    0 — zero orphan failure modes (o orphans <= --allow-orphans)
    1 — orphan failure modes trovate (oltre la soglia)

Wired in CI via Nx target `validate-failure-modes` (Task 3 di Plan 05-03).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

WORKSPACE_ROOT = Path(__file__).parent.parent

# Aggiungiamo il package sft-domain al PYTHONPATH per importare il loader
# (in CI il workspace e' installato via `uv sync --all-packages` quindi questo
# potrebbe gia' essere disponibile, ma manteniamo il path injection per
# robustezza in esecuzione standalone)
_SFT_DOMAIN_SRC = WORKSPACE_ROOT / "packages" / "sft-domain" / "src"
if str(_SFT_DOMAIN_SRC) not in sys.path:
    sys.path.insert(0, str(_SFT_DOMAIN_SRC))

from sft_domain.failure_modes import FailureMode, load_failure_modes  # noqa: E402

# SOP filename pattern (mirror di scripts/validate-corpus-frontmatter.py)
SOP_FILENAME_PATTERN = re.compile(r"^SOP-[A-Z]+-[0-9]{3}-[a-z0-9-]+-(it|en)\.md$")
_TOKEN_SPLIT = re.compile(r"[\s_\-]+")
_MIN_NEEDLE_LEN = 4


def _build_needles(fm: FailureMode) -> set[str]:
    """Costruisce il set di needle da cercare nei token/title delle SOP."""
    needles: set[str] = {
        fm.id.lower(),
        fm.name_it.lower(),
        fm.name_en.lower(),
    }
    # estrai parole >= MIN_NEEDLE_LEN dai nomi (per matching parziale)
    for n in (fm.id.lower(), fm.name_it.lower(), fm.name_en.lower()):
        for piece in _TOKEN_SPLIT.split(n):
            if len(piece) >= _MIN_NEEDLE_LEN:
                needles.add(piece)
    # rimuovi stringhe vuote
    return {n for n in needles if n}


def _extract_sop_signals(sop_path: Path) -> tuple[set[str], str] | None:
    """Estrae il set di token e il title da una SOP.

    Returns (tokens, title_lowercase) o None se il file non e' parsabile.
    """
    text = sop_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None

    tokens: set[str] = set()
    for v in meta.get("tags") or []:
        tokens.add(str(v).lower())
    for v in meta.get("related_glossary") or []:
        tokens.add(str(v).lower())
    asset_family = str(meta.get("asset_family") or "").lower()
    if asset_family:
        tokens.add(asset_family)

    title = str(meta.get("title") or "").lower()
    return (tokens, title)


def _needle_matches(needle: str, tokens: set[str], title: str) -> bool:
    """True se `needle` si trova come token o substring in tokens/title."""
    if not needle:
        return False
    # 1. exact match contro un token
    if needle in tokens:
        return True
    # 2. variante normalizzata '_' <-> '-'
    v1 = needle.replace("_", "-")
    v2 = needle.replace("-", "_")
    if v1 in tokens or v2 in tokens:
        return True
    # 3. substring contro qualsiasi token (entrambe direzioni)
    if len(needle) >= _MIN_NEEDLE_LEN:
        for t in tokens:
            if len(t) >= _MIN_NEEDLE_LEN and (needle in t or t in needle):
                return True
        # 4. substring nel title
        if needle in title:
            return True
    return False


def _find_referencing_sop(
    fm: FailureMode,
    sop_signals: list[tuple[str, set[str], str]],
) -> str | None:
    """Restituisce il nome della prima SOP che referenzia `fm`, o None."""
    needles = _build_needles(fm)
    for sop_name, tokens, title in sop_signals:
        for needle in needles:
            if _needle_matches(needle, tokens, title):
                return sop_name
    return None


def validate(corpus_dir: Path, allow_orphans: int) -> int:
    """Esegue la validazione. Returns 0 (ok) o 1 (orphan)."""
    if not corpus_dir.is_absolute():
        corpus_dir = WORKSPACE_ROOT / corpus_dir

    if not corpus_dir.exists():
        print(
            f"ERROR: corpus-dir non trovato: {corpus_dir}",
            file=sys.stderr,
        )
        return 1

    sop_paths = [
        p
        for p in sorted(corpus_dir.rglob("*.md"))
        if SOP_FILENAME_PATTERN.match(p.name)
    ]
    if not sop_paths:
        print(
            f"WARNING: nessuna SOP trovata in {corpus_dir} — "
            f"impossibile validare cross-reference",
            file=sys.stderr,
        )
        return 1

    sop_signals: list[tuple[str, set[str], str]] = []
    for sop in sop_paths:
        result = _extract_sop_signals(sop)
        if result is None:
            print(f"WARNING: skipping unparseable SOP {sop.name}", file=sys.stderr)
            continue
        tokens, title = result
        sop_signals.append((sop.name, tokens, title))

    fms = load_failure_modes()

    orphans: list[FailureMode] = []
    for fm in fms:
        if _find_referencing_sop(fm, sop_signals) is None:
            orphans.append(fm)

    total = len(fms)
    referenced = total - len(orphans)
    print(
        f"FAILURE_MODES: total={total} referenced={referenced} "
        f"orphans={len(orphans)}"
    )

    if len(orphans) > allow_orphans:
        print(
            f"FAILED: {len(orphans)} orphan failure mode(s) "
            f"(threshold --allow-orphans={allow_orphans}):",
            file=sys.stderr,
        )
        for fm in orphans:
            print(
                f"  - {fm.id} (name_it='{fm.name_it}', name_en='{fm.name_en}', "
                f"asset_families={fm.asset_families})",
                file=sys.stderr,
            )
        print(
            "\nFix: aggiungere riferimento alla failure mode in una SOP "
            "(tags / related_glossary / title) oppure rimuoverla dal YAML "
            "fino a quando il corpus non la copre.",
            file=sys.stderr,
        )
        return 1

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verifica che ogni FailureMode sia referenziata da almeno una SOP "
            "del corpus (D-65 / KNW-08 SC#4)."
        ),
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=WORKSPACE_ROOT / "simulators" / "synthetic-corpus",
        help="Directory del corpus sintetico (default: simulators/synthetic-corpus)",
    )
    parser.add_argument(
        "--allow-orphans",
        type=int,
        default=0,
        help=(
            "Massimo numero di failure mode orphan consentite (default: 0). "
            "Da deprecare in Phase 8 quando KnowledgeCurator garantira' "
            "automaticamente il pairing FailureMode <-> SOP."
        ),
    )
    args = parser.parse_args()

    sys.exit(validate(args.corpus_dir, args.allow_orphans))


if __name__ == "__main__":
    main()
