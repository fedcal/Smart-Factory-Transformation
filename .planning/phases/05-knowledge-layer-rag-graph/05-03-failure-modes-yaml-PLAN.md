---
plan_id: 05-03-failure-modes-yaml
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 1
depends_on: []
requirements: [KNW-08]
files_modified:
  - packages/sft-domain/src/sft_domain/failure_modes.yaml
  - packages/sft-domain/src/sft_domain/failure_modes/__init__.py
  - packages/sft-domain/src/sft_domain/failure_modes/_loader.py
  - packages/sft-domain/src/sft_domain/failure_modes/models.py
  - packages/sft-domain/tests/test_failure_modes_loader.py
  - packages/sft-domain/project.json
  - scripts/validate-failure-modes.py
autonomous: true
estimated_atomic_commits: 3
must_haves:
  truths:
    - "failure_modes.yaml contains ≥30 failure mode entries derived from Phase 2 defect taxonomy"
    - "load_failure_modes() returns tuple[FailureMode, ...] (immutable)"
    - "Loader is lru_cache singleton; second call returns identical object reference"
    - "Each FailureMode has at least one corresponding SOP in the corpus (CI validator)"
    - "FailureMode model is frozen + extra=forbid"
  artifacts:
    - path: packages/sft-domain/src/sft_domain/failure_modes.yaml
      provides: 30+ failure mode definitions with name_it/name_en, asset_families, parts
    - path: packages/sft-domain/src/sft_domain/failure_modes/_loader.py
      provides: lru_cache singleton loader returning immutable tuple
    - path: scripts/validate-failure-modes.py
      provides: CI validator — every FailureMode has ≥1 SOP referencing it
  key_links:
    - from: packages/sft-domain/src/sft_domain/failure_modes/_loader.py
      to: packages/sft-domain/src/sft_domain/failure_modes.yaml
      via: yaml.safe_load + Pydantic validation
      pattern: "yaml\\.safe_load"
    - from: scripts/validate-failure-modes.py
      to: simulators/synthetic-corpus/
      via: cross-reference FailureMode.id vs SOP frontmatter tags/related fields
      pattern: "failure_mode"
---

<objective>
Add `failure_modes.yaml` + Pydantic loader + 30+ entries derived from Phase 2 defect taxonomy + CI validator that every FailureMode has at least one SOP referencing it.

Purpose: input for Plan 05-08 Neo4j graph builder (FailureMode nodes + DOCUMENTED_BY edges) and Plan 05-09 traverse_graph tool. Without this, KNW-08 SC#4 ("traversal query returns a valid SOP for a given failure mode") cannot be satisfied.

Output: a `sft_domain.failure_modes` sub-package with 30+ validated entries and a CI gate that prevents orphan failure modes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md
@.planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md
@.planning/phases/02-domain-modeling-synthetic-corpus/02-CONTEXT.md
@packages/sft-assets/src/sft_assets/_loader.py
@packages/sft-domain/src/sft_domain/glossary/_loader.py
@packages/sft-domain/project.json
</context>

<interfaces>
FailureMode schema (D-65 + 05-PATTERNS.md failure_modes loader section):

```
class FailureMode(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    id: str                       # e.g. "broken_end" — used as Neo4j FailureMode.id
    name_it: str                  # e.g. "rottura filo ordito"
    name_en: str                  # e.g. "broken end"
    asset_families: list[str]     # e.g. ["weaving"]
    parts: list[str]              # e.g. ["warp", "heddle"]
    severity: Literal["low", "medium", "high"] = "medium"
```

YAML shape (D-65 CONTEXT lines 269-283):
```
failure_modes:
  - id: broken_end
    name_it: rottura filo ordito
    name_en: broken end
    asset_families: [weaving]
    parts: [warp, heddle]
    severity: medium
```

Loader contract (mirror `packages/sft-assets/src/sft_assets/_loader.py`):
- `@lru_cache(maxsize=1) def load_failure_modes() -> tuple[FailureMode, ...]:`
- raises FileNotFoundError if yaml missing
- raises ValueError if not list under `failure_modes` key
- yaml.safe_load only (T-03-01-yaml threat)
- `invalidate_cache() -> None` for tests

Phase 2 defect taxonomy (source for 30+ entries):
- Weaving defects: broken_end, mispick, slub, neppy, selvage_fault, double_pick, oil_stain, weft_bar, reed_mark
- Spinning defects: yarn_break, thin_place, thick_place, yarn_imbalance, fiber_contamination
- Dyeing defects: shade_deviation, unlevel_dyeing, dye_streaks, crocking, color_migration, tailing
- Finishing defects: pilling, shrinkage_excess, hand_feel_off, finish_streaks
- Quality grading defects: snag, hole, foreign_yarn, knot, missing_yarn, bow_distortion, skew

