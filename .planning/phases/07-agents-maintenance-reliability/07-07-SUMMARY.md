---
phase: 07-agents-maintenance-reliability
plan: 07-07
subsystem: maintenance/rca-specialist
tags: [agent, maintenance, rca, 5-why, citation-grounding, hitl, langgraph, asyncpg, pydantic]
dependency_graph:
  requires: ["07-00", "07-01", "07-02", "07-04", "sft-agents", "sft-knowledge"]
  provides: ["mnt-rca-specialist", "RCASpecialist", "RCAChain", "WhyStep", "RCAChainValidator"]
  affects: ["07-10-api-gateway", "07-12-e2e"]
tech_stack:
  added: ["mnt-rca-specialist package", "RCAChainValidator with asyncpg PG lookup", "5-Why bilingue prompts"]
  patterns: ["TDD RED/GREEN", "ReAct LangGraph node", "ALWAYS-supervisor HITL (D-RCA-02)", "Open Q5 full PG lookup"]
key_files:
  created:
    - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/models.py
    - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/validators.py
    - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/prompts.py
    - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/metadata.py
    - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py
    - apps/agents/maintenance/rca-specialist/tests/test_models.py
    - apps/agents/maintenance/rca-specialist/tests/test_validators.py
  modified:
    - apps/agents/maintenance/rca-specialist/pyproject.toml
    - apps/agents/maintenance/rca-specialist/README.md
    - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/__init__.py
decisions:
  - "Open Q5 resolved: full PG lookup (SELECT 1 FROM documents WHERE source_uri = $1 LIMIT 1) — audit-friendly, rejects hallucinated citations"
  - "ALWAYS-supervisor gate: _resolve_tier() returns Tier.SUPERVISOR unconditionally (D-RCA-02 literal, no severity branching)"
  - "RagCitation.source_uri confirmed field name from sft_agents.models.evidence (not 'uri' or 'doc_uri')"
  - "Pool=None fallback logs structlog ERROR (loud degradation, not silent shape-only)"
  - "Agent E2E tests delegated to plan 07-12 (mock LLM JSONL scenarios)"
  - "langchain-core constraint relaxed to >=0.3 (no upper bound) to avoid workspace version conflict with ops-production-planner"
metrics:
  duration: "11 minutes"
  completed: "2026-05-23"
  tasks: 3
  files_created: 7
  files_modified: 4
  tests_written: 37
  tests_passing: 37
---

# Phase 07 Plan 07: RCASpecialist Agent — 5-Why Chain with Citation Grounding and ALWAYS-Supervisor HITL

## One-liner

RCASpecialist ReAct LangGraph node implementing form-based 5-Why methodology with asyncpg PG citation lookup and unconditional supervisor HITL gate (D-RCA-01 + D-RCA-02).

## What Was Built

### Task 1: Package Scaffold + RED Tests (commit 2f072a5)

- Updated `pyproject.toml` with full dependencies (sft-agents, sft-knowledge, asyncpg, langgraph, pydantic, structlog)
- Updated `README.md` describing the 5-Why methodology, citation grounding, and ALWAYS-supervisor gate
- Wrote 23 model tests (RED) covering WhyStep/RCAChain field constraints, frozen/extra=forbid, round-trip, request/response shape
- Wrote 14 validator tests (RED) covering PG lookup contract, OrphanCitationError, MissingCitationError, SQL parameterization, pool=None fallback, case-sensitive comparison

### Task 2: models.py + validators.py + prompts.py + metadata.py (commits efa6450, b933cbc, 6af22da)

- `models.py`: WhyStep (frozen+extra=forbid, question/answer/citations/confidence), RCAChain (exactly 5 named why_1..why_5 fields, tz-aware created_at validator), RCASpecialistRequest, RCASpecialistResponse with Literal hitl_status
- `validators.py`: MissingCitationError + OrphanCitationError domain exceptions; RCAChainValidator with `_SQL: ClassVar[str]` parameterized PG lookup; pool=None fallback logs structlog ERROR (loud, not silent); case-sensitive, no whitespace trimming
- `prompts.py`: SYSTEM_PROMPT_IT + SYSTEM_PROMPT_EN bilingue, build_system_prompt(), build_retry_prompt() for retry corrective SystemMessage
- `metadata.py`: TOOL_INVENTORY, DATA_SOURCES, KPIS_IMPACTED, build_ops05_evidence_panel() with ALWAYS-supervisor default

### Task 3: RCASpecialist agent.py (commit 40c327a)

- 556-line async `__call__(state)` LangGraph node (exceeds 250-line minimum)
- ReAct loop with rag_search + traverse_graph tools via `create_react_agent`
- Retry policy: catches ValidationError + MissingCitationError + OrphanCitationError, appends corrective SystemMessage, 3 total attempts (_MAX_VALIDATION_RETRIES=2)
- JSON fence stripping (robustness against LLM markdown wrapping)
- ALWAYS-supervisor gate: `escalate_to_supervisor` called BEFORE audit write (Pitfall §3)
- Both success + exhaustion paths escalate with appropriate reason strings
- `_resolve_tier()` returns `Tier.SUPERVISOR` unconditionally (no severity branching)
- AuditRecord with ActionType.RCA_CHAIN, Decision.HITL_SUPERVISOR

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Dependency] pyproject.toml langchain-core constraint relaxed**
- **Found during:** Task 1 (first test run)
- **Issue:** `langchain-core>=0.3,<0.4` conflicted with `ops-production-planner`'s `langchain-core>=1.0,<2.0` in the shared uv workspace
- **Fix:** Changed to `langchain-core>=0.3` (no upper bound), and removed upper bound on langgraph/langgraph-prebuilt to let uv resolve compatibility
- **Files modified:** `pyproject.toml`

