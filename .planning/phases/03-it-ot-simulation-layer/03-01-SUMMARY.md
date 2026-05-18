---
phase: 03-it-ot-simulation-layer
plan: "01"
subsystem: asset-registry
tags: [pydantic, yaml, json-schema, sft-assets, asset-registry, tag-dictionary, opcua]

# Dependency graph
requires:
  - phase: 02-domain-modeling-synthetic-corpus
    provides: sft-domain package pattern (Pydantic v2 frozen models, YAML loader con lru_cache, JSON Schema Draft 2020-12, Nx project layout)

provides:
  - "packages/sft-assets: pacchetto Nx importabile con Asset/Tag/AssetFamily/SemanticType Pydantic v2 frozen + extra=forbid"
  - "load_assets() -> tuple[Asset, ...] con lru_cache(maxsize=1)"
  - "load_assets_dict() -> dict[str, Asset] per lookup O(1) per asset_id"
  - "load_tag_dict() -> dict[str, Tag] con consistency check inter-asset"
  - "registry.yaml: 30 asset seed Mantis-realistic (12 LOOM + 8 SPIN + 4 WARP + 4 DYE + 2 STEN), 24 tag distinti"
  - "schemas/asset.schema.json: JSON Schema Draft 2020-12 con additionalProperties=false"
  - "scripts/validate-asset-registry.py: CLI validator con argparse + --dry-run + exit codes 0/1"
  - "Makefile target validate-assets e validate-all aggiornato"

affects:
  - 03-02-sft-tools
  - 03-03-sim-textile
  - 03-04-ot-bridge
  - phase-04-core-agentic-runtime
  - phase-06-anomaly-detection
  - phase-07-predictive-maintenance

# Tech tracking
tech-stack:
  added:
    - "pydantic>=2.13.4 (gia' nel workspace, ora anche in sft-assets)"
    - "pyyaml>=6.0 (gia' nel workspace, ora anche in sft-assets)"
    - "jsonschema>=4.23 (gia' nel workspace, ora anche in sft-assets)"
    - "hatchling (build backend, pattern da sft-domain)"
  patterns:
    - "Pydantic v2 frozen + extra=forbid per tutti i modelli asset (model_config = {'frozen': True, 'extra': 'forbid'})"
    - "@field_validator per security constraint opcua_namespace startswith urn:mantis:"
    - "lru_cache(maxsize=1) su load_assets/load_assets_dict/load_tag_dict"
    - "invalidate_cache() per isolamento test pytest con monkeypatch"
    - "Consistency check inter-asset in load_tag_dict() via AssertionError"
    - "JSON Schema Draft 2020-12 con $id canonico + additionalProperties=false"
    - "CLI validator con yaml.safe_load + Draft202012Validator.iter_errors + uniqueness check"
    - "Pattern barrel: _models.py (private) + models.py (public re-export)"

key-files:
  created:
    - "packages/sft-assets/pyproject.toml"
    - "packages/sft-assets/project.json"
    - "packages/sft-assets/package.json"
    - "packages/sft-assets/src/sft_assets/__init__.py"
    - "packages/sft-assets/src/sft_assets/_models.py"
    - "packages/sft-assets/src/sft_assets/models.py"
    - "packages/sft-assets/src/sft_assets/_loader.py"
    - "packages/sft-assets/src/sft_assets/loader.py"
    - "packages/sft-assets/src/sft_assets/registry.yaml"
    - "packages/sft-assets/src/sft_assets/schemas/asset.schema.json"
    - "packages/sft-assets/tests/conftest.py"
    - "packages/sft-assets/tests/test_models.py"
    - "packages/sft-assets/tests/test_loader.py"
    - "packages/sft-assets/tests/test_registry_validation.py"
    - "scripts/validate-asset-registry.py"
  modified:
    - "pyproject.toml (root): aggiunto packages/sft-assets ai workspace members uv"
    - "Makefile: aggiunti target validate-assets, validate-all, validate-glossary, validate-corpus, generate-*"

key-decisions:
  - "D-45 implementato: packages/sft-assets come SSOT platform metadata; distinto da sft-domain (domain concepts)"
  - "IOT-09 parzialmente coperto: asset registry + tag dictionary + UoM come Pydantic+YAML+JSON Schema; docs MkDocs deferred a plan 03-07"
  - "opcua_namespace validator impone prefisso urn:mantis: (security constraint T-03-01-pydantic)"
  - "Tag consistency check in load_tag_dict() assicura stesso tag_id = stessa unit/sample_rate/semantic_type in tutti gli asset"
  - "registry.yaml usa YAML invece di DB-backed registry (D-45, Phase 11 deferred)"

