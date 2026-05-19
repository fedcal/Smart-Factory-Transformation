---
phase: 5
plan: 05-02-acl-migration
subsystem: knowledge-layer
tags: [acl, frontmatter, migration, corpus, security, validator]
requires:
  - .planning/phases/02-domain-modeling-synthetic-corpus  # scripts/validate-corpus-frontmatter.py + 40 SOPs
  - scripts/validate-corpus-frontmatter.py
provides:
  - acl_level field on every SOP frontmatter (D-72 mapping)
  - scripts/migrate-sop-acl.py (idempotent one-shot migration)
  - extended frontmatter validator requiring acl_level + value range
affects:
  - simulators/synthetic-corpus/**/*.md (40 SOPs)
  - downstream Plan 05-09 (KNW-06 SC#2 ACL pre-filter enforcement) — UNBLOCKED
tech-stack:
  added: []
  patterns:
    - immutable-frontmatter-update (new_meta dict, never in-place mutation)
    - additive-validator-rules (extra constants in script, schema.json untouched)
    - idempotent-migration (skip if field already present)
key-files:
  created:
    - scripts/migrate-sop-acl.py
    - tests/test_acl_migration.py
  modified:
    - scripts/validate-corpus-frontmatter.py
    - simulators/synthetic-corpus/it/**/*.md  (20 files)
    - simulators/synthetic-corpus/en/**/*.md  (20 files)
decisions:
  - "Plan referenced '41 SOPs' but real count is 40 (SOP-*.md filename pattern). README.md is correctly excluded by the validator filter. Documented in chore commit body."
  - "JSON Schema (packages/sft-domain/.../sop.schema.json) intentionally NOT modified — acl_level requirement implemented as additive checks in the validator script. Lower-risk: Phase 2 artifact stays untouched and the schema is still valid for any downstream consumer that does not yet know about acl_level."
  - "frontmatter.dumps() alphabetizes top-level YAML keys; this produces a large per-file diff (~21 added / ~20 removed lines per SOP) but no body change. Benign because frontmatter.load returns a dict and the validator is order-independent. Verified by re-running the validator and the unrelated test_corpus_inventory.py suite."
  - "Bug fix in validate_file(): old code crashed with ValueError when corpus dir was outside WORKSPACE_ROOT (e.g. pytest tmp_path). Falls back to corpus_root, then raw md_path. Required to make the validator unit-testable."
metrics:
  duration: ~25 min
  completed: 2026-05-19
---

# Phase 5 Plan 02: ACL Migration Summary

One-liner: Added `acl_level` frontmatter field to all 40 SOPs per the D-72 audience→ACL mapping, plus extended the Phase 2 validator so any future SOP without `acl_level` (or with an invalid value) fails CI — unblocking Qdrant ACL pre-filter enforcement in Plan 05-09.

## What Was Built

| Artifact | Purpose |
|---|---|
| `scripts/migrate-sop-acl.py` | Idempotent one-shot migration script. Maps each SOP's existing `audience` field to `acl_level` per the D-72 mapping table. Uses the immutable dict update pattern (`new_meta = {**post.metadata, "acl_level": mapped}`) — never mutates `post.metadata` in place. Supports `--dry-run` and `--corpus-dir`. Exits 0 iff errors == 0. |
| `tests/test_acl_migration.py` | 17 unit tests covering the pure mapping function (D-72 table including the conservative fallback), `migrate_file` behavior (add / idempotent / dry-run-no-write / unknown-audience / pre-existing-acl_level / parse-error), and the validator extension (rejects missing field, rejects invalid value, accepts real corpus). |
| `scripts/validate-corpus-frontmatter.py` (extended) | Two new check blocks (2b, 2c) enforce that `acl_level` is present and that its value is one of `{public, internal, restricted}`. Includes a side-fix that lets the validator run against arbitrary corpus directories (required for unit-testing). |
| 40 migrated SOPs | All `it/` (20) and `en/` (20) SOPs under `simulators/synthetic-corpus/` now carry `acl_level` in frontmatter. |

## ACL Distribution (post-migration)

| acl_level | Count | Source audience |
|---|---:|---|
| public | 12 | operations |
| internal | 28 | maintenance (16), quality (12) |
| restricted | 0 | (no SOPs with `audience` in {management, safety} exist in the current corpus) |
| **Total** | **40** | |

## Idempotency Verification

Post-migration re-run output:

```
[APPLIED] SCANNED: 40, MIGRATED: 0, SKIPPED: 40, ERRORS: 0
```

And `--dry-run` of the same script:

```
[DRY-RUN] SCANNED: 40, MIGRATED: 0, SKIPPED: 40, ERRORS: 0
```

Re-running the migration is a guaranteed no-op as long as every SOP already has the `acl_level` field, regardless of the value stored (the script intentionally does NOT overwrite an existing value — it only adds the field if absent, so manually-set ACLs are preserved).

## Validator Extension Verification

```
$ uv run python scripts/validate-corpus-frontmatter.py
OK: validated 40 SOP(s) — 0 errors

$ uv run pytest tests/test_acl_migration.py -q
.................                                                        [100%]
17 passed in 0.09s
```

Tests that exercise the gate:
- `test_validator_rejects_missing_acl_level` — SOP without `acl_level` → validator returns False.
- `test_validator_rejects_invalid_acl_value` — SOP with `acl_level: top_secret` → validator returns False.
- `test_validator_accepts_valid_corpus` — real migrated corpus → validator returns True.

## Commits

| Task | Subject | Hash |
|---|---|---|
| 1 | `feat(05-02-acl-migration): add migrate-sop-acl.py script + unit tests` | `e4449b4` |
| 2 | `chore(05-02-acl-migration): add acl_level field to 40 SOP frontmatter per D-72 mapping` | `d6d0f87` |
| 3 | `feat(05-02-acl-migration): extend frontmatter validator to require acl_level` | `26c4919` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Corpus actual count is 40 SOPs, not 41**
- **Found during:** Task 1 (dry-run output) and confirmed in Task 2.
- **Issue:** Plan repeatedly references "41 SOP files"; the validator's `FILENAME_PATTERN` matches 40 files (README.md is correctly excluded).
- **Fix:** Used the validator's existing `FILENAME_PATTERN` in the migration script so the two scripts always agree on which files are SOPs. Documented the discrepancy in the chore commit body so the audit trail records the real count.
- **Files modified:** scripts/migrate-sop-acl.py (filter), commit body of `d6d0f87`.
- **Impact:** None on plan goals — KNW-06 SC#2 unblock is independent of the exact count.

**2. [Rule 1 — Bug] `validate_file` crashed on corpus dirs outside WORKSPACE_ROOT**
- **Found during:** Task 1, when the validator-extension tests in `tests/test_acl_migration.py` tried to validate a `tmp_path` corpus.
- **Issue:** `md_path.relative_to(WORKSPACE_ROOT)` raised `ValueError` for any corpus dir outside the workspace (e.g. pytest tmp_path), preventing unit-testing of the validator.
- **Fix:** Added a try/except cascade in `validate_file`: workspace-relative → corpus_root-relative → raw path. Existing behavior is preserved for the real corpus.
- **Files modified:** scripts/validate-corpus-frontmatter.py.
- **Commit:** `26c4919`.

**3. [Rule 2 — Missing critical functionality] Validator value-range check**
- **Found during:** Task 3.
- **Issue:** Plan acceptance criteria require rejecting `acl_level: top_secret` as well as missing `acl_level`. The plan instructions only said "add `acl_level` to the required_fields set" but the existing validator uses JSON Schema, not a `required_fields` set.
- **Fix:** Implemented both checks (2b: required-field; 2c: value-range) as additive code in `validate_file`. Left the Phase 2 JSON Schema untouched.
- **Files modified:** scripts/validate-corpus-frontmatter.py.
- **Commit:** `26c4919`.

### Architectural Decision (logged, not asked — borderline Rule 4 → executed as Rule 3)

**Schema-vs-script enforcement of `acl_level`**
- **Two options:** (A) Add `acl_level` to `sop.schema.json` required + enum constraint. (B) Keep the schema untouched and put the check in the validator script as additive code.
- **Chosen:** Option B (script-only).
- **Rationale:** The JSON Schema is a Phase 2 artifact that may be consumed by other tools that don't yet know about `acl_level`. Putting the constraint in the validator script keeps Phase 2 unchanged and concentrates the new requirement in one Phase 5 file. The validator is the only CI gate, so behavior is equivalent. If a future plan wants the schema to be the source of truth, the constants `REQUIRED_EXTRA_FIELDS` and `VALID_ACL_LEVELS` can be deleted from the script in the same commit that adds them to the schema.

## Coding-style Compliance

- **Immutability rule:** The migration script uses `new_meta = {**post.metadata, "acl_level": mapped}` followed by `frontmatter.Post(post.content, **new_meta)`. Never `post.metadata["acl_level"] = ...`. Test `test_migrate_file_dry_run_does_not_write` asserts the file is byte-identical after a dry-run, proving no hidden side-effects.
- **Input validation:** Validator now hard-fails on any non-conforming `acl_level` value at the corpus boundary.
- **Error handling:** `migrate_file` returns `"error"` on parse failure, prints to stderr; `main` exits 1 if any errors occurred.
- **Small focused files:** migrate-sop-acl.py is ~190 lines, single responsibility.

## Threat Surface Scan

No new trust boundaries introduced beyond those documented in the plan's `<threat_model>`. Mitigations are in place:
- T-05-02-01 (audience→acl_level mapping disclosure) — mapping constant, conservative fallback to `internal`, never `public`.
- T-05-02-02 (corpus rewrite tampering) — `--dry-run` flag, idempotency, single atomic commit per task.
- T-05-02-03 (per-file repudiation) — accepted; single chore commit captures all 40 file changes.
- T-05-02-SC (supply-chain) — zero new dependencies; only `python-frontmatter` (already in pyproject.toml from Phase 2) is used.

## Verification (final)

```
$ uv run python scripts/migrate-sop-acl.py --dry-run
[DRY-RUN] SCANNED: 40, MIGRATED: 0, SKIPPED: 40, ERRORS: 0

$ uv run python scripts/validate-corpus-frontmatter.py
OK: validated 40 SOP(s) — 0 errors

$ uv run pytest tests/test_acl_migration.py -q
.................   17 passed in 0.09s

$ uv run pytest tests/test_corpus_inventory.py -q   # regression check
.......             7 passed in 0.04s
```

## Success Criteria

- [x] 3 atomic commits with `feat(05-02-acl-migration):` / `chore(05-02-acl-migration):` scopes
- [x] All SOP files migrated (40 of 40 matching SOP filename pattern; plan stated "41" — the README.md was always excluded by the validator filter)
- [x] Idempotency verified (second run reports MIGRATED: 0)
- [x] ACL distribution recorded in chore commit body (auditable)
- [x] Validator extended; CI now blocks any future SOP added without `acl_level`
- [x] No regression in pre-existing Phase 2 tests

## Self-Check: PASSED

- `scripts/migrate-sop-acl.py` — FOUND
- `tests/test_acl_migration.py` — FOUND
- `scripts/validate-corpus-frontmatter.py` (extended) — FOUND
- Commit `e4449b4` — FOUND
- Commit `d6d0f87` — FOUND
- Commit `26c4919` — FOUND
