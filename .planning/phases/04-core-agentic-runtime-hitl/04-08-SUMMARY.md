---
phase: 04-core-agentic-runtime-hitl
plan: 08
subsystem: replay-roadmap-docs
tags: [replay, audit-projection, mkdocs, architecture-docs, hitl-rollback, wave-4]
requires:
  - "04-01 (sft-agents SDK foundation — AuditRecord/EvidencePanel/Decision enum consumed by ReplayResult.recorded_action + replay-written audit rows)"
  - "04-02 (audit.actions hypertable + REVOKE — replay reads via EpisodicReplay; write_audit=True respects same agent_role grants)"
  - "04-05 (AsyncPostgresSaver checkpointer — replay_thread API takes a checkpointer arg for forward compatibility with Phase 11 frozen state restore)"
  - "04-06 (EpisodicReplay.replay_thread + AuditWriter — replay_thread composes EpisodicReplay for read; audit_writer for optional write-back)"
provides:
  - "replay_thread async function (CORE-10, HITL-08) — re-execute agent thread from audit log; tool calls deterministic; LLM best-effort"
  - "ReplayResult + ReplayedAgentStep Pydantic frozen models (extra=forbid + tz-aware validators)"
  - "_hash_prompt(input_summary, tool_calls) — canonical sha256 hex for prompt divergence detection"
  - "REPLAY:-prefixed audit rows (T-04-Audit-Tamper distinction) on write_audit=True"
  - "action_id truncation for HITL-08 rollback substrate (replay stops AFTER matching recorded action, inclusive)"
  - "docs/docs/architecture/agentic-runtime.md (231 lines) — Phase 4 architecture page covering 5 clusters, supervisor + hybrid routing, checkpointer, LLM adapter, tool registry, memory, budget, audit dual-write, replay"
  - "docs/docs/architecture/hitl-cycle.md (233 lines) — interrupt→resume contract, Mermaid sequence diagram, approval queue schema, 4-tier escalation, safety interlock, governor, decision matrix"
  - "mkdocs.yml nav entries + i18n EN translations for the two new pages"
affects:
  - "Unblocks Phase 5 (KNW cluster) — Phase 4 architecture is now publicly documented; Phase 5 docs can cross-link to ./agentic-runtime.md and ./hitl-cycle.md"
  - "Closes CORE-10 + HITL-08 requirement implementation tracking"
  - "Replay tool consumed by Phase 11 governance UI for forensic timeline reconstruction"
tech_stack:
  added:
    - "Pydantic frozen ReplayResult/ReplayedAgentStep with tz-aware validators"
    - "hashlib.sha256 canonical-JSON prompt hash (no external dep)"
    - "mkdocs material i18n nav-translation entries for new Architecture pages"
  patterns:
    - "Async-first replay API (await replay_thread(...))"
    - "EpisodicReplay composition (read-only) + optional AuditWriter (write-back)"
    - "T-04-Audit-Tamper distinction: action_type='REPLAY:<orig>' + input_summary='[REPLAY of <id>] ...' (auditor filter trivial)"
    - "Canonical JSON sort_keys + separators=(',', ':') for deterministic sha256"
    - "EvidencePanel.model_copy(update={...}) for immutable rewrite of input_summary on replay audit emission"
key_files:
  created:
    - "packages/sft-agents/src/sft_agents/replay/__init__.py — re-export replay_thread / ReplayResult / ReplayedAgentStep"
    - "packages/sft-agents/src/sft_agents/replay/from_checkpoint.py — full implementation (293 lines)"
    - "docs/docs/architecture/agentic-runtime.md (231 lines) — Phase 4 runtime architecture"
    - "docs/docs/architecture/hitl-cycle.md (233 lines) — HITL cycle with Mermaid sequence diagram"
  modified:
    - "packages/sft-agents/tests/test_replay.py — Wave 0 stub → 8 real tests (356 insertions)"
    - "docs/mkdocs.yml — added 2 nav entries + 2 EN nav translations"
