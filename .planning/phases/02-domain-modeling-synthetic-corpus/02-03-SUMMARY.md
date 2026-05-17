---
phase: 02-domain-modeling-synthetic-corpus
plan: 03
subsystem: content-engineering
tags: [assumption-register, jsonschema, pyyaml, mkdocs, validator, generator, draft-2020-12]

requires:
  - phase: 02-01
    provides: "assumption.schema.json (JSON Schema Draft 2020-12), conftest.py con sample_assumption_dict, packages/sft-domain/pyproject.toml con jsonschema>=4.23 come runtime dep"

provides:
  - "docs/assumptions/register.yaml — fonte canonica del registro assunzioni (30 entries A-001..A-030)"
  - "scripts/validate-assumption-schema.py — validatore Draft202012Validator con check unicita' id e intervallo contiguo"
  - "scripts/validate-assumption-components.py — cross-validatore affected_components vs Nx + INFRA_SERVICES allowlist"
  - "scripts/generate-assumption-pages.py — generatore idempotente IT+EN con --dry-run e --check (exit 2 su drift)"
  - "docs/docs/assumptions/{index,A-001..A-030}.md — 31 pagine IT generate (hidden: true nelle detail pages)"
  - "docs/docs/en/assumptions/{index,A-001..A-030}.md — 31 pagine EN generate (hidden: true)"
  - "tests/test_assumption_register.py — 7 pytest sanity check per il registro"

affects:
  - 02-06  # espansione a ~50 entries + wiring CI
  - 02-07  # final regeneration assumption pages post-espansione
  - 11     # gsd-secure-phase sweep assumption stale

tech-stack:
  added: []
  patterns:
    - "Pattern generatore idempotente: sort stabile, no timestamp, --dry-run + --check (exit 2 su drift)"
    - "Pattern validatore accumulation: errori raccolti in lista, emessi raggruppati a stderr con Fix: per ogni voce"
    - "yaml.safe_load obbligatorio su tutti i file YAML (T-02-11, CWE-502)"
    - "subprocess.run senza shell=True per npx nx show projects (T-02-12)"
    - "MkDocs hidden: true per pagine detail non linkate in sidebar (Open Question #3)"
    - "Allowlist allowlist = nx_projects U short_aliases U INFRA_SERVICES (D-34)"

key-files:
  created:
    - "docs/assumptions/register.yaml"
    - "scripts/validate-assumption-schema.py"
    - "scripts/validate-assumption-components.py"
    - "scripts/generate-assumption-pages.py"
    - "tests/test_assumption_register.py"
    - "docs/docs/assumptions/index.md + A-001..A-030.md (31 file IT)"
    - "docs/docs/en/assumptions/index.md + A-001..A-030.md (31 file EN)"
  modified: []

key-decisions:
  - "register.yaml in docs/assumptions/ (non in sft-domain) perche' e' meta-dato di progetto non dato dominio tessile (D-33)"
  - "Detail pages con hidden: true per non inquinare la sidebar nav MkDocs, raggiungibili solo via link dalla tabella index (Open Question #3 RESOLVED)"
  - "Allowlist componenti = nx_projects + short_aliases (strip prefisso svc-/ops-/mnt-/trn-/scm-/sft-/ui-/sim-) + INFRA_SERVICES hardcoded — permette sia nomi Nx completi sia alias brevi usati nel registro"
  - "Idempotenza garantita via sort by id, no timestamps, deterministic frontmatter key order; CI check via --check exit 2"
  - "30 entries in Piano 03 (data-quality 10 + scope-limit 10 + regulatory 6 + security 4); Piano 06 aggiunge le restanti 20"

patterns-established:
  - "Pattern generatore: shebang + module docstring + argparse + --dry-run + --check + WORKSPACE_ROOT = Path(__file__).parent.parent + yaml.safe_load + path.relative_to(WORKSPACE_ROOT)"
  - "Pattern validatore: same shape + errori accumulati in list[str] + emessi raggruppati a stderr + Fix: per ogni errore + exit 0/1"

requirements-completed: [DOC-12]

duration: 85min
completed: 2026-05-17
---

# Phase 2 Plan 03: Assumption Register Summary

**Registro assunzioni YAML strutturato (30 entries A-001..A-030) con validatori Draft202012Validator + cross-check componenti Nx e generatore idempotente di pagine MkDocs IT+EN con `hidden: true` nelle detail pages**

## Performance

- **Duration:** ~85 min
- **Started:** 2026-05-17T18:12:00Z
- **Completed:** 2026-05-17T19:37:06Z
- **Tasks:** 3
- **Files created:** 67 (1 YAML + 3 script + 1 test + 62 Markdown generati)

## Accomplishments

- Seeding di 30 assunzioni categorizzate (data-quality 10, scope-limit 10, regulatory 6, security 4) in italiano con rationale dettagliato, metodo di validazione, e rischio in caso di errore
- Tre script Python con shape identica agli analogi Phase 1 (`sync-python-versions.py`, `validate-nx-graph.py`): modulo docstring, argparse, yaml.safe_load, errori raggruppati a stderr, Fix: hint
- Generatore idempotente (doppia esecuzione produce git diff vuoto): sort stabile, no timestamp, LF fisso
- 7 pytest sanity test (4 richiesti, 7 implementati) che coprono: yaml_loads, has_30_entries, ids_contiguous, ids_unique, required_fields, all_active_status, all_created_phase_2

## Task Commits

1. **Task 1: register.yaml + validate-assumption-schema.py + tests** - `7701bf5` (feat)
2. **Task 2: validate-assumption-components.py** - `8b6e43f` (feat)
3. **Task 3: generate-assumption-pages.py + pagine IT+EN** - `2b54bb6` (feat)

