#!/usr/bin/env python3
"""
scripts/validate-glossary-coverage.py

D-32 — Glossary coverage CI check.

Extracts **bold** tokens from:
  - simulators/synthetic-corpus/it/**/*.md  → checked against glossary/it.yaml
  - simulators/synthetic-corpus/en/**/*.md  → checked against glossary/en.yaml
  - docs/docs/domain/**/*.md               → checked against glossary/it.yaml
  - docs/docs/en/domain/**/*.md            → checked against glossary/en.yaml
  - docs/docs/assumptions/**/*.md          → checked against glossary/it.yaml
  - docs/docs/en/assumptions/**/*.md       → checked against glossary/en.yaml
  - docs/docs/glossary.md                  → skipped (generated file)
  - docs/docs/en/glossary.md              → skipped (generated file)

Normalisation applied to every extracted token:
  - Lowercase
  - Strip leading/trailing underscores, hyphens, spaces
  - Simple singular heuristic: strip trailing 's' if > 4 chars and result is known term
    (conservative — only applied when unambiguous match improves coverage)
  - Skip tokens that look like code paths (contain '/', '.py', '.yaml', etc.)
  - Skip tokens that are only numbers or punctuation

Lang-matched lookup:
  - IT corpus tokens → it.yaml
  - EN corpus tokens → en.yaml
  - Cross-language references (IT terms in EN files, e.g. **telaio** in EN SOP) are
    looked up in it.yaml as a fallback; this reflects the authoring pattern where EN
    SOPs label foreign-language terms in bold for reader clarity.

Exit codes:
  0 — All bold tokens are covered (possibly with STALE warnings on stdout)
  1 — One or more bold tokens are missing from any glossary

Stale warning (stdout, NOT a failure):
  If >5% of glossary terms are never referenced as **bold** in any document, prints
  STALE: <term> for each stale term. Exit code remains 0 (D-32 explicit: stale is
  warning-only, never fail).

Usage:
    python3 scripts/validate-glossary-coverage.py [--glossary-dir PATH] [--corpus-root PATH]
                                                   [--docs-root PATH] [--no-stale]

Security: uses yaml.safe_load exclusively (CWE-502 prevention, T-02-27).
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

WORKSPACE_ROOT = Path(__file__).parent.parent

_DEFAULT_GLOSSARY_DIR = WORKSPACE_ROOT / "packages/sft-domain/src/sft_domain/glossary"
_DEFAULT_CORPUS_ROOT = WORKSPACE_ROOT / "simulators/synthetic-corpus"
_DEFAULT_DOCS_ROOT = WORKSPACE_ROOT / "docs/docs"

# Patterns that indicate a token is a code artifact, URL, or non-term noise
_CODE_NOISE_RE = re.compile(
    r"(?:/"                          # path separator
    r"|\.py|\.yaml|\.json|\.md"     # file extensions
    r"|\.ts|\.js|\.sh"              # more extensions
    r"|https?:)"                     # URLs
)

# Minimum token length to consider for glossary lookup
_MIN_TOKEN_LEN = 2

# Stale threshold: warn if more than this fraction of glossary terms are never referenced
_STALE_THRESHOLD = 0.05


def load_glossary(yaml_path: Path) -> dict[str, str]:
    """Load glossary YAML, return {term_lower: term_original}.

    Uses yaml.safe_load exclusively (CWE-502 prevention).
    """
    if not yaml_path.exists():
        return {}
    with yaml_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)  # SEMPRE safe_load
    if not isinstance(data, list):
        return {}
    result: dict[str, str] = {}
    for entry in data:
        if isinstance(entry, dict) and "term" in entry:
            term = str(entry["term"])
            result[term.lower()] = term
    return result


def normalise_token(token: str) -> str:
    """Normalise a bold token for glossary lookup.

    Steps:
      1. Lowercase
      2. Strip surrounding whitespace, underscores, hyphens
      3. Replace internal spaces with underscore (multi-word token)
      4. Strip trailing punctuation
    """
    token = token.lower().strip()
    token = token.strip("_-")
    token = re.sub(r"\s+", "_", token)
    token = token.rstrip(".,;:!?)")
    return token


def is_noise_token(token: str) -> bool:
    """Return True if the token is not a meaningful term candidate.

    Heuristics:
    - Too short
    - All numeric / punctuation
    - Code artifacts (path separators, file extensions, URLs)
    - Bolded step headings: multi-word phrases that contain spaces OR that
      start with an uppercase letter followed by verb/preposition (these are
      SOP procedural steps, not glossary terms)
    - Contains common Italian/English verbs or auxiliary words that indicate
      a sentence rather than a term
    """
    if len(token) < _MIN_TOKEN_LEN:
        return True
    # Skip all-numeric tokens
    if re.fullmatch(r"[\d\s_\-\.]+", token):
        return True
    # Skip code artifacts
    if _CODE_NOISE_RE.search(token):
        return True

    # Known assumption-register field names that appear as bolded labels in
    # generated assumption pages — not glossary terms
    _ASSUMPTION_FIELDS = {
        "affermazione", "statement", "identificativo", "id", "categoria",
        "category", "stato", "status", "affetta_i_componenti",
        "affected_components", "rationale", "razionale",
        "created_in_phase", "creata_nella_fase", "superseded_by",
        "sostituita_da", "last_reviewed_in_phase",
    }
    if token.lower() in _ASSUMPTION_FIELDS:
        return True

    # Space-separated words (after normalise, underscores are used instead)
    # If the token still has spaces at this point it was not normalised yet —
    # check word count on the un-normalised form (caller passes raw token here)
    raw_word_count = len(token.split())

    # Tokens that are clearly bolded sentence fragments (> 3 words)
    if raw_word_count > 3:
        return True

    # Tokens with 2-3 words: keep only if snake_case compound or known multi-word term
    # (e.g. "pick density", "color matching" are 2-word terms; "eseguire il rincorso" is a step)
    if raw_word_count > 1:
        # Allow 2-word terms that look like technical compounds (no verb words)
        _VERB_WORDS_IT = {
            "eseguire", "verificare", "analizzare", "definire", "documentare",
            "compilare", "classificare", "confrontare", "applicare", "portare",
            "regolare", "riavviare", "identificare", "mettere", "localizzare",
            "fissare", "tagliare", "annodare", "inserire", "preparare",
            "prelevare", "raccogliere", "finalizzare", "controllare",
            "osservare", "rimuovere", "calcolare", "caricare", "caratterizzare",
            "registrare",
        }
        _VERB_WORDS_EN = {
            "identify", "perform", "check", "verify", "apply", "remove",
            "install", "ensure", "confirm", "measure", "record", "document",
            "collect", "calculate", "prepare", "adjust", "restart", "locate",
            "make", "resume", "secure", "tighten", "loosen", "clean",
            "carry", "classify", "execute", "log", "mend", "position",
            "set", "unload", "preliminary",
        }
        first_word = token.split()[0].lower()
        if first_word in _VERB_WORDS_IT or first_word in _VERB_WORDS_EN:
            return True
        # Allow 2-word tokens only if they look like well-known multi-word terms
        # (contain only lowercase letters, digits, and hyphens — no apostrophes)
        if "'" in token or "'" in token:
            return True

    return False


def extract_bold_tokens(md_path: Path) -> set[str]:
    """Extract all **bold** tokens from a Markdown file and return normalised set."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()

    # Match **...**  — non-greedy, single line
    raw_tokens = re.findall(r"\*\*([^*\n]+?)\*\*", text)
    result: set[str] = set()
    for raw in raw_tokens:
        raw = raw.strip()
        if not raw:
            continue
        # Skip field labels (end with colon or colon+space) — found in assumption pages
        if raw.rstrip().endswith(":"):
            continue
        # Skip tokens that contain a colon (field label pattern)
        if ":" in raw:
            continue
        # Skip tokens that contain parentheses (malformed compound references)
        if "(" in raw or ")" in raw:
            continue
        if is_noise_token(raw):
            continue
        normalised = normalise_token(raw)
        if normalised and not is_noise_token(normalised):
            result.add(normalised)
    return result