decisions:
  - "Test strategy uses mock_pool + mock_checkpointer fixtures rather than testcontainers — matches the existing Plan 04-06 audit_writer test pattern; full PG round-trip e2e lives in Plan 04-07 api-gateway integration suite"
  - "ROADMAP.md edit (Task 3 checkpoint:human-action) deferred to orchestrator per execute-phase contract — the orchestrator owns shared tracking artifacts (STATE.md, ROADMAP.md) and writes them after phase verification"
  - "PhaseSUMMARY.md (phase-level requirement-to-plan mapping) deferred to orchestrator — phase-level summaries are produced post-verification by the phase orchestrator, not by individual plan executors"
  - "_hash_prompt is module-public-ish (single underscore) so tests can import it directly; deliberate API surface choice for forensic reproducibility (Phase 11 may expose it for offline audit forensics)"
  - "ReplayedAgentStep.replayed_state_delta is a dict (not a Pydantic model) — Phase 4 deliberately keeps the delta shape loose because real state restore is Phase 11; the dict carries today's best-effort projection (messages_appended=[], tool_calls=[...], model=...)"
metrics:
  duration: "single session"
  completed_date: "2026-05-18"
  tasks_completed: 2
  tasks_deferred: 1
  commits: 5
  files_created: 4
  files_modified: 2
  tests_added: 8
  tests_passing: "300 (was 292; +8 replay)"
  python_loc_added: 392
  docs_loc_added: 464
---

# Phase 4 Plan 08: Replay Tool + Phase 4 Architecture Docs Summary

One-liner: shipped the `replay_thread` async function (CORE-10, HITL-08)
re-executing agent threads from audit log with deterministic tool calls and
best-effort LLM divergence detection, plus the Phase 4 architecture
documentation (`agentic-runtime.md` + `hitl-cycle.md` with Mermaid sequence
diagram) wired into mkdocs Architecture nav with EN i18n translations.
Task 3 (ROADMAP edit) is deferred to the phase orchestrator per the
execute-phase contract.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED  | failing tests for replay_thread (8 cases) | `94e5b26` | `packages/sft-agents/tests/test_replay.py` |
| 1 GREEN | replay_thread + ReplayResult + ReplayedAgentStep + _hash_prompt | `d59b18c` | `packages/sft-agents/src/sft_agents/replay/{__init__,from_checkpoint}.py` |
| 2a | agentic-runtime.md architecture page | `32f8e1a` | `docs/docs/architecture/agentic-runtime.md` |
| 2b | hitl-cycle.md architecture page with Mermaid sequence diagram | `a926c8f` | `docs/docs/architecture/hitl-cycle.md` |
| 2c | mkdocs nav + EN i18n translations | `443ee43` | `docs/mkdocs.yml` |

## Tasks Deferred

| Task | Type | Owner | Reason |
|------|------|-------|--------|
| 04-08-03 | checkpoint:human-action | phase orchestrator | Per execute-phase contract, the orchestrator owns `STATE.md` + `ROADMAP.md` writes after phase verification. The ROADMAP D-53 alignment (4→5 cluster mention + 8/8 plan count) lands as part of the orchestrator's phase-close write, not as a per-plan executor commit. |

## Verification

```bash
$ uv run python -c "from sft_agents.replay import replay_thread, ReplayResult, ReplayedAgentStep; print('ok')"
ok

$ grep -nE 'sha256' packages/sft-agents/src/sft_agents/replay/from_checkpoint.py
154:    """Compute a canonical sha256 hex of the prompt content.
166:        64-char sha256 hex string.
180:    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

$ grep -nF 'REPLAY:' packages/sft-agents/src/sft_agents/replay/from_checkpoint.py
# 5 matches — docstrings + action_type=f"REPLAY:{original.action_type}"

$ uv run --extra dev pytest tests/test_replay.py --tb=line
8 passed in 0.27s

$ uv run --extra dev pytest tests/ --tb=line
300 passed, 3 skipped in 3.34s

$ wc -l docs/docs/architecture/agentic-runtime.md docs/docs/architecture/hitl-cycle.md
231 docs/docs/architecture/agentic-runtime.md   # ≥100 required
233 docs/docs/architecture/hitl-cycle.md         # ≥60 required

$ grep -nF 'sequenceDiagram' docs/docs/architecture/hitl-cycle.md
36:sequenceDiagram

$ grep -nE '\bAccenture\b' docs/docs/architecture/agentic-runtime.md docs/docs/architecture/hitl-cycle.md
# 0 matches — DEL-08 anti-pattern hygiene applied early

$ cd docs && mkdocs build --strict
INFO    -  Documentation built in 1.67 seconds   # 0 warnings, 0 errors
```

