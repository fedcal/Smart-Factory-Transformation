# Phase 3: IT/OT Simulation Layer — Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 38 (new + modified)
**Analogs found:** 32 / 38 (6 files = greenfield, no analog → use RESEARCH.md patterns)

> Tutti i path sono relativi a `/media/federicocalo/D1/prj/Smart Factory Transformation`.
> Tutti gli excerpts riportano file path + line numbers concreti dai file Phase 1 + Phase 2 già committati.

---

## File Classification

### Wave 1 — Foundation packages (parallelizable)

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `packages/sft-assets/pyproject.toml` | config | n/a | `packages/sft-domain/pyproject.toml` | exact |
| `packages/sft-assets/project.json` | config | n/a | `packages/sft-domain/project.json` | exact |
| `packages/sft-assets/package.json` | config | n/a | `packages/sft-domain/package.json` | exact |
| `packages/sft-assets/src/sft_assets/__init__.py` | barrel | n/a | `packages/sft-domain/src/sft_domain/glossary/__init__.py` | exact |
| `packages/sft-assets/src/sft_assets/models.py` | model (Pydantic) | request-response | `packages/sft-domain/src/sft_domain/glossary/_models.py` | exact |
| `packages/sft-assets/src/sft_assets/loader.py` | loader (YAML→Pydantic) | file-I/O | `packages/sft-domain/src/sft_domain/glossary/_loader.py` | exact |
| `packages/sft-assets/src/sft_assets/registry.yaml` | data (seed) | n/a | `packages/sft-domain/src/sft_domain/glossary/it.yaml` | role-match |
| `packages/sft-assets/src/sft_assets/schemas/asset.schema.json` | schema (JSON Draft 2020-12) | n/a | `packages/sft-domain/src/sft_domain/schemas/glossary.schema.json` | exact |
| `packages/sft-assets/tests/conftest.py` | test (fixture) | n/a | `packages/sft-domain/tests/conftest.py` | exact |
| `packages/sft-assets/tests/test_models.py` | test (unit) | n/a | `packages/sft-domain/tests/test_glossary_models.py` | exact |
| `packages/sft-assets/tests/test_loader.py` | test (unit) | n/a | `packages/sft-domain/tests/test_glossary_loader.py` | exact |
| `packages/sft-assets/tests/test_registry_validation.py` | test (schema) | n/a | `packages/sft-domain/tests/test_glossary_schema.py` | exact |
| `packages/sft-tools/pyproject.toml` | config | n/a | `packages/sft-domain/pyproject.toml` | role-match |
| `packages/sft-tools/project.json` | config | n/a | `packages/sft-domain/project.json` | exact |
| `packages/sft-tools/src/sft_tools/__init__.py` | barrel | n/a | `packages/sft-domain/src/sft_domain/glossary/__init__.py` | exact |
| `packages/sft-tools/src/sft_tools/replay/{cmapss,uci}.py` | tool (LangChain BaseTool) | request-response | **no analog** (greenfield) | none — use RESEARCH §Pattern 5 |
| `packages/sft-tools/src/sft_tools/replay/models.py` | model (Pydantic) | request-response | `packages/sft-domain/src/sft_domain/glossary/_models.py` | role-match |
| `packages/sft-tools/src/sft_tools/timescale/query.py` | tool (DB query) | request-response | **no analog** | none — use RESEARCH §Pattern 4 (asyncpg) |
| `packages/sft-tools/tests/*` | test | n/a | `packages/sft-domain/tests/test_glossary_loader.py` | role-match |

### Wave 2 — Service implementation (parallel)

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `simulators/sim-textile/pyproject.toml` (modify) | config | n/a | `packages/sft-domain/pyproject.toml` + existing scaffold | exact |
| `simulators/sim-textile/src/sim_textile/main.py` | entry (asyncio) | event-driven/streaming | **no analog** | none — use RESEARCH §Pattern 1 |
| `simulators/sim-textile/src/sim_textile/server.py` | service (asyncua server) | streaming | **no analog** | none — use RESEARCH §Pattern 1 |
| `simulators/sim-textile/src/sim_textile/emitter.py` | service (per-asset task) | streaming | **no analog** | none — use RESEARCH §Pattern 2 |
| `simulators/sim-textile/src/sim_textile/models.py` | model (Pydantic) | request-response | `packages/sft-domain/src/sft_domain/glossary/_models.py` | exact |
| `simulators/sim-textile/src/sim_textile/faults/*.py` | utility (pure functions) | transform | **no analog** | none — use RESEARCH §Pattern 2 |
| `simulators/sim-textile/src/sim_textile/cli.py` | cli | request-response | `scripts/sync-python-versions.py` | role-match |
| `simulators/sim-textile/profiles/*.yaml` | data (config) | n/a | `packages/sft-domain/src/sft_domain/glossary/it.yaml` | role-match |
| `simulators/sim-textile/tests/conftest.py` | test (fixture) | n/a | `packages/sft-domain/tests/conftest.py` | exact |
| `simulators/sim-textile/tests/test_profile_validation.py` | test (schema) | n/a | `packages/sft-domain/tests/test_glossary_schema.py` | role-match |
| `services/ot-bridge/pyproject.toml` (modify) | config | n/a | existing scaffold + `packages/sft-domain/pyproject.toml` | exact |
| `services/ot-bridge/src/svc_ot_bridge/main.py` | entry (asyncio) | event-driven | **no analog** | none — use RESEARCH §Pattern 3+4 |
| `services/ot-bridge/src/svc_ot_bridge/opcua_client.py` | service (asyncua client subscribe) | streaming | **no analog** | none — use RESEARCH §Pattern 1 |
| `services/ot-bridge/src/svc_ot_bridge/normalizer.py` | service (pure transform) | transform | `packages/sft-domain/src/sft_domain/glossary/_models.py` (pattern: frozen Pydantic) | role-match |
| `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py` | service (NATS pub) | pub-sub | **no analog** | none — use RESEARCH §Pattern 3 |
| `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` | service (asyncpg batch) | batch | **no analog** | none — use RESEARCH §Pattern 4 |
| `services/ot-bridge/src/svc_ot_bridge/models.py` | model (Pydantic) | request-response | `packages/sft-domain/src/sft_domain/glossary/_models.py` | exact |
| `infra/migrations/timescale/001_create_sensor_events.sql` | migration | n/a | **no analog** | none — use RESEARCH §Code Examples "TimescaleDB migration SQL" |
| `scripts/timescale-migrate.py` | script (idempotent migration runner) | file-I/O | `scripts/sync-python-versions.py` | exact (idempotent + --dry-run pattern) |
| `scripts/nats-bootstrap-streams.py` | script (idempotent NATS setup) | request-response | `scripts/sync-python-versions.py` | role-match (idempotent + --dry-run pattern) |
| `scripts/download-replay-datasets.py` | script (download + SHA256) | file-I/O | `scripts/sync-python-versions.py` | role-match |

