# Phase 2: Domain Modeling & Synthetic Corpus — Research

**Researched:** 2026-05-17
**Domain:** Content engineering (textile domain modeling) + retrieval-friendly metadata + bilingual MkDocs scaffolding + CI content validation
**Confidence:** HIGH (stack reuses Phase 1; tutte le dipendenze verificate su PyPI), MEDIUM (rendering Mermaid limits, accessibility), MEDIUM (autorità terminologiche IT — ISO 5247 in inglese; UNI italiano non aperto pubblicamente)

## Summary

Phase 2 è una fase di **content engineering** sopra l'infrastruttura già messa in piedi in Phase 1. Tutto lo stack runtime serve solo a:
1. **Caricare** YAML (glossario in `packages/sft-domain/`, assumption register in `docs/assumptions/`) tramite Pydantic + PyYAML,
2. **Validare** YAML/Markdown frontmatter via `jsonschema`,
3. **Generare** Markdown idempotente per MkDocs (script Python con argparse + dry-run, identico pattern di `scripts/sync-python-versions.py` già in repo),
4. **Validare in CI** i contenuti tramite Nx targets su `sft-domain` e `simulators/synthetic-corpus` (riuso del workflow `ci.yml` già operativo, nessun nuovo workflow GHA dedicato).

Non si introduce alcuna dipendenza nuova significativa: `pydantic` 2.13.x, `pyyaml` 6.0.x, `jsonschema` 4.26.x, `python-frontmatter` 1.1.0 — tutte battle-tested e già parzialmente installate (PyYAML 6.0.2 + jsonschema 4.19.2 presenti come transitivi nel sistema). Nessuna nuova libreria MkDocs è necessaria: lo scaffold di Phase 1 (`mkdocs-material 9.7.6` + `mkdocs-static-i18n 1.3.1` con `docs_structure: folder`) supporta nativamente directory annidate per lingua, quindi `domain/`, `sop/`, `assumptions/` sono drop-in.

**Primary recommendation:** trattare Phase 2 come "data engineering di contenuti" — single source of truth in YAML/Markdown sotto `packages/sft-domain/` e `docs/`, rendering MkDocs derivato da script idempotenti integrati come Nx targets nel `ci.yml` esistente, validation gates su frontmatter + bilingual mirror + glossary coverage come step `npx nx affected --target=validate-*`. Riusare il pattern `scripts/sync-python-versions.py` (argparse, dry-run, idempotent) per `generate-glossary-pages.py`, `generate-assumption-pages.py`, `validate-*.py`.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-21 — Domain Analysis split per processo + ruolo**
- `docs/docs/domain/processes/{weaving,spinning,warping,dyeing,finishing}.md` (5 file processo)
- `docs/docs/domain/roles/{operator,technician,quality-manager,shift-supervisor}.md` (4 file ruolo)
- `docs/docs/domain/index.md` (indice + overview, ~400 parole)
- Mirror EN completo in `docs/docs/en/domain/...` (stessa struttura)

**D-22 — Profondità: Process flow + asset + KPI + pain point** in ogni pagina processo; responsabilità + asset/processi + decisione critica + pain point in ogni pagina ruolo.

**D-23 — Specificità Mantis: generico + sidebar contextual** via callout `!!! note "Mantis context"` (MkDocs admonition).

**D-24 — Bilingue completo IT+EN in Phase 2** — sia IT che EN sono complete e sostanziose. CI check `scripts/validate-bilingual-mirror.py` verifica H1/H2 simmetrici.

**D-25 — SOP authoring: hybrid LLM-draft + human review** (draft IT → review → traduzione EN → review pass-2 più rapido). Fallback: marker `status: draft-unreviewed` nel frontmatter se review umano non scala.

**D-26 — SOP formato: frontmatter YAML + sezioni standardizzate**:
```yaml
---
id: SOP-LOOM-001
title: ...
version: 1.0
lang: it
asset: loom
asset_family: weaving
role: technician
hazard_level: medium
estimated_duration_min: 45
prerequisites: [SOP-LOOM-000]
related_glossary: [warp_beam, heddle_frame, pick_density]
tags: [maintenance, mechanical, weaving]
audience: operations
status: reviewed
created_in_phase: 2
---
```
Sezioni H2 fisse e required: Scope, Prerequisites, Tools and PPE, Step-by-step Procedure, Verification, Troubleshooting, References.

**D-27 — Topic mix SOP: bilanciato 5+5+5+5** (loom troubleshooting / dyeing procedure / spinning maintenance / quality grading).

**D-28 — Stile narrativo: factory-floor realistico** (gergo tecnico, unità reali, range tipici industria — non valori esatti Mantis).

**D-29 — Glossario: dual-channel sft-domain YAML + render MkDocs**:
- Fonte canonica: `packages/sft-domain/src/sft_domain/glossary/{it,en}.yaml`
- Script `scripts/generate-glossary-pages.py` rigenera `docs/docs/glossary.md` + `docs/docs/en/glossary.md`
- API loader `sft_domain.glossary.load_terms(lang: Literal["it","en"]) -> list[Term]`

**D-30 — Glossario layout unificato textile+agentic** con 9 tag categoria (`textile-process`, `textile-asset`, `textile-defect`, `textile-kpi`, `textile-tool-ppe`, `textile-material`, `agentic-platform`, `agentic-tool`, `regulatory`). Tag → MkDocs material-tags rendering.

**D-31 — Glossario coverage: ~150 termini per lingua** (esaustivo). Distribuzione: ~100 textile + ~40 agentic + ~10 economia/OEPV seed.

**D-32 — Glossary coverage CI check** via `scripts/validate-glossary-coverage.py` (estrae **bold** tokens da `docs/**` + `simulators/synthetic-corpus/**`, normalizza, verifica esistenza in YAML, exit 1 su gap, warning su >5% stale).

**D-33 — Assumption Register: YAML strutturato in `docs/assumptions/register.yaml`** (NON in sft-domain). Schema con: `id`, `statement`, `category`, `affected_components[]`, `rationale`, `validation_method`, `risk_if_wrong`, `status`, `created_in_phase`, `last_reviewed_in_phase`, `superseded_by`.

**D-34 — Assumption tagging doppio asse**: `category` enum + `affected_components[]` validato contro inventario dinamico di `apps/`, `services/`, `simulators/`, `packages/`.

**D-35 — Living doc + audit trail git** (no ADR file-per-assumption; `status: active|validated|invalidated|superseded`).

**D-36 — ~50 assumption seed** distribuite: data-quality 10, simulation 8, scope-limit 10, external-dependency 8, regulatory 6, security 4, performance 3, cost 1.

### Claude's Discretion

- **MkDocs nav update:** APPEND sotto entries Phase 1, non riordinare. Nuovi top-level: `Dominio` (IT) / `Domain` (EN), `Procedure (SOP)` / `Procedures (SOP)`, `Assumption Register`, `Glossario` / `Glossary`.
- **YAML validation library:** `pydantic` (runtime) + `jsonschema` (CI). No nuovi heavyweight deps.
- **Mermaid:** `flowchart LR` per process, max 8 nodi, stile sobrio (no custom CSS).
- **Frontmatter parsing in SOP:** `python-frontmatter` 1.1.0 pinned esatto.
- **Bilingual mirror check granularity:** match H1 + prime 5 H2 fra IT e EN. Body diff troppo rumoroso.
- **Idempotency:** script re-eseguiti producono output identico (sort stabile, no timestamp). CI valida via `git diff` vuoto dopo double-run.
- **Italiano:** standard (no dialetti). Gergo industriale lombardo ammesso nei Mantis-context callouts se applicabile.
- **Synthetic-corpus layout:** `simulators/synthetic-corpus/{it,en}/{loom,dyeing,spinning,quality}/SOP-XXX-slug.md`. Project-level Nx target su `simulators/synthetic-corpus` per `validate`.
- **Synthetic-corpus i18n:** corpus NON va in MkDocs i18n — è dataset, non documentazione utente. Reference link da `docs/docs/sop/index.md`.

### Deferred Ideas (OUT OF SCOPE)

