---
phase: 2
phase_name: Domain Modeling & Synthetic Corpus
phase_slug: domain-modeling-synthetic-corpus
discussed_at: "2026-05-17"
requirements: [DOC-05, DOC-12, DOC-18, KNW-10]
depends_on_phases: [1]
---

# Phase 2 Context — Domain Modeling & Synthetic Corpus

<domain>
**What this phase delivers:** the knowledge substrate that every downstream agentic phase will retrieve from.

Concretely:
- A **textile domain analysis** in `docs/docs/{,en/}domain/` that describes processes, roles, and pain points of an Italian textile manufacturing site (Mantis Textile Group as reference), with explicit KPIs and asset coverage.
- A **bilingual glossary** (IT+EN, ~150 terms per language) of textile-domain + agentic-platform terminology, with category tagging and CI-enforced coverage against SOPs and domain analysis.
- An **assumption register** (~50 entries seeded) that names every data-quality, simulation-fidelity, scope, external-dependency, and regulatory assumption the system relies on — tagged by `category` and `affected_components[]`, evolving as a living doc.
- A **synthetic SOP corpus** of 20 documents (5 each for loom troubleshooting, dyeing procedures, spinning maintenance, quality grading), in IT+EN, factory-floor realistic tone, structured by frontmatter+sections for retrieval-friendliness — committed under `simulators/synthetic-corpus/` with a CI format check.

This phase does NOT build agents, retrieval pipelines, or LLM wiring. It produces the **content** that Phase 4 (Core Agentic Runtime) and Phase 5 (Knowledge Layer with BGE-M3+Qdrant) will index and retrieve from.
</domain>

<canonical_refs>
Files downstream agents (researcher, planner) MUST consult:

- `.planning/ROADMAP.md` — Phase 2 goal, requirements, success criteria
- `.planning/REQUIREMENTS.md` — full definitions of DOC-05, DOC-12, DOC-18, KNW-10
- `.planning/PROJECT.md` — core value, Mantis Textile Group reference, OEPV bid model
- `.planning/phases/01-foundation-monorepo/01-CONTEXT.md` — D-02 (`packages/sft-domain/` for textile data), D-15 (MkDocs Material i18n IT default + EN secondary), D-16/D-17 (no binary diagrams — Mermaid/D2 only)
- `.planning/phases/01-foundation-monorepo/01-01-nx-workspace-SUMMARY.md` — confirms `packages/sft-domain/src/sft_domain/` exists with `__version__.py` and is publishable
- `.planning/phases/01-foundation-monorepo/01-07-mkdocs-SUMMARY.md` — MkDocs structure: `docs/docs/` (IT default), `docs/docs/en/`, navigation tabs, material-tags plugin available
- `.planning/phases/01-foundation-monorepo/01-08-changesets-SUMMARY.md` — sft-domain is in `workspaces` for Changesets versioning; bumps must accompany glossary YAML schema breaking changes
- `.planning/research/STACK.md` — confirms Python 3.12 toolchain; YAML schema validation should use `jsonschema` or `pydantic` (already available)

No external SPEC.md or ADR exists for Phase 2 — this CONTEXT.md is the source of truth for downstream agents until ROADMAP.md is updated.
</canonical_refs>

<code_context>
**Already exists from Phase 1 — reuse, do NOT duplicate:**

- `packages/sft-domain/src/sft_domain/__init__.py` — empty namespace package, ready for `glossary/` and `assumptions/` submodules
- `packages/sft-domain/pyproject.toml` — published as `sft-domain` 0.1.0 with `[tool.uv]` dev deps; add `pyyaml` and `jsonschema` for dataloader at runtime
- `docs/docs/index.md` + `docs/docs/en/index.md` — MkDocs landing pages with i18n; add domain/glossary/assumptions/sop sections to nav
- `docs/docs/architecture/overview.md` (IT + EN) — placeholder; do NOT overwrite, link from new domain pages
- `docs/mkdocs.yml` — Material theme + i18n; APPEND new navigation entries, do not rewrite
- `simulators/sim-textile/` — Phase 1 scaffold (placeholder); **synthetic-corpus is a sibling** under `simulators/synthetic-corpus/`, do NOT nest inside sim-textile
- `Makefile` — has `make docs` (mkdocs build --strict); add `make validate-corpus`, `make generate-glossary`, `make validate-assumptions` targets
- `.github/workflows/ci.yml` — nx affected; corpus/glossary/assumption validation should be integrated as new Nx targets on `sft-domain` and `simulators/synthetic-corpus`
- `scripts/sync-python-versions.py` — Phase 1 helper; the new corpus validation script should follow the same `argparse + dry-run` shape

