---
plan_id: 05-02-acl-migration
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 1
depends_on: []
requirements: [KNW-06]
files_modified:
  - scripts/migrate-sop-acl.py
  - scripts/validate-corpus-frontmatter.py
  - simulators/synthetic-corpus/it/**/*.md
  - simulators/synthetic-corpus/en/**/*.md
  - tests/test_acl_migration.py
autonomous: true
estimated_atomic_commits: 3
must_haves:
  truths:
    - "All 41 SOP files have `acl_level` field in frontmatter"
    - "acl_level values are constrained to {public, internal, restricted}"
    - "Frontmatter validator rejects SOPs missing `acl_level`"
    - "Migration is idempotent — re-running the script makes zero changes"
  artifacts:
    - path: scripts/migrate-sop-acl.py
      provides: one-shot idempotent migration script with audience → acl_level mapping per D-72
    - path: scripts/validate-corpus-frontmatter.py
      provides: extended Phase 2 validator that requires acl_level
  key_links:
    - from: scripts/migrate-sop-acl.py
      to: simulators/synthetic-corpus/
      via: pathlib rglob + frontmatter.load + frontmatter.dumps
      pattern: "frontmatter\\.(load|dumps)"
    - from: scripts/validate-corpus-frontmatter.py
      to: required_fields gate
      via: required field check
      pattern: "acl_level"
---

