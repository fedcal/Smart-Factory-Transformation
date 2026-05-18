---
phase: 03-it-ot-simulation-layer
plan: 02
subsystem: sft-tools
tags:
  - langchain-tools
  - replay-loader
  - cmapss
  - uci
  - asyncpg
  - pydantic-v2
dependency_graph:
  requires:
    - packages/sft-domain (workspace dep, Pydantic pattern)
  provides:
    - packages/sft-tools (REPLAY_TOOLS, TIMESCALE_TOOLS — LangChain ToolNode-ready)
    - scripts/download-replay-datasets.py (dataset management)
    - simulators/sim-textile/replay-data/ (dataset storage location)
  affects:
    - Phase 4 agents (import sft_tools.replay + sft_tools.timescale)
    - Phase 7 PredictiveMaintenance (training on C-MAPSS replay data)
tech_stack:
  added:
    - langchain-core==1.4.0 (Pydantic v2 native BaseTool)
    - pandas==2.3.3
    - asyncpg==0.31.0
    - pydantic==2.13.4 (already workspace dep)
  patterns:
    - LangChain BaseTool async-first pattern (_arun primary, _run raises NotImplementedError)
    - Pydantic v2 frozen + extra=forbid + tz-aware field_validator
    - asyncpg $1/$2/$3 placeholder SQL (no f-string — T-03-02-sql)
    - deterministic SHA256 hash unit_id → asset_id (OQ5 resolution)
    - WORKSPACE_ROOT pathlib.Path(__file__).parent.parent pattern (S-3)
