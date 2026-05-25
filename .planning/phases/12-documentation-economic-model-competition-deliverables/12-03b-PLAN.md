---
phase: 12-documentation-economic-model-competition-deliverables
plan: 03b
type: execute
wave: 4
depends_on: ["12-00"]
files_modified:
  - docs/docs/adr/index.md
  - docs/docs/adr/ADR-001-langgraph-supervisor.md
  - docs/docs/adr/ADR-002-qdrant-bge-m3.md
  - docs/docs/adr/ADR-003-self-hosted-llm.md
  - docs/docs/adr/ADR-004-hitl-tiers.md
  - docs/docs/adr/ADR-005-mkdocs-i18n.md
  - docs/docs/en/adr/index.md
  - docs/docs/en/adr/ADR-001-langgraph-supervisor.md
  - docs/docs/en/adr/ADR-002-qdrant-bge-m3.md
  - docs/docs/en/adr/ADR-003-self-hosted-llm.md
  - docs/docs/en/adr/ADR-004-hitl-tiers.md
  - docs/docs/en/adr/ADR-005-mkdocs-i18n.md
  - README.md
  - CONTRIBUTING.md
  - CODE_OF_CONDUCT.md
  - docs/mkdocs.yml
autonomous: true
gap_closure: false
requirements: [DOC-13, DOC-14, DOC-16]
must_haves:
  truths:
    - "At least 5 ADRs document key decisions (LangGraph supervisor, Qdrant BGE-M3, self-hosted LLM, HITL tiers, MkDocs i18n), each tracing to shipped code (DOC-13, SC-3)"
    - "Root README.md exists with quick start, repo structure and a contributing pointer (DOC-14)"
    - "Root CONTRIBUTING.md and CODE_OF_CONDUCT.md exist; LICENSE is Apache 2.0 (already present) (DOC-16)"
    - "ADR pages are in mkdocs nav (+EN nav_translations); IT pages have EN mirrors; build stays strict-green"
  artifacts:
    - path: "docs/docs/adr/index.md"
      provides: "ADR index (DOC-13)"
      contains: "ADR"
    - path: "README.md"
      provides: "Root README with quick start + structure (DOC-14)"
      contains: "Quick"
    - path: "CONTRIBUTING.md"
      provides: "Contributing guide (DOC-16)"
      contains: "Contribut"
    - path: "CODE_OF_CONDUCT.md"
      provides: "Code of conduct (DOC-16)"
      contains: "Conduct"
  key_links:
    - from: "docs/docs/adr/ADR-001-langgraph-supervisor.md"
      to: ".planning/phases/04-core-agentic-runtime-hitl"
      via: "decision traces to the shipped supervisor runtime"
      pattern: "LangGraph"
    - from: "README.md"
      to: "CONTRIBUTING.md"
      via: "README links to contributing guide"
      pattern: "CONTRIBUTING"
---

<objective>
Creare ADR (DOC-13), README root (DOC-14) e i file community (DOC-16): ≥5 ADR chiave in `docs/docs/adr/` tracciate al codice (LangGraph supervisor, Qdrant BGE-M3, LLM self-hosted, HITL 4-tier, MkDocs i18n); `README.md` root con quick start + struttura + puntatore contributing; `CONTRIBUTING.md` e `CODE_OF_CONDUCT.md` root (LICENSE Apache 2.0 già presente). Aggiungere le ADR al nav (+EN). Mirror EN per le ADR.

Purpose: realizza DOC-13 (ADR), DOC-14 (README), DOC-16 (community files + LICENSE Apache 2.0).
Output: index ADR + 5 ADR IT+EN, README/CONTRIBUTING/CODE_OF_CONDUCT root, nav aggiornato.

Execution note: SEQUENZIALE su main tree. Wave 4; dipende SOLO da 12-00. File disgiunti da 12-03a (adr/ + root vs security/). Tocca mkdocs.yml SOLO per le ADR (12-03a NON tocca mkdocs.yml).

ATTENZIONE brand-scrub (SC-4): README/CONTRIBUTING/CODE_OF_CONDUCT e le ADR sono file tracciati NON-.planning/ → il gate 12-05 li scansiona. NON nominare il brand originale. Descrivere il progetto per quello che è (piattaforma agentica tessile).
SC-3: ogni ADR traccia a una decisione realmente implementata (citare fase/SUMMARY).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/12-documentation-economic-model-competition-deliverables/12-CONTEXT.md
@.planning/phases/12-documentation-economic-model-competition-deliverables/12-RESEARCH.md
@.planning/phases/12-documentation-economic-model-competition-deliverables/12-00-SUMMARY.md
@docs/docs/contributing/index.md

