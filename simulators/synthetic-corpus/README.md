# synthetic-corpus

Bilingual (IT+EN) synthetic SOP corpus for textile manufacturing — retrieval target for Phase 5 Knowledge Layer.

## Scope

This corpus is the KNW-10 deliverable: 20 bilingual Standard Operating Procedures (10 IT + 10 EN)
covering the four main textile process families — loom troubleshooting (weaving), dyeing procedures,
spinning maintenance, and quality grading inspection.

**What this corpus IS:**
- A retrieval-friendly SOP dataset for testing Phase 5 (BGE-M3 + Qdrant knowledge layer)
- Factory-floor realistic content using industrial terminology and typical industry ranges
- Ground truth for evaluating `OperatorAssistant`, `MaintenanceCoach`, and `QualityInspector` agents

**What this corpus is NOT:**
- Real Mantis Textile Group IP or proprietary operational data
- A source of exact machine-specific parameters (temperatures, tensions, RPM) — values are
  *range tipici industria*, not site-specific validated figures
- A replacement for domain-expert-reviewed technical documentation

## Directory layout

```
simulators/synthetic-corpus/
├── it/                         # Italian SOPs (Plan 02-04 baseline)
│   ├── loom/                   # asset_family: weaving (loom asset)
│   ├── dyeing/                 # asset_family: dyeing
│   ├── spinning/               # asset_family: spinning
│   └── quality_grading/        # asset_family: quality_grading (cross-cutting)
└── en/                         # English SOPs (Plan 02-05 translations)
    ├── loom/
    ├── dyeing/
    ├── spinning/
    └── quality_grading/
```

**Filename convention:** `SOP-{FAMILY}-{NNN}-{slug}-{lang}.md`

Examples:
- `it/loom/SOP-LOOM-001-troubleshoot-broken-end-it.md`
- `en/loom/SOP-LOOM-001-troubleshoot-broken-end-en.md`

**asset_family enum (6 values, per `sop.schema.json`):**
- `weaving` — loom/rapier/projectile operations
- `spinning` — ring spinning frame, open-end spinner
- `warping` — warp beam preparation (reserved for Phase 2+ expansion)
- `dyeing` — jet dyeing, beam dyeing
- `finishing` — stenter, calender, sanforizing (reserved for Phase 2+ expansion)
- `quality_grading` — cross-cutting inspection activity operating across all processes

**process (D-21, 5 values) vs asset_family (SOP scope, 6 values):**
Every textile process (`weaving`, `spinning`, `warping`, `dyeing`, `finishing`) is a valid
`asset_family`. However, `quality_grading` is additionally an `asset_family` even though it
is NOT a primary textile process — it is a cross-cutting inspection activity (D-27) that
operates on the output of all processes. Phase 2 corpus covers 4 subdirectories:
`loom` (weaving SOPs), `dyeing`, `spinning`, and `quality_grading`.

## Frontmatter schema

Every SOP file carries a YAML frontmatter block validated against:

```
packages/sft-domain/src/sft_domain/schemas/sop.schema.json
```

**Required frontmatter fields (D-26):**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | `^SOP-[A-Z]+-[0-9]{3}$` — unique SOP identifier |
| `title` | string | Descriptive title (≥5 chars) |
| `version` | string | `MAJOR.MINOR` (e.g. `1.0`) |
| `lang` | `it` or `en` | Document language |
| `asset` | string | Physical asset (e.g. `loom`, `jet dyeing machine`) |
| `asset_family` | enum (6 values) | Asset family scope — see enum above |
| `role` | enum | `operator`, `technician`, `quality-manager`, `shift-supervisor` |
| `hazard_level` | enum | `low`, `medium`, `high`, `critical` |
| `estimated_duration_min` | integer (1-480) | Estimated procedure duration in minutes |
| `status` | enum | `reviewed`, `draft-unreviewed`, `deprecated` |
| `created_in_phase` | integer | Project phase when SOP was created |
| `prerequisites` | array | SOP IDs that must be completed first |
| `related_glossary` | array | Glossary terms referenced in this SOP |
| `tags` | array | Free tags for categorization |
| `audience` | string | Intended audience (e.g. `operations`, `maintenance`) |