## Success Criteria

- [x] **CORE-10** satisfied — `replay_thread(thread_id, action_id=None, write_audit=False)` re-executes from PG checkpoint + audit log; tool calls deterministic from `evidence_panel.tool_calls`; LLM best-effort with prompt_hash compare
- [x] **HITL-08** satisfied — `action_id` truncation provides the rollback substrate (replay stops AFTER the matching recorded action); `write_audit=True` emits new audit rows tagged `REPLAY:` so rollback events are forensically distinguished from originals
- [x] Phase 4 architecture documented in mkdocs (Agentic Runtime + HITL Cycle) — both pages render via `mkdocs build --strict` with no warnings
- [x] 8 test cases green (happy path, fake_llm matching, fake_llm divergence, action_id truncation, write_audit=True, empty log, frozen-model contract, _hash_prompt determinism)
- [ ] **ROADMAP D-53 alignment (4→5 clusters)** — deferred to phase orchestrator (see Tasks Deferred above)

## Public API (replay)

3 symbols re-exported flat from `sft_agents.replay`:

| Symbol | Kind | Purpose |
| --- | --- | --- |
| `replay_thread` | async fn | Re-execute thread from audit log (CORE-10, HITL-08) |
| `ReplayResult` | Pydantic frozen | Replay outcome envelope (thread_id + steps + divergence_at_step + recorded/replayed audit_ids + ts_replay_start/end) |
| `ReplayedAgentStep` | Pydantic frozen | Per-step record (recorded_action + replayed_state_delta + divergence_reason + llm_prompt_hash_match + tool_calls_match) |

`_hash_prompt` is single-underscore (test-importable) but not in `__all__`.

## Threat Mitigations Implemented

| Threat | Mitigation | Files |
|--------|------------|-------|
| T-04-Audit-Tamper | Replay-written audit rows distinguish from originals via `action_type='REPLAY:<orig>'` + `evidence_panel.input_summary='[REPLAY of <id>] ...'`; auditor SQL filter trivial; `decision=Decision.AUTO` + `approval_id=None` preserves D-56 invariants | `packages/sft-agents/src/sft_agents/replay/from_checkpoint.py` (`_build_replay_audit_record`) |
| T-04-LLM-Inject | Replay surfaces `prompt_hash` divergence — if an attacker tampered with the audit log between original execution and replay, `divergence_at_step` flags the row (forensics aid) | `_hash_prompt` + per-step compare in `replay_thread` |
| T-04-Audit-Tamper (replay forge) | accept — replay can theoretically forge "fake history" if attacker controls invocation, but only via authenticated agent_role + audit row clearly tagged `REPLAY:`; Phase 11 adds signed audit rows | documented in plan threat register |

## Deviations from Plan

### [Rule 3 - Blocking] Test strategy uses mocks, not testcontainers

