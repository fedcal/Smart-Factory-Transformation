# Phase 2: Domain Modeling & Synthetic Corpus — Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 26 new files (categorized in 7 buckets)
**Analogs found:** 22 / 26 (4 senza analog diretto in repo — derivati da RESEARCH.md)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/generate-glossary-pages.py` | utility / generator | file-I/O + transform | `scripts/sync-python-versions.py` | exact (shape pattern) |
| `scripts/generate-assumption-pages.py` | utility / generator | file-I/O + transform | `scripts/sync-python-versions.py` | exact (shape pattern) |
| `scripts/validate-glossary-coverage.py` | utility / validator | file-I/O + read-only | `scripts/validate-nx-graph.py` | exact |
| `scripts/validate-glossary-schema.py` | utility / validator | file-I/O + read-only | `scripts/validate-nx-graph.py` | exact |
| `scripts/validate-bilingual-mirror.py` | utility / validator | file-I/O + read-only | `scripts/validate-nx-graph.py` | exact |
| `scripts/validate-corpus-frontmatter.py` | utility / validator | file-I/O + read-only | `scripts/validate-nx-graph.py` | exact |
| `scripts/validate-corpus-pairing.py` | utility / validator | file-I/O + read-only | `scripts/validate-nx-graph.py` | exact |
| `scripts/validate-assumption-schema.py` | utility / validator | file-I/O + read-only | `scripts/validate-nx-graph.py` | exact |
| `scripts/validate-assumption-components.py` | utility / validator | file-I/O + read-only | `scripts/validate-nx-graph.py` | exact |
| `packages/sft-domain/src/sft_domain/glossary/__init__.py` | module / exports | n/a | `packages/sft-domain/src/sft_domain/__init__.py` | exact |
| `packages/sft-domain/src/sft_domain/glossary/models.py` | model | pure (Pydantic) | (no analog in repo) | RESEARCH-only |
| `packages/sft-domain/src/sft_domain/glossary/loader.py` | service / data-access | file-I/O + transform | (no analog in repo) | RESEARCH-only |
| `packages/sft-domain/src/sft_domain/glossary/{it,en}.yaml` | content / data | static | (no YAML in repo yet) | RESEARCH-only |
| `packages/sft-domain/src/sft_domain/schemas/glossary.schema.json` | schema / config | static | (no JSON Schema in repo yet) | RESEARCH-only |
| `packages/sft-domain/src/sft_domain/schemas/sop.schema.json` | schema / config | static | (no JSON Schema in repo yet) | RESEARCH-only |
| `packages/sft-domain/src/sft_domain/schemas/assumption.schema.json` | schema / config | static | (no JSON Schema in repo yet) | RESEARCH-only |
| `packages/sft-domain/tests/test_glossary_loader.py` | test | pure | (no pytest in repo yet) | RESEARCH-only |
| `packages/sft-domain/tests/test_glossary_schema.py` | test | pure | (no pytest in repo yet) | RESEARCH-only |
| `packages/sft-domain/tests/conftest.py` | test fixture | pure | (no conftest in repo yet) | RESEARCH-only |
| `packages/sft-domain/pyproject.toml` (MODIFY) | config | n/a | `packages/sft-domain/pyproject.toml` (current) | exact (extend) |
| `packages/sft-domain/project.json` (MODIFY) | Nx project config | n/a | `packages/sft-domain/project.json` (current) | exact (extend) |
| `simulators/synthetic-corpus/project.json` | Nx project config | n/a | `simulators/sim-textile/project.json` | exact (sibling) |
| `simulators/synthetic-corpus/README.md` | docs | static | `simulators/sim-textile/README.md` | exact (sibling) |
| `docs/mkdocs.yml` (MODIFY) | config | n/a | `docs/mkdocs.yml` (current — APPEND only) | exact (extend) |
| `Makefile` (MODIFY) | build config | n/a | `Makefile` (current — APPEND targets) | exact (extend) |
| `.github/workflows/ci.yml` (MODIFY) | CI config | n/a | `.github/workflows/ci.yml` (current — add step) | exact (extend) |
| `pyproject.toml` root (MODIFY) | config | n/a | `pyproject.toml` (current — extend dev deps) | exact (extend) |
| `docs/docs/{domain,sop,assumptions,glossary.md}` + EN mirror | content / authored | static | `docs/docs/getting-started.md`, `docs/docs/architecture/overview.md` | role-match |
| `simulators/synthetic-corpus/{it,en}/{loom,dyeing,spinning,quality}/*.md` | content / authored | static (frontmatter) | (no SOP analog in repo) | RESEARCH-only |
| `docs/assumptions/register.yaml` | content / data | static | (no YAML data in repo yet) | RESEARCH-only |

---

## Pattern Assignments

### `scripts/generate-glossary-pages.py` (utility, generator/transform)
### `scripts/generate-assumption-pages.py` (utility, generator/transform)

**Analog:** `scripts/sync-python-versions.py`

**Module docstring + usage + exit codes pattern** (lines 1-20):
```python
#!/usr/bin/env python3
"""
scripts/sync-python-versions.py

Synchronizes Python package versions from package.json to:
  - src/<module>/__version__.py
  - pyproject.toml (version field)

Used in the Changesets release workflow: after `changeset version` bumps
package.json files, this script propagates the version to the corresponding
Python __version__.py and pyproject.toml so that `sft_agents.__version__`
and `pyproject.toml` version fields stay in sync.

Usage:
    python3 scripts/sync-python-versions.py [--dry-run]

Exit codes:
    0 - All versions synced (or dry-run completed)
    1 - Error reading a file
"""
```
**Why copy:** RESEARCH.md § "Wave 0 Gaps" line 952 says verbatim *"Pattern dei nuovi script copia 1:1 scripts/sync-python-versions.py: argparse, --dry-run, idempotent, exit codes 0/1/2 documentati nel docstring."* For generators, extend exit codes: `0 = no change OR generated`, `1 = read/IO error`, `2 = (optional) drift detected in dry-run`.

**Workspace root resolution pattern** (line 27):
```python
WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent
```
**Why copy:** Canonical idiom in this repo for resolving paths relative to repo root from `scripts/`.

**Dry-run dual-branch pattern** (lines 71-79):
```python
if dry_run:
    current = py_version_file.read_text()
    if current == new_content:
        print(f"[dry-run] {py_version_file.relative_to(WORKSPACE_ROOT)}: already {version!r}")
    else:
        print(f"[dry-run] WOULD update {py_version_file.relative_to(WORKSPACE_ROOT)}: -> {version!r}")
else:
    py_version_file.write_text(new_content)
    print(f"Updated {py_version_file.relative_to(WORKSPACE_ROOT)} -> {version!r}")
```
**Why copy:** Idempotency check (current == new before write) is exactly what D-29 requires for generated `glossary.md` and `assumption pages` — running twice produces empty `git diff`. Always print `relative_to(WORKSPACE_ROOT)` for human-readable logs.

**Argparse + main + exit pattern** (lines 119-135):
```python
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync Python __version__.py and pyproject.toml from package.json (Changesets integration).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be changed without writing files.",
    )
    args = parser.parse_args()

    success = sync_versions(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```
**Why copy:** Standard CLI shape — keep `--dry-run` flag name, `description` field, single `success: bool` returned by core function, `sys.exit` mapping at end. Generator scripts should additionally accept `--output-dir` (default `docs/docs/glossary.md`).

**Error accumulation pattern** (lines 42-44, 109-113):
```python
updated: list[str] = []
skipped: list[str] = []
errors: list[str] = []
# ... loop ...
if errors:
    print("\nErrors:", file=sys.stderr)
    for err in errors:
        print(f"  {err}", file=sys.stderr)
    return False
```
**Why copy:** Don't fail-fast on first error — accumulate all errors, emit grouped report to stderr, then return False. Phase 2 validators must list ALL missing glossary terms / mismatched mirrors, not just the first one.

---

### `scripts/validate-glossary-coverage.py` (utility, validator)
### `scripts/validate-glossary-schema.py` (utility, validator)
### `scripts/validate-bilingual-mirror.py` (utility, validator)
### `scripts/validate-corpus-frontmatter.py` (utility, validator)
### `scripts/validate-corpus-pairing.py` (utility, validator)
### `scripts/validate-assumption-schema.py` (utility, validator)
### `scripts/validate-assumption-components.py` (utility, validator)

**Analog:** `scripts/validate-nx-graph.py`

**Module docstring + exit codes pattern** (lines 1-15):
```python
#!/usr/bin/env python3
"""
scripts/validate-nx-graph.py

Validates that all required Python->TypeScript dependency edges are present
in the Nx dep graph JSON. Run after `nx graph --file=tmp/graph.json`.

Usage:
    nx graph --file=tmp/graph.json
    python3 scripts/validate-nx-graph.py [--graph-file PATH]

Exit codes:
    0 - All required edges are present
    1 - One or more required edges are missing
"""
```
**Why copy:** Same "validator" shape as the seven new Phase 2 validators — purpose, usage, explicit exit codes documented up front.

**Missing-items accumulation + actionable error pattern** (lines 49-62):
```python
missing: list[str] = []
for source, target in REQUIRED_EDGES:
    targets = [d["target"] for d in dependencies.get(source, [])]
    if target not in targets:
        missing.append(f"  MISSING: {source} -> {target}")

if missing:
    print("Dependency graph validation FAILED. Missing edges:")
    for m in missing:
        print(m)
    print(
        "\nFix: add the target to 'implicitDependencies' in the source project's project.json"
    )
    return False
```
**Why copy:** Two-part error reporting — (1) list every offending item, (2) ALWAYS suggest fix ("Fix: ..."). For `validate-glossary-coverage` the fix message is "Fix: add term to packages/sft-domain/src/sft_domain/glossary/{lang}.yaml or remove **bold** from source"; for `validate-bilingual-mirror` it's "Fix: create docs/docs/en/{path} with matching H1/H2".

**Argparse Path + default + main pattern** (lines 70-85):
```python
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Nx dep graph edges for Python->TypeScript links.",
        epilog="Run 'nx graph --file=tmp/graph.json' first.",
    )
    parser.add_argument(
        "--graph-file",
        type=Path,
        default=Path("tmp/graph.json"),
        help="Path to the Nx graph JSON file (default: tmp/graph.json)",
    )
    args = parser.parse_args()

    success = validate(args.graph_file)
    sys.exit(0 if success else 1)
```
**Why copy:** Use `type=Path` for path args (not `str`), provide sensible default rooted at workspace, use `epilog` for prerequisite hints. For Phase 2 validators, defaults are like `Path("docs/docs")`, `Path("packages/sft-domain/src/sft_domain/glossary")`.

**Success path with summary print** (lines 64-67):
```python
print(f"OK: All {len(REQUIRED_EDGES)} required dependency edges are present.")
for source, target in REQUIRED_EDGES:
    print(f"  {source} -> {target}")
return True
```
**Why copy:** On success, print a confirmation summary (count + list). CI logs need positive confirmation, not silence.

---

### `packages/sft-domain/src/sft_domain/glossary/__init__.py` (module, exports)

**Analog:** `packages/sft-domain/src/sft_domain/__init__.py`

**Full file** (lines 1-3):
```python
"""Textile domain models: defect taxonomy, asset registry, IT/EN glossary"""

__version__ = "0.1.0"
```
**Pattern to apply:**
```python
"""Glossary loader and Term model for IT/EN textile + agentic terminology."""

from sft_domain.glossary.loader import load_terms, load_terms_dict
from sft_domain.glossary.models import Category, Term

__all__ = ["Category", "Term", "load_terms", "load_terms_dict"]
```
**Why copy:** Module docstring is single-line description (matches package `__init__`); explicit `__all__` keeps the public API minimal. Do NOT add `__version__` in submodule — version lives only in top-level `sft_domain/__version__.py`.

---

### `packages/sft-domain/src/sft_domain/glossary/models.py` (model, pure Pydantic)
### `packages/sft-domain/src/sft_domain/glossary/loader.py` (service, file-I/O)

**Analog:** No existing Pydantic model in repo. Use RESEARCH.md § "Pattern 1: Pydantic Glossary Loader" (lines 341-400) as source-of-truth template.

**Style constraints inherited from repo:**
- Python 3.12 syntax (`list[str]`, `str | None`, `Literal["it", "en"]`) — `pyproject.toml` line 4 fixes `requires-python = ">=3.12,<3.13"`.
- Ruff lint rules `["E", "F", "I", "B", "UP", "N"]`, line-length 120 (root `pyproject.toml` lines 43-50).
- Mypy strict on `packages/sft-domain/src` (root `pyproject.toml` lines 52-59) → all functions need type hints, return types, no `Any`.
- YAML loading MUST use `yaml.safe_load` (RESEARCH.md Pitfall 3 + security section line 968).
- `model_config = {"frozen": True, "extra": "forbid"}` per global immutability rule (coding-style.md).
- Use `functools.lru_cache(maxsize=2)` on the loader (one slot per language).

---

### `packages/sft-domain/tests/conftest.py` (test fixture)
### `packages/sft-domain/tests/test_glossary_loader.py` (test)
### `packages/sft-domain/tests/test_glossary_schema.py` (test)

**Analog:** No existing pytest tests or `conftest.py` in repo. Phase 2 is the FIRST package to introduce pytest under `packages/sft-domain/tests/`.

**Apply repo-level conventions from `pyproject.toml`** (lines 61-63):
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```
**Why copy:** Root pytest config already sets `asyncio_mode = "auto"` — tests can use `async def` freely. `testpaths = ["tests"]` is workspace-relative — `packages/sft-domain/tests/` works because Nx runs `uv run pytest` with `cwd: packages/sft-domain` (see project.json analog below).

**Nx test target invocation pattern from `packages/sft-domain/project.json`** (lines 7-13):
```json
"test": {
  "executor": "@nxlv/python:run-commands",
  "options": {
    "command": "uv run pytest",
    "cwd": "packages/sft-domain"
  }
}
```
**Why copy:** The `test` target is ALREADY defined — no project.json change needed for tests. Tests just need to exist under `packages/sft-domain/tests/` and they'll be picked up by `nx affected --target=test`.

**Dependency declaration** — pytest must be available. Root `pyproject.toml` lines 34-41:
```toml
[dependency-groups]
dev = [
  "pre-commit>=4.6",
  "pytest>=8.0",
  "pytest-asyncio>=0.24",
  "mypy>=1.10",
  "ruff>=0.11",
]
```
Already includes `pytest>=8.0` — nothing to add for test framework itself.

---

### `packages/sft-domain/pyproject.toml` (MODIFY — add runtime deps)

**Analog:** `packages/sft-domain/pyproject.toml` (current state).

**Current full file:**
```toml
[project]
name = "sft-domain"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
description = "Textile domain models: defect taxonomy, asset registry, IT/EN glossary"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sft_domain"]
```
**Modification (extend `dependencies = []`):**
```toml
dependencies = [
    "pydantic>=2.10,<3",
    "pyyaml>=6.0,<7",
]
```
**Why copy:** Existing layout — hatchling backend, src-layout, version pinned by Changesets workflow via `sync-python-versions.py`. Keep `dependencies = []` becoming a list (NOT `[tool.uv]` dev — these are runtime). Pin both to compatible-release bounds: matches existing repo convention (no exact pins, no wildcard upper bound).

---

### `simulators/synthetic-corpus/project.json` (Nx project config)
### `simulators/synthetic-corpus/README.md` (docs)

**Analog:** `simulators/sim-textile/project.json` + `simulators/sim-textile/README.md` (sibling layout).

**project.json full template** (sim-textile lines 1-25):
```json
{
  "name": "sim-textile",
  "$schema": "../../node_modules/nx/schemas/project-schema.json",
  "projectType": "application",
  "sourceRoot": "simulators/sim-textile/src",
  "targets": {
    "test": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "command": "uv run pytest",
        "cwd": "simulators/sim-textile"
      }
    },
    "lint": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "command": "uv run ruff check src",
        "cwd": "simulators/sim-textile"
      }
    }
  },
  "implicitDependencies": [
    "sft-contracts"
  ]
}
```
**Adaptation for synthetic-corpus:**
```json
{
  "name": "synthetic-corpus",
  "$schema": "../../node_modules/nx/schemas/project-schema.json",
  "projectType": "library",
  "sourceRoot": "simulators/synthetic-corpus",
  "targets": {
    "validate-frontmatter": {
      "executor": "nx:run-commands",
      "options": {
        "command": "python3 scripts/validate-corpus-frontmatter.py --corpus-dir simulators/synthetic-corpus"
      }
    },
    "validate-pairing": {
      "executor": "nx:run-commands",
      "options": {
        "command": "python3 scripts/validate-corpus-pairing.py --corpus-dir simulators/synthetic-corpus"
      }
    }
  },
  "implicitDependencies": ["sft-domain"]
}
```
**Why copy:** Same `$schema` ref (`../../node_modules/...`), same `executor` family. Differences justified:
- `projectType: library` (corpus is consumed by Phase 5 retrieval, not run as app)
- `executor: nx:run-commands` (built-in Nx) instead of `@nxlv/python:run-commands` — no Python `src/`, only Markdown files
- `implicitDependencies: ["sft-domain"]` because `validate-corpus-frontmatter` resolves schema from `packages/sft-domain/src/sft_domain/schemas/sop.schema.json`
- NO `pyproject.toml` needed if no Python package — Claude's discretion in CONTEXT.md line 432 confirms `pyproject.toml` is optional

**README.md full template** (sim-textile lines 1-5):
```markdown
# sim-textile

Textile line simulator: loom, spinning, warping machine event generation (Fase 3)

> Skeleton populated in Phase 2.
```
**Adaptation:** Title + 1-line description + scope callout. Synthetic-corpus README must additionally include: (a) directory layout (`it/{loom,dyeing,spinning,quality}/`, `en/...`), (b) SOP frontmatter schema reference (link to `packages/sft-domain/src/sft_domain/schemas/sop.schema.json`), (c) authoring guidelines (D-25 hybrid workflow + D-28 style), (d) Nx target invocation (`npx nx run synthetic-corpus:validate-frontmatter`).

---

### `packages/sft-domain/project.json` (MODIFY — add validation targets)

**Analog:** `packages/sft-domain/project.json` (current state).

**Current targets block** (lines 6-21):
```json
"targets": {
  "test": {
    "executor": "@nxlv/python:run-commands",
    "options": {
      "command": "uv run pytest",
      "cwd": "packages/sft-domain"
    }
  },
  "lint": {
    "executor": "@nxlv/python:run-commands",
    "options": {
      "command": "uv run ruff check src",
      "cwd": "packages/sft-domain"
    }
  }
}
```
**Modification (APPEND siblings inside `targets`):**
```json
"validate-glossary-schema": {
  "executor": "nx:run-commands",
  "options": { "command": "python3 scripts/validate-glossary-schema.py" }
},
"validate-glossary-coverage": {
  "executor": "nx:run-commands",
  "options": { "command": "python3 scripts/validate-glossary-coverage.py" }
},
"validate-assumption-schema": {
  "executor": "nx:run-commands",
  "options": { "command": "python3 scripts/validate-assumption-schema.py" }
},
"validate-assumption-components": {
  "executor": "nx:run-commands",
  "options": { "command": "python3 scripts/validate-assumption-components.py" }
},
"generate-glossary": {
  "executor": "nx:run-commands",
  "options": { "command": "python3 scripts/generate-glossary-pages.py" }
},
"generate-assumptions": {
  "executor": "nx:run-commands",
  "options": { "command": "python3 scripts/generate-assumption-pages.py" }
}
```
**Why copy:** Keep `@nxlv/python:run-commands` for targets that need `uv run` (Python pkg-local commands). Use `nx:run-commands` for scripts under `scripts/` that are workspace-level (no `cwd` override needed — defaults to repo root).

---

### `docs/mkdocs.yml` (MODIFY — APPEND nav entries)

**Analog:** `docs/mkdocs.yml` (current state — full file is 94 lines).

**Current nav block** (lines 88-94):
```yaml
nav:
  - Home: index.md
  - Iniziare: getting-started.md
  - Architettura:
    - Overview: architecture/overview.md
  - Contributing: contributing/index.md
```

**Current i18n nav_translations block** (lines 55-59):
```yaml
nav_translations:
  Architettura: Architecture
  Iniziare: Getting Started
  Contributing: Contributing
```

**Modification — APPEND only (do NOT reorder Phase 1 entries, per Claude's discretion in CONTEXT.md line 425):**
```yaml
nav:
  - Home: index.md
  - Iniziare: getting-started.md
  - Architettura:
    - Overview: architecture/overview.md
  - Dominio:
    - Indice: domain/index.md
    - Processi:
      - Tessitura: domain/processes/weaving.md
      - Filatura: domain/processes/spinning.md
      - Orditura: domain/processes/warping.md
      - Tintoria: domain/processes/dyeing.md
      - Finissaggio: domain/processes/finishing.md
    - Ruoli:
      - Operatore: domain/roles/operator.md
      - Tecnico: domain/roles/technician.md
      - Quality Manager: domain/roles/quality-manager.md
      - Caposquadra: domain/roles/shift-supervisor.md
  - Procedure (SOP): sop/index.md
  - Assumption Register: assumptions/index.md
  - Glossario: glossary.md
  - Contributing: contributing/index.md
```
**And extend `nav_translations`:**
```yaml
nav_translations:
  Architettura: Architecture
  Iniziare: Getting Started
  Contributing: Contributing
  Dominio: Domain
  Indice: Index
  Processi: Processes
  Ruoli: Roles
  Tessitura: Weaving
  Filatura: Spinning
  Orditura: Warping
  Tintoria: Dyeing
  Finissaggio: Finishing
  Operatore: Operator
  Tecnico: Technician
  Caposquadra: Shift Supervisor
  Procedure (SOP): Procedures (SOP)
  Glossario: Glossary
```
**Why copy:** Existing i18n shape uses IT nav keys + EN translations table. Quality Manager stays as-is (already English in original). MkDocs strict mode (Makefile line 82) will catch missing files at build time.

**material-tags plugin** — required by D-30 for glossary category tag filtering. Add to `plugins` block (currently lines 41-59):
```yaml
plugins:
  - search
  - tags  # NEW for D-30 glossary category filtering
  - i18n: ...  # existing
```
Verify `tags` is bundled with `mkdocs-material==9.7.6` (already in `docs/requirements.txt` line 1).

---

### `Makefile` (MODIFY — APPEND targets)

**Analog:** `Makefile` (current state, line 80-86 for `docs` and `docs-serve`).

**Current `docs` target pattern** (lines 80-86):
```makefile
# Build del sito MkDocs in strict mode (fallisce su broken link o warning critici)
# Prerequisito: mkdocs installato — cd docs && pip install -r requirements.txt
docs:
	@command -v mkdocs >/dev/null || (echo "mkdocs non trovato: cd docs && pip install -r requirements.txt" && exit 1)
	cd docs && mkdocs build --strict

# Preview locale con hot-reload su http://127.0.0.1:8000
docs-serve:
	cd docs && mkdocs serve -a 127.0.0.1:8000
```

**Modification — APPEND new section (after `## Docs`, before `## Demo`):**
```makefile
## Content validation & generation (Phase 2)
# -----------------------------------------------------------------------

# Generate IT+EN glossary pages from YAML source (idempotente)
generate-glossary:
	python3 scripts/generate-glossary-pages.py

# Generate assumption register index + per-id pages from YAML (idempotente)
generate-assumptions:
	python3 scripts/generate-assumption-pages.py

# Validate glossary coverage: every **bold** in docs/SOPs must exist in glossary
validate-glossary:
	python3 scripts/validate-glossary-schema.py
	python3 scripts/validate-glossary-coverage.py

# Validate SOP frontmatter + bilingual pairing
validate-corpus:
	python3 scripts/validate-corpus-frontmatter.py --corpus-dir simulators/synthetic-corpus
	python3 scripts/validate-corpus-pairing.py --corpus-dir simulators/synthetic-corpus
	python3 scripts/validate-bilingual-mirror.py --docs-dir docs/docs

# Validate assumption schema + affected_components inventory
validate-assumptions:
	python3 scripts/validate-assumption-schema.py
	python3 scripts/validate-assumption-components.py

# Run every Phase 2 validator (CI entry point)
validate-all: validate-glossary validate-corpus validate-assumptions
```
**Why copy:** Existing Makefile uses Italian comments above each target (e.g., "Esegue tutti i test...", "Build del sito MkDocs...") — match that voice. Use `## Section name` header comments (lines 18, 45, 56, 75, 94 etc.). Add new targets to `.PHONY` declaration on line 16:
```makefile
.PHONY: up up-gpu up-core down reset test lint format docs docs-serve demo sbom license-scan helm-test ps logs \
        generate-glossary generate-assumptions validate-glossary validate-corpus validate-assumptions validate-all
```

---

### `.github/workflows/ci.yml` (MODIFY — add validation step)

**Analog:** `.github/workflows/ci.yml` (current state).

**Existing inline-python-call pattern** (lines 75-79):
```yaml
- name: Validate Nx dependency graph (Python<->TS edges)
  run: |
    mkdir -p tmp
    npx nx graph --file=tmp/graph.json
    python3 scripts/validate-nx-graph.py
```
**Why copy:** This is the canonical "run an inline Python validator" step shape. Multi-line `run: |` block; name uses descriptive sentence-case; `python3` (not `python`) for Linux runner.

**Modification — INSERT new step between "Validate Nx dependency graph" (line 75-79) and "Nx Affected Lint" (line 81-82):**
```yaml
- name: Validate content (Phase 2 — glossary, corpus, assumptions)
  run: |
    python3 scripts/validate-glossary-schema.py
    python3 scripts/validate-glossary-coverage.py
    python3 scripts/validate-corpus-frontmatter.py --corpus-dir simulators/synthetic-corpus
    python3 scripts/validate-corpus-pairing.py --corpus-dir simulators/synthetic-corpus
    python3 scripts/validate-bilingual-mirror.py --docs-dir docs/docs
    python3 scripts/validate-assumption-schema.py
    python3 scripts/validate-assumption-components.py
```
**Why copy:** Same step shape as existing `Validate Nx dependency graph`. Step is workspace-level (not Nx-affected) because content validators must run on EVERY PR — a SOP edit in `simulators/synthetic-corpus` doesn't naturally affect `sft-domain` but still needs frontmatter validation. (Alternative: rely on `Nx Affected Lint` line 82 picking up the per-project targets — but explicit step is safer for content drift detection and matches Phase 1 pattern.)

**Setup pre-existing** — no need to change Setup Python (line 33-37), Install uv (line 38-43), or Install Python dependencies (line 62-63) — they already install `sft-domain` via `uv sync --all-packages`, so `pydantic`, `pyyaml`, `python-frontmatter` ship with the venv once `pyproject.toml` is updated.

---

### `pyproject.toml` (root, MODIFY — extend dev deps)

**Analog:** `pyproject.toml` (current state).

**Current dev deps block** (lines 34-41):
```toml
[dependency-groups]
dev = [
  "pre-commit>=4.6",
  "pytest>=8.0",
  "pytest-asyncio>=0.24",
  "mypy>=1.10",
  "ruff>=0.11",
]
```
**Modification (APPEND inside `dev`):**
```toml
[dependency-groups]
dev = [
  "pre-commit>=4.6",
  "pytest>=8.0",
  "pytest-asyncio>=0.24",
  "mypy>=1.10",
  "ruff>=0.11",
  "jsonschema>=4.23,<5",
  "python-frontmatter>=1.1,<2",
  "pyyaml>=6.0,<7",
]
```
**Why copy:** Existing dev deps use `>=X.Y` compatible-release bound, no upper cap. The new content-validation deps (`jsonschema`, `python-frontmatter`, `pyyaml`) need upper bounds because they're more security-sensitive (D-32 supply-chain). Note `pyyaml` is ALSO a runtime dep of `sft-domain` — listing it in root dev is fine (uv resolves to single version via lockfile).

**Existing `[tool.mypy]` files block** (lines 52-59) already covers `packages/sft-domain/src` — new `glossary/` and `schemas/` submodules will be type-checked automatically. No change needed.

---

### Domain pages: `docs/docs/domain/**.md` + `docs/docs/en/domain/**.md` (content)

**Analog:** `docs/docs/architecture/overview.md` for tone + Mermaid usage; `docs/docs/getting-started.md` for admonition + bilingual mirror precedent.

**Italian voice + admonition pattern** (`overview.md` lines 1-6):
```markdown
# Architettura: Overview

!!! info "Dettagli in espansione"
    Questa pagina mostra l'architettura ad alto livello del sistema. I dettagli
    per ogni layer verranno documentati nelle fasi successive.

## Schema ad alto livello
```
**Why copy:** Standard Italian voice ("Questa pagina ...", "I dettagli ..."). Use `!!! info` / `!!! note` / `!!! warning` MkDocs admonitions (enabled in `mkdocs.yml` line 62: `markdown_extensions: - admonition`). D-23 specifically requires `!!! note "Mantis context"` callouts on every process/role page.

**Mermaid `flowchart` pattern** (`overview.md` lines 9-30):
```markdown
\`\`\`mermaid
graph TD
    DEV[Developer / Operatore]
    ...
    subgraph DEV_STACK["Stack Dev (Docker Compose)"]
        DC_CORE[Core\nPostgres + TimescaleDB + Qdrant]
        ...
\`\`\`
```
**Why copy:** Mermaid is enabled in mkdocs.yml (lines 69-73 — pymdownx.superfences custom_fence). Use `\n` for in-node line breaks. D-22 mandates `flowchart LR` for process diagrams, max 8 nodes. Add `accTitle:` and `accDescr:` per RESEARCH.md Pitfall 2 for accessibility.

**Bilingual mirror precedent** — `docs/docs/getting-started.md` has counterpart `docs/docs/en/getting-started.md`; the EN version preserves the same H2 structure ("Prerequisites", "Starting the dev stack", etc.). The `validate-bilingual-mirror.py` script (D-24) enforces this — H1 + first 5 H2 must match across IT/EN (per Claude's discretion in CONTEXT.md line 429-430).

---

## Shared Patterns

### Shebang + Module Docstring + Exit Codes
**Source:** `scripts/sync-python-versions.py` (lines 1-20), `scripts/validate-nx-graph.py` (lines 1-15)
**Apply to:** All 9 new Python scripts under `scripts/`
```python
#!/usr/bin/env python3
"""
scripts/<name>.py

<one-sentence purpose>

<2-3 sentence what+why>

Usage:
    python3 scripts/<name>.py [--flag]

Exit codes:
    0 - Success / dry-run completed / no drift
    1 - I/O error or validation failed
    2 - (optional) Drift detected (generators only)
"""
```

### `pathlib.Path` over string concatenation
**Source:** `scripts/sync-python-versions.py` line 27, `scripts/validate-nx-graph.py` line 19
**Apply to:** All new scripts (mitigates Path traversal — RESEARCH.md security section line 968)
```python
import pathlib
WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent
# Then: WORKSPACE_ROOT / "packages" / "sft-domain" / ...
```
Never use `os.path.join` or f-string concatenation for paths.

### Argparse + `success: bool` + `sys.exit` pattern
**Source:** `scripts/sync-python-versions.py` lines 119-131
**Apply to:** All 9 new Python scripts
```python
def main() -> None:
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--dry-run", action="store_true", help="...")
    args = parser.parse_args()
    success = <core_function>(...)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

### YAML safe load (security)
**Source:** RESEARCH.md Pitfall 3 (line 719) + Threat patterns (line 975)
**Apply to:** `glossary/loader.py`, all `scripts/validate-*.py` and `scripts/generate-*.py` that read YAML
```python
import yaml
with path.open() as f:
    data = yaml.safe_load(f)  # NEVER yaml.load(f) — CWE-502 / Bandit B506
```

### Stderr for errors, stdout for results
**Source:** `scripts/sync-python-versions.py` lines 39, 109-112; `scripts/validate-nx-graph.py` lines 40-41, 56-58
**Apply to:** All 9 new Python scripts
```python
print(f"ERROR: ...", file=sys.stderr)   # all errors
print(f"OK: ...")                        # success messages
print(f"  MISSING: {item}")              # validation results (stdout — parsed by CI)
```

### Repo-relative path printing
**Source:** `scripts/sync-python-versions.py` line 76, 79
**Apply to:** All new scripts that report file locations
```python
print(f"{path.relative_to(WORKSPACE_ROOT)}: ...")
```
Never print absolute paths in CI output (noise + leaks runner filesystem layout).

### Nx target for workspace-level scripts: `nx:run-commands`
**Source:** (no analog — first use in Phase 2; contrast with `@nxlv/python:run-commands` in `simulators/sim-textile/project.json` line 8)
**Apply to:** New targets in `packages/sft-domain/project.json` and `simulators/synthetic-corpus/project.json` that invoke `python3 scripts/<name>.py`
Use built-in `nx:run-commands` (no extra plugin needed). Use `@nxlv/python:run-commands` only when the command needs `uv run` from a package cwd.

### Conventional Commit scope: `feat(02-NN-slug):`
**Source:** CONTEXT.md line 53 + Phase 1 commit history (e.g., `feat(01-07-mkdocs): ...`)
**Apply to:** Every commit in Phase 2
- `feat(02-NN-slug):` for new features
- `docs(02-NN-slug):` for content (SOPs, domain pages, glossary)
- `chore(02-NN-slug):` for tooling
- Scope numbering matches plan files (`02-PLAN-NN-slug-PLAN.md`)

### Immutability for Pydantic models
**Source:** User global rules (`~/.claude/rules/common/coding-style.md`) + RESEARCH.md Pattern 1 line 365
**Apply to:** All Pydantic models in `sft_domain/glossary/models.py`, `sft_domain/assumptions/models.py` (if added)
```python
class Term(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
```
`frozen=True` → immutable (no mutation). `extra="forbid"` → schema strictness (matches "Never trust external data" rule).

---

## No Analog Found

Files with no close match in the Phase 1 codebase (planner should use RESEARCH.md patterns directly):

| File | Role | Reason | Fallback Source |
|------|------|--------|-----------------|
| `packages/sft-domain/src/sft_domain/glossary/models.py` | Pydantic model | No Pydantic model exists in repo yet | RESEARCH.md § Pattern 1 (lines 347-401) |
| `packages/sft-domain/src/sft_domain/glossary/loader.py` | YAML loader with `lru_cache` | No data loader exists in repo yet | RESEARCH.md § Pattern 1 (lines 374-400) |
| `packages/sft-domain/src/sft_domain/glossary/{it,en}.yaml` | YAML data | No content YAML in repo yet | D-29 schema definition (CONTEXT.md lines 227-240) |
| `packages/sft-domain/src/sft_domain/schemas/*.schema.json` | JSON Schema Draft 2020-12 | No JSON Schema in repo yet | RESEARCH.md § Pattern 3 (lines 464-520) + § Pattern 1 (Pydantic↔JSON Schema export) |
| `packages/sft-domain/tests/*.py` + `conftest.py` | pytest tests | No pytest tests in repo yet (root config exists but unused) | RESEARCH.md § Validation Architecture (lines 885-922) |
| `simulators/synthetic-corpus/{it,en}/**/SOP-*.md` | Frontmatter + sectioned SOP | No SOP analog in repo | D-26 schema (CONTEXT.md lines 137-181) |
| `docs/assumptions/register.yaml` | Assumption data YAML | No data YAML in repo yet | D-33 schema (CONTEXT.md lines 313-325) |

For all "no analog" files, the planner MUST reference RESEARCH.md by section + line number in the plan's `## Pattern Source` block, and treat the Phase 2 first implementation as the new canonical analog for Phase 3+.

---

## Metadata

**Analog search scope:**
- `/scripts/` (2 files scanned)
- `/packages/sft-domain/` (6 files scanned — full subtree)
- `/simulators/sim-textile/` (4 files scanned — full subtree)
- `/docs/` (mkdocs.yml + 4 markdown samples scanned)
- `/.github/workflows/ci.yml` (full file scanned)
- `/Makefile`, root `/pyproject.toml`, root `/package.json` (full files scanned)
- `/tests/` (verified empty of pytest — only license fixture present)

**Files scanned:** 18 actual repo files
**Pattern extraction date:** 2026-05-17
**Phase 1 dependency:** All analogs come from Phase 1 deliverables (commit `8c2cc5d` and earlier) — Phase 1 marked complete in `01-VERIFICATION.md`.