<objective>
One-shot migration that adds `acl_level` field to all 41 SOP frontmatter files per D-72 audience→ACL mapping, plus extension of the Phase 2 frontmatter validator to require `acl_level` going forward. This unblocks ACL pre-filter enforcement in Plan 05-09 (KNW-06 SC#2).

Purpose: every chunk indexed in Qdrant must carry an `acl_level` payload field; the source-of-truth is the SOP frontmatter, so the corpus must be migrated before any ingest run.

Output: 41 modified SOP files committed in a single atomic commit, plus an extended CI validator that prevents drift.
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
@scripts/validate-corpus-frontmatter.py
</context>

<interfaces>
ACL mapping (D-72 LOCKED — execute verbatim):

| audience (existing) | acl_level (new) |
|--------------------|-----------------|
| operations | public |
| maintenance | internal |
| quality | internal |
| engineering | internal |
| management | restricted |
| safety | restricted |
| (missing) | internal (conservative fallback) |

Existing SOP frontmatter (verified): `id, title, version, lang, asset, asset_family, role, hazard_level, estimated_duration_min, prerequisites, related_glossary, tags, audience, status, created_in_phase`. `acl_level` is ABSENT in all 41 files.

Phase 2 validator (`scripts/validate-corpus-frontmatter.py`) currently enforces a `required_fields` set. Plan 05-02 extends this set with `acl_level`.

Immutability rule (coding-style.md): when adding the field, build a NEW metadata dict — do not mutate `post.metadata` in-place. Pattern:
- new_meta = {**post.metadata, "acl_level": mapped_value}
- updated_post = frontmatter.Post(post.content, **new_meta)
- write updated_post via `frontmatter.dumps(updated_post)`
</interfaces>

<tasks>

<task id="05-02-01" type="auto" tdd="true">
  <name>Task 1: Write idempotent migration script + unit test for mapping logic</name>
  <files>
    scripts/migrate-sop-acl.py,
    tests/test_acl_migration.py
  </files>
  <read_first>
    scripts/validate-corpus-frontmatter.py (WORKSPACE_ROOT pattern line 36, frontmatter.load lines 76-80, file iteration lines 153-156),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-72 mapping lines 656-672),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (migrate-sop-acl.py section)
  </read_first>
  <behavior>
    - `map_audience_to_acl(audience: str | None) -> str` is pure function:
      - "operations" → "public"
      - "maintenance" | "quality" | "engineering" → "internal"
      - "management" | "safety" → "restricted"
      - None or unknown → "internal" (conservative fallback per D-72)
    - `migrate_file(path: Path, dry_run: bool) -> Literal["migrated", "skipped", "error"]`:
      - Returns "skipped" if `acl_level` already present
      - Returns "migrated" if added (writes to disk only if not dry_run)
      - Returns "error" on parse failure
    - Building updated frontmatter MUST use immutable dict copy (NEVER `post.metadata["acl_level"] = ...` in-place mutation per coding-style.md immutability rule)
    - Script supports `--dry-run`, `--corpus-dir` (default `simulators/synthetic-corpus`)
    - Script prints summary: total scanned, migrated, skipped, errors; exits 0 if errors == 0
    - Re-running script on already-migrated corpus prints "MIGRATED: 0, SKIPPED: 41, ERRORS: 0" and exits 0 (idempotency)
  </behavior>
  <action>
    Create `scripts/migrate-sop-acl.py`:
    - `from __future__ import annotations`, `import argparse`, `import sys`, `from pathlib import Path`, `import frontmatter`
    - Module-level constant `AUDIENCE_TO_ACL: dict[str, str]` with exact mapping per D-72.
    - Function `map_audience_to_acl(audience: str | None) -> str` returning the mapped value, defaulting to `"internal"` for None/unknown.
    - Function `migrate_file(path: Path, dry_run: bool) -> str` using the immutable update pattern from 05-PATTERNS.md migrate-sop-acl.py section: `new_meta = {**post.metadata, "acl_level": mapped}` then `frontmatter.Post(post.content, **new_meta)` then `frontmatter.dumps`.
    - `main()` derives `WORKSPACE_ROOT = Path(__file__).parent.parent`, uses `argparse` for `--dry-run`, `--corpus-dir`, iterates `corpus.rglob("*.md")` excluding any `__pycache__` / non-SOP files (filter by frontmatter having required field `id`), calls migrate_file for each, prints summary, exits 0 iff errors == 0.
    - Use `print()` for human-readable script output (not structlog — this is a one-shot script, RESEARCH §6 convention).

    Create `tests/test_acl_migration.py` (workspace-level, NOT inside packages/):
    - `test_map_operations_to_public` — assert `map_audience_to_acl("operations") == "public"`
    - `test_map_maintenance_to_internal` — assert `map_audience_to_acl("maintenance") == "internal"`
    - `test_map_management_to_restricted` — assert `map_audience_to_acl("management") == "restricted"`
    - `test_map_missing_defaults_internal` — assert `map_audience_to_acl(None) == "internal"`
    - `test_map_unknown_defaults_internal` — assert `map_audience_to_acl("rocketscience") == "internal"` (conservative fallback)
    - `test_migrate_file_idempotent` (tmp_path): create tmp MD with frontmatter including `audience: maintenance`; call migrate_file twice; first returns "migrated", second returns "skipped"; assert final acl_level == "internal".
    - `test_migrate_file_immutable_pattern` (tmp_path): create tmp MD; migrate_file dry_run=True; verify file on disk is unchanged byte-for-byte (no in-place write).

    Add a `conftest.py` at workspace root (if not present) or use `pytest.ini` to ensure `tests/test_acl_migration.py` is discoverable by `pytest tests/test_acl_migration.py`.

    Commit: `feat(05-02-acl-migration): add migrate-sop-acl.py script + unit tests`.
  </action>
  <acceptance_criteria>
    - `scripts/migrate-sop-acl.py` exists and contains literal `AUDIENCE_TO_ACL`
    - `grep -q 'def map_audience_to_acl' scripts/migrate-sop-acl.py`
    - `grep -q '\{\*\*post.metadata, "acl_level":' scripts/migrate-sop-acl.py` (immutable update pattern)
    - `grep -vc '^#' scripts/migrate-sop-acl.py | tr -d ' '` is greater than 50 (non-trivial implementation; not just stub) — use `grep -v '^#' scripts/migrate-sop-acl.py | wc -l` returns >50
    - `uv run pytest tests/test_acl_migration.py -v` exits 0 with all unit tests passing
    - `uv run python scripts/migrate-sop-acl.py --dry-run` exits 0 and prints summary
  </acceptance_criteria>
  <verify>
    <automated>uv run pytest tests/test_acl_migration.py -v &amp;&amp; uv run python scripts/migrate-sop-acl.py --dry-run</automated>
  </verify>
  <done>Migration script + unit tests committed; dry-run reports expected migration counts.</done>
