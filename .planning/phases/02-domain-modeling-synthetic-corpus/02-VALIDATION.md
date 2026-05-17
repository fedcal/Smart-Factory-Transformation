---
phase: 2
slug: domain-modeling-synthetic-corpus
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-17
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `02-RESEARCH.md` § Validation Architecture (single source of truth).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` 8.x (per loader + content asserts) + Python script self-validation (jsonschema, pyyaml, python-frontmatter) — no JS test framework needed |
| **Config file** | `pyproject.toml` root `[tool.pytest.ini_options]` (Wave 0 creates if absent) + `packages/sft-domain/pyproject.toml` for project-local tests |
| **Quick run command** | `python3 scripts/validate-corpus-frontmatter.py && python3 scripts/validate-bilingual-mirror.py && python3 scripts/validate-glossary-coverage.py` |
| **Full suite command** | `npx nx run-many --target=validate-glossary,validate-frontmatter,validate-bilingual-mirror --all && python3 scripts/generate-glossary-pages.py --check && python3 scripts/generate-assumption-pages.py --check && mkdocs build --strict` |
| **Estimated runtime** | ~5 s (quick) / ~20-30 s (full incl. mkdocs strict) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (`~5 s` via pre-commit hook, extension of Phase 1 hook config)
- **After every plan wave:** Run full suite (`~20-30 s`) via `make validate-all` (new Makefile target)
- **Before `/gsd:verify-work`:** Full suite must be green on CI workflow `.github/workflows/ci.yml` + `docs-deploy.yml`
- **Max feedback latency:** 30 s

---

## Per-Task Verification Map

> Filled by planner during Step 8. Each task in every PLAN.md MUST map to one row here (or be flagged Manual-Only).
> `File Exists` column resolves to ✅ after Wave 0 ships the script/test file; ❌ W0 means Wave 0 must create it before the task can run.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-02-T2 | 02-02 | 2 | DOC-05 | T-02-10 | Bilingual mirror IT↔EN preserved (H1+first 5 H2 match) | structural | `python3 scripts/validate-bilingual-mirror.py` (with `--allow-missing-en` until 02-05; without after) | ❌ W0 (created 02-04) | ⬜ pending |
| 02-02-T2 | 02-02 | 2 | DOC-05 | T-02-07 | Each process page contains Mermaid `flowchart LR` + KPI + pain point sections + Mantis admonition | content | `pytest tests/test_domain_pages.py::test_process_sections` | ❌ W0 (created 02-02) | ⬜ pending |
| 02-03-T1 | 02-03 | 2 | DOC-12 | T-02-11 | Assumption register YAML schema-valid (Draft 2020-12) — 30 entries Plan 03, 50 after Plan 06 | schema | `python3 scripts/validate-assumption-schema.py` | ❌ W0 (created 02-03) | ⬜ pending |
| 02-03-T2 | 02-03 | 2 | DOC-12 | T-02-12 | `affected_components` references existing Nx project / known infra | reference | `python3 scripts/validate-assumption-components.py` | ❌ W0 (created 02-03) | ⬜ pending |
| 02-03-T3 | 02-03 | 2 | DOC-12 | T-02-15 | Generated assumption pages idempotent vs YAML | regression | `python3 scripts/generate-assumption-pages.py --check` | ❌ W0 (created 02-03) | ⬜ pending |
| 02-06-T1 | 02-06 | 3 | DOC-18 | T-02-27 | Glossary YAML files schema-valid (IT + EN) | schema | `python3 scripts/validate-glossary-schema.py` | ❌ W0 (created 02-06) | ⬜ pending |
| 02-06-T1 | 02-06 | 3 | DOC-18 | T-02-28 | All `**bold**` tokens in docs/corpus have glossary entry (lang-matched) — Pitfall-5 hardened | coverage | `python3 scripts/validate-glossary-coverage.py` | ❌ W0 (created 02-06) | ⬜ pending |
| 02-06-T2 | 02-06 | 3 | DOC-18 | T-02-29 | Generated `glossary.md` idempotent vs YAML | regression | `python3 scripts/generate-glossary-pages.py --check` | ❌ W0 (created 02-06) | ⬜ pending |
| 02-01-T3 | 02-01 | 1 | DOC-18 | T-02-02 | `sft_domain.glossary.load_terms()` returns ≥70 (Plan 01) / ≥150 (after Plan 05) | unit | `uv run --project packages/sft-domain pytest packages/sft-domain/tests/test_glossary_loader.py` | ✅ created 02-01 | ⬜ pending |
| 02-05-T1 | 02-05 | 3 | KNW-10 | — | Corpus has 5+5+5+5 = 20 IT SOPs (40 with EN) | inventory | `pytest tests/test_corpus_inventory.py::test_distribution_phase04` (relaxed Plan 04 ≥1, tightened in Plan 05) | ❌ W0 (created 02-04) | ⬜ pending |
| 02-04-T2 | 02-04 | 2 | KNW-10 | T-02-17 | Each SOP frontmatter validates against sop.schema.json | schema | `python3 scripts/validate-corpus-frontmatter.py` | ❌ W0 (created 02-04) | ⬜ pending |
| 02-04-T2 | 02-04 | 2 | KNW-10 | T-02-18 | Each SOP has IT+EN counterpart with matching `id` + asset + role + hazard | bilingual | `python3 scripts/validate-corpus-pairing.py` (with `--allow-missing-en` Plan 04 only) | ❌ W0 (created 02-04) | ⬜ pending |
| 02-04-T2 | 02-04 | 2 | KNW-10 | T-02-17 | Each SOP has required 7 H2 sections in fixed order (Scope, Prereq, Tools, Steps, Verif, Trouble, Refs) | structural | included in `validate-corpus-frontmatter.py` | ❌ W0 (created 02-04) | ⬜ pending |
| 02-07-T1+T2+T4 | 02-07 | 4 | ALL | T-02-35 | MkDocs site builds clean with full Phase 2 content + extended nav + tags plugin | integration | `mkdocs build --strict` via `make docs` | ✅ Phase 1 (`docs-deploy.yml`) | ⬜ pending |
| 02-07-T3 | 02-07 | 4 | KNW-10 | T-02-33 | D-25 user review batch — SOPs promoted from draft-unreviewed to reviewed | manual | checkpoint:human-verify (Plan 07 Task 3) | ✅ manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 (foundation) MUST ship the following before any content-authoring task runs. All paths are new in Phase 2.

**JSON Schemas (Draft 2020-12):**
- [ ] `packages/sft-domain/src/sft_domain/schemas/glossary.schema.json`
- [ ] `packages/sft-domain/src/sft_domain/schemas/sop.schema.json`
- [ ] `packages/sft-domain/src/sft_domain/schemas/assumption.schema.json`

**Glossary loader (Pydantic v2):**
- [ ] `packages/sft-domain/src/sft_domain/glossary/__init__.py` — exports
- [ ] `packages/sft-domain/src/sft_domain/glossary/models.py` — Pydantic `Term` + `Category` enum
- [ ] `packages/sft-domain/src/sft_domain/glossary/loader.py` — `load_terms(lang)` + `load_terms_dict(lang)` with `lru_cache`

**Tests:**
- [ ] `packages/sft-domain/tests/test_glossary_loader.py`
- [ ] `packages/sft-domain/tests/test_glossary_schema.py`
- [ ] `packages/sft-domain/tests/conftest.py` — shared fixtures (sample Term, sample SOP frontmatter)
- [ ] `tests/test_domain_pages.py` — domain-page structural asserts
- [ ] `tests/test_corpus_inventory.py` — corpus distribution count
- [ ] `tests/conftest.py` (root) — repo-level pytest fixtures

**Synthetic-corpus Nx project:**
- [ ] `simulators/synthetic-corpus/project.json` — Nx project with `validate-frontmatter`, `validate-bilingual-mirror`, `validate-pairing` targets
- [ ] `simulators/synthetic-corpus/README.md` — scope, schema reference, authoring guidelines

**Generation + validation scripts (pattern: copy `scripts/sync-python-versions.py`):**
- [ ] `scripts/generate-glossary-pages.py` (supports `--check` for drift)
- [ ] `scripts/generate-assumption-pages.py` (supports `--check`)
- [ ] `scripts/validate-glossary-schema.py`
- [ ] `scripts/validate-glossary-coverage.py`
- [ ] `scripts/validate-bilingual-mirror.py`
- [ ] `scripts/validate-corpus-frontmatter.py`
- [ ] `scripts/validate-corpus-pairing.py`
- [ ] `scripts/validate-assumption-schema.py`
- [ ] `scripts/validate-assumption-components.py`

**Build + dependency wiring:**
- [ ] `Makefile` — add `validate-corpus`, `generate-glossary`, `generate-assumptions`, `validate-glossary`, `validate-all`
- [ ] root `pyproject.toml` — add `python-frontmatter`, `jsonschema` (upgrade), `pytest`-related deps to `[dependency-groups] dev`
- [ ] `packages/sft-domain/pyproject.toml` — add runtime deps `pydantic`, `pyyaml`
- [ ] `.github/workflows/ci.yml` — new step "Validate content" after "Validate Nx dependency graph"
- [ ] `.gitignore` — ensure `Smart Factory Transformation.md` (the original brief) is covered or explicitly moved

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SOP technical correctness (no fabricated dyeing temperatures, no impossible warp tensions) | KNW-10 | LLM-drafted content needs domain-expert sanity check — cannot be automated without ground-truth dataset | Per D-25 hybrid review: user reviews each draft IT in `phase-02-sop-drafts/` branch before merge; only `status: reviewed` SOPs accepted as ground truth for downstream agent retrieval |
| Italian terminology fidelity for ISO 5247 / UNI standards | DOC-18 | UNI translations not freely verifiable; pragmatic: tag `source: industry-standard` when ISO not confirmable in Italian (per Research § Confidence: MEDIUM) | User pass on glossary terms tagged `category: textile-process / textile-defect`; check Italian field for non-anglicism unless gergo industriale standard |
| Brand isolation: zero Accenture references in any Phase 2 content (D-08 from Phase 1) | ALL | Phase 12 brand-scrub CI not yet in place; Phase 2 LLM-drafted content needs human pass | User reviews draft batches for inadvertent brand contamination before merge |
| Mantis sidebar context accuracy (D-23) | DOC-05 | Mantis-specific yarn types / shift patterns are domain-expert claims; CI cannot verify | User reviews each `!!! note "Mantis context"` admonition during domain page authoring |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies declared
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references in Per-Task Verification Map (`File Exists = ❌ W0`)
- [ ] No watch-mode flags (all commands exit deterministically)
- [ ] Feedback latency < 30 s
- [ ] `nyquist_compliant: true` set in frontmatter after planner fills Per-Task Verification Map and Wave 0 dependencies wired

**Approval:** pending