### Wave 3 — Integration + tests

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `infra/compose/sim.yml` (modify) | config | n/a | `infra/compose/sim.yml` (existing) + `infra/compose/core.yml` | exact (self-extending) |
| `tests/integration/test_data_diode.py` | test (integration) | n/a | **no analog** | none — pattern in RESEARCH.md §Code Examples "pytest data-diode" |
| `tests/integration/test_e2e_sim_to_timescale.py` | test (integration) | n/a | **no analog** | none — testcontainers pattern in RESEARCH |
| `tests/load/harness.py` | test infra (asyncio publisher) | streaming | **no analog** | none — bespoke (D-48) |
| `tests/load/test_ingestion_smoke.py` | test (load smoke) | n/a | `tests/test_corpus_inventory.py` (pytest layout) | role-match |
| `tests/load/test_ingestion_throughput.py` | test (full load) | n/a | `tests/test_corpus_inventory.py` | role-match |
| `tests/conftest.py` (modify) | test (fixture) | n/a | `tests/conftest.py` (existing) | exact (extension) |

### Wave 4 — Docs + CI

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docs/docs/it-ot/ingest-schema.md` | docs (IT) | n/a | autogen pattern via `scripts/generate-glossary-pages.py` (idempotent) | role-match |
| `docs/docs/en/it-ot/ingest-schema.md` | docs (EN) | n/a | same | role-match |
| `docs/docs/it-ot/opcua-schema.md` | docs (IT) | n/a | same | role-match |
| `scripts/validate-asset-registry.py` | script (schema validation) | file-I/O | `scripts/validate-glossary-schema.py` | exact |
| `scripts/validate-fault-profiles.py` | script (schema validation) | file-I/O | `scripts/validate-glossary-schema.py` | exact |
| `.github/workflows/ci.yml` (modify) | ci | n/a | existing `ci.yml` step "Validate content" lines 81-94 | exact (extension) |
| `Makefile` (modify) | build | n/a | existing `Makefile` lines 137-149 `validate-*` targets | exact (extension) |

---

## Pattern Assignments

### `packages/sft-assets/src/sft_assets/models.py` (model, Pydantic v2 frozen)

**Analog:** `packages/sft-domain/src/sft_domain/glossary/_models.py`

**Imports pattern** (lines 1-13):
```python
"""Modelli Pydantic v2 per il glossario bilingue IT/EN.

Tutti i modelli sono frozen=True, extra="forbid" per immutabilita' e validazione stretta.
Vedi: RESEARCH.md Pattern 1, T-02-02 (immutabilita' + strict schema).
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field
```

**Core pattern — frozen Pydantic model with `extra="forbid"`** (lines 38-69):
```python
class Term(BaseModel):
    """Termine del glossario bilingue.

    Immutabile (frozen=True) — crea nuovi oggetti invece di mutare quelli esistenti.
    Extra fields sono vietati (extra="forbid") per validazione stretta del YAML (T-02-02).
    """

    model_config = {"frozen": True, "extra": "forbid"}  # immutable, strict schema

    term: Annotated[str, Field(min_length=1, description="Nome canonico del termine")]
    definition: Annotated[
        str, Field(min_length=10, description="Definizione nel contesto textile/agentic")
    ]
    category: Annotated[Category, Field(description="Categoria tassonomica (D-30)")]
    related_terms: Annotated[
        list[str],
        Field(description="Termini correlati nel glossario"),
    ] = []
```

**Enum pattern** (lines 15-27) — applicabile a `AssetFamily`, `SemanticType`:
```python
class Category(str, Enum):
    """Categorie tassonomiche del glossario (D-30) — 9 valori."""

    TEXTILE_PROCESS = "textile-process"
    TEXTILE_ASSET = "textile-asset"
    ...
```

**Copy this to:** `sft_assets.Asset`, `sft_assets.Tag`, `sim_textile.FaultProfile`, `svc_ot_bridge.SensorEvent`, `sft_tools.replay.ReplayRecord`. Aggiungere validator custom richiesti da RESEARCH §Security checks 2 (es. `Asset.opcua_namespace` deve iniziare con `urn:mantis:`).

---

### `packages/sft-assets/src/sft_assets/loader.py` (loader, lru_cache + yaml.safe_load)

**Analog:** `packages/sft-domain/src/sft_domain/glossary/_loader.py`

**Imports + module constants** (lines 1-18):
```python
"""Loader del glossario bilingue IT/EN con caching LRU per cold-start performance.