</task>

<task id="05-02-02" type="auto">
  <name>Task 2: Run migration on 41 SOPs + commit corpus changes</name>
  <files>
    simulators/synthetic-corpus/it/**/*.md,
    simulators/synthetic-corpus/en/**/*.md
  </files>
  <read_first>
    scripts/migrate-sop-acl.py (just created in Task 1),
    simulators/synthetic-corpus/it/loom/ (sample 1-2 files to confirm audience field exists)
  </read_first>
  <action>
    1. Run `uv run python scripts/migrate-sop-acl.py --dry-run` and capture output. Verify expected count: 41 MIGRATED, 0 SKIPPED, 0 ERRORS (assuming first run; if Task 1 left side-effects, re-fix Task 1 first — DO NOT manually edit files).
    2. Run `uv run python scripts/migrate-sop-acl.py` (no dry-run) to apply migrations.
    3. Verify: `grep -l 'acl_level:' simulators/synthetic-corpus/**/*.md | wc -l` returns 41 (or whatever the actual SOP count is — record exact number in commit msg).
    4. Verify distribution: `grep -h 'acl_level:' simulators/synthetic-corpus/**/*.md | sort | uniq -c` shows distribution across public/internal/restricted.
    5. Re-run script once more: must report `MIGRATED: 0, SKIPPED: 41` (idempotency confirmed).
    6. `git diff --stat simulators/synthetic-corpus/` to confirm only frontmatter `acl_level:` line added (no body changes, no reordering of other fields).

    NOTE: If git diff shows reordered frontmatter keys (some YAML libs reorder), document this in the commit message and confirm parser doesn't rely on field order (frontmatter.load returns dict, order-independent).

    Commit (in this exact form to preserve audit trail):
    `chore(05-02-acl-migration): add acl_level field to 41 SOP frontmatter per D-72 mapping`

    Include in commit body the distribution counts (e.g., "public: 12, internal: 22, restricted: 7").
  </action>
  <acceptance_criteria>
    - `grep -l 'acl_level:' simulators/synthetic-corpus/it/**/*.md simulators/synthetic-corpus/en/**/*.md 2&gt;/dev/null | wc -l` returns the full SOP count (≥41 per VALIDATION.md baseline)
    - `grep -hE '^acl_level:' simulators/synthetic-corpus/**/*.md | awk '{print $2}' | sort -u` returns only values from {public, internal, restricted}
    - Re-running `uv run python scripts/migrate-sop-acl.py` after the commit prints `MIGRATED: 0` (idempotency)
    - `git log -1 --format=%s` returns subject line containing `acl_level`
  </acceptance_criteria>
  <verify>
    <automated>test "$(grep -l 'acl_level:' simulators/synthetic-corpus/**/*.md 2&gt;/dev/null | wc -l)" -ge 41 &amp;&amp; uv run python scripts/migrate-sop-acl.py 2&gt;&amp;1 | grep -q 'MIGRATED: 0'</automated>
  </verify>
  <done>All 41 SOP files contain `acl_level`; idempotency verified; corpus changes committed in single atomic commit.</done>
</task>