**Naming conventions to honor:**
- Conventional Commits with scope `feat(02-NN-slug):` per atomic commit (matches Phase 1 pattern)
- Bilingual mirroring: every `docs/docs/{topic}.md` has a counterpart at `docs/docs/en/{topic}.md` (MkDocs i18n `docs_structure: folder`)
- YAML field names in `snake_case` (sft-domain Python idiom); Markdown frontmatter keys equally `snake_case`
</code_context>

<decisions>

## D-21 — Domain Analysis: split per processo + ruolo

**Decision:** Domain Analysis non è monolitica. Splittata in:
- `docs/docs/domain/processes/{weaving,spinning,warping,dyeing,finishing}.md` (5 file processo)
- `docs/docs/domain/roles/{operator,technician,quality-manager,shift-supervisor}.md` (4 file ruolo)
- `docs/docs/domain/index.md` (indice + overview, ~400 parole)
- Mirror EN completo in `docs/docs/en/domain/...` (stessa struttura)

**Why:** Navigabilità per evaluators + indicizzazione granulare per agenti RAG di Phase 5 (BGE-M3 + Qdrant). Pagine corte (~300-500 parole/processo) sono unità di retrieval naturali. Lo split per ruolo serve a `OperatorAssistant` / `MaintenanceCoach` per filtrare retrieval per persona.

**Rejected alternatives:**
- Monolitico: harder to navigate, chunk-retrieval meno utile
- Ibrido (overview monolitico + processi deep-dive solo IT): asimmetria traduzione complica MkDocs i18n e i CI check di Area 3.

## D-22 — Profondità: Process flow + asset + KPI + pain point

**Decision:** Ogni pagina processo contiene, in quest'ordine:
1. Process flow diagram (Mermaid `flowchart LR`, max 8 nodi)
2. Asset coinvolti (lista con asset family, esempio modello tipico, parametri operativi indicativi)
3. KPI tipici (3-5 KPI con unità di misura, range tipico, formula breve)
4. Pain point (3-5 narrativi con esempio concreto + impatto operativo)

Ogni pagina ruolo: responsabilità (3-5), interazione tipica con asset/processi, decisione critica giornaliera (esempio concreto), pain point.

**Why:** Distinguibile da un white-paper generico, strutturato così che il `gsd-eval-planner` di Phase 4 può estrarre KPI come metriche di valutazione agente.

**Rejected alternatives:**
- Solo descrittivo + pain point: agenti RAG perdono ancore quantitative.
- Deep technical con parametri operativi (RPM/tensioni filato/temperature reali): rischio invenzione non realistica → l'assumption register ne tracerà i limiti, ma il dato non finisce nelle pagine domain.

## D-23 — Specificità Mantis: generico + sidebar contextual

**Decision:** Il body di ogni pagina è scritto per il settore textile manifatturiero italiano (medium-sized). Ogni processo/ruolo include un callout `!!! note "Mantis context"` (MkDocs admonition) con specificità note: tipologia filati (es. cotone/lana/lino blend), mercato finale (es. abbigliamento outdoor), turni produttivi tipici.

**Why:** Doppia funzione del progetto (open-source reference + pitch Mantis): contenuto riusabile + contestualizzato. Sidebar separa cleanly i due livelli.

**Locked from Phase 1:** Mantis Textile Group è il caso di riferimento PROJECT.md — NON è la sola fattispecie supportata.

**Rejected alternatives:**
- Mantis-first body + sidebar industria: rompe la riusabilità open-source.
- Completamente generico: perde il legame col caso d'uso che giustifica il bid OEPV.

## D-24 — Bilingue completo IT+EN in Phase 2