## Authoring workflow (D-25 hybrid)

SOPs are authored using a hybrid LLM-draft + human review process:

1. **Claude drafts IT** — in the Phase 2 execution session, Claude generates the
   Italian SOP draft using factory-floor realistic language per D-28.
2. **Committed as `draft-unreviewed`** — all LLM-generated SOPs ship with
   `status: draft-unreviewed` to gate Phase 5 retrieval (see below).
3. **Human review IT** — the user reviews draft Italian content, may edit in-place,
   accept, or request regeneration with a different prompt.
4. **EN translation** — after IT review, Claude translates to English preserving
   frontmatter structure and section headings.
5. **Human review EN pass-2** — faster pass focused on translation quality,
   not technical content.
6. **Promotion to `reviewed`** — Plan 07 promotes accepted SOPs to `status: reviewed`
   after the user's review pass is complete.

**Fallback:** If review backlog prevents timely review, SOPs remain in
`draft-unreviewed` state. This is acceptable — the `status` field gates
Phase 5 retrieval so draft content is never surfaced to production agents.

## Style (D-28)

Factory-floor realistic language. Industrial jargon is allowed and encouraged
(terms must be in the IT glossary at `packages/sft-domain/src/sft_domain/glossary/it.yaml`).

- **Units of measure:** `g/m²`, `tex`, `Nm`, `picks per cm`, `°C`, `bar`, `N`
- **Numbers:** *range tipici industria* only — no site-specific Mantis values
- **Bold terms:** every textile/agentic term appearing in the SOP body must be in `**bold**`
  and must exist in the glossary (validated by `scripts/validate-glossary-coverage.py`)
- **Instruments named:** calibri digitali, durometri, igrometri, conta-trama, spettrofotometro
- **Mantis context:** if a Mantis-specific callout is needed, use
  `!!! note "Contesto Mantis"` admonition — do NOT embed Mantis values in procedure steps

## Validation

Run validation from the workspace root:

```bash
# Validate SOP frontmatter schema + H2 sections
npx nx run synthetic-corpus:validate-frontmatter

# Validate bilingual pairing (IT + EN must both exist per id)
npx nx run synthetic-corpus:validate-pairing

# Validate docs bilingual mirror (docs/docs/ IT <-> docs/docs/en/ EN)
npx nx run synthetic-corpus:validate-bilingual-mirror

# Equivalent direct script invocations:
python3 scripts/validate-corpus-frontmatter.py --corpus-dir simulators/synthetic-corpus
python3 scripts/validate-corpus-pairing.py --corpus-dir simulators/synthetic-corpus
python3 scripts/validate-bilingual-mirror.py --docs-dir docs/docs

# During Plan 02-04 (IT-only, no EN translations yet):
python3 scripts/validate-corpus-pairing.py --corpus-dir simulators/synthetic-corpus --allow-missing-en
```

## Retrieval contract for Phase 5 (Open Question #5)

Phase 5 (Knowledge Layer) ingestion pipelines MUST default-filter `status: reviewed` SOPs
when surfacing to agents. SOPs with `status: draft-unreviewed` are visible only through
an explicit opt-in query parameter or developer mode.

**Rationale:** Draft content has not passed domain-expert sanity check and must NOT become
false ground truth in agent eval/test suites. LLM-drafted SOPs may contain technically
plausible but incorrect parameter ranges that could mislead the `OperatorAssistant` or
`MaintenanceCoach` agents in production scenarios.

**Implementation guidance for Phase 5:**
- Default Qdrant filter: `{"must": [{"key": "status", "match": {"value": "reviewed"}}]}`
- Opt-in to drafts: pass `include_drafts=True` to the retrieval function or
  `status: ["reviewed", "draft-unreviewed"]` to the filter
- Agent eval/test harnesses MUST use the default filter (reviewed-only) to avoid
  contaminating evaluation benchmarks with unvalidated content
