---
phase: 08-agents-knowledge-training
plan: 00a
subsystem: audit-infra
tags: [migration, enum, timescaledb, actiontype, lockstep, phase8]
dependency_graph:
  requires: [07-01]
  provides: [08-00a-migration, 08-00a-enum]
  affects: [08-02, 08-05, 08-06, 08-07]
tech_stack:
  added: []
  patterns: [DROP-IF-EXISTS-ADD-CHECK, enum-sql-lockstep, testcontainers-integration-test]
key_files:
  created:
    - infra/migrations/timescale/010_extend_audit_knw.sql
    - infra/migrations/timescale/tests/test_migration_010.py
    - packages/sft-agents/src/sft_agents/models/enums.py
  modified: []
decisions:
  - "Copiare file infrastruttura (001-009 SQL, migrate.py) nel worktree per rendere importabile migrate() nel test (Rule 3 — blocking issue)"
metrics:
  duration: ~15min
  completed: "2026-05-24T09:56:25Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 17
---

# Phase 8 Plan 00a: Migration 010 + ActionType Enum Lockstep Summary

**One-liner:** TimescaleDB migration 010 + Python ActionType enum extended in lockstep con 7 valori Phase 8 (HANDOVER_DRAFT, HANDOVER_SIGNOFF, TRAINING_SESSION, TRAINING_SIGNOFF, KNOWLEDGE_DEDUP, STALE_FLAG, SOP_DRAFT) per il cluster Knowledge & Training (D-X-01).

## What Was Built

### Task 1: Migration 010 + ActionType enum lockstep (D-X-01)

**`infra/migrations/timescale/010_extend_audit_knw.sql`** — migrazione idempotente che estende il CHECK constraint `audit_actions_action_type_chk` con i 7 nuovi valori Phase 8. Pattern verbatim da `009_extend_audit_mnt.sql`: DROP CONSTRAINT IF EXISTS + ADD CONSTRAINT. Preserva tutti i valori legacy Phase 1-7. Non tocca il Decision CHECK constraint (D-X-01 esplicito).

**`packages/sft-agents/src/sft_agents/models/enums.py`** — enum `ActionType` estesa con 7 nuovi membri Phase 8 sotto il commento di sezione `# Phase 8 additions — keep in lockstep with migration 010 (D-X-01)`. Ogni membro ha commento inline con il codice decisionale (D-SH-01, D-SH-03, D-TC-01, D-TC-03, D-KC-01, D-KC-02, D-DS-03). I valori stringa sono byte-identici ai literal SQL.

**Verifica lockstep:** script Python che assert la presenza di tutti e 7 i valori sia nel SQL che nell'enum — PASSED.

### Task 2: Migration 010 integration test

**`infra/migrations/timescale/tests/test_migration_010.py`** — 7 funzioni test (27 test case con parametrizzazione) che coprono:
1. `test_pre_migration_rejects_handover_draft` — before 010, HANDOVER_DRAFT rejected
2. `test_post_migration_admits_handover_draft` — after 010, HANDOVER_DRAFT admitted
3. `test_post_migration_admits_all_phase8_action_types` — parametrize su 7 valori Phase 8
4. `test_post_migration_legacy_action_types_ok` — parametrize su 15 valori legacy (Phase 1-7)
5. `test_post_migration_decision_enum_unchanged` — Decision CHECK intatto
6. `test_idempotent_double_apply` — double-apply è no-op
7. `test_migrate_runner_picks_up_010` — migrate() runner include 010

Usa `testcontainers.postgres.PostgresContainer(image="timescale/timescaledb:2.18.0-pg16")` e asyncpg. Struttura esatta mirror di `test_migration_009.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] File infrastruttura mancanti nel worktree**
- **Found during:** Task 2
- **Issue:** Il worktree è basato su un commit della Fase 2; `infra/migrations/timescale/migrate.py` e i file SQL 001-009 non esistono nel worktree. Il test usa `from infra.migrations.timescale.migrate import migrate` e `_run_baseline_migrations()` che richiedono questi file.
- **Fix:** Copiati dal repo principale nel worktree: `migrate.py`, `__init__.py`, `pyproject.toml`, file SQL 001-009, `tests/__init__.py`, `tests/conftest.py`.
- **Files modified:** `infra/migrations/timescale/` (file infrastruttura copiati)
- **Commit:** 62e831c

**2. [Rule 3 - Blocking] `enums.py` non esistente nel worktree**
- **Found during:** Task 1
- **Issue:** `packages/sft-agents/src/sft_agents/models/enums.py` non esiste nel worktree (Phase 2 base); il piano richiede di estendere il file esistente con le aggiunte Phase 8.
- **Fix:** Creato il file con il contenuto completo: base Phase 4 + estensioni Phase 6 + Phase 7 + nuove Phase 8, seguendo esattamente la versione attuale del repo principale come base.
- **Files modified:** `packages/sft-agents/src/sft_agents/models/enums.py`
- **Commit:** 4cc5226

## Commits

| Hash | Task | Description |
|------|------|-------------|
| 4cc5226 | Task 1 | feat(08-00a): migration 010 + ActionType enum lockstep Phase 8 (D-X-01) |
| 62e831c | Task 2 | feat(08-00a): migration 010 integration test (7 test functions + Rule 3 infra fix) |

## Verification Results

- Lockstep verify (7 values in SQL AND enum): PASSED
- `ActionType.SOP_DRAFT.value == 'SOP_DRAFT'`: PASSED
- `python -m pytest --co -q` collects 27 tests (>=7 required): PASSED
- All legacy Phase 1-7 values present in SQL CHECK: PASSED
- Decision CHECK constraint untouched: verified by test structure

## Known Stubs

None — migration and enum are complete. Test stubs (testcontainers) require Docker for runtime execution.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes beyond what the plan specifies. Migration 010 only extends an existing CHECK constraint — no new tables, columns, or permissions introduced.

## Self-Check: PASSED

- `infra/migrations/timescale/010_extend_audit_knw.sql`: FOUND
- `packages/sft-agents/src/sft_agents/models/enums.py`: FOUND
- `infra/migrations/timescale/tests/test_migration_010.py`: FOUND
- Commit 4cc5226: FOUND
- Commit 62e831c: FOUND