Utilizza yaml.safe_load (mai yaml.load) per sicurezza.
Il loader e' idempotente: multiple chiamate con la stessa lingua restituiscono
la stessa lista cached (lru_cache sul parse del file).
"""

from __future__ import annotations

import pathlib
from functools import lru_cache
from typing import Literal

import yaml

from sft_domain.glossary._models import Term

_GLOSSARY_DIR = pathlib.Path(__file__).parent
```

**Core loader with lru_cache + safe_load** (lines 41-60):
```python
@lru_cache(maxsize=2)
def _load_terms_cached(lang: Literal["it", "en"]) -> list[Term]:
    """Versione cached di load_terms — massimo 2 entry (it + en)."""
    yaml_path = _GLOSSARY_DIR / f"{lang}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"File glossario non trovato: {yaml_path}. "
            f"Assicurati che il file esista in {_GLOSSARY_DIR}."
        )

    raw_text = yaml_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load, mai yaml.load

    if not isinstance(raw_data, list):
        raise ValueError(
            f"Il file {yaml_path} deve contenere una lista YAML di termini, "
            f"trovato: {type(raw_data).__name__}"
        )

    return [Term.model_validate(entry) for entry in raw_data]
```

**Dict variant for O(1) lookup** (lines 63-74):
```python
@lru_cache(maxsize=2)
def load_terms_dict(lang: Literal["it", "en"]) -> dict[str, Term]:
    """Restituisce un dizionario {term.lower(): Term} per lookup O(1).
    ...
    """
    return {t.term.lower(): t for t in load_terms(lang)}
```

**Cache invalidation for tests** (lines 77-80):
```python
def invalidate_cache() -> None:
    """Invalida la cache del loader (utile nei test per ricaricare YAML modificati)."""
    _load_terms_cached.cache_clear()
    load_terms_dict.cache_clear()
```

**Copy this to:** `sft_assets.loader.load_assets()`, `load_assets_dict()`, `load_tag_dict()`. Per `sim_textile`: stesso pattern per `load_profile(family: str) -> FaultProfile`. Mantenere `_GLOSSARY_DIR` → `_REGISTRY_DIR` / `_PROFILES_DIR` come modulo costante derivato da `pathlib.Path(__file__).parent`.

---

### `packages/sft-assets/src/sft_assets/schemas/asset.schema.json` (JSON Schema Draft 2020-12)

**Analog:** `packages/sft-domain/src/sft_domain/schemas/glossary.schema.json`

**Schema header + required + additionalProperties=false** (lines 1-9):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sft-domain/schemas/glossary.schema.json",
  "title": "SFT Glossary Term",
  "description": "Schema Draft 2020-12 per un termine del glossario bilingue (IT/EN) — dominio textile + agentic platform (D-29, D-30)",
  "type": "object",
  "required": ["term", "definition", "category"],
  "additionalProperties": false,
  "properties": {
```

**Field with enum** (lines 20-34) — adattare per `asset_family` / `semantic_type`:
```json
"category": {
  "type": "string",
  "enum": [
    "textile-process",
    "textile-asset",
    ...
  ],
  "description": "Categoria tassonomica del termine (D-30) — 9 valori ammessi"
}
```

**Copy this to:** `asset.schema.json` (Asset entity), `tag.schema.json` (Tag entity), `fault-profile.schema.json` (sim-textile profile YAML schema). `$id` deve essere coerente con il package: `https://sft-assets/schemas/asset.schema.json`.

---

### `packages/sft-assets/pyproject.toml` (uv workspace project config)

**Analog:** `packages/sft-domain/pyproject.toml`

**Full pattern** (lines 1-28):
```toml
[project]
name = "sft-domain"
version = "0.2.0"
requires-python = ">=3.12,<3.13"
description = "Textile domain models: defect taxonomy, asset registry, IT/EN glossary"
dependencies = [
  "pydantic>=2.13.4",
  "pyyaml>=6.0",
  "jsonschema>=4.23",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "python-frontmatter>=1.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sft_domain"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Adattamento per Phase 3 packages:**
- `sft-assets`: dependencies = `["pydantic>=2.13.4", "pyyaml>=6.0", "jsonschema>=4.23"]`. `[tool.hatch.build.targets.wheel] packages = ["src/sft_assets"]`.
- `sft-tools`: dependencies = `["pydantic>=2.13.4", "langchain-core>=0.3", "pandas>=2.2", "asyncpg>=0.30", "sft-assets", "sft-domain"]`. Workspace deps via `tool.uv.sources` (vedi `uv.lock` esistente per pattern).
- `sim-textile` (modify): dependencies = `["asyncua>=1.1", "pydantic>=2.13.4", "pyyaml>=6.0", "structlog>=24", "prometheus-client>=0.21", "sft-assets"]`.
- `svc-ot-bridge` (modify): dependencies = `["asyncua>=1.1", "nats-py>=2.9", "asyncpg>=0.30", "pydantic>=2.13.4", "structlog>=24", "prometheus-client>=0.21", "sft-assets"]`.

Conservare `requires-python = ">=3.12,<3.13"` (lock di Phase 1 ribadito in CONTEXT §code_context).

---

### `packages/sft-assets/project.json` (Nx project shape)

**Analog:** `packages/sft-domain/project.json`

**Full pattern** (lines 1-30):
```json
{
  "name": "sft-domain",
  "$schema": "../../node_modules/nx/schemas/project-schema.json",
  "projectType": "library",
  "sourceRoot": "packages/sft-domain/src",
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
    },
    "validate-glossary": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "command": "python3 ../../scripts/validate-glossary-schema.py && python3 ../../scripts/validate-glossary-coverage.py",
        "cwd": "."
      }
    }
  },
  "implicitDependencies": []
}
```

**Adattamento per Phase 3:**
- `sft-assets`: `projectType: "library"`. Custom target `validate-registry`: `"command": "python3 ../../scripts/validate-asset-registry.py"`.
- `sft-tools`: `projectType: "library"`, `implicitDependencies: ["sft-assets", "sft-domain"]`.
- `sim-textile` (esistente): `projectType: "application"`, già con `implicitDependencies: ["sft-contracts"]` — estendere con `"sft-assets"`. Custom target `validate-profiles`.
- `ot-bridge` (esistente): `projectType: "application"`, già con `implicitDependencies: ["sft-contracts"]` — estendere con `"sft-assets"`.

Analog file `simulators/sim-textile/project.json` (lines 1-26) e `services/ot-bridge/project.json` (lines 1-26) confermano il pattern application + sourceRoot.

---

### `packages/sft-assets/src/sft_assets/__init__.py` (barrel export)

**Analog:** `packages/sft-domain/src/sft_domain/glossary/__init__.py`

**Pattern** (lines 1-13):
```python
"""Glossario bilingue IT/EN del dominio textile + agentic platform.