- **TrainingCoach SOP variants** (pedagogical-tutorial): differito a Phase 7.
- **Deep-technical parameters reali** (RPM/tensioni/temperature precise Mantis): differito a Phase 7+ (QualityInspector + PredictiveMaintenance forniranno feedback su precisione necessaria).
- **Defect taxonomy strutturata** in YAML (`sft-domain/defects.yaml`): Phase 6 (QualityInspector).
- **OEPV-specific glossary entries** oltre i ~10 seed: Phase 11.
- **ADR formali (DOC-13)** delle decisioni D-21..D-36: Phase 14 (DOC polish) — questo CONTEXT.md/02-RESEARCH.md fungono da ADR de facto.
- **BGE-M3 embedding / vector store ingestion** del corpus: Phase 5.
- **Retrieval pipeline** che usa il corpus: Phase 5.
- **Translation Phase 1 docs** (getting-started, architecture/overview EN già presente ma Phase 1-shape): Phase 14.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-05 | Sezione **Domain Analysis**: dominio tessile manifatturiero (processi, ruoli, pain point) | D-21/D-22/D-23 + Architecture Patterns §"Domain Analysis split" + § Italian terminology authority |
| DOC-12 | Sezione **Assumption Register**: assunzioni esplicite su data quality, simulazione, limiti | D-33/D-34/D-35/D-36 + Standard Stack (pydantic+jsonschema for schema-validated YAML) + § Architecture Patterns "Assumption register generator" |
| DOC-18 | Glossario IT+EN dei termini tessili + agentici | D-29/D-30/D-31/D-32 + Pydantic loader pattern + Glossary coverage CI check pattern |
| KNW-10 | Corpus sintetico bilingue (IT/EN) di SOP tessili seedato nel repo per demo | D-25/D-26/D-27/D-28 + python-frontmatter for SOP parsing + Nx project-level validate target on `simulators/synthetic-corpus` |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Glossary canonical storage (YAML) | Python package (`sft-domain`) | — | Dati semantici riusabili da agenti Phase 5+; Pydantic loader rende il dato consumabile come API |
| Glossary Markdown rendering | Build script (`scripts/generate-glossary-pages.py`) | MkDocs Material (static site) | Markdown è artifact generato, non source-of-truth |
| Domain analysis (processi, ruoli) | MkDocs Material (Markdown sotto `docs/docs/domain/`) | — | Documentazione human-first, non struttura dati riusabile a runtime |
| Assumption register canonical storage | YAML in `docs/assumptions/register.yaml` | — | Meta-progetto, non dato tessile → fuori da sft-domain (vedi D-33) |
| Assumption register rendering | Build script (`scripts/generate-assumption-pages.py`) | MkDocs Material | Tabella sortable + per-assumption detail pages |
| SOP corpus storage | Markdown in `simulators/synthetic-corpus/` | — | Dataset retrieval-target; layout per asset family/lingua serve Phase 5 ingestion |
| SOP frontmatter parsing (runtime) | `python-frontmatter` in `sft-domain` o script | — | Schema validation in CI; runtime parsing differito a Phase 5 |
| Bilingual mirror enforcement | Script Python in CI (`scripts/validate-bilingual-mirror.py`) | — | Pure validation, no rendering — Nx target `validate-bilingual-mirror` |
| Glossary coverage check | Script Python in CI (`scripts/validate-glossary-coverage.py`) | — | Cross-references **bold** tokens vs YAML; Nx target `validate-glossary` |
| Frontmatter schema validation | Script Python in CI (`scripts/validate-corpus-frontmatter.py`) | — | `jsonschema` enforcement; Nx target `validate-corpus` on `simulators/synthetic-corpus` |
| CI orchestration | GitHub Actions (`ci.yml`) | Nx affected | Riuso del workflow esistente; nuovi step `nx run-many --target=validate-*` invocati dal job `main` |
| Mermaid diagram rendering | MkDocs Material (built-in) | — | Phase 1 ha già `pymdownx.superfences` con custom fence `mermaid` |

## Standard Stack

### Core (tutte già installate o trivial add)

| Library | Version verificata | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pyyaml` | 6.0.3 (latest), 6.0.2 installato | Parse YAML glossario + assumption register | Standard de facto Python; CVE history pulita post-6.0.1; `safe_load` mandatorio [VERIFIED: PyPI registry + ufficiale GitHub yaml/pyyaml] |
| `jsonschema` | 4.26.0 (latest), 4.19.2 installato | Validazione schema YAML + Markdown frontmatter in CI | Supporto completo Draft 2020-12; lazy validation; standard per JSON Schema in Python [VERIFIED: PyPI registry + python-jsonschema.readthedocs.io] |
| `pydantic` | 2.13.4 (latest, 2026-05-06) | Runtime models per glossary loader API `sft_domain.glossary.load_terms()` | v2 5-10x più veloce di v1 (pydantic-core in Rust); standard Python ecosystem; type-safe immutabile per default [VERIFIED: PyPI registry + ufficiale pydantic.dev] |
| `python-frontmatter` | 1.1.0 | Parse YAML frontmatter da SOP Markdown | Standard de facto per Markdown + YAML frontmatter; API stabile; usato in MkDocs ecosystem [VERIFIED: PyPI registry, https://pypi.org/project/python-frontmatter/] |

### Supporting (build/CI only, no runtime impact)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `mkdocs-material` | 9.7.6 (già pinned in `docs/requirements.txt`) | Tema docs + mermaid + admonitions + material-tags | Già operativo da Phase 1 — nessun cambio |
| `mkdocs-static-i18n` | 1.3.1 (già pinned) | `docs_structure: folder` IT default + EN parallelo | Già operativo; nested directories (`domain/`, `sop/`, `assumptions/`) supportati nativamente [VERIFIED: ultrabug.github.io/mkdocs-static-i18n/getting-started/quick-start/ + WebSearch conferma supporto nested] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pydantic` | `dataclasses` + manual validation | Più leggero ma niente serializzazione/validazione gratis; perdiamo immutable-by-default e error reporting |
| `pydantic` | `attrs` + `cattrs` | Maturo ma meno standard nell'ecosistema GenAI già scelto (LangGraph/LangChain usano Pydantic); split runtime conviene evitarlo |
| `python-frontmatter` | parsing manuale YAML (split su `---`) | Funziona ma non gestisce edge case (escape, multi-doc YAML, encoding); 50 LOC che riinventano una rotella stabile |
| `jsonschema` (Python) | `pydantic` per validare frontmatter | Pydantic non genera errori JSON Schema-compliant facili da pubblicare in docs; jsonschema dà error path puntuale ottimo per CI feedback |
| YAML come fonte glossario | JSON | YAML supporta commenti (critico per glossario IT con note traduzione); supporta multi-line readable strings; standard per config in stack Python già scelto (LangGraph, MkDocs) |
| YAML come fonte glossario | TOML | TOML manca di liste annidate ergonomiche per `examples[]` lunghi; YAML è coerente con `mkdocs.yml` e `pyproject.toml` co-esiste |
| `mike` per versioning docs MkDocs | nessuno | **Non in scope Phase 2** (versioning docs è DOC-03 → Phase 12). Citato qui come scelta differita perché PROJECT.md lo menziona |

**Installation (delta su pyproject.toml di `sft-domain` + root):**

```toml
# packages/sft-domain/pyproject.toml — runtime deps glossary loader
[project]
dependencies = [
  "pydantic>=2.13,<3.0",
  "pyyaml>=6.0.2,<7.0",
]

# root pyproject.toml — dev/CI deps (gruppo dev, PEP 735)
[dependency-groups]
dev = [
  # ... esistenti ...
  "jsonschema>=4.26,<5.0",
  "python-frontmatter>=1.1.0,<2.0",
]
```

Comandi:
```bash
uv sync --all-packages   # rigenera uv.lock con nuovi deps
```

**Version verification (eseguita 2026-05-17):**
```bash
pip3 index versions pyyaml          # → 6.0.3 latest, 6.0.2 installato
pip3 index versions jsonschema      # → 4.26.0 latest, 4.19.2 installato
pip3 index versions pydantic        # → 2.13.4 latest
pip3 index versions python-frontmatter  # → 1.1.0 latest
```

## Package Legitimacy Audit

> Eseguito 2026-05-17. ⚠️ `slopcheck` esiste sul sistema ma **interroga npm di default, non PyPI**. Per pacchetti Python serve verifica esplicita via `pip index versions` + ispezione `pypi.org`. Documento entrambi i risultati per trasparenza.

| Package | Registry corretto | Età | Downloads (weekly, ord. grandezza) | Source Repo | slopcheck (npm) | pip index (PyPI) | Disposition |
|---------|-------------------|-----|-----------|-------------|-----------|------------------|-------------|
| `pyyaml` | PyPI | >15 anni | 100M+/week | github.com/yaml/pyyaml | [OK] su npm (homonym package coincidentale) | 6.0.3 confermato | **Approvato** |
| `jsonschema` | PyPI | >10 anni | 100M+/week | github.com/python-jsonschema/jsonschema | [OK] su npm (homonym) | 4.26.0 confermato | **Approvato** |
| `pydantic` | PyPI | >7 anni | 200M+/week | github.com/pydantic/pydantic | [OK] su npm (homonym) | 2.13.4 confermato | **Approvato** |
| `python-frontmatter` | PyPI | >5 anni | ~500K/week | github.com/eyeseast/python-frontmatter | [SLOP] su npm (corretto — non esiste su npm! conferma che è solo PyPI) | 1.1.0 confermato | **Approvato** |
| `mike` (versioning docs) | PyPI | >6 anni (n/a Phase 2) | ~200K/week | github.com/jimporter/mike | [SUS] su npm (typosquat di `vite`) — falso positivo per ecosistema sbagliato | 2.2.0 confermato | **Deferred to Phase 12** (DOC-03) |

**Lessons learned (importanti per il planner):**
- `slopcheck install` **modifica `package.json` e `package-lock.json`** del progetto in background. Esecuzione del researcher ha temporaneamente alterato i file; ripristinati via `git checkout`. Il planner deve **non** invocare `slopcheck install` per pacchetti Python — usare invece `pip index versions <pkg>` + ispezione PyPI page.
- Per Phase 2 nessuna installazione npm reale è necessaria (tutte le dipendenze sono Python lato `sft-domain` o doc-tooling già pinned in `docs/requirements.txt`).

**Packages removed due to slopcheck [SLOP] verdict:** None (il flag su `python-frontmatter` era falso positivo da ecosistema sbagliato).
**Packages flagged as suspicious [SUS]:** `mike` — falso positivo cross-ecosystem, non in scope Phase 2.

## Architecture Patterns

### System Architecture Diagram