<task id="05-02-03" type="auto" tdd="true">
  <name>Task 3: Extend Phase 2 frontmatter validator to require acl_level + CI integration</name>
  <files>
    scripts/validate-corpus-frontmatter.py,
    tests/test_acl_migration.py
  </files>
  <read_first>
    scripts/validate-corpus-frontmatter.py (current required_fields set + validation flow),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-72 validator section lines 675-679)
  </read_first>
  <behavior>
    - Validator now treats `acl_level` as a required frontmatter key
    - Validator now treats `acl_level` value as constrained to {public, internal, restricted}; any other value → error
    - Adding a synthetic test SOP without `acl_level` triggers validator failure with non-zero exit
    - Existing 41 SOPs pass the validator (they were migrated in Task 2)
  </behavior>
  <action>
    Edit `scripts/validate-corpus-frontmatter.py`:
    - Locate the `required_fields` constant or set definition. Add `"acl_level"` to the set.
    - Add a value-range check: if `metadata["acl_level"]` not in `{"public", "internal", "restricted"}`, append error `f"{rel}: invalid acl_level: {metadata['acl_level']!r} (must be public|internal|restricted)"`.
    - Preserve existing error reporting format; do NOT change Phase 2 behavior beyond the additive ACL check.

    Extend `tests/test_acl_migration.py`:
    - `test_validator_rejects_missing_acl_level` (tmp_path + monkeypatched corpus dir): create a tmp MD with all required fields EXCEPT `acl_level`; invoke validator main() with corpus pointing at tmp dir; assert exit code != 0 OR errors list non-empty.
    - `test_validator_rejects_invalid_acl_value`: tmp MD with `acl_level: top_secret`; assert validator rejects.
    - `test_validator_accepts_valid_corpus`: run validator against `simulators/synthetic-corpus/` (the real, just-migrated corpus); assert exits 0.

    Verify the validator runs successfully in CI by invoking it directly: `uv run python scripts/validate-corpus-frontmatter.py` exits 0 against the migrated corpus.

    Commit: `feat(05-02-acl-migration): extend frontmatter validator to require acl_level`.
  </action>
  <acceptance_criteria>
    - `grep -q 'acl_level' scripts/validate-corpus-frontmatter.py` (was absent before this task)
    - `grep -qE '\{"public", "internal", "restricted"\}|public.*internal.*restricted' scripts/validate-corpus-frontmatter.py`
    - `uv run python scripts/validate-corpus-frontmatter.py` exits 0 (real corpus passes after Task 2 migration)
    - `uv run pytest tests/test_acl_migration.py::test_validator_rejects_missing_acl_level tests/test_acl_migration.py::test_validator_rejects_invalid_acl_value tests/test_acl_migration.py::test_validator_accepts_valid_corpus -v` exits 0
  </acceptance_criteria>
  <verify>
    <automated>uv run python scripts/validate-corpus-frontmatter.py &amp;&amp; uv run pytest tests/test_acl_migration.py -v</automated>
  </verify>
  <done>Validator now blocks any future SOP added without acl_level; real corpus passes; tests exit 0.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| filesystem write → SOP corpus | Migration script writes to git-tracked SOP files; mistakes propagate to all agents reading the corpus |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-02-01 | Information Disclosure | audience → acl_level mapping | mitigate | Mapping is constant in code (D-72), reviewed in commit; conservative fallback "internal" for unknown audience prevents accidental public exposure |
| T-05-02-02 | Tampering | corpus file rewrite | mitigate | `--dry-run` flag for safe preview; git commit creates auditable record; idempotency guarantees re-runs are no-ops |
| T-05-02-03 | Repudiation | who migrated which file | accept | Single atomic commit captures all 41 file changes with author + timestamp; no per-file audit needed |
| T-05-02-SC | Tampering | npm/pip install | mitigate | Only python-frontmatter used (already in workspace from Phase 2); zero new deps in this plan |
</threat_model>

<verification>
- `uv run python scripts/migrate-sop-acl.py --dry-run` prints `MIGRATED: 0` post-Task-2 (idempotency)
- `uv run python scripts/validate-corpus-frontmatter.py` exits 0 against migrated corpus
- All 41 SOPs have `acl_level` in {public, internal, restricted}
- `uv run pytest tests/test_acl_migration.py -v` exits 0
- `nx run sft-knowledge:test --args="-k test_markdown -m 'not integration and not gpu'"` still exits 0 (MarkdownParser still works post-migration — the acl_level field is now present in all 41 SOPs, so the default fallback path is no longer triggered)
</verification>

<success_criteria>
- 3 atomic commits with `feat(05-02-acl-migration):` and `chore(05-02-acl-migration):` scopes
- 41 SOP files migrated, idempotency verified
- ACL distribution recorded in commit body (auditable)
- Validator extended; CI prevents future drift
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-02-acl-migration-SUMMARY.md` when done with: total files migrated, ACL distribution counts (public/internal/restricted), idempotency verification output, validator extension confirmation.
</output>