Espone:
    Category                            — enum categorie tassonomiche (D-30)
    Term                                — modello Pydantic frozen per un termine
    load_terms(lang) -> list[Term]      — carica i termini del glossario per lingua
    load_terms_dict(lang) -> dict[str, Term]  — lookup O(1) per termine (chiave lowercase)
"""

from sft_domain.glossary._loader import load_terms, load_terms_dict
from sft_domain.glossary._models import Category, Term

__all__ = ["Category", "Term", "load_terms", "load_terms_dict"]
```

**Copy this to:** `sft_assets/__init__.py` esportando `Asset, Tag, AssetFamily, load_assets, load_assets_dict, load_tag_dict`. Stessa convention naming: private modules `_models.py` / `_loader.py` + public re-export modules `models.py` / `loader.py` (vedi `packages/sft-domain/src/sft_domain/glossary/models.py` lines 1-12 e `loader.py` lines 1-12).

---

### `scripts/timescale-migrate.py` (idempotent migration script)

**Analog:** `scripts/sync-python-versions.py`

**Argparse + module structure** (lines 1-27):
```python
#!/usr/bin/env python3
"""
scripts/sync-python-versions.py
...
Usage:
    python3 scripts/sync-python-versions.py [--dry-run]

Exit codes:
    0 - All versions synced (or dry-run completed)
    1 - Error reading a file
"""
import argparse
import json
import pathlib
import re
import sys

WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent
```

**Argparse boilerplate** (lines 119-131):
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
```

**Path printing via relative_to(WORKSPACE_ROOT)** (lines 72-79):
```python
if dry_run:
    current = py_version_file.read_text()
    if current == new_content:
        print(f"[dry-run] {py_version_file.relative_to(WORKSPACE_ROOT)}: already {version!r}")
    else:
        print(f"[dry-run] WOULD update {py_version_file.relative_to(WORKSPACE_ROOT)}: -> {version!r}")
else:
    py_version_file.write_text(new_content)
```

**Copy this to:**
- `scripts/timescale-migrate.py`: argparse `--dry-run` + `--dsn` (env fallback `TIMESCALE_DSN`); legge `infra/migrations/timescale/*.sql` in ordine; idempotent (controllo `IF NOT EXISTS` nelle DDL). Exit 0 OK, 1 errore I/O/SQL.
- `scripts/nats-bootstrap-streams.py`: stessa struttura argparse + `--dry-run` + `--server` (default `nats://nats:4222`). Idempotent via `js.add_stream` → fallback `update_stream` (RESEARCH §Pattern 3 lines 519-536).
- `scripts/download-replay-datasets.py`: argparse `--dry-run` + `--dest`; SHA256 verify via `replay-data/CHECKSUMS.txt`; exit 1 su mismatch.

---

### `scripts/validate-asset-registry.py` (JSON Schema CLI validator)

**Analog:** `scripts/validate-glossary-schema.py`

**Module docstring + imports** (lines 1-38):
```python
#!/usr/bin/env python3
"""
scripts/validate-glossary-schema.py

Validates packages/sft-domain/src/sft_domain/glossary/it.yaml and en.yaml against
the JSON Schema Draft 2020-12 definition in
packages/sft-domain/src/sft_domain/schemas/glossary.schema.json.
...
Uses yaml.safe_load exclusively (never yaml.load or Loader= parameter).

Usage:
    python3 scripts/validate-glossary-schema.py [--glossary-dir PATH] [--schema-file PATH]

Exit codes:
    0 - Both it.yaml and en.yaml are schema-valid with unique terms
    1 - One or more validation errors (schema violations or duplicate terms)
"""
import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema.validators import Draft202012Validator

WORKSPACE_ROOT = Path(__file__).parent.parent
```

**Validation loop with `Draft202012Validator.iter_errors`** (lines 96-116):
```python
for idx, entry in enumerate(data):
    entry_term = (
        entry.get("term", f"<entry #{idx + 1}>")
        if isinstance(entry, dict)
        else f"<entry #{idx + 1}>"
    )
    for schema_error in sorted(
        validator.iter_errors(entry), key=lambda e: list(e.path)
    ):
        field_path = (
            " -> ".join(str(p) for p in schema_error.path)
            if schema_error.path
            else "(root)"
        )
        errors.append(
            f"  [{lang}: '{entry_term}'] field '{field_path}': {schema_error.message}\n"
            f"    Fix: correct the value for field '{field_path}' in "
            f"{yaml_path.relative_to(WORKSPACE_ROOT)} entry '{entry_term}'."
        )
```

**Argparse with default paths** (lines 202-244):
```python
parser = argparse.ArgumentParser(
    description=(
        "Validate it.yaml and en.yaml glossary files against the glossary JSON Schema "
        "(Draft 2020-12). Checks schema validity and term uniqueness per language."
    ),
    ...
)
parser.add_argument(
    "--glossary-dir",
    type=Path,
    default=_DEFAULT_GLOSSARY_DIR,
    ...
)
```

**Safe YAML loading** (lines 64-66):
```python
try:
    with yaml_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)  # SEMPRE safe_load, mai yaml.load
```

**Copy this to:**
- `scripts/validate-asset-registry.py`: stessa struttura, valida `packages/sft-assets/src/sft_assets/registry.yaml` contro `schemas/asset.schema.json` + uniqueness check su `asset_id` (case-sensitive).
- `scripts/validate-fault-profiles.py`: valida `simulators/sim-textile/profiles/{loom,spinning,warping,dyeing,finishing}.yaml` contro `schemas/fault-profile.schema.json`. Range validator `0 ≤ nan_probability ≤ 1` (RESEARCH §Security checks 2).

---

### `tests/conftest.py` + `packages/sft-assets/tests/conftest.py` (pytest fixtures)

**Analog:** `packages/sft-domain/tests/conftest.py`

**Fixture pattern** (lines 1-26):
```python
"""Shared pytest fixtures per i test di sft-domain.

Fornisce:
    sample_term_dict        — dict valido per Term (textile-kpi)
    ...
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def sample_term_dict() -> dict:
    """Restituisce un dizionario valido per un Term del glossario (textile-kpi)."""
    return {
        "term": "pick density",
        "definition": "Number of weft picks per centimeter of fabric, determining fabric density and weight.",
        "category": "textile-kpi",
        "related_terms": ["warp_tension", "weft_yarn"],
        "examples": [
            "Pick density of 22-28 picks/cm is typical for cotton shirting fabrics."
        ],
        "source": "industry-standard",
    }
