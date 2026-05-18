---
phase: 04-core-agentic-runtime-hitl
plan: 01
subsystem: sft-agents-sdk-foundation
tags: [sdk, pydantic, abc, hitl, audit, evidence-panel, wave-1, foundation]
requires: []
provides:
  - "Public API contract: 19 symbols from `sft_agents` (Agent/Tool/Memory/Policy ABCs + 14 Pydantic models + 4 enums)"
  - "EvidencePanel (HITL-06) Pydantic schema with input_summary length cap, model+prompt_hash regex, tz-aware datetime validators"
  - "AuditRecord (D-56) with model_validator enforcing HITL-07 motivation-required + approval_id consistency"
  - "ApprovalRequest + ApprovalDecision (D-55) Pydantic projections"
  - "BudgetSnapshot + BudgetLimits (D-60) Pydantic models"
  - "ProposedAction with deterministic UUID from sha256(thread_id|action_type|canonical_json(args)) (Pitfall 6 idempotency)"
  - "Tier / Decision / ActionType / ApprovalStatus str-Enum (JSON-stable, DB CHECK-compatible)"
  - "12 Wave 0 stub test files (importorskip + pytest.skip) covering plans 04-02..04-08"
  - "Shared pytest fixtures: frozen_dt, mock_pool, mock_nats_js, mock_llm, mock_checkpointer"
affects:
  - "Unblocks plans 04-02..04-08 — every downstream `from sft_agents import <X>` resolves"
tech_stack:
  added:
    - "pydantic 2.9+ (frozen + extra=forbid + Annotated/Field/field_validator/model_validator)"
    - "langchain-core 1.0+ (BaseTool subclassing for Tool ABC)"
  patterns:
    - "Pydantic v2 frozen + extra=forbid on every BaseModel"
    - "field_validator enforcing tz-aware datetime (Pitfall 7)"
    - "model_validator(mode='after') for cross-field invariants (HITL-07 / D-56 line 431)"
    - "Async-first Tool: _run → NotImplementedError forces _arun"
    - "Deterministic UUID via sha256 + canonical JSON for idempotency (Pitfall 6)"
    - "Wave 0 import-then-skip pattern: pytest.importorskip(target_module) + pytest.skip body"
key_files:
  created:
    - "packages/sft-agents/src/sft_agents/sdk/__init__.py — flat re-export of ABCs"
    - "packages/sft-agents/src/sft_agents/sdk/agent.py — Agent ABC (async step)"
    - "packages/sft-agents/src/sft_agents/sdk/tool.py — Tool ABC (async-first BaseTool)"
    - "packages/sft-agents/src/sft_agents/sdk/memory.py — Memory ABC (query/store)"
    - "packages/sft-agents/src/sft_agents/sdk/policy.py — Policy ABC (pre_tool_check abstract + post_decision_check no-op)"
    - "packages/sft-agents/src/sft_agents/models/__init__.py — flat re-export of 14 model symbols"
    - "packages/sft-agents/src/sft_agents/models/evidence.py — EvidencePanel + ToolCall + RagCitation + TokenUsage"
    - "packages/sft-agents/src/sft_agents/models/audit.py — AuditRecord + HITL-07 model_validator"
    - "packages/sft-agents/src/sft_agents/models/approval.py — ApprovalRequest + ApprovalDecision"
    - "packages/sft-agents/src/sft_agents/models/budget.py — BudgetSnapshot + BudgetLimits"
    - "packages/sft-agents/src/sft_agents/models/proposed_action.py — ProposedAction.from_payload (deterministic UUID)"
    - "packages/sft-agents/src/sft_agents/models/enums.py — Tier / Decision / ActionType / ApprovalStatus"
    - "packages/sft-agents/src/sft_agents/models/memory_record.py — MemoryRecord (D-59)"
    - "packages/sft-agents/tests/conftest.py — frozen_dt / mock_pool / mock_nats_js / mock_llm / mock_checkpointer"
    - "packages/sft-agents/tests/test_sdk_interfaces.py — ABC enforcement matrix (12 tests)"
    - "packages/sft-agents/tests/test_public_api.py — 19-symbol contract + __version__ (6 tests)"
    - "packages/sft-agents/tests/test_evidence_panel.py — 21 tests (tz-aware, length cap, pattern, frozen, extra=forbid)"
    - "packages/sft-agents/tests/test_audit_record.py — 10 tests"
    - "packages/sft-agents/tests/test_audit_constraints.py — 14 tests (HITL-07 matrix)"
    - "packages/sft-agents/tests/test_approval_request.py — 12 tests"
    - "packages/sft-agents/tests/test_budget_snapshot.py — 9 tests"
    - "12 Wave 0 stub files: test_migrations / test_llm_adapter / test_llm_factory / test_supervisor / test_hitl_cycle / test_escalation / test_governor / test_budget / test_replay / test_safety_interlock / test_rate_limit_audit_query / test_recursion_limit / test_tool_registry"
  modified:
    - "packages/sft-agents/pyproject.toml — Plan 04-01 Task 1 (deps + pytest config, committed pre-execution)"
    - "packages/sft-agents/src/sft_agents/__init__.py — flat re-export of 19 public symbols"
