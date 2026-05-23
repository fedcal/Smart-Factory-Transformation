#!/usr/bin/env python3
"""
scripts/validate-failure-modes.py

CI validator (D-65 + D-MNT-TAX Phase 7) — verifica:

  1. Ogni FailureMode definita in
     packages/sft-domain/src/sft_domain/failure_modes.yaml abbia almeno
     una SOP del corpus che la referenzia (matching token/title-based).
  2. (Phase 7 / 07-02) reason_code uniqueness cross-entry.
  3. (Phase 7 / 07-02) intervention_steps_sop_id resolution: ogni id
     SOP referenziato in maintenance.intervention_steps_sop_id deve
     esistere come documento SOP nel corpus.

Logica di matching orphan (ogni FailureMode e' "referenced" se almeno UNA
delle seguenti e' true in almeno una SOP):

  - fm.id appare (exact o normalizzato '-'/'_') in tags / related_glossary
  - fm.name_it.lower() o fm.name_en.lower() appaiono come token o substring
    in tags / related_glossary / asset_family / title
  - Una parola lunga >= 4 caratteri estratta dai nomi/id appare in qualsiasi
    token o nel title (case-insensitive)

Output:
    FAILURE_MODES: total=X referenced=Y orphans=Z
    MAINTENANCE:   total=N unique_reason_codes=M sop_refs_resolved=K/N

Exit codes:
    0 — tutti i check OK (orphans <= --allow-orphans, no duplicate codes,
        SOP refs risolti — oppure --strict-sop disabilitato e corpus
        non trovato/refs missing → solo WARN)
    1 — orphan threshold superata OR duplicate reason_codes OR
        (--strict-sop attivo AND SOP ref missing)

Wired in CI via Nx target `validate-failure-modes` (Task 3 di Plan 05-03,
esteso da Plan 07-02 con maintenance taxonomy checks).
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
# Pattern per estrarre l'id SOP canonico dal filename (es. SOP-LOOM-001)
SOP_ID_FROM_FILENAME = re.compile(r"^(SOP-[A-Z]+-[0-9]{3})")
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


def _check_reason_code_uniqueness(modes: tuple[FailureMode, ...]) -> list[str]:
    """Verifica che i reason_code (sotto maintenance:) siano unici tra le entries.

    Args:
        modes: tuple di FailureMode caricate dal loader.

    Returns:
        Lista di error messages (vuota = nessun duplicato).

    Reference:
        D-MNT-TAX (07-02-PLAN.md must_haves "reason_code uniqueness")
        T-V7-tax-drift (07-02 threat register)
    """
    errors: list[str] = []
    seen: dict[str, str] = {}  # reason_code -> first failure_mode.id seen
    for fm in modes:
        if fm.maintenance is None:
            continue
        code = fm.maintenance.reason_code
        if code in seen:
            errors.append(
                f"duplicate reason_code '{code}': "
                f"used by both '{seen[code]}' and '{fm.id}'"
            )
        else:
            seen[code] = fm.id
    return errors


def _discover_sop_corpus_ids(corpus_dir: Path) -> set[str] | None:
    """Estrae l'insieme di SOP id canonici disponibili nel corpus.

    Strategia di discovery (fallback in ordine):

    1. Walk del ``corpus_dir`` cercando file ``SOP-XXX-###-*.md``;
       l'id canonico viene estratto via ``SOP_ID_FROM_FILENAME`` regex.
       Sufficiente per il corpus sintetico Phase 5 attuale
       (simulators/synthetic-corpus/{en,it}/{loom,spinning,dyeing,quality}/).
    2. Se ``corpus_dir`` non esiste o non contiene file SOP, return None.
       Il caller emettera' WARN ed eviterà di bloccare la PR
       (a meno di ``--strict-sop``).

    Returns:
        Set di id SOP (es. {"SOP-LOOM-001", "SOP-SPN-004", ...}) o None
        se il corpus non e' disponibile.
    """
    if not corpus_dir.exists():
        return None
    ids: set[str] = set()
    for sop_path in corpus_dir.rglob("*.md"):
        match = SOP_ID_FROM_FILENAME.match(sop_path.name)
        if match is not None:
            ids.add(match.group(1))
    return ids if ids else None


def _check_sop_id_resolution(
    modes: tuple[FailureMode, ...],
    corpus_ids: set[str] | None,
) -> list[str]:
    """Verifica che ogni intervention_steps_sop_id sia presente nel corpus.

    Args:
        modes: tuple di FailureMode caricate dal loader.
        corpus_ids: set di SOP id disponibili (o None se corpus non trovato).

    Returns:
        Lista di error messages (vuota = tutti i ref risolti, oppure
        corpus non disponibile — il caller decide se hard-fail con
        --strict-sop o WARN).

    Reference:
        D-MNT-TAX (07-02-PLAN.md "intervention_steps_sop_id reference resolution")
        T-V7-tax-orphan-sop (07-02 threat register)
    """
    if corpus_ids is None:
        # Corpus non disponibile — restituiamo lista vuota; il caller
        # ha gia' loggato WARN. Pattern Rule 3: non bloccare PR per
        # mancanza di infrastruttura esterna.
        return []
    errors: list[str] = []
    for fm in modes:
        if fm.maintenance is None:
            continue
        sop_id = fm.maintenance.intervention_steps_sop_id
        if sop_id not in corpus_ids:
            errors.append(
                f"failure_mode '{fm.id}' references missing SOP "
                f"'{sop_id}' (not found in corpus)"
            )
    return errors


def validate(corpus_dir: Path, allow_orphans: int, strict_sop: bool = False) -> int:
    """Esegue la validazione. Returns 0 (ok) o 1 (orphan/dup/sop-missing).

    Args:
        corpus_dir: directory del corpus SOP sintetico.
        allow_orphans: soglia max di orphan failure modes (legacy D-65).
        strict_sop: se True, fallisce su SOP id non risolti. Default False
            (warn-only) per non bloccare PR durante Phase 5 stabilization.
    """
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

    exit_code = 0
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
        exit_code = 1

    # ------------------------------------------------------------------
    # Phase 7 / 07-02 — maintenance taxonomy checks (D-MNT-TAX)
    # ------------------------------------------------------------------
    maintained = tuple(fm for fm in fms if fm.maintenance is not None)
    total_maint = len(maintained)

    # 1) reason_code uniqueness — hard fail (T-V7-tax-drift mitigation)
    dup_errors = _check_reason_code_uniqueness(fms)
    unique_codes = len({fm.maintenance.reason_code for fm in maintained})

    # 2) intervention_steps_sop_id resolution — warn-only by default,
    #    hard fail with --strict-sop (T-V7-tax-orphan-sop mitigation)
    corpus_ids = _discover_sop_corpus_ids(corpus_dir)
    if corpus_ids is None:
        print(
            "WARN: sop_corpus_not_found — skipping intervention_steps_sop_id "
            "resolution (use --strict-sop to fail on missing corpus).",
            file=sys.stderr,
        )
        # TODO 07-02: once Phase 5 corpus path is stable, flip --strict-sop
        # default to True. Tracked in 07-02-SUMMARY.md follow-ups.
        sop_resolved = 0
        sop_errors: list[str] = []
    else:
        sop_errors = _check_sop_id_resolution(fms, corpus_ids)
        sop_resolved = total_maint - len(sop_errors)

    print(
        f"MAINTENANCE:   total={total_maint} "
        f"unique_reason_codes={unique_codes} "
        f"sop_refs_resolved={sop_resolved}/{total_maint}"
    )

    if dup_errors:
        print(
            f"\nFAILED: {len(dup_errors)} duplicate reason_code(s) "
            f"(MUST be unique cross-entry):",
            file=sys.stderr,
        )
        for err in dup_errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            "\nFix: rinominare i reason_code duplicati seguendo la "
            "convenzione ISO 14224 '<MODULE>-<DEFECT_ABBR>-<NNN>'.",
            file=sys.stderr,
        )
        exit_code = 1

    if sop_errors:
        msg = (
            f"\n{'FAILED' if strict_sop else 'WARN'}: "
            f"{len(sop_errors)} maintenance.intervention_steps_sop_id "
            f"reference(s) cannot be resolved against corpus:"
        )
        print(msg, file=sys.stderr)
        for err in sop_errors:
            print(f"  - {err}", file=sys.stderr)
        if strict_sop:
            print(
                "\nFix: aggiungere i SOP mancanti al corpus oppure "
                "aggiornare intervention_steps_sop_id nel YAML.",
                file=sys.stderr,
            )
            exit_code = 1
        else:
            print(
                "\nNote: usa --strict-sop per trasformare questi WARN in "
                "hard failure quando il corpus Phase 5 sara' stabile.",
                file=sys.stderr,
            )

    return exit_code


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
    parser.add_argument(
        "--strict-sop",
        action="store_true",
        default=False,
        help=(
            "Hard-fail su intervention_steps_sop_id non risolti nel corpus "
            "(default: WARN-only per non bloccare PR durante Phase 5 "
            "stabilization; Plan 07-02)."
        ),
    )
    args = parser.parse_args()

    sys.exit(validate(args.corpus_dir, args.allow_orphans, args.strict_sop))


if __name__ == "__main__":
    main()