**Decision:** Sia IT che EN sono **complete e sostanziose** in Phase 2 per:
- Domain analysis (5+4+1 = 10 file × 2 lingue = 20 file)
- Glossario (rigenerato da YAML, vedi D-29)
- Assumption register (rigenerato da YAML, vedi D-31)
- SOP corpus (10 IT + 10 EN distinti, vedi D-26)

**Why:** Decisione esplicita dell'utente. Allinea Phase 2 con il commitment bilingue del progetto invece di rinviare a Phase 14.

**Drift mitigation:** CI check `scripts/validate-bilingual-mirror.py` verifica che ogni file `docs/docs/X.md` abbia controparte `docs/docs/en/X.md` con stessi heading H1/H2. Fallisce build se asimmetrico. Glossario e assumption register sono auto-coerenti perché generati dalla stessa fonte YAML.

**Rejected alternatives:**
- IT prima, EN deferred a Phase 14: viola scelta esplicita utente.
- Solo EN + IT stub: stride con orientamento italiano (Mantis, OEPV).

## D-25 — SOP authoring: hybrid LLM-draft + human review

**Decision:** Generazione dei 20 SOP è hybrid:
1. Claude (in sessione di esecuzione Phase 2) genera draft IT per ogni topic usando prompt strutturato (vedi RESEARCH.md TBD per template di prompt).
2. Draft committato in branch `phase-02-sop-drafts/`.
3. Utente fa review sui draft IT — può modificare in-place, accettare, o rifiutare (chiedendo regen con altro prompt).
4. Solo dopo review IT, Claude traduce a EN preservando frontmatter e struttura.
5. EN viene review pass-2 (più rapido — focus su traduzione, non contenuto tecnico).

**Why:** Velocità di LLM + qualità di review umano. Il review umano è il gate che evita errori tecnici di invenzione (es. temperature dyeing irrealistiche) che diventerebbero false ground truth per i test retrieval di Phase 5.

**Rejected alternatives:**
- Pure LLM no review: rischio inaccettabile di errori tecnici nei reference che agenti useranno.
- Hand-written da te + domain expert in Phase futura: viola KNW-10 success criterion in Phase 2.

**Cost note:** se review umano risulta troppo lento, fallback è marcare SOP non-reviewed con `status: draft-unreviewed` nel frontmatter e produrre 10 reviewed + 10 draft. Il planner Phase 2 deve presentare questa opzione di fallback nel PLAN.

## D-26 — SOP formato: frontmatter YAML + sezioni standardizzate

**Decision:** Ogni SOP segue questo schema:

```markdown
---
id: SOP-LOOM-001
title: Sostituzione rapida del subbio di ordito
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

# Sostituzione rapida del subbio di ordito

## Scope
…

## Prerequisites
…

## Tools and PPE
…

## Step-by-step Procedure
1. …
2. …

## Verification
…

## Troubleshooting
…

## References
…
```

Schema validato in CI via `jsonschema` su frontmatter. Sezioni H2 sono fisse e required (Scope, Prerequisites, Tools and PPE, Step-by-step Procedure, Verification, Troubleshooting, References).

**Why:** Frontmatter è chunk-metadata pronto per retrieval (filter by `asset`, `role`, `hazard_level`). Sezioni fisse permettono extraction structured per `OperatorAssistant` (es. "show me Verification steps for SOP-LOOM-001").

**Rejected alternatives:**
- Prosa + tag tassonomici: harder to parse, struttura meno utile per retrieval test.
- Markdown loose con sezioni convenzionali: validazione CI fragile.

## D-27 — Topic mix SOP: bilanciato 5+5+5+5

**Decision:** 20 SOP totali (per lingua, 40 file totali) distribuiti:
- 5 SOP **loom** (weaving) — focus troubleshooting (broken pick, warp tension drift, shuttle jam, selvage fault, defect cleanup)
- 5 SOP **dyeing** — focus procedure (bath preparation, color matching procedure, shade verification, fastness check, post-dyeing wash)
- 5 SOP **spinning** — focus maintenance (spindle calibration, drafting cylinder cleanup, ring rail adjustment, slub control, preventive lubrication)
- 5 SOP **quality grading** — focus inspection (4-point grading, broken end detection, mispick analysis, shade deviation report, lot acceptance)