decisions:
  - "ApprovalDecision uses Literal['approve','reject','escalate'] (not an Enum) because it is request-body shape that is converted to ApprovalStatus on persistence"
  - "ApprovalStatus enum (PENDING/APPROVED/REJECTED/ESCALATED/TIMED_OUT) is exported as the 19th public symbol — required by API gateway in Plan 04-07"
  - "All str-Enums kept as `class Foo(str, Enum):` form (not `StrEnum`) per plan instruction — explicit values match DB CHECK constraints"
  - "Wave 0 stub strategy: pytest.importorskip(target_module) at module level + pytest.skip body — prevents collection-time ImportError until plans 04-02..04-08 land"
metrics:
  duration: "single session"
  completed_date: "2026-05-18"
  tasks_completed: 3
  files_created: 25
  tests_passing: "84 (66 model + 12 ABC + 6 public-API)"
  tests_skipped_stubs: 13
  public_api_symbols: 19
  wave_0_stubs: 13
---

# Phase 4 Plan 01: sft-agents SDK Foundation Summary

Plan 04-01 (sft-agents SDK foundation) is complete: 9 Pydantic v2 models + 4 ABC interfaces + 19-symbol public API + 13 Wave 0 test stubs. Every downstream plan (04-02..04-08) can now `from sft_agents import <X>` without scaffolding gaps. HITL-06 (EvidencePanel) and HITL-07 (motivation-required validator) are mechanically enforced at the SDK boundary.

## Tasks Completed

| Task | Name                                                          | Commit  | Files                                                                |
| ---- | ------------------------------------------------------------- | ------- | -------------------------------------------------------------------- |
| 1    | pyproject deps + tests conftest                               | 773dd92 | pyproject.toml, tests/__init__.py, tests/conftest.py (170 lines)     |
| 2 RED | failing tests for pydantic models                            | 82eae63 | 5 test files (686 lines): test_evidence_panel + test_audit_record + test_audit_constraints + test_approval_request + test_budget_snapshot |
| 2 GREEN | pydantic v2 models (8 model files)                          | 2cfab43 | models/{evidence,audit,approval,budget,proposed_action,enums,memory_record,__init__}.py (534 lines) |
| 3    | ABC interfaces + public API + Wave 0 stubs                    | 8b1335d | sdk/{__init__,agent,tool,memory,policy}.py + __init__.py + 14 test files |

## Verification Results

```bash
$ uv run python -c "from sft_agents import Agent, Tool, Memory, Policy, EvidencePanel, AuditRecord, ApprovalRequest, ApprovalDecision, ApprovalStatus, BudgetSnapshot, BudgetLimits, ProposedAction, ToolCall, RagCitation, TokenUsage, MemoryRecord, Tier, Decision, ActionType; print('OK', 19)"
OK 19

$ uv run pytest tests/ -x --tb=short
84 passed, 13 skipped in 0.17s

$ find tests -name 'test_*.py' | wc -l
20

$ uv run ruff check src/sft_agents/sdk
All checks passed!
```