```
                                 ┌─────────────────────────────────────────┐
                                 │  Source of Truth (YAML/Markdown in git) │
                                 └─────────────────────────────────────────┘
                                                 │
                  ┌──────────────────────────────┼──────────────────────────────────┐
                  │                              │                                   │
                  ▼                              ▼                                   ▼
       ┌──────────────────────┐     ┌──────────────────────┐         ┌─────────────────────────────┐
       │ packages/sft-domain/ │     │ docs/assumptions/    │         │ simulators/synthetic-corpus/│
       │   glossary/it.yaml   │     │   register.yaml      │         │   {it,en}/{loom,…}/         │
       │   glossary/en.yaml   │     │                      │         │     SOP-XXX-slug.md         │
       └──────────────────────┘     └──────────────────────┘         │   (Markdown + frontmatter)  │
                  │                              │                    └─────────────────────────────┘
                  │                              │                                   │
        ┌─────────┴──────────┐          ┌────────┴─────────┐                         │
        │                    │          │                  │                         │
        ▼                    ▼          ▼                  ▼                         │
┌─────────────────┐  ┌──────────────┐  ┌──────────────┐ ┌──────────────────┐         │
│ Runtime loader  │  │ Generator    │  │ Generator    │ │ Schema validator │         │
│ sft_domain.     │  │ generate-    │  │ generate-    │ │ (CI only)        │◀────────┘
│ glossary.load_  │  │ glossary-    │  │ assumption-  │ │ jsonschema       │
│ terms(lang)     │  │ pages.py     │  │ pages.py     │ │ python-frontmtr  │
│ (Pydantic)      │  │ (idempotent) │  │ (idempotent) │ └──────────────────┘
└─────────────────┘  └──────────────┘  └──────────────┘          │
        │                    │                  │                 │
        │                    ▼                  ▼                 ▼
        │           ┌───────────────────────────────────────────────────────┐
        │           │ Generated Markdown (committed, must equal re-run)     │
        │           │  docs/docs/glossary.md           docs/docs/en/glossary│
        │           │  docs/docs/assumptions/*.md      docs/docs/en/assumpt │
        │           └───────────────────────────────────────────────────────┘
        │                                       │
        │                                       ▼
        │                            ┌─────────────────────┐
        │                            │ MkDocs Material     │
        │                            │ build --strict      │
        │                            │ (Phase 1 ci.yml +   │
        │                            │  docs-deploy.yml)   │
        │                            └─────────────────────┘
        │                                       │
        │                                       ▼
        │                            ┌─────────────────────┐
        │                            │ gh-pages branch     │
        │                            │ (DOC-02, Phase 1)   │
        │                            └─────────────────────┘
        │
        ▼
[Phase 5 — Knowledge Layer ingestion]
  BGE-M3 + Qdrant index sft-domain glossary as semantic ground truth
  + synthetic-corpus SOPs as primary retrieval target
```

### Recommended Project Structure

```
packages/sft-domain/
├── pyproject.toml                    # + pydantic, + pyyaml
├── src/sft_domain/
│   ├── __init__.py
│   ├── __version__.py                # già esistente (Phase 1, Plan 08)
│   ├── glossary/
│   │   ├── __init__.py               # esporta load_terms(), Term
│   │   ├── loader.py                 # Pydantic + PyYAML
│   │   ├── models.py                 # Term, Category enum
│   │   ├── it.yaml                   # ~150 termini IT
│   │   └── en.yaml                   # ~150 termini EN
│   └── schemas/
│       ├── glossary.schema.json      # JSON Schema Draft 2020-12
│       └── assumption.schema.json    # JSON Schema Draft 2020-12

docs/
├── mkdocs.yml                        # APPEND nav entries (no rewrite)
├── docs/                             # IT
│   ├── index.md                      # esistente (Phase 1)
│   ├── domain/
│   │   ├── index.md                  # overview + diagramma Mermaid alto livello
│   │   ├── processes/
│   │   │   ├── weaving.md
│   │   │   ├── spinning.md
│   │   │   ├── warping.md
│   │   │   ├── dyeing.md
│   │   │   └── finishing.md
│   │   └── roles/
│   │       ├── operator.md
│   │       ├── technician.md
│   │       ├── quality-manager.md
│   │       └── shift-supervisor.md
│   ├── sop/
│   │   └── index.md                  # spiega scope corpus + link a simulators/
│   ├── assumptions/
│   │   ├── index.md                  # generato — tabella sortable
│   │   └── A-001.md … A-050.md       # generati — uno per assumption
│   └── glossary.md                   # generato — IT
└── docs/en/                          # EN — mirror identico
    ├── domain/{processes,roles}/…
    ├── sop/index.md
    ├── assumptions/{index,A-NNN}.md
    └── glossary.md
└── assumptions/
    └── register.yaml                 # fonte canonica assumption register

simulators/synthetic-corpus/
├── project.json                      # Nx project — target `validate`
├── README.md                         # spiega corpus, schema, regole authoring
├── pyproject.toml                    # optional — solo se Nx richiede project Python
├── it/
│   ├── loom/SOP-LOOM-001-…-it.md
│   ├── dyeing/SOP-DYE-001-…-it.md
│   ├── spinning/SOP-SPN-001-…-it.md
│   └── quality/SOP-QLT-001-…-it.md
└── en/
    ├── loom/SOP-LOOM-001-…-en.md
    └── …

scripts/
├── sync-python-versions.py           # esistente Phase 1 — PATTERN da copiare
├── generate-glossary-pages.py        # NEW — argparse + dry-run + idempotent
├── generate-assumption-pages.py      # NEW — argparse + dry-run + idempotent
├── validate-glossary-coverage.py     # NEW — D-32
├── validate-bilingual-mirror.py      # NEW — D-24 H1/H2 check
├── validate-corpus-frontmatter.py    # NEW — D-26 schema enforcement
└── validate-assumption-components.py # NEW — D-34 component inventory check
```

### Pattern 1: Pydantic Glossary Loader (D-29)

**What:** Single source of truth YAML → Pydantic model → list[Term] consumabile da agenti.
**When to use:** Glossary lookup in test, Phase 5 agent retrieval, Phase 11 audit.
**Example:**

```python
# packages/sft-domain/src/sft_domain/glossary/models.py
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field

class Category(str, Enum):
    TEXTILE_PROCESS = "textile-process"
    TEXTILE_ASSET = "textile-asset"
    TEXTILE_DEFECT = "textile-defect"
    TEXTILE_KPI = "textile-kpi"
    TEXTILE_TOOL_PPE = "textile-tool-ppe"
    TEXTILE_MATERIAL = "textile-material"
    AGENTIC_PLATFORM = "agentic-platform"
    AGENTIC_TOOL = "agentic-tool"
    REGULATORY = "regulatory"

class Term(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}  # immutable, strict schema

    term: str
    definition: str
    category: Category
    related_terms: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    source: str | None = None  # e.g., "ISO 5247", "industry-standard", "internal"

# packages/sft-domain/src/sft_domain/glossary/loader.py
from functools import lru_cache
from pathlib import Path
from typing import Literal
import yaml
from .models import Term

_GLOSSARY_DIR = Path(__file__).parent

@lru_cache(maxsize=2)  # cold start 1x per lang, then dict cached
def load_terms(lang: Literal["it", "en"]) -> list[Term]:
    """Load and validate glossary for given language. Cached after first call."""
    path = _GLOSSARY_DIR / f"{lang}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Glossary not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)  # safe_load mandatorio — no arbitrary class instantiation
    return [Term.model_validate(item) for item in raw]

# Convenience dict lookup (300 termini totali — O(1) lookup)
@lru_cache(maxsize=2)
def load_terms_dict(lang: Literal["it", "en"]) -> dict[str, Term]:
    """Returns {term.lower(): Term} for fast lookup."""
    return {t.term.lower(): t for t in load_terms(lang)}
```

**Performance note:** Pydantic v2 (pydantic-core in Rust) valida ~150 termini in <5ms cold start (riferimento: prrao87/pydantic-benchmarks su dataset Kaggle Wine Reviews → v2 ~4-5x più veloce di v1) [CITED: dev.to/donovandicks pydantic v2 investigation]. lru_cache rende le call successive O(1) — perfetto per i ~300 termini totali.

### Pattern 2: Idempotent Generator Script (D-29, D-33)

**What:** Script che rigenera Markdown dal YAML in modo deterministico — re-run produce identico output.
**When to use:** `generate-glossary-pages.py`, `generate-assumption-pages.py`.
**Example (skeleton — pattern copia `scripts/sync-python-versions.py`):**