**Why:** Copertura uniforme supporta evaluation cross-asset di agenti retrieval/RAG di Phase 5-6. Permette al `gsd-eval-planner` di costruire rubrics di valutazione bilanciate (no asset bias).

**Rejected alternatives:**
- Minimo 10 IT + 10 EN tradotti: 1:1 mapping IT↔EN ma corpus più piccolo per stress-test retrieval.
- Weighted by complexity (8 loom + 6 dyeing + ...): bias verso loom nei test agenti, scelta riservata a Phase 7+ quando ci sarà use-case feedback.

## D-28 — Stile narrativo SOP: factory-floor realistico

**Decision:** Linguaggio tecnico di settore. Termini gergali ammessi (e tracciati in glossario per D-29):
- `pick density`, `warp tension`, `slub`, `selvage fault`, `mispick`, `broken end`
- Unità di misura realistiche: `g/m²`, `tex`, `Nm`, `picks per cm`, `°C`, `bar`, `Nm di torsione`
- Strumenti reali nominati: calibri digitali, durometri, picometri, conta-trama, igrometri

**Why:** Corpus di valore per retrieval test "reale". Gli agenti devono essere stress-testati su linguaggio operativo, non su simplification.

**Boundary di sicurezza:** numeri tipici operativi (es. tensioni warp tipiche 15-25 N) sono presentati come **range tipici industria** non come valori esatti Mantis. Mantis-specifici sono nell'assumption register (D-30) marcati `validation_required: domain-expert-review`.

**Rejected alternatives:**
- Pedagogico-tutorial: utile per `TrainingCoach` ma erode utilità retrieval-test operativa.
- 70/30 misto: troppo complesso da bilanciare in Phase 2; differito a Phase 7 (TrainingCoach impl) che può cherry-pick 6 SOP esistenti e produrre varianti tutorial.

## D-29 — Glossario: dual-channel sft-domain YAML + render MkDocs

**Decision:** Fonte canonica è **YAML in sft-domain**:
- `packages/sft-domain/src/sft_domain/glossary/it.yaml`
- `packages/sft-domain/src/sft_domain/glossary/en.yaml`

Schema per termine:
```yaml
- term: pick density
  definition: Number of weft picks per centimeter of fabric…
  category: textile-process
  related_terms: [warp_tension, weft_yarn]
  examples:
    - "Pick density of 22-28 picks/cm is typical for cotton shirting"
  source: industry-standard
- term: hitl
  definition: Human-in-the-Loop — interaction pattern where…
  category: agentic-platform
  related_terms: [interrupt, audit_trail]
  …
```

Script `scripts/generate-glossary-pages.py` (Python 3.12, argparse + dry-run + idempotente) consuma i due YAML e rigenera:
- `docs/docs/glossary.md` (IT)
- `docs/docs/en/glossary.md` (EN)

Glossary loader API in `sft_domain.glossary.load_terms(lang: Literal["it","en"])` → `list[Term]` per agenti.

**Why:** Single source of truth strutturato. Agenti di Phase 5+ possono importare il dato direttamente; MkDocs vede solo Markdown rigenerato. Eliminata classe di bug "MkDocs e dati Python divergono".

**Rejected alternatives:**
- Solo MkDocs Markdown: agenti devono parsare Markdown, fragile.
- Solo sft-domain + plugin MkDocs custom: plugin custom è additional surface da mantenere; uno script idempotente è più leggero.

## D-30 — Glossario layout: unificato textile+agentic con tag categoria

**Decision:** Un singolo glossario per lingua (~150 termini IT, ~150 EN). Categorie supportate:
- `textile-process` — processi (weaving, dyeing, spinning, …)
- `textile-asset` — asset/macchine (loom, ring spinning frame, jet dyeing, …)
- `textile-defect` — difetti (slub, broken end, mispick, …)
- `textile-kpi` — KPI/metriche (OEE, MTTR, throughput, pick density, …)
- `textile-tool-ppe` — strumenti e DPI
- `textile-material` — materiali (warp yarn, weft yarn, cotton tex, …)
- `agentic-platform` — concept core (HITL, LangGraph node, checkpoint, interrupt, embedding, retrieval, audit-trail)
- `agentic-tool` — pattern tool/MCP/function-calling
- `regulatory` — termini conformità (GDPR, audit retention, …)

