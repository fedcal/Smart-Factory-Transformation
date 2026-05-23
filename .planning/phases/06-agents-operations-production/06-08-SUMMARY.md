---
phase: 06-agents-operations-production
plan: 08
plan_id: 06-08
subsystem: ops-production-planner
tags: [agent, ops-cluster, scheduling, hitl, llm-rationale, supervisor-tier]
requires: [06-00, 06-01, 06-03, 06-04, 06-05]
provides:
  - ProductionPlanner          # apps/agents/ops/production-planner/src/ops_production_planner/agent.py
  - PlanRequest                # models.py
  - PlanResponse               # models.py
  - RATIONALE_PROMPT           # prompts.py
  - render_system_prompt       # prompts.py
  - citations_block            # prompts.py
affects:
  - apps/agents/ops/production-planner/pyproject.toml   # added runtime deps
tech-stack:
  added: []
  patterns:
    - "Thin-orchestrator agent (06-PATTERNS lines 495-519): collaborators injected via __init__, algorithm-first / LLM-explanation-after"
    - "Pydantic v2 frozen + extra=forbid request models (T-V6-injection)"
    - "LLM scope-clamp via JSON schema {rationale_md, citation_ids} (T-V6-llm-hallucination)"
    - "model_copy(update={...}) for immutable Pydantic updates (06-04 ScheduleDraft)"
    - "Lazy import of build_chat_model so tests injecting a mock LLM never touch the factory"
    - "Static fallback rationale on JSON parse error keeps supervisor UI non-empty"
key-files:
  created:
    - apps/agents/ops/production-planner/src/ops_production_planner/agent.py
    - apps/agents/ops/production-planner/src/ops_production_planner/models.py
    - apps/agents/ops/production-planner/src/ops_production_planner/prompts.py
  modified:
    - apps/agents/ops/production-planner/src/ops_production_planner/__init__.py
    - apps/agents/ops/production-planner/pyproject.toml
    - apps/agents/ops/production-planner/tests/test_production_planner.py
decisions:
  - "LLM scope is strictly rationale-only: parsed JSON's `items` / `schedule_id` / `horizon_*` are dropped; only `rationale_md` (string) flows into the ScheduleDraft via model_copy. Pinned by test_llm_cannot_mutate_items_list."
  - "Fallback rationale uses a fixed markdown template referencing `items` and `unscheduled_orders` so the supervisor UI never renders an empty rationale even when the LLM is unreachable or returns malformed JSON."
  - "`citations` flow from the rag_pipeline output (never from the LLM), so the citation set is auditable and ACL-filtered (T-V6-citation + T-V6-acl-leak). LLM only emits indices into the already-validated citation list."
  - "`_clock` is an injectable lambda so determinism tests can pin `horizon_start` across two invocations and assert identical schedule_id. Production callers pay no overhead — default is `datetime.now(UTC)`."
  - "RAG search failure is non-fatal: caught with a structlog warning, `citations` degrades to []. Tests don't cover this path explicitly because the production-planner contract is 'schedule must always reach a supervisor for review' and missing citations is a softer degradation than blocking the draft."
  - "EvidencePanel is constructed inline with placeholder values (confidence=1.0 — algorithm deterministic; model='schedule-heuristic@sft-domain'). Full evidence_panel wiring (OPS-05 completion) lands in plan 06-14."
  - "`load_failure_modes()` returns a tuple per the sft-domain API; the agent normalises to a dict keyed by `fm.id` for compatibility with `earliest_slot`'s `.get(asset_id, default)` lookup. The conversion is defensive — works for empty tuples used in tests too."
metrics:
  duration_minutes: 25
  completed: 2026-05-23
---

# Phase 06 Plan 08: ProductionPlanner Summary

ProductionPlanner agent ships as a thin orchestrator wiring the deterministic SPT/EDD heuristic from `packages/sft-domain/scheduling/` (06-04) to an LLM-driven rationale and a supervisor-tier HITL gate. The algorithm always runs first; the LLM is scope-clamped to the `rationale_md` string field; every draft is routed through `human_approval_node(tier=Tier.SUPERVISOR)` before any audit decision can record `approved` — Phase 06 success criterion #4.

## What landed

### `apps/agents/ops/production-planner/src/ops_production_planner/models.py` — strict request contract

`PlanRequest` (`frozen=True`, `extra="forbid"`):
- `strategy: Literal["spt", "edd"]` — whitelist whitelist; any other string raises `ValidationError` at entry (T-V6-injection).
- `horizon_days: int` bounded `[1, 30]` — prevents unbounded compute and overlarge ScheduleDraft payloads.
- `user_roles: list[str]` — propagated to `rag_pipeline.search` for ACL pre-filter (Phase 5 D-72; T-V6-acl-leak).