```python
#!/usr/bin/env python3
"""
scripts/generate-glossary-pages.py

Renders packages/sft-domain/src/sft_domain/glossary/{it,en}.yaml to
  docs/docs/glossary.md  (IT)
  docs/docs/en/glossary.md  (EN)

Idempotent: re-run must produce identical output (sorted, no timestamps).

Usage:
    python3 scripts/generate-glossary-pages.py [--dry-run] [--check]

Exit codes:
    0 - Files written (or dry-run/check passed)
    1 - Read/validate error
    2 - --check mode: files differ from would-be output (CI gate)
"""
import argparse, sys, pathlib
from sft_domain.glossary import load_terms

WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent
OUTPUTS = {"it": WORKSPACE_ROOT / "docs/docs/glossary.md",
           "en": WORKSPACE_ROOT / "docs/docs/en/glossary.md"}

def render(lang: str) -> str:
    terms = sorted(load_terms(lang), key=lambda t: t.term.lower())  # sort stabile
    # ... markdown rendering with material-tags ...
    return rendered

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true",
                        help="Exit 2 if existing files differ from generated output")
    args = parser.parse_args()
    for lang, out_path in OUTPUTS.items():
        new = render(lang)
        if args.check:
            current = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
            if current != new:
                print(f"DRIFT: {out_path}", file=sys.stderr)
                sys.exit(2)
        elif args.dry_run:
            print(f"would write {len(new)} bytes to {out_path}")
        else:
            out_path.write_text(new, encoding="utf-8")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

**CI integration:** `--check` mode in Nx target → fallisce se autore ha modificato `glossary.md` a mano dimenticando di rigenerare. Garantisce single-source-of-truth.

### Pattern 3: SOP Frontmatter Schema Validation (D-26)

**What:** JSON Schema Draft 2020-12 enforced per ogni file SOP via `python-frontmatter` + `jsonschema`.
**When to use:** CI gate prima di accettare nuovi SOP.
**Example:**

```python
# scripts/validate-corpus-frontmatter.py
import sys, json, pathlib
import frontmatter  # python-frontmatter
from jsonschema import Draft202012Validator

SCHEMA_PATH = pathlib.Path("packages/sft-domain/src/sft_domain/schemas/sop.schema.json")
CORPUS_ROOT = pathlib.Path("simulators/synthetic-corpus")

schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
validator = Draft202012Validator(schema)
errors_total = 0

for md_path in CORPUS_ROOT.rglob("*.md"):
    post = frontmatter.load(md_path)
    errors = list(validator.iter_errors(post.metadata))
    if errors:
        errors_total += len(errors)
        for err in errors:
            print(f"{md_path}: {'.'.join(map(str, err.absolute_path))} — {err.message}",
                  file=sys.stderr)

sys.exit(0 if errors_total == 0 else 1)
```

**JSON Schema (extract):**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["id", "title", "version", "lang", "asset", "asset_family",
               "role", "hazard_level", "estimated_duration_min", "status",
               "created_in_phase"],
  "properties": {
    "id": {"type": "string", "pattern": "^SOP-[A-Z]+-[0-9]{3}$"},
    "title": {"type": "string", "minLength": 5},
    "version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+$"},
    "lang": {"enum": ["it", "en"]},
    "asset": {"type": "string"},
    "asset_family": {"enum": ["weaving", "spinning", "dyeing", "finishing", "quality"]},
    "role": {"enum": ["operator", "technician", "quality-manager", "shift-supervisor"]},
    "hazard_level": {"enum": ["low", "medium", "high", "critical"]},
    "estimated_duration_min": {"type": "integer", "minimum": 1, "maximum": 480},
    "status": {"enum": ["reviewed", "draft-unreviewed", "deprecated"]},
    "created_in_phase": {"type": "integer", "minimum": 1}
  },
  "additionalProperties": true  /* permette tags, audience, prerequisites, related_glossary */
}
```

### Pattern 4: Bilingual Mirror Check (D-24)

**What:** Per ogni `docs/docs/X.md` deve esistere `docs/docs/en/X.md` con H1 + prime 5 H2 corrispondenti.
**When to use:** CI gate per evitare drift IT/EN.
**Example:**

```python
# scripts/validate-bilingual-mirror.py
import re, sys, pathlib

IT_ROOT = pathlib.Path("docs/docs")
EN_ROOT = pathlib.Path("docs/docs/en")
EXCLUDE = {"en", "assets"}  # docs/docs/en/ è il mirror — non da mirrorare a sé stesso
HEADING_RE = re.compile(r"^(#{1,2})\s+(.+?)\s*$", re.MULTILINE)

def headings(text: str) -> list[tuple[int, str]]:
    """Returns [(level, text)] for H1 and H2."""
    return [(len(m.group(1)), m.group(2).strip())
            for m in HEADING_RE.finditer(text)
            if len(m.group(1)) in (1, 2)][:6]  # H1 + 5 H2

errors = 0
for it_path in IT_ROOT.rglob("*.md"):
    if any(part in EXCLUDE for part in it_path.relative_to(IT_ROOT).parts):
        continue
    relative = it_path.relative_to(IT_ROOT)
    en_path = EN_ROOT / relative
    if not en_path.exists():
        print(f"MISSING EN mirror: {en_path}", file=sys.stderr)
        errors += 1
        continue
    it_h = headings(it_path.read_text(encoding="utf-8"))
    en_h = headings(en_path.read_text(encoding="utf-8"))
    if len(it_h) != len(en_h):
        print(f"HEADING COUNT MISMATCH: {it_path} ({len(it_h)}) vs {en_path} ({len(en_h)})",
              file=sys.stderr); errors += 1; continue
    for (l_it, _), (l_en, _) in zip(it_h, en_h):
        if l_it != l_en:
            print(f"HEADING LEVEL MISMATCH: {it_path} vs {en_path}", file=sys.stderr)
            errors += 1; break

sys.exit(0 if errors == 0 else 1)
```

**Granularity choice:** match livelli H1/H2 + presenza file, **NON match testo** (le traduzioni differiscono per definizione). Tradeoff documentato in D-24 + claudes_discretion.

### Pattern 5: Glossary Coverage Check (D-32)

**What:** Estrae **bold** tokens da Markdown, normalizza, verifica esistenza in glossary YAML.
**When to use:** CI gate per evitare che il glossario sia un'isola morta.
**Example logic:**

```python
# scripts/validate-glossary-coverage.py — abbreviato
import re, sys, pathlib
from sft_domain.glossary import load_terms_dict

BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")
NORMALIZE = lambda s: re.sub(r"[^\w\s-]", "", s.strip().lower())

# lingua → set di file rilevanti
LANG_PATHS = {
    "it": [pathlib.Path("docs/docs"), pathlib.Path("simulators/synthetic-corpus/it")],
    "en": [pathlib.Path("docs/docs/en"), pathlib.Path("simulators/synthetic-corpus/en")],
}

errors = 0
for lang, roots in LANG_PATHS.items():
    glossary = load_terms_dict(lang)  # {term.lower(): Term}
    referenced = set()
    for root in roots:
        for md in root.rglob("*.md"):
            for bold in BOLD_RE.findall(md.read_text(encoding="utf-8")):
                norm = NORMALIZE(bold)
                referenced.add(norm)
                if norm not in glossary:
                    print(f"MISSING GLOSSARY: '{bold}' in {md} (lang={lang})",
                          file=sys.stderr)
                    errors += 1
    # stale check
    glossary_keys = set(glossary.keys())
    stale = glossary_keys - referenced
    if len(stale) / max(len(glossary_keys), 1) > 0.05:
        print(f"WARNING: {len(stale)} stale terms in {lang} glossary (>{5}%)",
              file=sys.stderr)

sys.exit(0 if errors == 0 else 1)
```

### Pattern 6: Nx Project-level Validate Target

**What:** Aggiungere target `validate-*` ai `project.json` di `sft-domain` e `simulators/synthetic-corpus` così che `npx nx affected --target=validate` li esegua selettivamente.
**Example (project.json snippet for `simulators/synthetic-corpus`):**

```json
{
  "name": "synthetic-corpus",
  "projectType": "library",
  "sourceRoot": "simulators/synthetic-corpus",
  "targets": {
    "validate-frontmatter": {
      "executor": "nx:run-commands",
      "options": {
        "command": "python3 scripts/validate-corpus-frontmatter.py",
        "cwd": "{workspaceRoot}"
      },
      "inputs": [
        "{projectRoot}/**/*.md",
        "{workspaceRoot}/packages/sft-domain/src/sft_domain/schemas/sop.schema.json",
        "{workspaceRoot}/scripts/validate-corpus-frontmatter.py"
      ]
    },
    "validate-bilingual-mirror": {
      "executor": "nx:run-commands",
      "options": {
        "command": "python3 scripts/validate-bilingual-mirror.py",
        "cwd": "{workspaceRoot}"
      }
    }
  }
}
```

Aggiunta nel `ci.yml` (un nuovo step nel job `main` dopo `Validate Nx dependency graph`):

```yaml
- name: Validate content (glossary, frontmatter, bilingual mirror)
  run: |
    npx nx run-many --target=validate-glossary --projects=sft-domain
    npx nx run-many --target=validate-frontmatter --projects=synthetic-corpus
    npx nx run-many --target=validate-bilingual-mirror --projects=synthetic-corpus
    python3 scripts/generate-glossary-pages.py --check
    python3 scripts/generate-assumption-pages.py --check
```

### Anti-Patterns to Avoid