def collect_tokens_for_lang(
    lang: str,
    corpus_root: Path,
    docs_root: Path,
) -> set[str]:
    """Collect all bold tokens from documents associated with a language.

    IT: synthetic-corpus/it/ + docs/docs/domain/ + docs/docs/assumptions/
    EN: synthetic-corpus/en/ + docs/docs/en/domain/ + docs/docs/en/assumptions/
    """
    tokens: set[str] = set()

    if lang == "it":
        search_paths = [
            corpus_root / "it",
            docs_root / "domain",
            docs_root / "assumptions",
        ]
    else:  # en
        search_paths = [
            corpus_root / "en",
            docs_root / "en" / "domain",
            docs_root / "en" / "assumptions",
        ]

    for search_path in search_paths:
        if not search_path.exists():
            continue
        for md_path in search_path.rglob("*.md"):
            # Skip generated glossary pages to avoid circular reference
            if md_path.name == "glossary.md":
                continue
            tokens.update(extract_bold_tokens(md_path))

    return tokens


def _token_in_glossary(token: str, glossary: dict[str, str]) -> bool:
    """Check if a token (possibly underscore_separated) matches a glossary entry.

    Handles the case where the glossary uses spaces in multi-word terms (e.g.
    'pick density') but the corpus uses underscores ('pick_density').
    """
    if token in glossary:
        return True
    # Try space variant (underscore → space)
    space_variant = token.replace("_", " ")
    if space_variant in glossary:
        return True
    # Try underscore variant (space → underscore) — unlikely but symmetric
    underscore_variant = token.replace(" ", "_")
    if underscore_variant in glossary:
        return True
    return False