Tag categoria → MkDocs material-tags rendering, permette filtraggio nel sito.

**Why:** Lookup cross-domain (un agentic engineer cerca `pick density`, un textile manager cerca `audit trail`). I tag categoria sostituiscono lo split fisico.

**Rejected alternatives:**
- File separati textile/agentic: termini di confine duplicati (es. `predictive maintenance`).
- Glossari nested in domain analysis: lookup cross-process impossibile.

## D-31 — Glossario coverage: ~150 termini per lingua (esaustivo)

**Decision:** Target ~150 termini IT + ~150 termini EN. Mapping concettuale 1:1 fra le due lingue (ogni termine IT ha controparte EN o nota `no-direct-equivalent`).

Distribuzione approssimativa per lingua:
- ~100 textile (10 process, 25 asset, 25 defect, 15 KPI, 10 tool/PPE, 15 material)
- ~40 agentic (20 platform, 15 tool/pattern, 5 regulatory)
- ~10 economia/OEPV (riservato per Phase 11-12 ma seedato qui)

**Why:** Glossario di valore come reference indipendente, non solo filler. Scelta esplicita utente per "esaustivo".

**Drift control:** un termine si aggiunge solo se referenziato (in **bold**) in almeno un SOP, domain page, o ADR. Validato dal CI check di D-32.

## D-32 — Glossary coverage CI check

**Decision:** Script `scripts/validate-glossary-coverage.py`:
1. Estrae token in `**bold**` da tutti i `docs/docs/**/*.md` e `simulators/synthetic-corpus/**/*.md`
2. Normalizza (lowercase, singolare, strip punteggiatura)
3. Per ogni token verifica esistenza in `glossary/{it,en}.yaml` rispettivo
4. Exit 1 con lista mancanti se gap > 0
5. Exit 0 con warning "X stale terms (in glossario ma mai referenziati)" se >5% termini stale

Integrato in:
- `Makefile` target `make validate-glossary`
- CI workflow `.github/workflows/ci.yml` come step `nx run sft-domain:validate-glossary` (target Nx aggiunto al `project.json` di sft-domain)
- pre-commit hook locale opzionale

**Why:** Garantisce che il glossario serva il corpus, non sia un'isola morta.

**Rejected alternatives:**
- No validazione: drift garantito.
- Linting warning-only: senza enforcement non funziona.

## D-33 — Assumption Register: YAML strutturato + render MkDocs

**Decision:** Fonte è `docs/assumptions/register.yaml` (NON in sft-domain — non sono dato dominio textile, sono meta-dati di progetto).

Schema per assumption:
```yaml
- id: A-001
  statement: "TimescaleDB hypertables ingest sensor events with p99 latency < 200ms at 5,000 msg/s"
  category: data-quality
  affected_components: [timescaledb, ot-bridge, anomaly-detector]
  rationale: "Phase 3 success criterion #3 requires this; based on Timescale benchmarks 2.18.x with chunk_interval=1day"
  validation_method: "Phase 3 integration test: 5min load injection at 5k msg/s, measure pg_stat_io tail latency"
  risk_if_wrong: "AnomalyDetector and PredictiveMaintenance produce stale insights; HITL queue floods"
  status: active
  created_in_phase: 2
  last_reviewed_in_phase: 2
  superseded_by: null
```

Script `scripts/generate-assumption-pages.py` consuma YAML, genera:
- `docs/docs/assumptions/index.md` (IT — tabella sortable con filtri material-tags)
- `docs/docs/en/assumptions/index.md` (EN)
- Una pagina dettaglio per assumption (slug = `id`) con tutti i campi visualizzati: `docs/docs/assumptions/A-001.md` + EN counterpart

**Why:** Auditable, filtrabile (es. "tutte le assumption con `affected_components` contenente `ot-bridge`"), schema-validated.

**Rejected alternatives:**
- Markdown table singola: non scala, hard to filter, dati non riusabili da agenti governance/audit di Phase 11+.
- Per-component files: lookup cross-component difficile, viola DRY su assumption che impattano più componenti.

## D-34 — Assumption tagging: doppio asse category + affected_components