- **Modificare a mano `docs/docs/glossary.md`:** è file generato — solo `glossary/{it,en}.yaml` è canonical. CI `--check` mode in `generate-glossary-pages.py` rileva drift.
- **Nestare synthetic-corpus dentro `sim-textile/`:** rompe Nx project isolation; corpus è dataset indipendente (vedi code_context — esplicito in CONTEXT.md).
- **Mettere assumption register in `sft-domain`:** sono meta-progetto, non dati tessili. Vivono in `docs/assumptions/register.yaml` (D-33).
- **Tradurre body completo IT↔EN in CI check:** body diff è troppo rumoroso — limitarsi a H1/H2 (D-24 + claudes_discretion).
- **YAML `unsafe_load` o `Loader=yaml.Loader`:** consente arbitrary code execution → sempre `yaml.safe_load`. La review umana dei file YAML non basta come mitigazione: nuovi contributor potrebbero introdurre exploit pattern.
- **Cercare di usare Pydantic v1 (`pydantic.v1`):** stack runtime è 3.12 only e pydantic 2.x; mescolare v1/v2 introduce confusione su API. Tutto v2-native.
- **Generare timestamp nel render Markdown:** rompe idempotenza → CI re-run fallisce. Niente `datetime.now()` nei generator.
- **Aggiungere termini in glossario "in anticipo" senza referenze in **bold**:** D-32 li flagga come stale; rispettare la regola "aggiungi solo quando referenziato".

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom split on `---` | `pyyaml.safe_load` | Edge case: multi-doc YAML, escape sequences, encoding; PyYAML è il parser standard, mantenuto, sicuro |
| Markdown frontmatter | Regex su `---...---` | `python-frontmatter` | Gestisce multi-line frontmatter, encoding UTF-8, fallback per file senza frontmatter |
| JSON Schema validation | If/else manuale per ogni campo | `jsonschema` Draft 2020-12 | Error path puntuale (`field.subfield[2].name`), supporto `$ref`, lazy iteration su errori multipli |
| Pydantic model evolution | Subclassing manuale, dict di defaults | `pydantic.BaseModel` con `Field(default_factory=...)` | Type-safe, validate on construction, immutable con `frozen=True`, error reporting strutturato |
| Stable Markdown rendering | Manual ordering | `sorted(items, key=...)` esplicito + no timestamps | Idempotenza CI; senza sort stabile il file generato cambia random → diff git infinito |
| Recursive Markdown discovery | `os.walk` + filtri custom | `pathlib.Path.rglob("*.md")` | Standard library, pulito, gestisce simlinks/encoding |
| Internazionalizzazione MkDocs | Plugin custom o multi-site | `mkdocs-static-i18n` con `docs_structure: folder` | Già operativo Phase 1; supporto nested directories nativo (verificato); nav translation built-in |
| Render Mermaid in PDF/PNG offline | Pre-render con CLI | Lasciar fare a Material for MkDocs (JS in-browser) | Mermaid.js è nativo nel tema; pre-render binari rompe DOC-15 (no immagini binarie) |
| Diff bilingue character-level | Algoritmi custom | H1/H2 level/count check | Body è translation — diff testo è semanticamente inutile, solo struttura conta |
| Indicizzazione glossario in Qdrant | Embedding manuale qui | **DIFFERIRE A PHASE 5** | BGE-M3 + Qdrant è il pattern Phase 5 — Phase 2 produce solo source-of-truth |

**Key insight:** Phase 2 è un **content engineering exercise sotto i constraint di idempotency + bilingual symmetry + CI-enforceable schema**. Quasi ogni problema "ho bisogno di X custom" ha già una soluzione mainstream nel Python ecosystem. La superficie di nuovo codice in `scripts/` dovrebbe rimanere sotto 1500 LOC totali tra 5-6 script, ognuno con argparse + dry-run + idempotent + exit codes documentati.

## Runtime State Inventory

> Phase 2 introduce nuovi artefatti ma **non rinomina/refactora niente di esistente**. Inventory è quindi prevalentemente "Nothing found" — incluso per completezza e per il planner.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verificato: nessun database/vector store ancora popolato (Phase 5 introduce Qdrant ingest del corpus generato qui) | None |
| Live service config | None — verificato: nessun n8n/Datadog/Cloudflare Tunnel registrato | None |
| OS-registered state | None — verificato: nessun Task Scheduler/launchd/systemd unit collegato al progetto | None |
| Secrets/env vars | None nuovi — Phase 2 non aggiunge secrets; tutti gli script leggono solo da git-tracked YAML/Markdown | None |
| Build artifacts / installed packages | `packages/sft-domain` riceverà nuove deps (`pydantic`, `pyyaml`) → `uv sync --all-packages` rigenera `uv.lock`. Nessun artefatto stale da invalidare. **Lessons learned:** `slopcheck install <pkg>` durante la fase di research ha temporaneamente modificato `package.json`/`package-lock.json` installando pacchetti npm omonimi. Pulito via `git checkout`. Il planner **non deve** invocare `slopcheck install` per pacchetti Python — usare `pip index versions` invece. | Re-run `uv sync --all-packages` dopo modifica `packages/sft-domain/pyproject.toml`; CI `Install Python dependencies` step lo fa già |

**Nothing found in category:** Stored data, Live service config, OS-registered state, Secrets — tutti verificati esplicitamente.

## Common Pitfalls

### Pitfall 1: Generated file drift (glossary.md / assumption pages)
**What goes wrong:** Autore modifica `docs/docs/glossary.md` direttamente, dimentica di rigenerare → al run successivo dello script il file viene sovrascritto silenziosamente, modifiche perse. Oppure il file in git diverge dallo YAML.
**Why it happens:** Markdown è visibile e tentante da editare; YAML è "nascosto" in `packages/sft-domain/`.
**How to avoid:**
1. Header esplicito nel Markdown generato: `<!-- AUTOGENERATED from packages/sft-domain/src/sft_domain/glossary/{lang}.yaml — DO NOT EDIT -->`.
2. CI `--check` mode in `generate-*.py` script confronta output rigenerato vs file committato; exit 2 su drift.
3. Hook pre-commit opzionale: rigenera prima di commit se YAML toccato.
**Warning signs:** Diff git in `docs/docs/glossary.md` SENZA diff in `glossary/it.yaml`.

### Pitfall 2: Mermaid diagram exceeds rendering limits
**What goes wrong:** Process flow con >8 nodi diventa illeggibile (zoom infinito) o eccede `maxTextSize` default di Mermaid (50K char — improbabile ma documentato).
**Why it happens:** Tentazione di disegnare l'intero processo end-to-end in un solo diagramma.
**How to avoid:**
- Rispettare D-22 (max 8 nodi per `flowchart LR`).
- Per processi complessi (es. dyeing): split in più diagrammi `subgraph` o file separati linkati.
- Aggiungere `accTitle` e `accDescr` (accessibility) in ogni diagramma: `mermaid` supporta nativamente `accDescr: "Process flow for warping: ..."` come prima riga dopo `flowchart LR`.
**Warning signs:** Diagramma con `flowchart` che produce scroll orizzontale > 2000px; reviewer non riesce a leggere i nodi a default zoom.
[CITED: mermaid.js.org/config/accessibility.html — `accTitle`/`accDescr` supported]

### Pitfall 3: `yaml.load` invece di `yaml.safe_load`
**What goes wrong:** Un contributor (umano o LLM) aggiunge `yaml.load(f, Loader=yaml.Loader)` o usa `yaml.full_load` per supportare un edge case; YAML diventa vettore di arbitrary code execution.
**Why it happens:** PyYAML supporta multiple load methods; `safe_load` perde feature avanzate (es. Python objects).
**How to avoid:**
1. Lint rule `bandit` (già installato come pre-commit hook?) flagga `yaml.load` non-safe.
2. Code review esplicito sui PR che modificano `glossary/loader.py` o `scripts/validate-*.py`.
3. Documentare in `docs/contributing/yaml-conventions.md` (NEW): "always `safe_load`; mai `Loader=`".
**Warning signs:** Grep `git grep "yaml.load(" -- '*.py'` deve restituire solo `safe_load`/`safe_dump`.
[VERIFIED: PyYAML official docs + pyyaml.org/wiki/PyYAMLDocumentation]

### Pitfall 4: Nested directory navigation in mkdocs-static-i18n folder mode
**What goes wrong:** Nuovi top-level nav entries (`Dominio`, `Procedure`, `Assumption Register`, `Glossario`) non vengono tradotti in EN o vengono renderati in posizioni diverse fra IT e EN.
**Why it happens:** `nav_translations` in `mkdocs.yml` deve essere esteso per ogni nuova voce; dimenticarsi una traduzione produce voce IT visibile anche in versione EN.
**How to avoid:**
1. Estendere `i18n.languages[1].nav_translations` con TUTTE le nuove voci:
   ```yaml
   nav_translations:
     Architettura: Architecture
     Iniziare: Getting Started
     Dominio: Domain
     Procedure (SOP): Procedures (SOP)
     Assumption Register: Assumption Register  # invariato — termine tecnico
     Glossario: Glossary
   ```
2. `mkdocs build --strict` rileva nav broken link ma NON traduzioni mancanti — aggiungere check manuale o test smoke nel PR.
**Warning signs:** Sito EN renderizza voce in italiano nella top nav (`Dominio` invece di `Domain`).
[VERIFIED: ultrabug.github.io/mkdocs-static-i18n/getting-started/quick-start/]

### Pitfall 5: Glossary coverage check explodes on **bold** in code samples
**What goes wrong:** `validate-glossary-coverage.py` estrae **bold** tokens da Markdown — ma in un SOP, parte del testo è dentro code blocks o esempi (`**WARNING**` in box callout) che NON sono termini di glossario, generando falsi positivi.
**Why it happens:** Regex `\*\*([^*\n]+?)\*\*` matcha indiscriminately.
**How to avoid:**
1. Filtrare `**WARNING**`, `**DANGER**`, `**NOTE**`, `**CAUTION**` (parole MkDocs admonition standard) via allowlist nel script.
2. Skippare contenuti dentro fenced code blocks (`` ```...``` ``) — strip code blocks prima di estrarre bold.
3. Skippare bold con caratteri non-alfanumerici prevalenti (es. `**42°C**` non è un termine).
**Warning signs:** CI fallisce su SOP appena scritti con bold di valori numerici o keyword di admonition.