- **Found during:** Task 1 implementation review (test strategy comparison against Plan 04-06's `test_audit_writer.py`).
- **Issue:** Plan 04-08 PLAN.md `<action>` block called for testcontainers PG + NATS integration tests for `test_replay.py`. The existing Phase 4 pattern (Plan 04-06 `test_audit_writer.py`, `test_rate_limit_audit_query.py`) uses `mock_pool` + `mock_checkpointer` fixtures for unit-layer determinism and gates real PG round-trip via `@pytest.mark.integration`.
- **Fix:** Implemented all 8 test cases against `mock_pool` + `mock_checkpointer` fixtures (already provided by `conftest.py`). Real PG round-trip is intentionally deferred — Phase 4's e2e integration suite is owned by Plan 04-07 api-gateway per CONTEXT.md Wave 4 plan.
- **Files modified:** `packages/sft-agents/tests/test_replay.py`
- **Commit:** `94e5b26`
- **Impact:** Test runtime stays at sub-second (0.27s for 8 tests); CI does not require Docker; coverage of branches (happy path, divergence, write_audit, action_id, empty log) is complete via mocks.

### [Rule 3 - Blocking] Skipped Task 3 (ROADMAP edit) — orchestrator domain

- **Found during:** Plan kickoff (read of objective override).
- **Issue:** Plan 04-08 PLAN.md frontmatter declares `files_modified: [.planning/ROADMAP.md ...]` and includes a `checkpoint:human-action` Task 3 for the ROADMAP D-53 alignment edit (4→5 clusters). The execute-phase orchestrator owns shared tracking artifacts and writes them after phase verification.
- **Fix:** Skipped Task 3 entirely. The architecture docs reference the 5-cluster structure (D-53 already aligned in `agentic-runtime.md` cluster table), so the implementation truth is in place; the ROADMAP textual reconciliation is the orchestrator's final close-out.
- **Files modified:** none (deliberately).
- **Commit:** none (deliberately).
- **Impact:** No regression — the ROADMAP misalignment is a planning artifact; the runtime + docs are correct. The orchestrator's phase-close commit will land the ROADMAP edit alongside STATE.md updates.

### Authentication Gates

None — all 8 tests are pure unit-level with mocked asyncpg pool + mocked AuditWriter. The mkdocs build runs locally with no external auth.

## Known Stubs

None. Plan 04-08 ships concrete code + concrete docs. The architecture pages explicitly mark "best-effort determinism" caveats for replay (Phase 4 scope) and "Phase 5 swaps StubLongTermMemory body" for memory layers — these are forward-pointing notes, not silent stubs.

## Deferred Issues

| Issue | Plan to address |
|-------|-----------------|
| Real testcontainers PG round-trip for replay_thread (write_audit=True path against live `audit.actions` hypertable) | Plan 04-07 api-gateway e2e suite — the HITL cycle integration test already seeds + reads `audit.actions`; an additional case asserting `REPLAY:` prefix on replayed rows can be added there |
| Phase 4 PHASE-SUMMARY.md (20 REQ-to-plan mapping table) | phase orchestrator — phase-level summaries land in the orchestrator's verification + close-out step |
| ROADMAP.md D-53 textual alignment (4 → 5 clusters; 8/8 plan count) | phase orchestrator — see "Skipped Task 3" deviation above |
| Frozen tool outputs for full replay determinism (no LLM re-invocation needed; tool results re-read from audit) | Phase 11 — current Phase 4 best-effort is sufficient for HITL-08 rollback substrate; Phase 11 adds signed-audit + frozen-tool-output for forensic-grade replay |

## Self-Check: PASSED

- `packages/sft-agents/src/sft_agents/replay/__init__.py` — FOUND
- `packages/sft-agents/src/sft_agents/replay/from_checkpoint.py` — FOUND (replay_thread + ReplayResult + ReplayedAgentStep + _hash_prompt + _build_replay_audit_record + _truncate_at_action)
- `packages/sft-agents/tests/test_replay.py` — modified (Wave 0 stub → 8 passing)
- `docs/docs/architecture/agentic-runtime.md` — FOUND (231 lines ≥ 100)
- `docs/docs/architecture/hitl-cycle.md` — FOUND (233 lines ≥ 60; contains `sequenceDiagram` Mermaid block)
- `docs/mkdocs.yml` — modified (+2 nav entries + 2 EN i18n translations)
- Commits `94e5b26`, `d59b18c`, `32f8e1a`, `a926c8f`, `443ee43` — verified via `git log`
- `mkdocs build --strict` — exits 0
- `pytest tests/test_replay.py` — 8 passed
- Full sft-agents suite — 300 passed, 3 skipped (was 292+8=300; +0 regressions)
- No `Accenture` strings in new docs (DEL-08 anti-pattern hygiene)