patterns-established:
  - "Pattern sft-assets: mirror esatto di sft-domain (stesso layout, stessi pattern Pydantic/YAML/schema)"
  - "Pattern barrel privato/pubblico: _models.py/_loader.py privati + models.py/loader.py re-export pubblici"
  - "Pattern validator CLI: yaml.safe_load + Draft202012Validator.iter_errors + argparse --dry-run + exit 0/1"

requirements-completed:
  - IOT-09

# Metrics
duration: 45min
completed: "2026-05-18"
---

# Phase 3 Plan 01: sft-assets Asset Registry Summary

**Pacchetto Nx sft-assets con Pydantic v2 frozen models, YAML registry 30 asset Mantis-realistic (12 LOOM+8 SPIN+4 WARP+4 DYE+2 STEN), JSON Schema Draft 2020-12 auto-validato, CLI validator e 20 test pytest passanti.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-05-18T09:57:00Z
- **Completed:** 2026-05-18T10:42:30Z
- **Tasks:** 2
- **Files modificati/creati:** 17

## Accomplishments

- Pacchetto `sft-assets` scaffoldato e registrato nel workspace uv: `from sft_assets import Asset, Tag, load_assets, load_tag_dict` funziona
- 30 asset seed Mantis-realistic committati in `registry.yaml` (833 righe): 12 LOOM-01..12 su weaving-line-1/2, 8 SPIN-01..08 su spinning-line-1, 4 WARP-01..04 su warping-line-1, 4 DYE-01..04 su dyeing-line-1, 2 STEN-01..02 su finishing-line-1
- 24 tag distinti, ~150 occorrenze: `warp_tension`, `pick_density`, `creel_speed`, `broken_pick_count`, `loom_temperature` (loom), `spindle_speed`, `yarn_tension`, `roller_temperature`, `broken_end_count`, `spindle_vibration` (spinning), `tension_imbalance`, `creel_feed_rate`, `warp_count`, `winding_speed` (warping), `bath_temperature`, `bath_ph`, `bath_level`, `flow_rate`, `recipe_deviation`, `bath_pressure` (dyeing), `fabric_tension`, `chamber_temperature`, `humidity`, `fabric_speed` (finishing)
- `scripts/validate-asset-registry.py` funzionante: `python3 scripts/validate-asset-registry.py` stampa `OK [packages/sft-assets/src/sft_assets/registry.yaml]: 30 assets valid`
- `make validate-assets` exit 0; `make validate-all` aggiornato con validate-assets come prerequisito

## Task Commits

1. **Task 1: Scaffold pacchetto Nx sft-assets + Pydantic models + JSON Schema + barrel exports** - `7798855` (feat)
2. **Task 2: Seed registry.yaml con 30 asset + CLI validator + integrazione CI/Makefile** - `53be448` (feat)

## Files Created/Modified

- `packages/sft-assets/pyproject.toml` - Config uv workspace (sft-assets v0.1.0, deps pydantic/pyyaml/jsonschema, hatchling)
- `packages/sft-assets/project.json` - Nx project (library, targets: test/lint/validate-registry)
- `packages/sft-assets/package.json` - @sft/sft-assets npm descriptor
- `packages/sft-assets/src/sft_assets/_models.py` - AssetFamily(5), SemanticType(10), Tag frozen+extra=forbid, Asset frozen+extra=forbid+opcua validator
- `packages/sft-assets/src/sft_assets/_loader.py` - load_assets/dict/tag con lru_cache(1) + consistency check + invalidate_cache()
- `packages/sft-assets/src/sft_assets/models.py` - Re-export pubblico modelli
- `packages/sft-assets/src/sft_assets/loader.py` - Re-export pubblico loader
- `packages/sft-assets/src/sft_assets/__init__.py` - Barrel export tutti i simboli pubblici
- `packages/sft-assets/src/sft_assets/registry.yaml` - 30 asset seed (833 righe)
- `packages/sft-assets/src/sft_assets/schemas/asset.schema.json` - JSON Schema Draft 2020-12
- `packages/sft-assets/tests/conftest.py` - Fixtures sample_asset_dict, sample_tag_dict, sample_registry_minimal
- `packages/sft-assets/tests/test_models.py` - 8 test modelli (frozen, namespace, extra, enum)
- `packages/sft-assets/tests/test_loader.py` - 7 test loader (lru_cache, dict, consistency, invalidate)
- `packages/sft-assets/tests/test_registry_validation.py` - 5 test schema+registry (self-valid, validates, unique, count breakdown, tag count)
- `scripts/validate-asset-registry.py` - CLI validator standalone
- `pyproject.toml` (root) - Aggiunto packages/sft-assets ai workspace members
- `Makefile` - Aggiunto validate-assets, validate-all (con prerequisito validate-assets), validate-glossary, validate-corpus, generate-* targets