```

**Path fixture pattern** (analog `tests/conftest.py` lines 17-36):
```python
@pytest.fixture(scope="module")
def domain_dir() -> pathlib.Path:
    """Return the root directory of IT domain analysis pages.

    The path is computed relative to this conftest so it works regardless
    of the cwd from which pytest is invoked (typically the repo root).
    """
    return pathlib.Path(__file__).parent.parent / "docs" / "docs" / "domain"
```

**Copy this to:**
- `packages/sft-assets/tests/conftest.py`: `sample_asset_dict` (LOOM-01 con 2-3 tag) + `sample_tag_dict` + `sample_registry_minimal` (dict 1 asset valido per loader test).
- `packages/sft-tools/tests/conftest.py`: `mock_timescale_pool` (asyncpg.Pool stub) + `sample_replay_record` (ReplayRecord valido) + `sample_cmapss_csv_row` (tuple di 26 colonne C-MAPSS FD001).
- `simulators/sim-textile/tests/conftest.py`: `sample_fault_profile_dict` (loom profile valido) + `frozen_time` fixture (`datetime(2026,5,18,12,0,0,tzinfo=UTC)` via `freezegun` o pytest monkeypatch).
- `services/ot-bridge/tests/conftest.py`: testcontainers fixtures `timescale_container` + `nats_container` (vedi RESEARCH §Don't Hand-Roll → testcontainers-python).
- `tests/conftest.py` (modify, estendere senza romperlo): aggiungere `compose_stack` fixture (docker-compose lifecycle: `up -d --wait` su `core.yml + sim.yml`; teardown `down -v`).

---

### `packages/sft-assets/tests/test_registry_validation.py` (JSON Schema self-validation test)

**Analog:** `packages/sft-domain/tests/test_glossary_schema.py`

**Pattern: self-valid schema test** (lines 1-43):
```python
"""Test di meta-validazione degli schemi JSON Draft 2020-12.

Verifica:
    test_glossary_schema_self_valid    — glossary.schema.json e' un JSON Schema valido
    ...
"""

from __future__ import annotations

import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

SCHEMAS_DIR = (
    pathlib.Path(__file__).parent.parent
    / "src"
    / "sft_domain"
    / "schemas"
)


def _load_schema(filename: str) -> dict:
    """Carica uno schema JSON dalla directory schemas/."""
    path = SCHEMAS_DIR / filename
    assert path.exists(), f"Schema non trovato: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_glossary_schema_self_valid() -> None:
    """glossary.schema.json deve essere un JSON Schema Draft 2020-12 valido."""
    schema = _load_schema("glossary.schema.json")
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", (
        "glossary.schema.json deve dichiarare $schema Draft 2020-12"
    )
    # check_schema() restituisce None su successo, solleva SchemaError su errore
    result = Draft202012Validator.check_schema(schema)
    assert result is None
```

**Copy this to:** `test_asset_schema_self_valid`, `test_tag_schema_self_valid`, `test_fault_profile_schema_self_valid` (in `simulators/sim-textile/tests/test_profile_validation.py`).

---

### `packages/sft-assets/tests/test_loader.py` (lru_cache + error path tests)

**Analog:** `packages/sft-domain/tests/test_glossary_loader.py`

**Test class structure** (lines 24-60):
```python
class TestLoadTermsValidation:
    """Validazione input della funzione load_terms."""

    def test_invalid_lang_raises_value_error(self) -> None:
        """Una lingua non supportata deve sollevare ValueError."""
        with pytest.raises(ValueError, match="Lingua non supportata"):
            load_terms("fr")  # type: ignore[arg-type]


class TestLoadTermsCache:
    """Test della cache LRU del loader."""

    def setup_method(self) -> None:
        """Invalida la cache prima di ogni test."""
        invalidate_cache()

    def test_cache_info_tracks_hits(self) -> None:
        """La cache LRU deve tracciare hits e misses."""
        info = _load_terms_cached.cache_info()
        assert info.maxsize == 2  # maxsize=2 per it+en
```

**Tempfile + monkeypatch _DIR pattern** (lines 69-96):
```python
def test_missing_yaml_raises_file_not_found(self) -> None:
    """Un file YAML mancante deve sollevare FileNotFoundError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("sft_domain.glossary._loader._GLOSSARY_DIR", pathlib.Path(tmpdir)):
            invalidate_cache()
            with pytest.raises(FileNotFoundError, match="File glossario non trovato"):
                load_terms("it")

def test_malformed_yaml_raises_yaml_error(self) -> None:
    """Un YAML malformato deve sollevare yaml.YAMLError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yaml_file = pathlib.Path(tmpdir) / "it.yaml"
        yaml_file.write_text("invalid: yaml: : :\n  - broken[", encoding="utf-8")
        with patch("sft_domain.glossary._loader._GLOSSARY_DIR", pathlib.Path(tmpdir)):
            invalidate_cache()
            with pytest.raises(yaml.YAMLError):
                load_terms("it")
```

**Copy this to:** `sft_assets/tests/test_loader.py` con classi `TestLoadAssetsValidation`, `TestLoadAssetsCache`, `TestLoadAssetsFileHandling`. Stessa policy `setup_method` → `invalidate_cache()`. Identity-check pattern `terms1 is terms2` (lines 122-138) per verifica cache hit.

---

### `infra/compose/sim.yml` (modify — estensione dual-network)

**Analog:** `infra/compose/sim.yml` (self) + `infra/compose/core.yml`

**Existing scaffold to extend** (lines 1-37 di `infra/compose/sim.yml`):
```yaml
# Smart Factory Transformation — Simulation Dev Stack
# Servizi sim: NATS JetStream (message broker OT)
# Decisioni: D-07 (split per area), D-18 (anticipa data-diode NetworkPolicy OT)
# Network sft-sim separato da sft-core per principio data-diode (D-18)

