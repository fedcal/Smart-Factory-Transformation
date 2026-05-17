#!/usr/bin/env python3
"""
scripts/validate-corpus-pairing.py

Validates that every SOP id in the synthetic corpus has the expected
bilingual pairing: exactly one file with lang=it and exactly one file
with lang=en. Also verifies semantic consistency between IT and EN files
for the same id (asset, asset_family, role, hazard_level must match).

Pitfall 7 mitigation: file naming convention embeds both id and lang for
`ls`-visible drift; this script enforces the pairing constraint at the
frontmatter level.

--allow-missing-en mode: Plan 02-04 ships IT-only. Pass this flag to
demote missing EN counterparts from errors to warnings. Plan 02-05 drops
this flag after EN translations are committed.

Graceful empty-corpus handling: if no *.md files found, exits 0.

Usage:
    python3 scripts/validate-corpus-pairing.py [--corpus-dir PATH] [--allow-missing-en]

Exit codes:
    0 - All pairings valid (or corpus-dir is empty)
    1 - One or more pairing errors found
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

import frontmatter

WORKSPACE_ROOT = Path(__file__).parent.parent

SEMANTIC_FIELDS = ["asset", "asset_family", "role", "hazard_level"]


def validate(corpus_dir: Path, allow_missing_en: bool) -> bool:
    """
    Validate bilingual SOP pairings under corpus_dir.

    Returns True if all pairings are valid (or corpus is empty), False otherwise.
    """
    # Resolve relative paths against workspace root
    if not corpus_dir.is_absolute():
        corpus_dir = WORKSPACE_ROOT / corpus_dir

    if not corpus_dir.exists():
        corpus_rel = corpus_dir.relative_to(WORKSPACE_ROOT) if corpus_dir.is_relative_to(WORKSPACE_ROOT) else corpus_dir
        print(f"OK: no SOPs found yet (corpus-dir does not exist: {corpus_rel})")
        return True

    md_files = sorted(corpus_dir.rglob("*.md"))
    if not md_files:
        corpus_rel = corpus_dir.relative_to(WORKSPACE_ROOT) if corpus_dir.is_relative_to(WORKSPACE_ROOT) else corpus_dir
        print(f"OK: no SOPs found yet (corpus-dir empty: {corpus_rel})")
        return True

    # Group files by SOP id, tracking lang and metadata
    # Structure: { sop_id: { lang: {"path": Path, "meta": dict} } }
    by_id: dict[str, dict[str, dict]] = defaultdict(dict)
    parse_errors: list[str] = []

    for md_path in md_files:
        rel = md_path.relative_to(WORKSPACE_ROOT)
        try:
            post = frontmatter.load(str(md_path))
        except Exception as exc:
            parse_errors.append(f"{rel}: ERROR parsing frontmatter: {exc}")
            continue

        sop_id = post.metadata.get("id", "")
        lang = post.metadata.get("lang", "")

        if not sop_id:
            parse_errors.append(
                f"{rel}: MISSING FIELD 'id' in frontmatter\n"
                f"    Fix: add 'id: SOP-ASSET-NNN' to frontmatter"
            )
            continue

        if lang not in ("it", "en"):
            parse_errors.append(
                f"{rel}: INVALID FIELD 'lang: {lang}' — must be 'it' or 'en'\n"
                f"    Fix: set 'lang: it' or 'lang: en' in frontmatter"
            )
            continue

        if lang in by_id[sop_id]:
            existing_rel = by_id[sop_id][lang]["path"].relative_to(WORKSPACE_ROOT)
            parse_errors.append(
                f"{rel}: DUPLICATE — id '{sop_id}' lang '{lang}' already seen in {existing_rel}\n"
                f"    Fix: each SOP id must have exactly one IT and one EN file"
            )
        else:
            by_id[sop_id][lang] = {"path": md_path, "meta": dict(post.metadata)}

    errors: list[str] = list(parse_errors)
    warnings: list[str] = []

    for sop_id, lang_map in sorted(by_id.items()):
        it_entry = lang_map.get("it")
        en_entry = lang_map.get("en")

        # Check IT presence (always required)
        if it_entry is None:
            errors.append(
                f"SOP '{sop_id}': MISSING Italian (lang=it) file\n"
                f"    Fix: create it/{{family}}/{sop_id}-{{slug}}-it.md with lang: it"
            )

        # Check EN presence (error unless --allow-missing-en)
        if en_entry is None:
            msg = (
                f"SOP '{sop_id}': missing English (lang=en) counterpart "
                f"(EN translations ship in Plan 02-05)"
            )
            if allow_missing_en:
                warnings.append(f"WARNING: {msg}")
            else:
                errors.append(
                    f"SOP '{sop_id}': MISSING English (lang=en) file\n"
                    f"    Fix: create en/{{family}}/{sop_id}-{{slug}}-en.md with lang: en\n"
                    f"    Hint: use --allow-missing-en if EN translations are not yet written"
                )

        # Check semantic consistency if both exist
        if it_entry is not None and en_entry is not None:
            it_meta = it_entry["meta"]
            en_meta = en_entry["meta"]
            it_rel = it_entry["path"].relative_to(WORKSPACE_ROOT)
            en_rel = en_entry["path"].relative_to(WORKSPACE_ROOT)

            for field in SEMANTIC_FIELDS:
                it_val = it_meta.get(field)
                en_val = en_meta.get(field)
                if it_val != en_val:
                    errors.append(
                        f"SOP '{sop_id}': SEMANTIC MISMATCH on field '{field}' — "
                        f"IT={it_val!r} EN={en_val!r}\n"
                        f"    Files: {it_rel}, {en_rel}\n"
                        f"    Fix: ensure {field} is identical in both IT and EN frontmatter"
                    )

    # Emit warnings
    for w in warnings:
        print(w)

    if errors:
        print(
            f"FAILED: {len(errors)} pairing error(s) across {len(by_id)} SOP id(s):",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return False

    sop_count = len(by_id)
    en_count = sum(1 for lm in by_id.values() if "en" in lm)
    print(
        f"OK: {sop_count} SOP id(s) validated — "
        f"{sop_count} IT file(s), {en_count} EN file(s)"
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate bilingual pairing of SOP files in synthetic-corpus.",
        epilog=(
            "Use --allow-missing-en during Plan 02-04 (IT-only phase). "
            "Drop this flag after Plan 02-05 ships EN translations."
        ),
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=WORKSPACE_ROOT / "simulators" / "synthetic-corpus",
        help="Path to the synthetic-corpus directory (default: simulators/synthetic-corpus)",
    )
    parser.add_argument(
        "--allow-missing-en",
        action="store_true",
        help=(
            "Demote missing EN counterparts from errors to warnings. "
            "Used during Plan 02-04 (IT-only). Drop after Plan 02-05."
        ),
    )
    args = parser.parse_args()

    success = validate(args.corpus_dir, args.allow_missing_en)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