def check_coverage(
    lang: str,
    tokens: set[str],
    glossary: dict[str, str],
    fallback_glossary: dict[str, str] | None = None,
) -> tuple[list[str], list[str]]:
    """Check which tokens are missing from the glossary.

    Returns (missing_tokens, covered_tokens).

    If fallback_glossary is provided (e.g. IT glossary for EN doc cross-references),
    tokens found in fallback are NOT reported as missing.
    """
    missing: list[str] = []
    covered: list[str] = []
    for token in sorted(tokens):
        if _token_in_glossary(token, glossary):
            covered.append(token)
        elif fallback_glossary and _token_in_glossary(token, fallback_glossary):
            # Cross-language reference found in fallback — not an error
            covered.append(token)
        else:
            missing.append(token)
    return missing, covered


def check_stale(
    glossary: dict[str, str],
    covered_tokens: set[str],
    lang: str,
    no_stale: bool,
) -> int:
    """Emit STALE warnings for terms in glossary never referenced as bold.

    Returns count of stale terms.
    """
    stale: list[str] = []
    for term_lower in glossary:
        if term_lower not in covered_tokens:
            stale.append(term_lower)

    total = len(glossary)
    stale_count = len(stale)
    stale_ratio = stale_count / total if total > 0 else 0.0

    if stale_ratio > _STALE_THRESHOLD and not no_stale:
        print(
            f"STALE WARNING [{lang}]: {stale_count}/{total} terms "
            f"({stale_ratio:.0%}) never bold-referenced in corpus/docs "
            f"(threshold {_STALE_THRESHOLD:.0%}):"
        )
        for term in sorted(stale):
            print(f"  STALE: {term}")

    return stale_count