### Pitfall 6: assumption `affected_components` referenzia componente inesistente
**What goes wrong:** `affected_components: [orchestrator, ot-bridge, sim-textile, langfuse]` ma `langfuse` non è un Nx project (è infra deployment, non codice).
**Why it happens:** Confusione tra service runtime e Nx project name.
**How to avoid:**
1. Script `validate-assumption-components.py` (CI) carica `nx show projects --json` e l'union con servizi infra noti (`langfuse`, `qdrant`, `postgresql`, `nats`, `redis`, `ollama`, `ot-bridge`, `clickhouse`, `minio`).
2. Manutenere `docs/assumptions/.valid-components.txt` (autogenerato) con union; assumption che cita componenti out-of-list fallisce CI.
**Warning signs:** CI fallisce con `unknown component: X` quando si aggiunge nuovo servizio.

### Pitfall 7: SOP cross-language ID drift (D-26 `id` field)
**What goes wrong:** `SOP-LOOM-001` esiste in IT con title "Sostituzione subbio" e in EN con title "Replace beam roll" ma — per errore — `SOP-LOOM-001` viene assegnato a un secondo SOP in EN, mentre l'EN counterpart del primo SOP è `SOP-LOOM-101`.
**Why it happens:** Authoring asincrono (D-25 hybrid: prima IT poi EN translation); refactoring degli ID non propagato.
**How to avoid:**
1. `validate-corpus-frontmatter.py` aggiungere check: per ogni `id` esiste esattamente 1 file `lang=it` e 1 file `lang=en` (no più, no meno, no orphan).
2. Convenzione naming filename: `SOP-LOOM-001-{slug}-{lang}.md` — il filename porta sia `id` sia `lang`, drift visibile in `ls`.
**Warning signs:** Differenza fra `find … -name "*-it.md" | wc -l` e `find … -name "*-en.md" | wc -l`.

## Code Examples

Vedi sezione **Architecture Patterns** sopra (Pattern 1-6) per esempi completi verificati. Sources:
- Pydantic v2 patterns: docs.pydantic.dev/latest/ (CITED)
- PyYAML safe_load: pyyaml.org/wiki/PyYAMLDocumentation (VERIFIED)
- jsonschema Draft 2020-12: python-jsonschema.readthedocs.io/en/stable/ (VERIFIED)
- python-frontmatter API: python-frontmatter.readthedocs.io/ (VERIFIED)
- mkdocs-static-i18n nested dirs: ultrabug.github.io/mkdocs-static-i18n/getting-started/quick-start/ (VERIFIED)
- Mermaid `accTitle`/`accDescr`: mermaid.js.org/config/accessibility.html (CITED)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 BaseModel + validators | Pydantic v2 BaseModel + `field_validator` + `model_config` | 2023 v2.0 release | API differenti: `model_validate()` vs `parse_obj()`, `model_dump()` vs `dict()`. 5-10x performance. Stack runtime già scelto v2 [CITED: pydantic.dev/articles/pydantic-v2-12-release] |
| `python-opcua` sincrono | `asyncua` async | Phase 3 (non Phase 2) | N/A per Phase 2 — citato in STACK.md |
| JSON Schema Draft 7 | Draft 2020-12 | 2020+ | jsonschema 4.x supporta entrambi; per nuovi schema **usare 2020-12** (`$dynamicRef`, `prefixItems`) [VERIFIED: jsonschema 4.26.0 readme] |
| Single-doc Markdown frontmatter (TOML/JSON) | YAML frontmatter (de facto MkDocs/Hugo/Jekyll standard) | Pre-2020 | YAML è il default universale; `python-frontmatter` lo gestisce nativamente |

**Deprecated/outdated (da NON usare in Phase 2):**
- **Pydantic v1 API:** `parse_obj`, `parse_raw`, validators `@validator` → usare v2 equivalenti.
- **`yaml.load` senza Loader o con `Loader=yaml.Loader`:** insicuro → solo `safe_load`.
- **JSON Schema Draft 4/6:** ancora supportato ma per nuovi schema usare 2020-12.
- **mkdocs i18n con suffix files (`index.fr.md`):** rotta legacy → noi usiamo `docs_structure: folder` (D-15 Phase 1).

## Assumptions Log

> Claims tagged `[ASSUMED]` in this research. Da confermare prima dell'esecuzione.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pydantic v2 lru_cache su `load_terms()` è sufficiente per ~150 termini per lingua senza ottimizzazioni custom (benchmark non eseguito specifico per questo corpus, ma estrapolazione da prrao87/pydantic-benchmarks 130K records) | Pattern 1 Pydantic Glossary Loader | Cold start lento o memory leak — basso: 150 oggetti Pydantic v2 sono <100KB, lru_cache size=2 limita memoria; ben sotto qualsiasi soglia operativa |
| A2 | Nessun secret nuovo serve in Phase 2 — tutti gli script leggono solo da git-tracked YAML/Markdown | Runtime State Inventory | Se sbagliato: secret leakage in git. Mitigation: `gitleaks` hook esistente (Phase 1, Plan 04) intercetta |
| A3 | `mkdocs-static-i18n` `docs_structure: folder` supporta correttamente nested directories `domain/processes/weaving.md` — verificato in docs ufficiali, non testato end-to-end con la struttura Phase 2 esatta | Pattern (project structure) | Se rotto: build fallisce con strict mode → catch in Phase 2 dev loop. Mitigation: Wave 0 / setup tasks possono fare `mkdocs build --strict` smoke test prima di scrivere contenuto sostanziale |
| A4 | ~150 termini glossario IT + ~150 EN è "esaustivo" per il corpus di 20 SOP + ~10 domain pages — basato su stima utente in D-31, non su grep dei termini distinti effettivi nel corpus draft | D-31 lock | Sovrastima → glossario stale (>5% warning del check D-32); sottostima → coverage check fallisce. Mitigation: D-32 stale warning soglia 5% è morbido (warning, non fail); coverage hard-fail è solo su missing |
| A5 | ISO 5247 (parts 2/3) è authority autorevole per terminologia weaving in IT — il documento è in EN/FR/RU/DE/ZH, non IT; la mappatura ISO 5247 → italiano è veicolata da UNI (non gratuita) o da pubblicazioni accademiche tessili | Italian Terminology Authority (sotto) | Se l'autorità citata in `source:` campo Term è imprecisa, il glossario perde autorevolezza accademica ma rimane operativamente corretto. Mitigation: usare `source: industry-standard` quando ISO non è verificabile in italiano; flaggare ISO solo per termini effettivamente tradotti |
| A6 | python-frontmatter 1.1.0 è ultima release stabile — Snyk segnala "no new versions in past 12 months" → potenziale package "in pausa". Funzionale e safe ma non in attivo sviluppo | Standard Stack | Se progetto diventa abbandoned: cercare maintained fork (es. `frontmatter-format` 0.x); API è stabile da anni, basso rischio di breakage. Mitigation: pin esatto in pyproject.toml + audit Phase 14 |
| A7 | Nessun progetto Nx esiste oggi per `simulators/synthetic-corpus` (Phase 1 ha solo `sim-textile` come simulator). Phase 2 deve creare un nuovo project `synthetic-corpus` se vuole project-level Nx targets | Pattern 6 + project structure | Se Nx target non aggiunto: validate scripts vanno comunque eseguiti manualmente in `ci.yml` come step `python3 scripts/validate-*.py`. Mitigation: planner sceglie tra "nuovo Nx project" (più clean) o "step diretti in ci.yml" (più semplice) |
| A8 | `nyquist_validation: true` in `.planning/config.json` → include Validation Architecture section. Confermato in config.json. | Validation Architecture section | None — config verificato |

## Italian Terminology Authority (DOC-18 / D-29)

> Sezione informativa per il planner. Phase 2 deve scegliere `source:` field per Term entries.

**Authority sources verificati:**

| Standard | Lingue | Disponibilità | Coverage |
|----------|--------|---------------|----------|
| ISO 5247-1:1983 | EN/FR/RU | a pagamento (iso.org/standard/11244.html) | Classification + vocabulary weaving machines |
| ISO 5247-2:1989 | EN/FR/RU | a pagamento | Accessories weaving — vocabulary |
| ISO 5247-3:1993 | EN/FR/DE/ZH | a pagamento | Parts of weaving machines — 158 terms |
| ISO 9902-6:2018 | EN | a pagamento | Noise test code fabric manufacturing |
| ISO 11111-1:2016 | EN | a pagamento | Safety requirements textile machinery |
| UNI (italiano nazionale) | IT | a pagamento (uni.com) | Adozioni nazionali italiane di ISO — non liberamente accessibili |
| BS EN, ASTM | EN | a pagamento | Equivalenti UK/US per dyeing, materials |

**Practical guidance for planner:**
- Per `source:` field nel glossario usare:
  - `iso-5247-2` o `iso-5247-3` per termini weaving traceable a ISO (anche se UNI non verificabile gratis)
  - `industry-standard` per gergo operativo non normativo ma universalmente accettato (es. "pick density", "warp tension")
  - `internal` per termini agentic-platform definiti da noi (es. specific HITL terminology)
  - `wikipedia-it` o `wikipedia-en` per glossario di tessile didattico (con cautela — non source-of-truth)
- **Non spendere effort cercando le traduzioni ISO ufficiali in italiano** — non sono pubbliche; il valore aggiunto qui è offrire una mappatura coerente IT↔EN, non claim di standard compliance.