**2. [Rule 1 - Bug] structlog caplog incompatibility in test**
- **Found during:** Task 2 (first test run)
- **Issue:** `test_validate_pool_none_returns_chain` used `caplog` (Python logging), but structlog writes to stdout by default — caplog captured no messages
- **Fix:** Changed to `capsys` (stdout/stderr capture) which correctly captures structlog output
- **Files modified:** `tests/test_validators.py`

**3. [Rule 3 - Blocking] __init__.py import loop during Task 2**
- **Found during:** Task 2 (before agent.py existed)
- **Issue:** `__init__.py` importing from `mnt_rca_specialist.agent` (which didn't exist) caused ModuleNotFoundError when any module was imported
- **Fix:** Added `try/except ModuleNotFoundError` in `__init__.py` for the agent import; removed after Task 3 implemented agent.py
- **Files modified:** `src/mnt_rca_specialist/__init__.py`

## Open Q5 Resolution

**Decision: Full PG lookup, audit-friendly** (locked in CONTEXT.md L284).

SQL used: `SELECT 1 FROM documents WHERE source_uri = $1 LIMIT 1`

This parameterized query is a `ClassVar[str]` on `RCAChainValidator._SQL` so tests can inspect it directly and assert no f-string interpolation (T-V5-sql compliance).

Rationale:
1. Hallucination mitigation: shape-only validation cannot catch fabricated source_uri values
2. Audit-friendly: validated chain is audit-authoritative without requiring re-lookup
3. Performance acceptable: max ~15 PG round-trips per RCA invocation, sub-50ms on indexed source_uri

Pool=None fallback degrades to shape-only with structlog ERROR (not silent, not WARNING) — discoverable, not swallowed.

## RagCitation Field Discovery

Field name is `source_uri` (confirmed from `packages/sft-agents/src/sft_agents/models/evidence.py`).
The interface spec in the plan (`source_uri: str`) matches the actual field exactly. No renaming needed.

RagCitation is defined in `sft_agents.models.evidence` and re-exported via `sft_knowledge.models.RagCitation`.

## Retry Policy + Exhaustion Path

- `_MAX_VALIDATION_RETRIES = 2` → 3 total attempts
- Corrective SystemMessage appended on each retry (authoritative correction, not user feedback)
- On exhaustion: escalate with `reason='rca_validation_exhausted'`, carry `best_chain_attempt` (even if invalid) in evidence for forensic review
- Both paths audit as ActionType.RCA_CHAIN, Decision.HITL_SUPERVISOR

## ALWAYS-Supervisor Literal Interpretation Defense

D-RCA-02 reads: "every corrective_action_recommendation passes through HITL tier supervisor". This is interpreted literally — `_resolve_tier()` returns `Tier.SUPERVISOR` with no parameters and no conditional branches. The exhaustion path ALSO escalates (reason='rca_validation_exhausted') to maintain the invariant even when no valid chain was produced.

## Agent E2E Coverage Delegation

Agent retry loop + ReAct + HITL chain is tested end-to-end in plan 07-12 (mock LLM JSONL scenarios), not in this plan. This is the explicit architectural decision documented in the plan (Task 3 behavior section):
> "This plan deliberately does NOT include test_agent.py — the retry loop + ReAct + HITL chain is best exercised against a real LangGraph runtime with mock LLM, not against AsyncMock stubs."

## Test Counts

| File | Tests | Status |
|------|-------|--------|
| test_models.py | 23 | All passed |
| test_validators.py | 14 | All passed |
| test_evidence_panel.py | 1 (Wave 0 stub) | Skipped (07-11 plan) |
| **Total** | **37 real tests** | **37 passed** |

## Threat Surface Scan

No new network endpoints or trust boundaries introduced beyond what the plan specifies. The agent respects:
- T-V7-llm-hallucination: mitigated by full PG lookup
- T-V7-rca-bypass-supervisor: mitigated by `_resolve_tier()` returning SUPERVISOR unconditionally
- T-V7-rca-retry-bomb: mitigated by `_MAX_VALIDATION_RETRIES=2` (3 total attempts)
- T-V5-sql: parameterized query ClassVar, never interpolated

## Self-Check: PASSED

- models.py: exists at `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/models.py`
- validators.py: exists at `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/validators.py`
- prompts.py: exists at `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/prompts.py`
- metadata.py: exists at `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/metadata.py`
- agent.py: exists at `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py`
- Commits 2f072a5, efa6450, b933cbc, 6af22da, 40c327a all verified in git log
- 37 tests passing