`PlanResponse` is the api-gateway-facing envelope (`draft`, `hitl_thread_id`, `proposed_action_id`); the agent itself returns a state-delta dict (`{"schedule_draft": ScheduleDraft, "approval": <hitl delta>}`), and the api-gateway adapter (future plan) wraps that into `PlanResponse`.

### `apps/agents/ops/production-planner/src/ops_production_planner/prompts.py` — LLM rationale template

- `RATIONALE_PROMPT` system message tells the LLM:
  - Items, assets, and timestamps are **already determined** — do not propose alternatives.
  - Output **strict JSON only** with shape `{"rationale_md": str, "citation_ids": list[int]}`.
  - Cite SOPs by their integer index using `[SOP-{n}]`.
- `render_system_prompt(strategy)` interpolates the strategy name and its long form ("shortest-processing-time first" / "earliest-due-date first").
- `citations_block(citations)` renders the supplied `RagCitation` list as a numbered block with truncated snippets (400-char hard cap) so prompt size stays predictable. When no citations are available the block returns a placeholder telling the LLM to write the rationale without citations (it must not fabricate).

### `apps/agents/ops/production-planner/src/ops_production_planner/agent.py` — `ProductionPlanner` orchestrator

End-to-end flow (`async __call__(state) -> {"schedule_draft", "approval"}`):

1. **Validate**: `PlanRequest.model_validate({strategy, horizon_days, user_roles})` — rejects malformed input.
2. **Load**: `load_orders()` + `load_asset_capacity()` + `load_failure_modes()` from `sft-domain` (cached at module level via `lru_cache`).
3. **Window**: `horizon_start = self._clock()`, `horizon_end = horizon_start + timedelta(days=request.horizon_days)`. `_clock` is injectable for deterministic tests.
4. **Schedule**: `schedule_spt if strategy == "spt" else schedule_edd` (06-04). Pure function, deterministic. `schedule_id` is sha256-derived from `(strategy, horizon_start_iso, sorted_order_ids)` so identical inputs → identical id.
5. **Retrieve**: `await rag_pipeline.search(query, user_roles, category="sop", k=5)`. RAG failure caught with a structlog warning; degrades to `citations = []`.
6. **Explain**: Build `[SystemMessage(render_system_prompt(strategy)), HumanMessage(<draft+citations+unscheduled>)]`; await `model.ainvoke`; parse JSON via `_parse_rationale` (strips markdown fences, validates dict shape, coerces citation ids to int). On any parse failure → `_FALLBACK_RATIONALE` template.
7. **Merge**: `final_draft = draft.model_copy(update={"rationale_md": rationale_md, "citations": list(citations)})` — Pydantic v2 immutable update. The LLM's `items`/`schedule_id` keys (if any) are **silently dropped** by `_parse_rationale` — only `rationale_md` flows through.
8. **Propose**: `ProposedAction.from_payload(thread_id, ActionType.SCHEDULE_DRAFT, final_draft.model_dump(mode="json"))` — sha256-deterministic id.
9. **HITL**: `await human_approval_node(state, proposed_action=..., tier=Tier.SUPERVISOR, ...)` — always supervisor tier, never auto-approve (T-V6-hitl-bypass).

### `apps/agents/ops/production-planner/pyproject.toml` — runtime deps

Added: `pydantic>=2.9,<3`, `structlog>=24.4`, `langchain-core>=1.0,<2.0`, plus workspace sources for `sft-agents`, `sft-domain`, `sft-knowledge`. Dev: `pytest`, `pytest-asyncio`, `pytest-mock`.

## Test counts

- `apps/agents/ops/production-planner/tests/test_production_planner.py`: **15 tests, all passing**.
  - Strategy dispatch: `test_spt_strategy_invokes_schedule_spt`, `test_edd_strategy_invokes_schedule_edd`.
  - Validation: `test_invalid_strategy_raises_validation`, `test_horizon_days_out_of_range_raises_validation`.
  - Horizon: `test_horizon_dates_computed_from_horizon_days`.
  - LLM rationale: `test_llm_rationale_populated_in_draft`, `test_llm_invalid_json_triggers_fallback_rationale`, `test_llm_cannot_mutate_items_list`.
  - RAG: `test_rag_search_called_for_sop_citations`, `test_citations_attached_to_draft`.
  - HITL: `test_human_approval_node_called_with_supervisor_tier`, `test_proposed_action_args_contain_full_draft`.
  - Unscheduled: `test_unscheduled_orders_surfaced_in_rationale`.
  - Determinism: `test_deterministic_schedule_id`.
  - Safety isolation: `test_safety_middleware_not_invoked_for_schedule_draft`.