[VERIFIED: iso.org/standard/11244.html, iso.org/standard/11245.html, iso.org/standard/11246.html]
[ASSUMED: che la mancanza di traduzione IT pubblica delle ISO 5247 sia accettabile come tradeoff. Da confermare con utente se serve compliance formale]

## Open Questions

1. **Should `simulators/synthetic-corpus` be a real Nx project (con `project.json` + `pyproject.toml`)?**
   - What we know: D-25/D-26 implicano CI validation target Nx-driven (`nx affected --target=validate-frontmatter`).
   - What's unclear: se vale la pena creare un project Python "vuoto" solo per portare il target Nx, o se gli script Python possono girare direttamente in `ci.yml` come step shell.
   - Recommendation: **creare project Nx leggero** (`simulators/synthetic-corpus/project.json` con targets ma senza `pyproject.toml`/`src/` — è data-only). Beneficio: `nx affected` salta validation se corpus non toccato; coerente con D-05 (project naming) di Phase 1.

2. **Glossary loader API: solo `load_terms(lang)` o anche `load_term(term, lang)` lookup singolo?**
   - What we know: D-29 specifica `load_terms(lang) -> list[Term]`.
   - What's unclear: agenti Phase 5 probabilmente vorranno lookup O(1) per singolo termine.
   - Recommendation: esporre **entrambi**: `load_terms(lang) -> list[Term]` + `load_terms_dict(lang) -> dict[str, Term]`. Il dict è semplicemente `{t.term.lower(): t for t in load_terms(lang)}` con `lru_cache`. Costo: 5 LOC.

3. **Assumption pages — una pagina per assumption o tabella + drill-down inline?**
   - What we know: D-33 dice "una pagina dettaglio per assumption (slug = `id`)".
   - What's unclear: 50 pagine generate (×2 lingue = 100 file) potrebbero appesantire `mkdocs build` e la sidebar nav.
   - Recommendation: **una pagina per assumption** come da D-33, ma escludere dalla sidebar nav (`hidden: true` in frontmatter) e linkare solo da `assumptions/index.md` tabella. Riduce nav noise mantenendo deep-link audit-friendly.

4. **Wave 1 vs Wave 2 split per glossary seed: ~70 termini bootstrap o glossario completo immediatamente?**
   - What we know: downstream_guidance suggerisce Wave 1 = ~70 termini bootstrap, Wave 3 = espansione a ~150.
   - What's unclear: se ~70 termini coprono i SOP esempio di Wave 2 (5 SOP — 1 per asset family). Se non coprono, il glossary coverage CI check fallisce in Wave 2.
   - Recommendation: bootstrap Wave 1 deve includere **tutti i termini che appariranno nei 5 SOP esempio di Wave 2** + ~50 termini textile core. Sequenza: prima draftare i 5 SOP esempio, estrarre i bold, comporre il seed glossary di conseguenza. Inverte parzialmente l'ordine implicito ma evita ping-pong CI.

5. **Hybrid LLM-draft fallback `status: draft-unreviewed` — chi rivede e quando?**
   - What we know: D-25 fallback è marcare 10 reviewed + 10 draft.
   - What's unclear: se il review umano viene posticipato a Phase 14, gli agenti Phase 5+ indicheranno SOP draft come retrieval source autorevole? Risk = false ground truth in agent eval.
   - Recommendation: se fallback attivo, la query glossary/retrieval di Phase 5 deve **filtrare** `status: reviewed` di default. Documentare questa contract in `simulators/synthetic-corpus/README.md` per Phase 5 planner.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | sft-domain loader, all `scripts/*.py` | ✓ (via `uv python install 3.12`) | 3.12.x via uv | — |
| uv 0.6+ | uv workspace, `uv sync --all-packages` | ✓ | 0.11.13 (installed) | — |
| Node.js 20 | Nx workspace, `npx nx ...` | ✓ | 20.x (Phase 1 .nvmrc) | — |
| pyyaml | glossary YAML parsing | ✓ | 6.0.2 installed, 6.0.3 latest | — |
| jsonschema | CI frontmatter validation | ✓ | 4.19.2 installed, 4.26.0 latest | upgrade in pyproject.toml |
| pydantic | loader runtime models | ✗ (non in `sft-domain` deps) | latest 2.13.4 | **install required** — add to `packages/sft-domain/pyproject.toml` |
| python-frontmatter | SOP frontmatter parsing in scripts | ✗ | latest 1.1.0 | **install required** — add to root `[dependency-groups] dev` |
| mkdocs-material | docs build | ✓ | 9.7.6 pinned in `docs/requirements.txt` | — |
| mkdocs-static-i18n | bilingual docs | ✓ | 1.3.1 pinned | — |
| GitHub Actions runner | CI validation step | ✓ | ubuntu-latest in `ci.yml` | — |
| MkDocs strict build (`mkdocs build --strict`) | CI gate | ✓ (esistente in `make docs` + `docs-deploy.yml`) | — | — |

**Missing dependencies with no fallback:** None — tutte risolvibili via `uv add` / pinning in `docs/requirements.txt`.
**Missing dependencies with fallback:** None.

## Validation Architecture