services:
  nats:
    image: nats:2.10-alpine
    command: ["-js", "-m", "8222"]
    ports:
      - "${NATS_PORT:-4222}:4222"
      - "${NATS_MONITORING_PORT:-8222}:8222"
    volumes:
      - nats-data:/data
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:8222/healthz | grep -q ok"]
      interval: 3s
      timeout: 5s
      retries: 10
    networks:
      - sft-sim
    restart: unless-stopped

  # sim-textile placeholder - popolato in Fase 3
  # sim-textile:
  #   build: ../../simulators/sim-textile
  #   networks:
  #     - sft-sim
  #   depends_on:
  #     nats: { condition: service_healthy }

volumes:
  nats-data:

networks:
  sft-sim:
    driver: bridge
```

**Note critico — naming network già esistente:**
- Phase 1 ha già `sft-sim` (analogo a "ot-network" nel decision D-51) e `sft-core` (in `core.yml` lines 62-64, analogo a "it-network"). **Riusare nomi esistenti** invece di introdurre `ot-network`/`it-network` per coerenza Phase 1.
- D-51 Layer 1 si traduce in: `sim-textile` su `sft-sim` solo; `ot-bridge` su `[sft-sim, sft-core]`; `nats`/`timescaledb` su `sft-core` solo. **CRITICAL:** NATS attualmente è su `sft-sim` (line 21) — Phase 3 deve spostarlo su `sft-core` per allineare al data-diode (NATS è IT-side per RESEARCH §Pattern + D-51).

**Healthcheck + restart pattern** (sim.yml lines 15-22) — replica per sim-textile e ot-bridge:
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -qO- http://localhost:8222/healthz | grep -q ok"]
  interval: 3s
  timeout: 5s
  retries: 10
networks:
  - sft-sim
restart: unless-stopped
```

**Env vars pattern** (core.yml lines 9-12):
```yaml
environment:
  POSTGRES_USER: ${POSTGRES_USER:-sft}
  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-sft_dev_pass}
  POSTGRES_DB: ${POSTGRES_DB:-sft}
```

**Copy this to:** Aggiungere blocco `sim-textile` (con env `SIM_PROFILES`, `SIM_TIME_SCALE`, `OPCUA_BIND`, `METRICS_PORT` per D-50) e `ot-bridge` (env `TIMESCALE_DSN`, `NATS_URL`, `OPCUA_ENDPOINT`). Mantenere `${ENV:-default}` pattern per overridability.

---

### `Makefile` (modify — aggiunta target validate Phase 3)

**Analog:** `Makefile` (lines 137-149 — esistente sezione validate)

**Existing pattern**:
```makefile
# Schema: validate-glossary-schema.py (jsonschema Draft 2020-12)
# Copertura: validate-glossary-coverage.py (bold token lookup, lang-matched)
validate-glossary:
	python3 scripts/validate-glossary-schema.py
	python3 scripts/validate-glossary-coverage.py

# Lancia tutte le validazioni (schema + content + cross-reference)
# e check drift pagine generate (--check mode per generate-glossary-pages.py)
validate-all: validate-glossary validate-corpus
	uv run python3 scripts/validate-assumption-schema.py
	uv run python3 scripts/validate-assumption-components.py
	python3 scripts/generate-glossary-pages.py --check
	uv run python3 scripts/generate-assumption-pages.py --check
```

**.PHONY declaration** (line 16):
```makefile
.PHONY: up up-gpu up-core down reset test lint format docs docs-serve demo sbom license-scan helm-test ps logs validate-corpus generate-glossary generate-assumptions validate-glossary validate-all
```

**Copy this to:** Aggiungere target Phase 3:
```makefile
# Phase 3 validation
validate-assets:
	python3 scripts/validate-asset-registry.py
validate-profiles:
	python3 scripts/validate-fault-profiles.py
validate-all: validate-glossary validate-corpus validate-assets validate-profiles
	...

# Phase 3 ops
migrate-timescale:
	python3 scripts/timescale-migrate.py
bootstrap-nats:
	python3 scripts/nats-bootstrap-streams.py
load-test-smoke:
	uv run pytest tests/load/test_ingestion_smoke.py -v
load-test-full:
	uv run pytest tests/load/test_ingestion_throughput.py -v --full
```

Estendere `.PHONY` con i nuovi target.

---

### `.github/workflows/ci.yml` (modify — aggiunta IT/OT step)

**Analog:** `.github/workflows/ci.yml` (esistente — step "Validate content" lines 81-94)

**Existing pattern**:
```yaml
- name: Validate content
  run: |
    npx nx run-many --target=validate-glossary,validate-frontmatter,validate-bilingual-mirror,validate-pairing --all --parallel=2 || true

    python3 scripts/validate-glossary-schema.py
    python3 scripts/validate-glossary-coverage.py
    uv run python3 scripts/validate-assumption-schema.py
    uv run python3 scripts/validate-assumption-components.py

    python3 scripts/generate-glossary-pages.py
    python3 scripts/generate-glossary-pages.py --check
    uv run python3 scripts/generate-assumption-pages.py
    uv run python3 scripts/generate-assumption-pages.py --check
```

**Copy this to:** Aggiungere nuovo step DOPO "Validate content":
```yaml
- name: Validate IT/OT artifacts
  run: |
    python3 scripts/validate-asset-registry.py
    python3 scripts/validate-fault-profiles.py
    # CI grep gates (RESEARCH §Phase 3-specific security checks 1)
    ! grep -rE "yaml\.load\(" packages/sft-assets packages/sft-tools simulators/sim-textile services/ot-bridge
    ! grep -rE 'f"(INSERT|SELECT|UPDATE|DELETE)' services/ot-bridge packages/sft-tools
    ! grep -rE "(set_value|write_attribute|write_value)" services/ot-bridge/src/
    ! grep -rE "datetime\.now\(\)" simulators/sim-textile services/ot-bridge

- name: Run IT/OT integration tests
  run: |
    docker compose -f infra/compose/core.yml -f infra/compose/sim.yml up -d --wait
    uv run pytest tests/integration/ -v
    docker compose -f infra/compose/core.yml -f infra/compose/sim.yml down -v

- name: Run IT/OT load test (smoke)
  run: |
    uv run pytest tests/load/test_ingestion_smoke.py -v
```