Sibling regression check (run inside the worktree):
- `packages/sft-domain/tests/test_scheduling.py`: 13/13 pass.
- `packages/sft-agents/tests/test_hitl_cycle.py`: 12/12 pass.

## TDD Gate Compliance

- RED gate: commit `a0c4b09 test(06-08): add failing tests for ProductionPlanner agent`.
- GREEN gate: commit `730f6b9 feat(06-08): implement ProductionPlanner agent (D-PP-01..04)`.
- REFACTOR gate: not needed — implementation passed all 15 tests on first run without intermediate cleanup.

Note: the RED tests use `pytest.importorskip("ops_production_planner.agent")` to skip cleanly when the agent module does not yet exist; this is the project's standard TDD pattern (see `packages/sft-agents/tests/test_hitl_cycle.py:27`). After the GREEN commit the importorskip resolves and all 15 tests collect + pass.

## HITL routing flow (success criterion #4)

```
PlanRequest validated
       │
       ▼
schedule_spt / schedule_edd  (deterministic, 06-04)
       │  draft (items, unscheduled_orders, rationale_md="")
       ▼
rag_pipeline.search(category="sop", user_roles=…)
       │  citations[]
       ▼
LLM.ainvoke(system=RATIONALE_PROMPT, human=draft+citations+unscheduled)
       │  raw.content → JSON → rationale_md   (fallback on parse error)
       ▼
final_draft = draft.model_copy(update={rationale_md, citations})
       │
       ▼
ProposedAction(action_type=SCHEDULE_DRAFT, args=final_draft.model_dump())
       │
       ▼
human_approval_node(tier=Tier.SUPERVISOR, …)   ← every draft, no auto-approve
       │
       ▼
return {"schedule_draft": final_draft, "approval": <hitl delta>}
```

## LLM fallback behaviour

`_parse_rationale` returns `None` (triggering fallback) when:
- `model.ainvoke` raises any exception → caught by outer try/except.
- Response content is non-string or empty.
- Content is not valid JSON (after stripping ```json fences).
- Parsed payload is not a `dict`.
- `rationale_md` key is missing, non-string, or only whitespace.

The fallback is:

```markdown
## Rationale

_LLM rationale is unavailable for this draft (fallback path)._

- The schedule was computed deterministically by the {strategy} heuristic.
- See the `items` list for the per-order asset + window assignment.
- See `unscheduled_orders` for orders that could not fit the horizon.
```

This guarantees the supervisor UI never renders an empty rationale, even with the LLM backend down.

## Deviations from Plan

None — the plan executed exactly as written. The optional refactor pass was skipped because the GREEN commit passed all 15 tests on first run with no fix-attempts needed.

One scope note: the plan referenced "12 tests"; the final implementation has 15 (added `test_horizon_days_out_of_range_raises_validation` for the bounded-int validator and `test_llm_cannot_mutate_items_list` to pin the T-V6-llm-hallucination contract that the plan calls out but doesn't explicitly enumerate). Extra coverage with no plan deletions.

## Known Stubs

- `EvidencePanel` construction inside `_invoke_human_approval` uses placeholder values (`confidence=1.0`, `model="schedule-heuristic@sft-domain"`, empty `tool_calls` and `rag_citations`). Full evidence_panel wiring — populating `tool_calls` from the rag_pipeline invocation and `rag_citations` from the actual returned hits — lands in plan **06-14** (OPS-05 completion). This stub is documented in the plan frontmatter (`# OPS-05 partial: ... full evidence_panel completion in 06-14`).

## Self-Check: PASSED

Created files (verified via `[ -f ... ]`):
- FOUND: `apps/agents/ops/production-planner/src/ops_production_planner/agent.py`
- FOUND: `apps/agents/ops/production-planner/src/ops_production_planner/models.py`
- FOUND: `apps/agents/ops/production-planner/src/ops_production_planner/prompts.py`
- FOUND (modified): `apps/agents/ops/production-planner/src/ops_production_planner/__init__.py`
- FOUND (modified): `apps/agents/ops/production-planner/pyproject.toml`
- FOUND (rewritten): `apps/agents/ops/production-planner/tests/test_production_planner.py`

Commits (verified via `git log`):
- FOUND: `a0c4b09` — test(06-08): add failing tests for ProductionPlanner agent
- FOUND: `730f6b9` — feat(06-08): implement ProductionPlanner agent (D-PP-01..04)