<interfaces>
<!-- ADR template (MADR-like): Title, Status, Context, Decision, Consequences. Ognuno traccia a codice: -->
<!-- ADR-001 LangGraph supervisor (Phase 4); ADR-002 Qdrant+BGE-M3 hybrid (Phase 5); ADR-003 self-hosted LLM/Ollama (Phase 1/4); ADR-004 HITL 4-tier (Phase 4); ADR-005 MkDocs Material i18n (Phase 1). -->
<!-- LICENSE alla root è già Apache 2.0 — README/CONTRIBUTING devono citarlo, non duplicarlo. -->
<!-- docs/docs/contributing/index.md esiste già (sezione docs); CONTRIBUTING.md root è il file community standard GitHub (può linkare alla pagina docs). -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: 5 ADR tracciate + index + nav (DOC-13)</name>
  <files>docs/docs/adr/index.md, docs/docs/adr/ADR-001-langgraph-supervisor.md, docs/docs/adr/ADR-002-qdrant-bge-m3.md, docs/docs/adr/ADR-003-self-hosted-llm.md, docs/docs/adr/ADR-004-hitl-tiers.md, docs/docs/adr/ADR-005-mkdocs-i18n.md, docs/docs/en/adr/index.md, docs/docs/en/adr/ADR-001-langgraph-supervisor.md, docs/docs/en/adr/ADR-002-qdrant-bge-m3.md, docs/docs/en/adr/ADR-003-self-hosted-llm.md, docs/docs/en/adr/ADR-004-hitl-tiers.md, docs/docs/en/adr/ADR-005-mkdocs-i18n.md, docs/mkdocs.yml</files>
  <action>Creare 5 ADR in formato MADR-like (Title, Status=Accepted, Context, Decision, Consequences), ognuna che traccia a una decisione implementata e cita la fase: ADR-001 LangGraph supervisor pattern (Phase 4), ADR-002 Qdrant + BGE-M3 hybrid retrieval (Phase 5), ADR-003 LLM self-hosted via Ollama (Phase 1/4), ADR-004 HITL 4-tier approval (Phase 4), ADR-005 MkDocs Material + i18n bilingue (Phase 1). Creare `adr/index.md` con la tabella delle ADR (numero, titolo, stato). Mirror EN per tutte. Aggiungere al nav (sotto `ADR`) le 5 ADR + index, e le `nav_translations` EN necessarie (i titoli ADR possono restare invariati; "Indice"→"Index" già presente). NON nominare il brand originale (SC-4). Nessun `![img]()`.</action>
  <verify>
    <automated>cd docs && for n in 001-langgraph-supervisor 002-qdrant-bge-m3 003-self-hosted-llm 004-hitl-tiers 005-mkdocs-i18n; do test -f "docs/adr/ADR-$n.md" && test -f "docs/en/adr/ADR-$n.md" || { echo "missing ADR-$n"; exit 1; }; done; python3 -c "s=open('docs/adr/ADR-001-langgraph-supervisor.md').read(); assert 'Decision' in s and 'LangGraph' in s" && python3 -m mkdocs build --strict</automated>
  </verify>
  <done>5 ADR IT+EN tracciate al codice (formato Status/Context/Decision/Consequences); index ADR; nav aggiornato; nessun brand; build strict verde.</done>
</task>

<task type="auto">
  <name>Task 2: README root + CONTRIBUTING + CODE_OF_CONDUCT (DOC-14/DOC-16)</name>
  <files>README.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md</files>
  <action>Creare `README.md` root: titolo progetto (piattaforma agentica opensource per industria tessile manifatturiera), badge/descrizione, Quick Start (clona, `make up`, `uv sync`, `cd docs && mkdocs serve` per le docs), struttura del repo (apps/, packages/, services/, infra/, docs/, simulators/), link a docs site (GitHub Pages) e a CONTRIBUTING.md, menzione LICENSE Apache 2.0. Creare `CONTRIBUTING.md` root: workflow conventional commits, pre-commit hooks, come eseguire test (`nx affected`, pytest), come buildare le docs; può linkare a `docs/docs/contributing/index.md`. Creare `CODE_OF_CONDUCT.md` root (Contributor Covenant standard). NESSUN riferimento al brand originale (SC-4) — descrivere il progetto in modo neutro. NON modificare LICENSE (già Apache 2.0).</action>
  <verify>
    <automated>cd "$(git rev-parse --show-toplevel)" && python3 -c "import re; r=open('README.md').read(); assert re.search(r'[Qq]uick', r) and 'CONTRIBUTING' in r and 'Apache' in r; c=open('CONTRIBUTING.md').read(); assert 'commit' in c.lower(); coc=open('CODE_OF_CONDUCT.md').read(); assert 'Conduct' in coc or 'conduct' in coc; print('community-files-ok')" && head -1 LICENSE >/dev/null</automated>
  </verify>
  <done>README.md (quick start+struttura+LICENSE+contributing), CONTRIBUTING.md (commit/test/docs), CODE_OF_CONDUCT.md creati; nessun brand; LICENSE Apache 2.0 invariata.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| root files → public repo surface | README/CONTRIBUTING/CODE_OF_CONDUCT sono file tracciati pubblici (gate brand-scrub) |
| docs claim → shipped code | ADR devono tracciare a decisioni realmente implementate (SC-3) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-12-03b-01 | Information Disclosure | brand originale in README/ADR | mitigate | Nessuna menzione del brand; gate brand-scrub 12-05 scansiona questi file. |
| T-12-03b-02 | Repudiation | ADR descrive decisione non implementata | mitigate | Ogni ADR cita fase/SUMMARY; SC-3 verificato in 12-05. |
</threat_model>

<verification>
- 5 ADR IT+EN + index nel nav; README/CONTRIBUTING/CODE_OF_CONDUCT root.
- Nessun brand; LICENSE Apache 2.0 invariata.
- `mkdocs build --strict` verde.
</verification>

<success_criteria>
DOC-13/DOC-14/DOC-16 chiusi: ≥5 ADR tracciate al codice, README con quick start/struttura, CONTRIBUTING + CODE_OF_CONDUCT, LICENSE Apache 2.0; nessun riferimento al brand.
</success_criteria>

<output>
Create `.planning/phases/12-documentation-economic-model-competition-deliverables/12-03b-SUMMARY.md` when done.
</output>