key_files:
  created:
    - packages/sft-tools/pyproject.toml
    - packages/sft-tools/project.json
    - packages/sft-tools/package.json
    - packages/sft-tools/src/sft_tools/__init__.py
    - packages/sft-tools/src/sft_tools/replay/__init__.py
    - packages/sft-tools/src/sft_tools/replay/models.py
    - packages/sft-tools/src/sft_tools/replay/cmapss.py
    - packages/sft-tools/src/sft_tools/replay/uci.py
    - packages/sft-tools/src/sft_tools/timescale/__init__.py
    - packages/sft-tools/src/sft_tools/timescale/query.py
    - packages/sft-tools/tests/conftest.py
    - packages/sft-tools/tests/test_replay_models.py
    - packages/sft-tools/tests/test_replay_cmapss.py
    - packages/sft-tools/tests/test_replay_uci.py
    - packages/sft-tools/tests/test_query_timescale.py
    - packages/sft-tools/tests/fixtures/cmapss_fd001_sample.txt
    - packages/sft-tools/tests/fixtures/uci_production_sample.csv
    - scripts/download-replay-datasets.py
    - simulators/sim-textile/replay-data/.gitkeep
    - simulators/sim-textile/replay-data/CHECKSUMS.txt
  modified:
    - pyproject.toml (workspace members: added packages/sft-tools)
    - uv.lock (regenerated)
    - .gitignore (added replay-data/* block)
decisions:
  - "D-46: ReplayRecord schema unificato (7 colonne: asset_id, timestamp_utc, sensor_id, value, unit, source_dataset, source_unit) implementato come Pydantic frozen model"
  - "D-47: sft-tools come Nx library dedicata ai LangChain Tools cross-cutting (non in sim-textile o agents)"
  - "OQ5: target_asset_id opzionale in ReplayCMAPSSArgs; fallback a deterministic SHA256 hash unit_id → asset_id da _FALLBACK_ASSET_LIST (sft-assets non ancora disponibile in Wave 1 parallela)"
  - "Pitfall 5: SOLO pydantic v2 native imports; docstring mentions sono stati sanitizzati per CI grep gate"
  - "Pitfall 6: statement_cache_size=0 in asyncpg.connect (TimescaleDB dynamic plan optimization)"
  - "T-03-02-sql: SQL esclusivamente con $1/$2/$3/$4 placeholders; ANY($4) per filtro tag"
  - "A4/A10: dataset gitignored, download-on-demand con SHA256 verify"
metrics:
  duration: "~35 minutes"
  completed_date: "2026-05-18"
  tasks_completed: 2
  files_created: 20
  files_modified: 3
  tests_added: 34
  tests_passing: 34
---

# Phase 3 Plan 02: sft-tools LangChain Tools Summary

**One-liner:** Nuovo pacchetto `packages/sft-tools` con 3 LangChain BaseTool async (replay_cmapss NASA C-MAPSS, replay_uci UCI Manufacturing, query_timescale asyncpg proxy) + script download-on-demand SHA256 per dataset gitignored.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Scaffold sft-tools + ReplayRecord + 3 Tool + test contracts | f439490 | 19 files |
| 2 | scripts/download-replay-datasets.py + replay-data gitignore | 0ec0235 | 4 files |

## Task 1: sft-tools Package

### Struttura creata

```
packages/sft-tools/
├── pyproject.toml          # langchain-core>=1.0,<2.0, pandas>=2.2, asyncpg>=0.30, pydantic>=2.13.4
├── project.json            # Nx library, implicitDependencies: [sft-domain]
├── package.json            # @sft/sft-tools
├── src/sft_tools/
│   ├── __init__.py         # barrel: REPLAY_TOOLS, TIMESCALE_TOOLS
│   ├── replay/
│   │   ├── __init__.py     # REPLAY_TOOLS = [ReplayCMAPSSTool(), ReplayUCITool()]
│   │   ├── models.py       # ReplayRecord, ReplayCMAPSSArgs, ReplayUCIArgs, QueryTimescaleArgs
│   │   ├── cmapss.py       # ReplayCMAPSSTool(BaseTool) + _deterministic_asset_for_unit
│   │   └── uci.py          # ReplayUCITool(BaseTool)
│   └── timescale/
│       ├── __init__.py     # TIMESCALE_TOOLS = [QueryTimescaleTool()]
│       └── query.py        # QueryTimescaleTool(BaseTool) + $N placeholders
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── cmapss_fd001_sample.txt  (26 cols, 5 units × 3 cycles = 15 rows)
    │   └── uci_production_sample.csv (10 rows, 5 sensors)
    ├── test_replay_models.py   (8 test items)
    ├── test_replay_cmapss.py   (11 test items)
    ├── test_replay_uci.py      (7 test items)
    └── test_query_timescale.py (8 test items)
```

### Test risultati

```
34 passed in 0.45s
```

Test coverage per contratto:
- `ReplayRecord` frozen + tz-aware datetime validator
- `ReplayCMAPSSArgs` range unit_id 1..260 + target_asset_id OQ5
- `ReplayCMAPSSTool._run` raises NotImplementedError
- `ReplayCMAPSSTool._arun` → DataFrame 7 colonne, ≥21 righe (fixture)
- Deterministic hash: stesso unit_id → stesso asset_id
- target_asset_id override: `df["asset_id"].unique() == ["LOOM-05"]`
- sensor_subset filtra correttamente
- `ReplayUCITool` → DataFrame schema unificato
- `QueryTimescaleTool` SQL usa $1/$2/$3 (mock asyncpg)
- tags filter usa `ANY($4)` con parametro lista
- statement_cache_size=0 verificato via mock

### Decisioni chiave

**OQ5 resolution — target_asset_id optional + deterministic hash:**
```
unit_id → hashlib.sha256(str(unit_id)) → index % len(asset_list) → asset_id
```
Fallback `_FALLBACK_ASSET_LIST` (30 asset: LOOM-01..12, SPIN-01..08, ecc.) per Wave 1 parallelismo (sft-assets non disponibile al momento del build di sft-tools).

**DataFrame schema unificato D-46:**
```python
["asset_id", "timestamp", "sensor_id", "value", "unit", "source_dataset", "source_unit"]
```
C-MAPSS cycle → `datetime(2026,1,1,UTC) + timedelta(seconds=cycle*60)` (A-002 invariante).

**SQL sicuro T-03-02-sql:**
```python
_BASE_SQL = "SELECT ... WHERE asset_id = $1 AND timestamp_utc >= $2 AND timestamp_utc <= $3"
_TAGS_SQL_SUFFIX = " AND tag_id = ANY($4)"
```
Mai f-string SQL. Tags passati come lista parametro (non interpolata).

## Task 2: Download Script

**Script `scripts/download-replay-datasets.py`:**
- argparse: `--dry-run`, `--dataset {cmapss-fd001,uci-air-quality,uci-energy,uci-production,all}`, `--dest`, `--force`
- `WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent` (Pattern S-3)
- SHA256 via `hashlib.sha256` streaming (memory-efficient)
- Download via `urllib.request.urlretrieve` (no external deps)
- Aggiorna `CHECKSUMS.txt` automaticamente al primo download
- URL override via env vars (es. `CMAPSS_FD001_URL=...`)

**Verifica dry-run:**
```
python3 scripts/download-replay-datasets.py --dry-run --dataset all
→ [dry-run] would download: ... (4 righe) → exit 0
```

**License compliance:**
- `simulators/sim-textile/replay-data/*` gitignored
- `.gitkeep` + `CHECKSUMS.txt` esclusi dal gitignore con `!`

## CI Grep Gates (tutti passing)

| Gate | Command | Result |
|------|---------|--------|
| Pitfall 5 | `grep -rE "(pydantic\.v1\|from langchain\.pydantic_v1)" src/` | 0 match |
| SQL injection | `grep -rE 'f"(INSERT\|SELECT\|UPDATE\|DELETE)' src/` | 0 match |
| $1 placeholder | `grep -c '\$1' timescale/query.py` | 5 |
| statement_cache_size=0 | `grep -c "statement_cache_size=0" timescale/query.py` | 4 |
| TIMESCALE_DSN hardcode | `grep -rE 'TIMESCALE_DSN\s*=\s*["\x27]' src/` | 0 match |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixture C-MAPSS generata con 28 colonne invece di 26**
- **Trovato durante:** Task 1 GREEN — test_arun_returns_dataframe_with_schema fallisce con 0 rows
- **Issue:** fixture `cmapss_fd001_sample.txt` aveva 28 valori per riga invece di 26 (formato C-MAPSS: unit_id + cycle + 3 op_settings + 21 sensors = 26)
- **Fix:** Rigenerata fixture con esattamente 26 colonne per riga
- **Files modified:** `packages/sft-tools/tests/fixtures/cmapss_fd001_sample.txt`
- **Commit:** f439490 (incluso nel commit Task 1 finale)

**2. [Rule 1 - Bug] Test mutazione frozen model usava object.__setattr__ (bypassa Pydantic)**
- **Trovato durante:** Task 1 GREEN — test_replay_record_frozen_raises_on_mutation non solleva eccezione
- **Issue:** `object.__setattr__` bypassa la validazione Pydantic frozen; il test deve usare assignment diretto `record.field = value`
- **Fix:** Cambiato test da `object.__setattr__(record, "asset_id", ...)` a `record.asset_id = "LOOM-99"`
- **Files modified:** `packages/sft-tools/tests/test_replay_models.py`
- **Commit:** f439490

**3. [Rule 2 - Security] Docstring con pattern "pydantic.v1" triggera CI grep gate**
- **Trovato durante:** Verifica CI gates post-implementazione
- **Issue:** Le note CRITICAL nei docstring contenevano la stringa `pydantic.v1` (es. "NESSUN import pydantic.v1"), facendo fallire il CI grep gate `grep -rE "(pydantic\.v1|from langchain\.pydantic_v1)"` anche senza import reali
- **Fix:** Riformulato le note dei docstring per evitare la stringa esatta senza perdere il significato semantico
- **Files modified:** `cmapss.py`, `uci.py`, `query.py`, `models.py`
- **Commit:** f439490

**4. [Rule 1 - Design] sft-assets non disponibile in Wave 1 parallela**
- **Trovato durante:** Task 1 - `from sft_assets import load_assets` non disponibile (sft-assets è piano 03-01, eseguito in parallelo)
- **Issue:** Il piano specifica `sft-assets` come workspace dep ma il pacchetto non esiste ancora nel workspace al momento dell'esecuzione di 03-02
- **Fix:** Implementato `_load_asset_list()` con try/except `ImportError` + fallback `_FALLBACK_ASSET_LIST` (30 asset statici). `pyproject.toml` non include `sft-assets` come dep fino a quando 03-01 non sarà mergeato. `project.json` non include `sft-assets` in `implicitDependencies` per evitare Nx build failure
- **Impact:** OQ5 resolution funziona correttamente con fallback; quando sft-assets sarà disponibile, il try block lo utilizzerà automaticamente
- **Files modified:** `cmapss.py`, `project.json`, `pyproject.toml`
- **Commit:** f439490

## Known Stubs

Nessun stub che impedisce il funzionamento del piano. Note:
- `CHECKSUMS.txt` contiene placeholder SHA256 (`<sha256_cmapss_fd001>`, ecc.) — sostituiti al primo download manuale (by design, A4/A10)
- `sft-assets` non è nel `pyproject.toml` come dep (parallel Wave 1) — quando 03-01 mergeato, aggiungere `sft-assets` al `pyproject.toml` deps

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: supply-chain | packages/sft-tools/pyproject.toml | Nuove deps `langchain-core>=1.0,<2.0`, `asyncpg>=0.30`, `pandas>=2.2` — già approved in RESEARCH §Package Legitimacy Audit |

## Self-Check: PASSED

Verifica file creati:
- packages/sft-tools/pyproject.toml: FOUND
- packages/sft-tools/src/sft_tools/replay/cmapss.py: FOUND
- packages/sft-tools/src/sft_tools/timescale/query.py: FOUND
- scripts/download-replay-datasets.py: FOUND
- simulators/sim-textile/replay-data/.gitkeep: FOUND
- simulators/sim-textile/replay-data/CHECKSUMS.txt: FOUND

Verifica commit:
- f439490: FOUND (Task 1 — sft-tools scaffold + 3 Tools)
- 0ec0235: FOUND (Task 2 — download script + gitignore)

Test: 34 passed in 0.45s