## Success Criteria

- [x] Foundation Wave 1 unblocks Waves 2-4: every downstream plan can `from sft_agents import <X>` without scaffolding gaps — verified by `test_public_api.py`
- [x] 4 ABC interfaces (Agent, Tool, Memory, Policy) instantiable from concrete subclasses; abstract enforcement validated via TypeError — verified by `test_sdk_interfaces.py`
- [x] 9 Pydantic v2 models (EvidencePanel, AuditRecord, ApprovalRequest, ApprovalDecision, BudgetSnapshot, BudgetLimits, ProposedAction, ToolCall, RagCitation, TokenUsage, MemoryRecord) with frozen+extra=forbid+tz-aware on every datetime — verified by 5 model test files (66 assertions)
- [x] HITL-06 contract stable: EvidencePanel shape locked for Phase 5 RAG to populate `rag_citations[]` — `rag_citations: list[RagCitation] = Field(default_factory=list)`
- [x] HITL-07 mechanically enforced: motivation field required on hitl_* decisions via model_validator — verified by `test_audit_constraints.py` (14 assertions across the hitl_*/auto matrix)
- [x] Wave 0 stubs cover all 11 implementation-pending requirements (CORE-03..10, HITL-01..05, HITL-08..10) — 12 stub files generated from template + 1 test_safety_interlock for HITL-04

## Public API (Final)

19 symbols re-exported flat from `sft_agents`:

| Category | Symbols |
| -------- | ------- |
| SDK ABCs (4) | `Agent`, `Tool`, `Memory`, `Policy` |
| Approval (2) | `ApprovalRequest`, `ApprovalDecision` |
| Audit (1)    | `AuditRecord` |
| Budget (2)   | `BudgetSnapshot`, `BudgetLimits` |
| Evidence (4) | `EvidencePanel`, `ToolCall`, `RagCitation`, `TokenUsage` |
| Memory (1)   | `MemoryRecord` |
| Action (1)   | `ProposedAction` |
| Enums (4)    | `Tier`, `Decision`, `ActionType`, `ApprovalStatus` |
| Meta (1)     | `__version__ = "0.1.0"` |

## Pydantic Model Validators (Mechanical Enforcement)

| Validator | Location | Enforces |
| --------- | -------- | -------- |
| `_tz_aware` (field_validator) | ToolCall.ts, RagCitation.retrieved_at, AuditRecord.ts, ApprovalRequest.created_at/sla_deadline/decided_at, MemoryRecord.ts | Pitfall 7 — rejects naive datetime |
| `max_length=500` (Field) | EvidencePanel.input_summary | T-04-Checkpoint-PII mitigation |
| `pattern=r"^[a-z0-9.\-]+@[a-z0-9.\-]+$"` | EvidencePanel.model | T-04-LLM-Inject — blocks malformed model identifiers |
| `pattern=r"^[a-f0-9]{64}$"` | EvidencePanel.prompt_hash | T-04-LLM-Inject — enforces sha256 hex |
| `_check_decision_consistency` (model_validator after) | AuditRecord | HITL-07 motivation required AND approval_id NOT NULL for hitl_*; approval_id IS NULL for auto |
| `min_length=1` (Field) | ApprovalDecision.motivation | HITL-07 — empty motivation rejected |

## Wave 0 Stubs Created (13 files)