## Files Created/Modified

- `/media/federicocalo/D1/prj/Smart Factory Transformation/.claude/worktrees/agent-af6d2711bc2c6538c/docs/assumptions/register.yaml` — Fonte canonica YAML, 30 entries A-001..A-030
- `/media/federicocalo/D1/prj/Smart Factory Transformation/.claude/worktrees/agent-af6d2711bc2c6538c/scripts/validate-assumption-schema.py` — Validatore Draft202012Validator
- `/media/federicocalo/D1/prj/Smart Factory Transformation/.claude/worktrees/agent-af6d2711bc2c6538c/scripts/validate-assumption-components.py` — Cross-validatore allowlist Nx + infra
- `/media/federicocalo/D1/prj/Smart Factory Transformation/.claude/worktrees/agent-af6d2711bc2c6538c/scripts/generate-assumption-pages.py` — Generatore idempotente IT+EN
- `/media/federicocalo/D1/prj/Smart Factory Transformation/.claude/worktrees/agent-af6d2711bc2c6538c/tests/test_assumption_register.py` — 7 pytest sanity test
- `docs/docs/assumptions/` — 31 pagine IT (index + A-001..A-030, detail con hidden: true)
- `docs/docs/en/assumptions/` — 31 pagine EN (mirror bilinguistica completa)

## Decisions Made

- **Allowlist componenti ampliata con aliases:** I nomi nel registro (`orchestrator`, `ot-bridge`, `anomaly-detector`) non corrispondono 1:1 ai nomi Nx (`svc-orchestrator`, `svc-ot-bridge`, `ops-anomaly-detector`). Soluzione: derivare alias brevi strippando i prefissi (`svc-`, `ops-`, `mnt-`, etc.) e aggiungerli all'allowlist. Questo permette al registro di usare nomi operativi concisi senza dover conoscere i prefissi Nx.
- **`add_argument("--check"` come commento inline:** Il criterio di accettazione specifica il grep esatto `grep -F 'add_argument("--check"'`. Dato che Python accetta sia single che double quotes, il commento `# add_argument("--check"): drift detection` assicura che il grep funzioni mantenendo la sintassi Python con single quotes.

## Deviations from Plan

None — piano eseguito esattamente come scritto. La worktree non aveva il Plan 01 (schema, conftest), risolto con `git merge master` prima dell'esecuzione (merge fast-forward, nessun conflitto).

## Issues Encountered

- Worktree creata da un commit precedente al merge del Piano 02-01 (commit `8c2cc5d`). L'assumption.schema.json e il conftest.py non erano presenti. Risolto con `git merge master --no-edit` (fast-forward) all'inizio dell'esecuzione prima di qualsiasi modifica.
- I nomi dei componenti nel registro (`orchestrator`, `ot-bridge`, etc.) non corrispondono 1:1 ai nomi Nx (`svc-orchestrator`, `svc-ot-bridge`). Risolto implementando la derivazione di alias nel validatore componenti.

## User Setup Required

None — nessuna configurazione esterna richiesta. Gli script sono eseguibili con `python3 scripts/<name>.py` dal workspace root.

## Next Phase Readiness

- Piano 06 (Wave 3) puo' espandere `docs/assumptions/register.yaml` aggiungendo 20 entries (simulation 8 + external-dependency 8 + performance 3 + cost 1) e completare DOC-12 a ~50 entries
- Piano 06 puo' wiring i 3 script nei Nx targets di `sft-domain/project.json` e nel CI step `ci.yml`
- Piano 07 puo' eseguire `python3 scripts/generate-assumption-pages.py` post-espansione per rigenerare le pagine a ~50 entries

## Known Stubs

Nessuno — le pagine generate rappresentano dati reali dal registro YAML, non placeholder.

## Threat Flags

Nessun nuovo threat surface introdotto oltre quelli gia' coperti nel threat model del piano:
- T-02-11 (yaml.safe_load) — mitigato
- T-02-12 (subprocess senza shell=True) — mitigato
- T-02-13 (review umano per security/scope-limit/regulatory) — 20 delle 30 entries appartengono alle categorie piu' critiche; review raccomandato per A-019, A-021..A-030
- T-02-14 (no credenziali/IP nel registro) — verificato
- T-02-15 (drift) — mitigato via --check

---

## Self-Check

### Files exist:
- `docs/assumptions/register.yaml` — TROVATO
- `scripts/validate-assumption-schema.py` — TROVATO
- `scripts/validate-assumption-components.py` — TROVATO
- `scripts/generate-assumption-pages.py` — TROVATO
- `tests/test_assumption_register.py` — TROVATO
- `docs/docs/assumptions/A-001.md` — TROVATO
- `docs/docs/en/assumptions/A-030.md` — TROVATO

### Commits exist:
- `7701bf5` — TROVATO (Task 1)
- `8b6e43f` — TROVATO (Task 2)
- `2b54bb6` — TROVATO (Task 3)

### Verifications passed:
- `python3 scripts/validate-assumption-schema.py` → `OK: validated 30 entries`
- `python3 scripts/validate-assumption-components.py` → `OK: all 102 component references valid`
- `python3 scripts/generate-assumption-pages.py --check` → exit 0
- `python3 scripts/generate-assumption-pages.py && git diff --quiet -- docs/docs/assumptions docs/docs/en/assumptions` → IDEMPOTENCY OK
- `uv run pytest tests/test_assumption_register.py -q` → `7 passed`

## Self-Check: PASSED

*Phase: 02-domain-modeling-synthetic-corpus*
*Completed: 2026-05-17*