---

## Shared Patterns (cross-cutting)

### Pattern S-1: Pydantic v2 frozen + extra=forbid

**Source:** `packages/sft-domain/src/sft_domain/glossary/_models.py` lines 45-46
```python
model_config = {"frozen": True, "extra": "forbid"}  # immutable, strict schema
```

**Apply to ALL new model files:**
- `packages/sft-assets/src/sft_assets/models.py` (Asset, Tag, TagRef, AssetFamily)
- `packages/sft-tools/src/sft_tools/replay/models.py` (ReplayRecord, ReplayCMAPSSArgs, ReplayUCIArgs)
- `simulators/sim-textile/src/sim_textile/models.py` (FaultProfile, FaultInjection, BaselineValue, EmitterState)
- `services/ot-bridge/src/svc_ot_bridge/models.py` (SensorEvent)

**Rationale:** CONTEXT §code_context naming conventions + RESEARCH §Security V5 + T-02-02.

---

### Pattern S-2: `yaml.safe_load` exclusively

**Source:** `packages/sft-domain/src/sft_domain/glossary/_loader.py` line 52
```python
raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load, mai yaml.load
```

**Apply to:** Tutti i loader YAML in Phase 3 (sft-assets registry loader, sim-textile profile loader, scripts/validate-*.py, scripts/nats-bootstrap-streams.py se legge config YAML).

**CI gate (RESEARCH §Security checks 1):** `grep -rE "yaml\.load\(" packages/sft-assets packages/sft-tools simulators/sim-textile services/ot-bridge` deve dare 0 match.

---

### Pattern S-3: WORKSPACE_ROOT module constant

**Source:** `scripts/sync-python-versions.py` line 27 + `scripts/validate-glossary-schema.py` line 33 + `tests/test_corpus_inventory.py` line 33
```python
WORKSPACE_ROOT = Path(__file__).parent.parent
```

**Apply to:** Tutti i nuovi script in `scripts/` Phase 3 + workspace-level tests in `tests/`. Sempre usare `pathlib.Path` (no `os.path`); print via `.relative_to(WORKSPACE_ROOT)`.

---

### Pattern S-4: argparse + --dry-run + documented exit codes

**Source:** `scripts/sync-python-versions.py` lines 119-131 + `scripts/generate-glossary-pages.py` lines 30-34, 319-377

**Exit code convention (Phase 1 + Phase 2):**
- `0` — success (o --dry-run/--check passato)
- `1` — errore I/O / parsing / validation
- `2` — drift mode (`--check` rileva differenze on-disk)

**Apply to:** `scripts/timescale-migrate.py`, `scripts/nats-bootstrap-streams.py`, `scripts/download-replay-datasets.py`, `scripts/validate-asset-registry.py`, `scripts/validate-fault-profiles.py`. Tutti devono supportare `--dry-run`.

---

### Pattern S-5: lru_cache(maxsize=N) + invalidate_cache()

**Source:** `packages/sft-domain/src/sft_domain/glossary/_loader.py` lines 41-43, 63-65, 77-80

**Apply to:** `sft_assets/_loader.py` (maxsize=1 perché unico registry YAML), `sim_textile/profile_loader.py` (maxsize=5 — uno per family). Sempre esporre `invalidate_cache()` per i test.

---

### Pattern S-6: UTC-aware datetime

**Source:** RESEARCH.md §Pitfall 7 + CONTEXT.md §claudes_discretion ("simulator emits con `datetime.now(UTC)`")

**Apply to:** `sim_textile.emitter`, `svc_ot_bridge.normalizer`, ogni Pydantic model con `datetime` field deve avere validator `tzinfo is not None`.

**CI gate (RESEARCH §Security checks 1):** `grep -rE "datetime\.now\(\)" simulators/sim-textile services/ot-bridge` deve dare 0 match (sempre `datetime.now(UTC)`).

---

### Pattern S-7: Public re-export module convention (`_models.py` private → `models.py` public)

**Source:** `packages/sft-domain/src/sft_domain/glossary/models.py` lines 10-12 + `loader.py` lines 10-12
```python
from sft_domain.glossary._models import Category, Term

__all__ = ["Category", "Term"]
```

**Apply to:** `packages/sft-assets/src/sft_assets/{models,loader}.py` (privati `_models.py` / `_loader.py`). NB: per `sft-tools` e i servizi `sim-textile` / `ot-bridge` questo split è opzionale (Phase 2 lo ha adottato per garantire interfaccia pubblica stabile in sft-domain v0.2.0 published). Per servizi non-published basta `models.py` diretto.

---

### Pattern S-8: Idempotent generators with `--check` for CI drift

**Source:** `scripts/generate-glossary-pages.py` lines 289-306
```python
if check:
    if not output_path.exists():
        print(f"DRIFT [{rel}]: file does not exist on disk — ...", file=sys.stderr)
        return 2
    current = output_path.read_text(encoding="utf-8")
    if current != content:
        print(f"DRIFT [{rel}]: generated content differs from disk — ...", file=sys.stderr)
        return 2
    print(f"OK [{rel}]: up to date")
    return 0
```

**Apply to:** Eventuali generator Phase 3 (es. `docs/docs/it-ot/ingest-schema.md` se diventa autogen da `sft_assets/registry.yaml`). Se invece ingest-schema.md è scritto a mano, NO generator necessario — vedi RESEARCH §Recommended Project Structure (sembra a mano).

---

## No Analog Found

I seguenti file sono greenfield: nessun analogo Phase 1+2 esiste. Il planner deve usare gli excerpts in `03-RESEARCH.md` come riferimento primario.