Each entry MUST map to ≥1 SOP in the existing 41-SOP corpus (search frontmatter `tags`, `related_glossary`, or `asset_family` for cross-reference).
</interfaces>

<tasks>

<task id="05-03-01" type="auto" tdd="true">
  <name>Task 1: FailureMode model + loader + 30+ YAML entries</name>
  <files>
    packages/sft-domain/src/sft_domain/failure_modes.yaml,
    packages/sft-domain/src/sft_domain/failure_modes/__init__.py,
    packages/sft-domain/src/sft_domain/failure_modes/models.py,
    packages/sft-domain/src/sft_domain/failure_modes/_loader.py,
    packages/sft-domain/tests/test_failure_modes_loader.py
  </files>
  <read_first>
    packages/sft-assets/src/sft_assets/_loader.py (lru_cache pattern lines 22-49, invalidate_cache lines 70-75),
    packages/sft-domain/src/sft_domain/glossary/_loader.py (parallel loader pattern in sft-domain),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (failure_modes loader section + Shared Pattern 5 yaml.safe_load + Shared Pattern 8 lru_cache),
    .planning/phases/02-domain-modeling-synthetic-corpus/02-CONTEXT.md (defect taxonomy section),
    simulators/synthetic-corpus/it/loom/*.md (1-2 files to confirm asset_family + tags fields)
  </read_first>
  <behavior>
    - `FailureMode` is a frozen Pydantic v2 model with the exact fields above
    - `load_failure_modes()` returns `tuple[FailureMode, ...]` (immutable per coding-style.md)
    - Calling load_failure_modes() twice returns the SAME object reference (`is` identity — lru_cache behavior)
    - The YAML file contains ≥30 entries spanning the 5 process families (weaving, spinning, dyeing, finishing, quality_grading)
    - Loader raises FileNotFoundError with descriptive message if YAML missing
    - Loader raises ValueError if root is not a dict with `failure_modes:` key holding a list
    - `invalidate_cache()` clears lru_cache (for tests after monkeypatching path)
    - Loader uses `yaml.safe_load` only (never `yaml.load`)
    - test_loads_at_least_30_failure_modes asserts `len(load_failure_modes()) >= 30`
    - test_each_entry_validates asserts every entry is FailureMode instance with non-empty asset_families + parts
    - test_yaml_safe_load_invoked: patch `yaml.load` to raise; loader must still succeed (proving it uses safe_load)
    - test_singleton_identity: two calls return identical object reference
    - test_frozen_failure_mode: mutating a FailureMode field raises ValidationError
  </behavior>
  <action>
    Create `packages/sft-domain/src/sft_domain/failure_modes/__init__.py` re-exporting `FailureMode, load_failure_modes, invalidate_cache` from `.models` and `._loader`.

    Create `packages/sft-domain/src/sft_domain/failure_modes/models.py`:
    - Frozen Pydantic `FailureMode` per the schema above. Severity defaults to "medium".

    Create `packages/sft-domain/src/sft_domain/failure_modes/_loader.py`:
    - Mirror `packages/sft-assets/src/sft_assets/_loader.py` exactly: WORKSPACE-relative path, `@lru_cache(maxsize=1)`, raise on FileNotFoundError + ValueError, `yaml.safe_load(text)`, return `tuple(FailureMode.model_validate(e) for e in raw["failure_modes"])`.
    - Add `invalidate_cache()` that calls `load_failure_modes.cache_clear()`.

    Create `packages/sft-domain/src/sft_domain/failure_modes.yaml` with **≥30 entries** covering the 5 process families. Use snake_case ids in English. For each entry, provide:
    - `id` (lowercase snake_case, English)
    - `name_it` (Italian noun phrase, lowercase)
    - `name_en` (English noun phrase, lowercase)
    - `asset_families` (1-2 values from {weaving, spinning, dyeing, finishing, quality_grading})
    - `parts` (1-3 textile-domain part names, snake_case English)
    - `severity` (low | medium | high; reserved high for safety-critical defects like fiber_contamination + foreign_yarn)

    Use the 30 candidate entries listed in the `<interfaces>` block as the minimum set. Cross-reference Phase 2 defect taxonomy in `02-CONTEXT.md` for any additional or renamed entries.

    Create `packages/sft-domain/tests/test_failure_modes_loader.py` with the unit tests from `<behavior>` (test_loads_at_least_30_failure_modes, test_each_entry_validates, test_yaml_safe_load_invoked, test_singleton_identity, test_frozen_failure_mode). Use `monkeypatch` for path injection where needed; call `invalidate_cache()` in setup/teardown.

    Update `packages/sft-domain/project.json` (if needed) to ensure `nx run sft-domain:test` discovers the new tests. Existing pytest config in `packages/sft-domain/pyproject.toml` should already discover them under `tests/`.

    Commit: `feat(05-03-failure-modes-yaml): add FailureMode model + loader + 30+ YAML entries`.
  </action>
  <acceptance_criteria>
    - `packages/sft-domain/src/sft_domain/failure_modes.yaml` exists
    - `python -c "import yaml; d=yaml.safe_load(open('packages/sft-domain/src/sft_domain/failure_modes.yaml')); assert len(d['failure_modes']) >= 30, len(d['failure_modes'])"` exits 0
    - `grep -q 'class FailureMode(BaseModel):' packages/sft-domain/src/sft_domain/failure_modes/models.py`
    - `grep -q 'model_config = {"frozen": True, "extra": "forbid"}' packages/sft-domain/src/sft_domain/failure_modes/models.py`
    - `grep -q '@lru_cache(maxsize=1)' packages/sft-domain/src/sft_domain/failure_modes/_loader.py`
    - `grep -q 'yaml.safe_load' packages/sft-domain/src/sft_domain/failure_modes/_loader.py`
    - `nx run sft-domain:test --args="-k test_failure_modes -v"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-domain:test --args="-k test_failure_modes -v" &amp;&amp; python -c "import yaml; d=yaml.safe_load(open('packages/sft-domain/src/sft_domain/failure_modes.yaml')); assert len(d['failure_modes']) &gt;= 30"</automated>
  </verify>
  <done>FailureMode loader + 30+ entries committed; tests exit 0; singleton + frozen behavior verified.</done>
</task>

<task id="05-03-02" type="auto" tdd="true">
  <name>Task 2: CI validator script — every FailureMode has ≥1 SOP reference</name>
  <files>
    scripts/validate-failure-modes.py,
    packages/sft-domain/tests/test_failure_modes_loader.py
  </files>
  <read_first>
    scripts/validate-corpus-frontmatter.py (WORKSPACE_ROOT pattern + corpus rglob iteration + exit code pattern),
    packages/sft-domain/src/sft_domain/failure_modes/_loader.py (just created in Task 1),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-65 CI validator spec lines 285-289)
  </read_first>
  <behavior>
    - validate-failure-modes.py loads failure modes via `load_failure_modes()` AND scans all SOPs via `frontmatter.load`
    - For each FailureMode, search SOP frontmatter for any of: `failure_mode_id == fm.id`, `fm.id in tags`, `fm.id in related_glossary`, or `fm.name_it in title` / `fm.name_en in title` (case-insensitive substring)
    - Build set of "referenced" failure mode ids
    - Report any FailureMode.id NOT in referenced set as orphan
    - Exit 0 if zero orphans; exit 1 (with stderr message listing orphans) if any
    - Script supports `--corpus-dir` flag (default `simulators/synthetic-corpus`)
    - Script supports `--allow-orphans` flag for Phase 5 bootstrap (allows up to N orphans during initial run, default 0; documented as deprecation path for Phase 8 KnowledgeCurator)
  </behavior>
  <action>
    Create `scripts/validate-failure-modes.py`:
    - `from __future__ import annotations`, argparse, sys, pathlib, frontmatter
    - `WORKSPACE_ROOT = Path(__file__).parent.parent`
    - `sys.path.insert(0, str(WORKSPACE_ROOT / "packages/sft-domain/src"))` (or rely on workspace pip install — if `sft_domain` already on PYTHONPATH from uv workspace, skip this)
    - `from sft_domain.failure_modes import load_failure_modes`
    - main():
      1. argparse: `--corpus-dir`, `--allow-orphans` (int, default 0)
      2. Load failure modes: `fms = load_failure_modes()`
      3. Scan corpus: `for md in corpus.rglob("*.md")`, parse frontmatter, build a normalized set of all reference tokens from {tags, related_glossary, audience-derived, title lowercased}.
      4. For each fm: search tokens for fm.id, fm.name_it.lower(), fm.name_en.lower(). Mark referenced.
      5. Report counts: `total_fms`, `referenced`, `orphans` (list).
      6. Print summary line `FAILURE_MODES: total=X referenced=Y orphans=Z`.
      7. If `len(orphans) > allow_orphans`: print orphan list to stderr; sys.exit(1). Else sys.exit(0).

    Add test in `packages/sft-domain/tests/test_failure_modes_loader.py`:
    - `test_all_failure_modes_referenced_by_at_least_one_sop`: invokes validator main() (via subprocess.run with `sys.executable`) against the real corpus; asserts exit code == 0. If orphans exist after Plan 05-03 task 1 YAML authoring, the YAML must be edited to remove orphan entries OR `--allow-orphans` set with explicit number to track Phase 8 commitments.

    **Constraint:** Plan 05-03 ships with `--allow-orphans=0` (zero orphans allowed). If the test fails, the YAML in Task 1 needs adjustment to use only failure modes that genuinely match the existing 41-SOP corpus. The executor MUST iterate on the YAML content until orphans=0.

    Commit: `feat(05-03-failure-modes-yaml): add CI validator + orphan check`.
  </action>
  <acceptance_criteria>
    - `scripts/validate-failure-modes.py` exists and is executable via `uv run python`
    - `grep -q 'from sft_domain.failure_modes import load_failure_modes' scripts/validate-failure-modes.py`
    - `grep -q 'orphan' scripts/validate-failure-modes.py` (orphan detection logic)
    - `uv run python scripts/validate-failure-modes.py` exits 0 (zero orphans after Task 1 YAML curation)
    - `nx run sft-domain:test --args="-k test_all_failure_modes_referenced -v"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>uv run python scripts/validate-failure-modes.py &amp;&amp; nx run sft-domain:test --args="-k test_all_failure_modes_referenced -v"</automated>
  </verify>
  <done>Validator script + test green; zero orphan failure modes; CI ready to wire.</done>
</task>

<task id="05-03-03" type="auto">
  <name>Task 3: Nx target for failure-modes validate + CI wiring</name>
  <files>
    packages/sft-domain/project.json,
    .github/workflows/ci.yml
  </files>
  <read_first>
    packages/sft-domain/project.json (existing target structure),
    .github/workflows/ci.yml (existing nx run invocations + Python setup steps)
  </read_first>
  <action>
    Edit `packages/sft-domain/project.json`:
    - Add new target `validate-failure-modes`:
      - executor: `@nxlv/python:run-commands`
      - options.command: `uv run python scripts/validate-failure-modes.py`
      - options.cwd: workspace root (use `"."` or omit if Nx defaults to workspace root)

    Edit `.github/workflows/ci.yml`:
    - In the existing test/validate job, add a step:
      - name: `Validate failure modes coverage`
      - run: `nx run sft-domain:validate-failure-modes`
    - Place this step after the test setup steps (Python+uv install) and before/alongside other nx validate targets.
    - Do NOT remove or reorder existing Phase 1-4 CI steps.

    Verify locally:
    - `nx run sft-domain:validate-failure-modes` exits 0.
    - Optional: simulate a CI failure by temporarily adding an orphan FailureMode to the YAML, run target, confirm exit 1; revert immediately. (This is sanity-check only — DO NOT commit the orphan.)

    Commit: `ci(05-03-failure-modes-yaml): add validate-failure-modes Nx target + GitHub Actions step`.
  </action>
  <acceptance_criteria>
    - `grep -q 'validate-failure-modes' packages/sft-domain/project.json`
    - `grep -q 'validate-failure-modes' .github/workflows/ci.yml`
    - `nx run sft-domain:validate-failure-modes` exits 0
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-domain:validate-failure-modes &amp;&amp; grep -q 'validate-failure-modes' .github/workflows/ci.yml</automated>
  </verify>
  <done>Validator wired into CI pipeline; failure modes coverage gate active for all future PRs.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| filesystem → YAML loader | YAML content is repo-trusted but parsed; use safe_load to avoid arbitrary code execution |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-03-01 | Tampering | YAML loader | mitigate | `yaml.safe_load` only (T-03-01-yaml inherited from Phase 3); test asserts unsafe load path is not used |
| T-05-03-02 | Tampering | failure_modes.yaml content drift | mitigate | CI validator (Task 3) blocks orphan failure modes; Pydantic frozen+forbid blocks malformed schema |
| T-05-03-03 | Information Disclosure | failure mode taxonomy | accept | Failure modes describe public textile manufacturing knowledge; no PII or trade secrets |
| T-05-03-SC | Tampering | npm/pip install | mitigate | Only existing workspace deps (pyyaml, pydantic, python-frontmatter); zero new packages |
</threat_model>

<verification>
- `nx run sft-domain:test --args="-k test_failure_modes -v"` exits 0
- `uv run python scripts/validate-failure-modes.py` exits 0
- `nx run sft-domain:validate-failure-modes` exits 0
- `python -c "from sft_domain.failure_modes import load_failure_modes; fms = load_failure_modes(); print(len(fms))"` prints a number ≥30
- Loader singleton: `python -c "from sft_domain.failure_modes import load_failure_modes; assert load_failure_modes() is load_failure_modes()"` exits 0
</verification>

<success_criteria>
- 3 atomic commits: `feat(05-03-failure-modes-yaml):` × 2 + `ci(05-03-failure-modes-yaml):`
- ≥30 FailureMode entries, zero orphans
- Loader is immutable singleton with yaml.safe_load
- CI validator wired and green
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-03-failure-modes-yaml-SUMMARY.md` when done with: total failure modes by family (weaving/spinning/dyeing/finishing/quality_grading), zero-orphans confirmation, CI step name.
</output>