**Decision:** Due dimensioni di tag:
- `category`: una di `data-quality | simulation | scope-limit | external-dependency | regulatory | security | performance | cost`
- `affected_components`: array libero di service/agent name (es. `[orchestrator, ot-bridge, sim-textile, langfuse]`). Validato contro inventario dinamico (uno script estrae nomi da `apps/`, `services/`, `simulators/`, `packages/`) → CI fallisce se un'assumption referenzia componente inesistente.

**Why:** Query potenti — "tutte le scope-limit che impattano `ot-bridge`" è una query naturale per audit Phase 11.

**Rejected alternatives:**
- Solo per agente (1 di 16): infra assumption non si mappa.
- Solo per cluster: granularità insufficiente per audit.

## D-35 — Assumption evolution: living doc + audit trail git

**Decision:** Una sola fonte YAML `register.yaml`. Ogni assumption ha:
- `status`: `active | validated | invalidated | superseded` (enum, schema-enforced)
- `last_reviewed_in_phase`: int — quale fase ha rivisto questa assumption
- `superseded_by`: optional `A-NNN` — id che la rimpiazza
- `created_in_phase`: int — fase creazione

Git history (con commit messaggi `feat(02-NN): refine assumption A-042 …`) è l'audit trail. Workflow `gsd-secure-phase` di Phase 11 farà sweep automatico delle assumption con `status=active` e nessun `last_reviewed_in_phase` recente, segnalando assumption potenzialmente stale.

**Why:** Una verità corrente facile da consumare. ADR-style produrrebbe 50+ file iniziali (un per assumption seed) → attrito eccessivo.

**Rejected alternatives:**
- ADR-style immutabile: 50+ file iniziali, vivibili solo con tooling pesante.
- Phase-snapshots: drift tra snapshot e living, duplicazione.

## D-36 — Assumption seed: ~50 entries esaustive

**Decision:** Phase 2 PLAN deve includere autorizzazione/scrittura di ~50 assumption seed distribuite:

- **data-quality (10):** NaN injection from sensor (Phase 3), drift, missing tags, timezone, missing units, IoT-bridge buffer overflow, dataset replay completeness, schema evolution backward compat, sample rate variability, time skew tra PLC.
- **simulation (8):** sim-textile fidelity boundaries, NASA C-MAPSS applicability to textile, UCI Manufacturing as proxy, ambient noise model realism, fault injection coverage gaps, OPC-UA mock vs real PLC differences, simulated network latency boundaries, simulator scale-out limit.
- **scope-limit (10):** Mantis-only deployment first, no multi-tenant, no real PLC integration in MVP, no real material flow tracking, no real labor cost data, no real ERP integration, single-language interface per session (no live IT/EN switch), no production-grade SLOs, no SOC2/ISO27001 in MVP, no formal verification of HITL safety.
- **external-dependency (8):** Ollama uptime SLA, Qwen2.5 weights stability, Qdrant scaling cliffs, Langfuse v3 ClickHouse cost, Postgres extension availability on managed services, Helm chart upstream version pin freshness, Github Actions free tier limits, GPU availability for vLLM fallback.
- **regulatory (6):** GDPR PII boundaries (audit trail), employee data retention limits, Italian labor law on AI decisions (D.lgs 81/2008 art. 15), EU AI Act high-risk categorization questions, audit retention 7 anni vs 30 giorni, right-to-explanation HITL coverage.
- **security (4):** data-diode OT bridge enforcement at runtime, secrets in Kubernetes (SealedSecrets vs Vault), Langfuse self-hosted vs cloud trade-off, Qwen weights supply-chain.
- **performance (3):** LangGraph checkpointer Postgres scaling, embedding compute cost, vector store sharding decisions deferred.
- **cost (1):** GPU vs CPU inference operational cost crossover point.

**Why:** Copertura "paranoica" che serve l'audit di Phase 11 (gsd-secure-phase) e fornisce ai planner di Phase 3-11 una baseline di rischi noti. ~50 è soglia di valore senza filler.

**Authoring:** stesso pattern hybrid di D-25 — Claude in esecuzione di Phase 2 produce draft IT (Italian field text) + EN labels; utente fa review pass su statements più critici (security, scope-limit, regulatory ≈ 20 entries). Pure data-quality / simulation possono passare con review più veloce.

</decisions>

<scope_boundaries>