## Decisions Made

- **D-45 implementato:** `packages/sft-assets` come SSOT platform metadata, separato da `sft-domain` (domain concepts). Nessun file `sft-domain` modificato.
- **opcua_namespace security constraint:** `@field_validator` impone prefisso `urn:mantis:` su ogni `Asset.opcua_namespace`. Violazione = `ValidationError` sia in Python che in JSON Schema.
- **Consistency check inter-asset:** `load_tag_dict()` usa `AssertionError` (non eccezione silente) se stesso `tag_id` ha unit/sample_rate/semantic_type divergenti tra asset. Garantisce SSOT tag definitions.
- **TDD eseguito:** Test scritti prima dell'implementazione (RED: ImportError), poi implementazione (GREEN: 20/20 passanti).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rimosso default_factory conflittuale su campo `tags` in Asset**
- **Found during:** Task 1 (implementazione _models.py)
- **Issue:** `Field(default_factory=tuple)` + `= ()` solleva `TypeError: cannot specify both default and default_factory` in Pydantic v2
- **Fix:** Rimosso `default_factory=tuple` dal `Field(...)`, mantenuto solo `= ()` come default
- **Files modified:** `packages/sft-assets/src/sft_assets/_models.py`
- **Verification:** `python -c "import sft_assets"` exit 0 dopo fix
- **Committed in:** `7798855` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Auto-fix necessario per correttezza Pydantic v2. Nessun scope creep.

## Issues Encountered

- `uv run --project packages/sft-assets pytest` fallisce senza `--extra dev` perche' pytest e' dev-dependency. Soluzione: `uv run --project packages/sft-assets --extra dev python -m pytest`.
- Il pacchetto `sft-assets` era installato senza i file sorgenti nella prima build perche' la directory `src/sft_assets/` era vuota quando hatchling ha fatto il build. Risolto con `--reinstall-package sft-assets` dopo aver creato tutti i file sorgenti.

## User Setup Required

Nessuno — nessun servizio esterno richiede configurazione manuale. Il pacchetto usa solo file locali (registry.yaml).

## Next Phase Readiness

- `packages/sft-assets` e' importabile: `from sft_assets import Asset, Tag, load_assets, load_tag_dict`
- `sim-textile` (Plan 03-03) puo' importare `sft-assets` per generare nodi OPC-UA da `load_assets()`
- `ot-bridge` (Plan 03-04) puo' importare `sft-assets` per risolvere `asset_id -> routing key NATS`
- `sft-tools` (Plan 03-02) puo' usare `load_tag_dict()` per mappare tag sensore a schema LangChain
- IOT-09 "ingest schema documented" parzialmente coperto — docs MkDocs deferred a Plan 03-07

---
*Phase: 03-it-ot-simulation-layer*
*Completed: 2026-05-18*

## Self-Check: PASSED

Files verificati:
- `packages/sft-assets/pyproject.toml` FOUND
- `packages/sft-assets/src/sft_assets/_models.py` FOUND
- `packages/sft-assets/src/sft_assets/_loader.py` FOUND
- `packages/sft-assets/src/sft_assets/registry.yaml` FOUND (833 righe, 30 asset)
- `packages/sft-assets/src/sft_assets/schemas/asset.schema.json` FOUND
- `scripts/validate-asset-registry.py` FOUND
- Commit `7798855` FOUND
- Commit `53be448` FOUND
- `pytest` 20/20 passed
- `validate-asset-registry.py` exit 0, output "30 assets valid"
- `grep -rE "yaml\.load\("` exit 1 (no match)