| Stub File | Target Module | Owner Plan |
| --------- | ------------- | ---------- |
| test_migrations.py | sft_agents.migrations | 04-02 |
| test_llm_adapter.py | sft_agents.llm.adapter | 04-03 |
| test_llm_factory.py | sft_agents.llm.factory | 04-03 |
| test_supervisor.py | sft_agents.runtime.supervisor | 04-05 |
| test_recursion_limit.py | sft_agents.runtime.supervisor | 04-05 |
| test_tool_registry.py | sft_agents.runtime.tool_registry | 04-05 |
| test_hitl_cycle.py | sft_agents.hitl.interrupt | 04-06 |
| test_escalation.py | sft_agents.hitl.escalation | 04-06 |
| test_governor.py | sft_agents.hitl.governor | 04-06 |
| test_budget.py | sft_agents.hitl.budget | 04-06 |
| test_safety_interlock.py | sft_agents.hitl.safety_interlock | 04-06 |
| test_rate_limit_audit_query.py | sft_agents.audit.rate_limit | 04-06 |
| test_replay.py | sft_agents.replay | 04-08 |

All use the same `pytest.importorskip(target_module, reason=...) + def test_<name>_stub(): pytest.skip(...)` pattern. They will become tests as their owner plan lands.

## Deviations from Plan

### Continuation Recovery

When this executor started, Tasks 1 and 2 (RED test commit) had already been committed in a prior session (commits `773dd92` and `82eae63`). The model implementation files for Task 2 (GREEN) existed on disk but were **untracked** — never committed. Recovery action: staged and committed the existing GREEN model implementations as `2cfab43` (Task 2 GREEN). Then proceeded normally with Task 3.

### [Rule 1 - Bug] Forward-reference quoting in Agent ABC

- **Found during:** Task 3 (ruff check on new SDK code)
- **Issue:** `tools: list["Tool"]` style forward references trip UP037 with `from __future__ import annotations` (PEP 563 makes all annotations strings; quotes become redundant).
- **Fix:** Removed quotes from class-attribute annotations in `sdk/agent.py`. Imports stay under `TYPE_CHECKING` for true circular safety; PEP-563 defers evaluation regardless.
- **Files modified:** `packages/sft-agents/src/sft_agents/sdk/agent.py`
- **Commit:** 8b1335d

## Deferred Issues

| Issue | File(s) | Plan to address |
| ----- | ------- | --------------- |
| Ruff UP042 on `class Foo(str, Enum):` (recommends `StrEnum`) | `models/enums.py` | Plan instruction explicitly used `class Foo(str, Enum)`; left as-is for Phase 4 compatibility with DB CHECK constraints. Can migrate to `enum.StrEnum` in a future cleanup pass — analog precedent in sft-tools also defers. |
| Ruff UP037 quoted forward ref in AuditRecord | `models/audit.py:70` | Pre-committed in Task 2 GREEN snapshot (commit 2cfab43); harmless. |
| Ruff UP037 quoted return type in ProposedAction.from_payload | `models/proposed_action.py:43,58` | Pre-committed in Task 2; harmless. |
| Ruff I001 import sort in `models/__init__.py` | `models/__init__.py:6` | Imports are alphabetized by sub-module; ruff prefers a different grouping. Pre-committed in Task 2; non-blocking. |

No threats flipped from `mitigate` to `accept`; STRIDE register (T-04-Checkpoint-PII, T-04-LLM-Inject, T-04-Audit-Tamper, T-04-Audit-Tamper-FK) all mechanically enforced.

## Self-Check: PASSED

- packages/sft-agents/src/sft_agents/sdk/__init__.py — FOUND
- packages/sft-agents/src/sft_agents/sdk/agent.py — FOUND
- packages/sft-agents/src/sft_agents/sdk/tool.py — FOUND
- packages/sft-agents/src/sft_agents/sdk/memory.py — FOUND
- packages/sft-agents/src/sft_agents/sdk/policy.py — FOUND
- packages/sft-agents/src/sft_agents/__init__.py — modified (19-symbol flat re-export)
- packages/sft-agents/src/sft_agents/models/* — 8 model files FOUND
- packages/sft-agents/tests/* — 20 test files FOUND (5 model tests + test_sdk_interfaces + test_public_api + 13 Wave 0 stubs)
- Commits 773dd92, 82eae63, 2cfab43, 8b1335d — verified via `git log`