**In scope (Phase 2):**
- Authoring di domain analysis, SOP corpus, glossario, assumption register (contenuto)
- Schema YAML per glossario e assumption register
- Script di generazione (`generate-glossary-pages.py`, `generate-assumption-pages.py`, `validate-glossary-coverage.py`, `validate-bilingual-mirror.py`, `validate-corpus-frontmatter.py`)
- Integrazione CI dei validation script (Nx targets + GH Actions step)
- Aggiornamento `mkdocs.yml` per nuove navigation entries

**Explicitly NOT in scope (deferred):**
- **BGE-M3 embedding** o vector store ingestion del corpus → Phase 5 (Knowledge Layer)
- **Retrieval pipeline** che usa il corpus → Phase 5
- **Defect taxonomy** in formato strutturato (oltre menzioni in glossario) → Phase 6 (QualityInspector agent)
- **OEPV / economic model** glossary terms beyond seed (~10) → Phase 11
- **ADR** (Architecture Decision Records) per Phase 2 decisions → questo CONTEXT.md serve come ADR di fatto fino a Phase 14 (DOC polish phase)
- **Translation of Phase 1 docs** (`getting-started`, `architecture/overview`) → Phase 14

**Out-of-bounds entirely (mentioned but deferred or rejected):**
- Multi-language oltre IT/EN → not in roadmap
- Domain analysis di settori non-textile → out-of-scope project boundary
- Generation di SOP **runtime** by agents (es. `DocumentationSynthesizer` di KNW cluster genera nuovi SOP) → that's Phase 7+ agent capability; here we seed only static corpus

</scope_boundaries>

<deferred_ideas>

**Recorded during this discussion but out of Phase 2 scope:**

- **`TrainingCoach` audience SOP variants** (D-28): producing 6 SOP in pedagogical-tutorial style. Differito a Phase 7 (Knowledge & Training cluster build-out). Phase 7 può cherry-pick 6 SOP factory-floor esistenti e produrre varianti tutorial.
- **Domain Analysis deep-technical parameters** (D-22): RPM mandrini reali, tensioni filato reali, temperature dyeing reali. Differito a Phase 7+ quando QualityInspector e PredictiveMaintenance avranno feedback su quale precisione serve davvero. Phase 2 lascia parametri come "range tipici industria".
- **Defect taxonomy strutturata** (oltre glossario): tipologie come `slub`, `mispick`, `broken end` saranno glossary entries in Phase 2 ma una taxonomy strutturata YAML in `sft-domain/defects.yaml` è Phase 6 work.
- **OEPV-specific glossary entries beyond seed** (~10 entries): ribasso anomalo, sub-criteria, scoring tecnico/economico → completati in Phase 11.
- **ADR formali (DOC-13)** delle decisioni Phase 2: questo CONTEXT.md serve come ADR di fatto; Phase 14 (DOC polish) può promuovere D-21..D-36 a `docs/docs/adr/A-NNN-*.md` formali.

</deferred_ideas>

<claudes_discretion>

Areas where the user did not request explicit discussion — Claude's PLAN will follow these sensible defaults and document them:

- **MkDocs navigation update strategy:** APPEND under existing nav, do not reorder Phase 1 entries. New top-level items: `Dominio` (IT) / `Domain` (EN), `Procedure (SOP)` / `Procedures (SOP)`, `Assumption Register`, `Glossario` / `Glossary`. Existing `Getting Started`, `Architecture`, `Contributing` stay in place.
- **YAML validation library:** `pydantic` (already common in Python ecosystem) for runtime parsing in `sft_domain.glossary.load_terms()` + `jsonschema` for CI validation. No new heavyweight deps.
- **Mermaid diagrams for process flows:** `flowchart LR` (left-right) per process. Max 8 nodi per diagramma. Style sobrio (no custom CSS).
- **Frontmatter parsing in SOPs:** `python-frontmatter` library (pinned exact version in `simulators/synthetic-corpus/pyproject.toml` if synthetic-corpus becomes a Nx project — TBD by planner).
- **Bilingual mirror check granularity:** match H1 + first 5 H2 headings between IT and EN counterpart. Body diff is too noisy.
- **Generation script idempotency:** scripts re-run produce identical output (sort stable, no timestamps in generated files). Validated in CI by running twice and `git diff` should be empty.
- **Italian variant:** standard italiano (no dialetti). Mantis-context callouts possono usare gergo industriale lombardo se applicabile (es. "subbio" come standard, no varianti regionali).
- **Synthetic-corpus directory layout:** `simulators/synthetic-corpus/{it,en}/{loom,dyeing,spinning,quality}/SOP-XXX-slug.md`. PROJECT-LEVEL Nx target on `simulators/synthetic-corpus` for `validate` (frontmatter schema + bilingual mirror).
- **Synthetic-corpus i18n:** corpus NON va in MkDocs i18n (è dataset, non documentazione utente). Reference link da `docs/docs/sop/index.md` punta al folder e spiega lo scope.