| File | Role | Data Flow | Reason | Reference |
|------|------|-----------|--------|-----------|
| `simulators/sim-textile/src/sim_textile/server.py` | asyncua server | streaming | Phase 1+2 no async messaging code | RESEARCH §Pattern 1 (lines 411-466) |
| `simulators/sim-textile/src/sim_textile/emitter.py` | asyncio per-asset loop | streaming | Phase 1+2 no asyncio workers | RESEARCH §Pattern 2 (lines 468-504) |
| `simulators/sim-textile/src/sim_textile/faults/*.py` | pure-function fault ops | transform | Phase 1+2 no signal-processing code | RESEARCH §Pattern 2 (replace-based mutation) |
| `simulators/sim-textile/src/sim_textile/main.py` | asyncio entry | event-driven | Phase 1+2 no long-running asyncio entry | RESEARCH §Pattern 1 line 460-465 + `asyncio.gather` orchestration |
| `services/ot-bridge/src/svc_ot_bridge/opcua_client.py` | asyncua subscriber | streaming | Phase 1+2 no OPC-UA client | RESEARCH §Pattern 1 + §Pitfall 1 (subscription throttling) |
| `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py` | NATS JetStream publisher | pub-sub | Phase 1+2 no NATS client code | RESEARCH §Pattern 3 (lines 506-558) |
| `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` | asyncpg batch writer | batch | Phase 1+2 no DB writer code | RESEARCH §Pattern 4 (lines 560-613) + §Pitfall 6 (statement_cache_size=0) |
| `services/ot-bridge/src/svc_ot_bridge/main.py` | asyncio entry | event-driven | greenfield | RESEARCH §Pattern 1-4 orchestration |
| `packages/sft-tools/src/sft_tools/replay/{cmapss,uci}.py` | LangChain BaseTool async | request-response | Phase 1+2 no LangChain code | RESEARCH §Pattern 5 (lines 615-662) + §Pattern 6 (lines 664-682 C-MAPSS mapping) |
| `packages/sft-tools/src/sft_tools/timescale/query.py` | LangChain BaseTool + asyncpg query | request-response | greenfield | RESEARCH §Pattern 4 (read path) + §Pattern 5 (BaseTool) |
| `infra/migrations/timescale/001_create_sensor_events.sql` | TimescaleDB DDL | n/a | Phase 1+2 no migrations | RESEARCH §Code Examples "TimescaleDB migration SQL idempotente" (lines 878-937) |
| `tests/integration/test_data_diode.py` | docker-in-docker integration | n/a | Phase 1+2 no integration test infra | RESEARCH §Code Examples "pytest data-diode integration test" (lines 995-1033) |
| `tests/integration/test_e2e_sim_to_timescale.py` | testcontainers E2E | n/a | greenfield | RESEARCH §Don't Hand-Roll → testcontainers-python row |
| `tests/load/harness.py` + `tests/load/test_ingestion_*.py` | custom asyncio load harness | streaming | greenfield (D-48) | RESEARCH §Pattern 4 (asyncpg.Pool batch) + custom asyncio.gather harness |

**Planner directive:** Per ognuno di questi, ogni PLAN.md deve referenziare l'excerpt RESEARCH.md per line number, NON inventare pattern nuovi.

---

## Metadata

**Analog search scope:**
- `packages/sft-domain/` (Phase 2 — modello primario per nuovi package Python)
- `simulators/sim-textile/` + `services/ot-bridge/` (Phase 1 scaffold — pyproject/project.json + barrel)
- `scripts/` (Phase 1+2 — pattern argparse + idempotent CLI)
- `tests/` workspace-root + `packages/sft-domain/tests/` (Phase 2 — pytest convention + conftest)
- `infra/compose/` (Phase 1 — yaml service+network+healthcheck)
- `Makefile` + `.github/workflows/ci.yml` (Phase 1+2 — build + CI targets)

**Files scanned (read tool):** 19
**Files greenfield (no analog):** 14 (resi a RESEARCH.md §Patterns 1-6 + §Code Examples)
**Pattern extraction date:** 2026-05-18

## PATTERN MAPPING COMPLETE

**Phase:** 03 — IT/OT Simulation Layer
**Files classified:** 38
**Analogs found:** 32 / 38

### Coverage
- Files with exact analog: 22 (config + model/loader/schema patterns + tests + script template + Makefile/CI/compose extensions)
- Files with role-match analog: 10 (CLI scripts, profile YAML, tool models, normalizer)
- Files with no analog (use RESEARCH.md): 14 (tutti gli async runtime components: asyncua server/client, NATS publisher, asyncpg writer, LangChain Tools, SQL migration, integration/load tests)

### Key Patterns Identified
- **Phase 2 modello canonico per nuovi Python packages:** `_models.py` (private) + `models.py` (public re-export) + `_loader.py`/`loader.py` con lru_cache + JSON Schema Draft 2020-12 + Nx project.json `executor: @nxlv/python:run-commands` + uv via `cwd` per pyproject ↔ Nx integration.
- **CLI scripts Phase 1+2 pattern:** argparse + `WORKSPACE_ROOT = Path(__file__).parent.parent` + `--dry-run` + exit codes documentati (0/1/2) + `.relative_to(WORKSPACE_ROOT)` per output. Da replicare 1:1 per timescale-migrate, nats-bootstrap, validate-asset-registry, validate-fault-profiles, download-replay-datasets.
- **YAML safety + immutability invariants:** `yaml.safe_load` universale + Pydantic `frozen=True, extra="forbid"` + `lru_cache + invalidate_cache()` + `datetime.now(UTC)` mandatory. Tutti enforcible via CI grep gates già documentati in RESEARCH §Security checks 1.
- **Compose dual-network già parzialmente esistente:** `sft-sim` (Phase 1) + `sft-core` (Phase 1) sono gli effective `ot-network`/`it-network` di D-51. Phase 3 deve solo riassegnare NATS da `sft-sim`→`sft-core` e definire `ot-bridge` come unico container bi-network. Non introdurre nuovi nomi network.

### File Created
`/media/federicocalo/D1/prj/Smart Factory Transformation/.planning/phases/03-it-ot-simulation-layer/03-PATTERNS.md`

### Ready for Planning
Pattern mapping completo. Il gsd-planner può ora referenziare gli analoghi Phase 1+2 (line numbers concreti) nei 5-7 PLAN.md attesi (vedi CONTEXT §downstream_guidance Waves 1-4) e ricadere su RESEARCH.md §Patterns 1-6 / §Code Examples per i 14 file greenfield.