def validate_coverage(
    glossary_dir: Path,
    corpus_root: Path,
    docs_root: Path,
    no_stale: bool,
) -> bool:
    """Run full coverage validation for IT and EN.

    Returns True if all tokens are covered (exit 0), False if any missing (exit 1).
    """
    it_glossary = load_glossary(glossary_dir / "it.yaml")
    en_glossary = load_glossary(glossary_dir / "en.yaml")

    if not it_glossary:
        print("ERROR: it.yaml not found or empty — run glossary bootstrap first.", file=sys.stderr)
        return False
    if not en_glossary:
        print("ERROR: en.yaml not found or empty — run glossary bootstrap first.", file=sys.stderr)
        return False

    all_ok = True
    it_covered: set[str] = set()
    en_covered: set[str] = set()

    for lang, glossary, fallback in [
        ("it", it_glossary, None),
        ("en", en_glossary, it_glossary),  # EN docs may reference IT terms
    ]:
        tokens = collect_tokens_for_lang(lang, corpus_root, docs_root)

        if not tokens:
            print(
                f"INFO [{lang}]: no bold tokens found in corpus/docs "
                f"(paths may not exist yet — skipping coverage check)."
            )
            # No tokens → no missing → no error; stale check still applies
            if lang == "it":
                it_covered = set()
            else:
                en_covered = set()
            continue

        missing, covered = check_coverage(lang, tokens, glossary, fallback)

        if lang == "it":
            it_covered = set(covered)
        else:
            en_covered = set(covered)

        if missing:
            print(
                f"COVERAGE ERROR [{lang}]: {len(missing)} bold token(s) not found "
                f"in glossary/{lang}.yaml:",
                file=sys.stderr,
            )
            for token in missing:
                print(f"  MISSING: {token}", file=sys.stderr)
            all_ok = False
        else:
            print(
                f"OK [{lang}]: {len(tokens)} bold token(s) checked — "
                f"all covered in glossary/{lang}.yaml"
                + (" (incl. cross-lang fallback)" if fallback else "")
            )

    # Stale check — warning only, never affects exit code
    check_stale(it_glossary, it_covered, "it", no_stale)
    check_stale(en_glossary, en_covered, "en", no_stale)

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate glossary coverage: every **bold** token in corpus/docs must "
            "exist in the corresponding language glossary YAML (D-32)."
        ),
        epilog=(
            "Exit 0: all tokens covered (STALE warnings are informational only).\n"
            "Exit 1: one or more bold tokens missing from the glossary."
        ),
    )
    parser.add_argument(
        "--glossary-dir",
        type=Path,
        default=_DEFAULT_GLOSSARY_DIR,
        help=f"Path to glossary directory with it.yaml and en.yaml (default: {_DEFAULT_GLOSSARY_DIR.relative_to(WORKSPACE_ROOT)})",
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=_DEFAULT_CORPUS_ROOT,
        help=f"Root directory of the synthetic corpus (default: {_DEFAULT_CORPUS_ROOT.relative_to(WORKSPACE_ROOT)})",
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=_DEFAULT_DOCS_ROOT,
        help=f"Root of the MkDocs docs directory (default: {_DEFAULT_DOCS_ROOT.relative_to(WORKSPACE_ROOT)})",
    )
    parser.add_argument(
        "--no-stale",
        action="store_true",
        help="Suppress STALE warnings output (useful in CI when only errors matter).",
    )
    args = parser.parse_args()

    glossary_dir = (
        args.glossary_dir
        if args.glossary_dir.is_absolute()
        else WORKSPACE_ROOT / args.glossary_dir
    )
    corpus_root = (
        args.corpus_root
        if args.corpus_root.is_absolute()
        else WORKSPACE_ROOT / args.corpus_root
    )
    docs_root = (
        args.docs_root
        if args.docs_root.is_absolute()
        else WORKSPACE_ROOT / args.docs_root
    )

    success = validate_coverage(
        glossary_dir=glossary_dir,
        corpus_root=corpus_root,
        docs_root=docs_root,
        no_stale=args.no_stale,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