</claudes_discretion>

<downstream_guidance>

**For gsd-phase-researcher (Phase 2):**

Research focus areas (high → low priority):
1. **Frontmatter schema design patterns for SOP/runbook corpora** — best practice for retrieval-friendly metadata, examples from real industrial SOP datasets if public.
2. **MkDocs Material i18n with mkdocs-static-i18n** — verify `docs_structure: folder` works correctly with nested topic directories (domain/, sop/, assumptions/). Already proven in Phase 1 for `getting-started.md` etc., but expanded scope.
3. **Pydantic-based glossary loader patterns** — fastest cold start + dict-based lookups; benchmark for ~300 terms.
4. **CI validation patterns for content (not code)** — pre-commit hooks vs Nx targets vs GHA dedicated workflow; reuse Phase 1 `nx affected` if possible.
5. **Schema versioning** — when sft-domain bumps minor (glossary schema change), how Changesets workflow handles non-code packages.
6. **Mermaid render limits in MkDocs Material** — verify max nodes/edges and accessibility (alt-text for diagrams).
7. **Italian technical terminology authority sources** — ISO 5247 / UNI standards on textile terminology that should be the authority for IT glossary; equivalent EN sources (BS EN, ASTM).

NOT research (already decided in this CONTEXT):
- File organization (D-21)
- Authoring approach (D-25)
- Authoring style (D-28)
- Schema shape (D-26, D-29, D-33)

**For gsd-planner (Phase 2):**

Expected plan count: **6-8 plans** with clear wave structure:
- Wave 1 (foundation): Glossary schema + loader + initial seed (50 textile + 20 agentic ≈ ~70 terms — bootstrap for D-32 coverage check)
- Wave 2 (parallel): Domain analysis IT, Assumption register schema + 30 seed entries, SOP frontmatter schema + 5 example SOPs (1 per asset family + 1 quality)
- Wave 3 (build-out): Remaining SOPs (15 more to hit 20), Glossary expansion to ~150, Assumption register expansion to ~50, Domain analysis EN translation, CI validation scripts and Nx targets
- Wave 4 (integration): MkDocs nav update, generation script runs, bilingual mirror check passes, end-to-end CI green

Each plan must have:
- Atomic commit boundaries (preserve Phase 1 conventional commit pattern with scope `02-NN`)
- Frontmatter schema validation step before content generation
- `depends_on` in canonical short-form (e.g., `["01"]` for glossary schema, `["01", "02"]` for SOP examples)

**Authoring time budget:**
Hybrid LLM-draft + review is dominant cost. Planner should size SOP plans as 1 plan = 5 SOPs (1 per asset family) drafted by Claude + queued for user review in single batch. **Do NOT** plan 1 SOP per plan — too much overhead.

</downstream_guidance>

<next_steps>

Run `/clear` to free context, then:

```
/gsd-plan-phase 2
```

This will:
1. Spawn `gsd-phase-researcher` (reads this CONTEXT + ROADMAP + research areas above) → produces `02-RESEARCH.md`
2. Spawn `gsd-pattern-mapper` → produces `02-PATTERNS.md` (maps new files to closest Phase 1 analogs)
3. Spawn `gsd-planner` → produces 6-8 `02-PLAN-NN-slug-PLAN.md` files
4. Spawn `gsd-plan-checker` → produces `02-VALIDATION.md` with READY-FOR-EXECUTION verdict

Only after planning is approved: `/gsd-execute-phase 2`.

</next_steps>