> `nyquist_validation: true` in `.planning/config.json` — questa sezione è inclusa.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` 8.x (CI) + Python script self-validation (no framework needed) |
| Config file | `pyproject.toml` root `[tool.pytest.ini_options]` (TBD: se Phase 2 introduce primi test Python; altrimenti puro script-based) |
| Quick run command | `python3 scripts/validate-corpus-frontmatter.py && python3 scripts/validate-bilingual-mirror.py && python3 scripts/validate-glossary-coverage.py` (~5s totale) |
| Full suite command | `npx nx run-many --target=validate-glossary,validate-frontmatter,validate-bilingual-mirror --all && python3 scripts/generate-glossary-pages.py --check && python3 scripts/generate-assumption-pages.py --check && mkdocs build --strict` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-05 | Domain analysis pages exist with required H1+H2 structure (10 IT + 10 EN) | structural | `python3 scripts/validate-bilingual-mirror.py` (verifies pairs exist + heading symmetry) | ❌ Wave 0 (new script) |
| DOC-05 | Each process page contains Mermaid `flowchart LR` + KPI section + pain point | content | `pytest tests/test_domain_pages.py::test_process_sections` (greps required sections) | ❌ Wave 0 (new test file) |
| DOC-12 | Assumption register YAML schema-valid + ~50 entries seeded | schema | `python3 scripts/validate-assumption-schema.py` (jsonschema Draft 2020-12) | ❌ Wave 0 (new script + schema) |
| DOC-12 | `affected_components` references existing Nx project or known infra component | reference | `python3 scripts/validate-assumption-components.py` | ❌ Wave 0 (new script) |
| DOC-12 | Generated assumption pages match YAML (idempotent) | regression | `python3 scripts/generate-assumption-pages.py --check` (exit 2 on drift) | ❌ Wave 0 (new script) |
| DOC-18 | Glossary YAML files schema-valid (IT + EN) | schema | `python3 scripts/validate-glossary-schema.py` | ❌ Wave 0 (new script + schema) |
| DOC-18 | All **bold** tokens in docs/corpus have glossary entry | coverage | `python3 scripts/validate-glossary-coverage.py` | ❌ Wave 0 (new script) |
| DOC-18 | Generated glossary.md matches YAML (idempotent) | regression | `python3 scripts/generate-glossary-pages.py --check` | ❌ Wave 0 (new script) |
| DOC-18 | Glossary loader API returns expected count of terms | unit | `pytest packages/sft-domain/tests/test_glossary_loader.py` | ❌ Wave 0 (new test file) |
| KNW-10 | Corpus has ≥20 SOPs distributed 5+5+5+5 across asset families | inventory | `pytest tests/test_corpus_inventory.py::test_distribution` (counts per family/lang) | ❌ Wave 0 (new test file) |
| KNW-10 | Each SOP frontmatter validates against schema | schema | `python3 scripts/validate-corpus-frontmatter.py` | ❌ Wave 0 (new script + schema) |
| KNW-10 | Each SOP has IT + EN counterpart with matching `id` | bilingual | `python3 scripts/validate-corpus-pairing.py` (group by id, assert ∃ it + en) | ❌ Wave 0 (new script) |
| KNW-10 | Each SOP has required H2 sections (Scope, Prereq, Tools, Steps, Verif, Trouble, Refs) | structural | included in `validate-corpus-frontmatter.py` (extract H2 list, assert match) | ❌ Wave 0 |
| ALL | MkDocs site builds clean with new content | integration | `mkdocs build --strict` (existing in `docs-deploy.yml`) | ✅ Phase 1 |

### Sampling Rate

- **Per task commit:** quick run command (~5s) eseguito da pre-commit hook (extension del config esistente Phase 1)
- **Per wave merge:** full suite (~15-30s con `mkdocs build --strict`) via `make validate-corpus` + `make docs` locally
- **Phase gate:** full suite green su CI workflow `ci.yml` prima di `/gsd:verify-work`. `gh-pages` deploy via `docs-deploy.yml` come final gate.

### Wave 0 Gaps

Tutti i seguenti file non esistono ancora — Wave 0 (foundation) li crea prima del content authoring:

- [ ] `packages/sft-domain/src/sft_domain/schemas/glossary.schema.json` — JSON Schema Draft 2020-12 per Term entries
- [ ] `packages/sft-domain/src/sft_domain/schemas/sop.schema.json` — JSON Schema per SOP frontmatter
- [ ] `packages/sft-domain/src/sft_domain/schemas/assumption.schema.json` — JSON Schema per assumption register entries
- [ ] `packages/sft-domain/src/sft_domain/glossary/__init__.py` — exports
- [ ] `packages/sft-domain/src/sft_domain/glossary/models.py` — Pydantic Term + Category enum
- [ ] `packages/sft-domain/src/sft_domain/glossary/loader.py` — `load_terms()` + `load_terms_dict()` con lru_cache
- [ ] `packages/sft-domain/tests/test_glossary_loader.py` — unit test loader
- [ ] `packages/sft-domain/tests/test_glossary_schema.py` — schema validation test
- [ ] `packages/sft-domain/tests/conftest.py` — shared pytest fixtures (sample Term, sample SOP frontmatter)
- [ ] `simulators/synthetic-corpus/project.json` — Nx project con `validate-frontmatter` target
- [ ] `simulators/synthetic-corpus/README.md` — scope, schema reference, authoring guidelines
- [ ] `scripts/generate-glossary-pages.py`
- [ ] `scripts/generate-assumption-pages.py`
- [ ] `scripts/validate-glossary-coverage.py`
- [ ] `scripts/validate-glossary-schema.py`
- [ ] `scripts/validate-bilingual-mirror.py`
- [ ] `scripts/validate-corpus-frontmatter.py`
- [ ] `scripts/validate-corpus-pairing.py`
- [ ] `scripts/validate-assumption-schema.py`
- [ ] `scripts/validate-assumption-components.py`
- [ ] `Makefile` additions: `validate-corpus`, `generate-glossary`, `generate-assumptions`, `validate-glossary`, `validate-all` targets
- [ ] `pyproject.toml` (root): aggiungere `python-frontmatter`, `jsonschema` (upgrade), `pytest`-related deps a `[dependency-groups] dev`
- [ ] `packages/sft-domain/pyproject.toml`: aggiungere runtime deps `pydantic`, `pyyaml`
- [ ] `.github/workflows/ci.yml`: nuovo step "Validate content" dopo "Validate Nx dependency graph"

*Pattern dei nuovi script copia 1:1 `scripts/sync-python-versions.py` (Phase 1): argparse, `--dry-run`, idempotent, exit codes 0/1/2 documentati nel docstring.*

## Security Domain

> Security enforcement non esplicitamente disabilitato in `.planning/config.json` — sezione inclusa. Note: Phase 2 è content-only, threat surface limitato.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A (Phase 2 è content/build pipeline, no user auth introdotto) |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A (assumption register è plain markdown — no access control until Phase 5 KNW-06) |
| V5 Input Validation | yes | `jsonschema` Draft 2020-12 su YAML; `python-frontmatter` su SOP; Pydantic v2 su loader |
| V6 Cryptography | no | N/A |
| V7 Error Handling & Logging | partial | Script CI emettono stderr strutturato + exit codes; nessun logging persistente |
| V12 File & Resources | yes | YAML `safe_load` enforced (NOT `yaml.load` raw); path traversal mitigated by `pathlib` (no string concat) |
| V14 Configuration | yes | `mkdocs.yml` validato da MkDocs strict mode; `pyproject.toml` deps pinned to allowed licenses (Phase 1 license-scan.yml gating) |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary code execution via YAML deserialization | Tampering / Elevation of Privilege | **Always `yaml.safe_load`**; lint with `bandit` (B506 — yaml_load_with_loader); code review on `scripts/validate-*.py` and `glossary/loader.py` |
| Prompt injection in synthetic SOP content (LLM-drafted, will be retrieved by agents Phase 5+) | Tampering | Hybrid review (D-25): umano valida draft IT prima di traduzione; status `reviewed` gate per agent retrieval Phase 5+ (Open Question #5) |
| Stale glossary entries become misleading retrieval source | Repudiation | D-32 stale terms warning (>5%); review periodico Phase 11/14 |
| Path traversal in script discovery (`Path.rglob("../../etc/passwd")`) | Tampering | `pathlib.Path` API + assertion che tutti i path risolvano sotto workspace root |
| Supply chain attack via new pip dependency | Tampering | Phase 1 license-scan.yml continua a operare; nuovi deps `pydantic`/`pyyaml`/`jsonschema`/`python-frontmatter` sono mainstream con allowlist licenses (MIT / Apache-2.0 / BSD) |
| MkDocs plugin malicious execution (PyYAML python/name fence) | Tampering | Già attivo in `mkdocs.yml` Phase 1 (`!!python/name:pymdownx.superfences.fence_code_format`) — è un import-time tag, file YAML è git-tracked e human-reviewed |
| gitleaks false negative on glossary/assumption YAML | Information Disclosure | gitleaks hook esistente (Phase 1 Plan 04); review esplicita su nuovi YAML che li policy NON deve contenere stringhe credenziali-like |

## Project Constraints (from PROJECT.md)

> No `./CLAUDE.md` esiste alla root del progetto. Constraints derivati da `.planning/PROJECT.md`.

- **Tech stack lockato:** Python 3.12+, Nx 20.x, MkDocs Material 9.7+, pydantic standard ecosystem
- **AI deployment:** self-hostable — non rilevante per Phase 2 (no LLM runtime ancora)
- **Documentazione bilingue IT + EN** — locked (D-24)
- **Repository:** monorepo singolo, deploy docs auto via GitHub Pages (operativo da Phase 1)
- **Branding:** zero riferimenti ad Accenture — verificato in D-08 di Phase 1 (license-scan + brand-scrub CI Phase 12). Phase 2 non introduce rischi di brand contamination ma il content authoring (D-25 LLM-draft) deve essere consapevole — la review umana è il gate.
- **Originalità:** la traccia originale `Smart Factory Transformation.md` NON deve essere riprodotta. Già in `?? "Smart Factory Transformation.md"` (untracked) — il planner deve assicurarsi che `.gitignore` la copra o che esista chiara separation
- **Governance AI:** HITL applica a runtime agentico (Phase 4+); Phase 2 contribuisce con SOP corpus che agenti useranno come retrieval source — la responsabilità "non inventare procedure pericolose" è di D-25 (hybrid review)

## Sources

### Primary (HIGH confidence)
- pypi.org/project/PyYAML/ — version 6.0.3 latest, security guidance `safe_load` [VERIFIED 2026-05-17 via `pip index versions pyyaml`]
- pypi.org/project/jsonschema/ — version 4.26.0, Draft 2020-12 support [VERIFIED 2026-05-17 via `pip index versions jsonschema` + python-jsonschema.readthedocs.io]
- pypi.org/project/pydantic/ — version 2.13.4 latest [VERIFIED 2026-05-17 via `pip index versions pydantic` + pydantic.dev/articles/pydantic-v2-12-release]
- pypi.org/project/python-frontmatter/ — version 1.1.0 [VERIFIED 2026-05-17 via `pip index versions`]
- ultrabug.github.io/mkdocs-static-i18n/getting-started/quick-start/ — `docs_structure: folder` + nested directories support [VERIFIED via WebSearch + Phase 1 01-07 SUMMARY operational confirmation]
- mermaid.js.org/config/accessibility.html — `accTitle` / `accDescr` API [CITED]
- iso.org/standard/11244.html, /11245.html, /11246.html — ISO 5247 parts [VERIFIED via WebSearch]
- pyyaml.org/wiki/PyYAMLDocumentation — safe_load convention [VERIFIED]
- python-jsonschema.readthedocs.io/en/stable/ — current API + Draft 2020-12 [VERIFIED]
- `.planning/research/STACK.md` Phase 1 — locked tech choices [VERIFIED in-repo]
- `.planning/phases/01-foundation-monorepo/01-07-mkdocs-SUMMARY.md` — `docs_structure: folder` operational, `mkdocs build --strict` enforced [VERIFIED in-repo]
- `.planning/phases/01-foundation-monorepo/01-01-nx-workspace-SUMMARY.md` — `packages/sft-domain` exists with `__version__.py`, hatchling backend [VERIFIED in-repo]

### Secondary (MEDIUM confidence)
- dev.to/donovandicks (Pydantic v2 performance investigation) — v2 ~4-5x faster than v1 [CITED]
- github.com/squidfunk/mkdocs-material/discussions/7126 — Mermaid rendering issues [CITED]
- github.com/mermaid-js/mermaid/issues/5632 — accessibility limitations [CITED]
- snyk.io/advisor/python/python-frontmatter — "no new versions in 12 months" warning [CITED, factored as A6]

### Tertiary (LOW confidence)
- Italian UNI standards adoption of ISO 5247 — not publicly accessible, treated as inference (A5)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tutte le versioni verificate via `pip index` + ufficiale PyPI; nessuna dipendenza esoterica
- Architecture: HIGH — pattern (Pydantic + idempotent generator + jsonschema CI gate) sono mainstream, già parzialmente in uso nel repo (`sync-python-versions.py`)
- Pitfalls: MEDIUM — pitfall #2 (Mermaid limits) e #5 (bold extraction false positive) sono induzioni da reading docs, non testati nello specifico contesto Phase 2
- Italian terminology: MEDIUM — ISO 5247 esiste ma traduzione UNI italiana non verificabile gratis; pragmatica: usare `source: industry-standard` quando ISO non confermabile

**Research date:** 2026-05-17
**Valid until:** ~30 giorni (stack stabile, libraries mature) — eccezione: `python-frontmatter` (A6) — rivedere a Phase 14 per maintenance status
