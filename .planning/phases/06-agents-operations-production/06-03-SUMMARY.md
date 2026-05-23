---
phase: 06-agents-operations-production
plan: 03
plan_id: 06-03
subsystem: llm-factory
tags: [wave-1, mock-llm, factory, tdd, deterministic-ci]
requires:
  - 06-00 (Wave 0 test stubs at tests/llm/test_mock_backend.py)
  - Phase 4 build_chat_model factory (ollama/vllm dispatch)
provides:
  - MockReplayChatModel (BaseChatModel) — JSONL record/replay async chat model
  - LLM_BACKEND=mock branch of build_chat_model() (third factory dispatch)
  - structlog event "mock_llm_hash_miss_fallback" for CI drift gates
affects:
  - packages/sft-agents/src/sft_agents/llm/__init__.py (new public export)
  - packages/sft-agents/src/sft_agents/llm/factory.py (LLMBackend Literal + dispatch)
tech-stack:
  added: []
  patterns:
    - "BaseChatModel subclass with pydantic v2 PrivateAttr for mutable replay state"
    - "Late local import of mock module from factory (mirror of ollama/vllm branches)"
    - "JSONL fixture format: prompt_hash + response{content,tool_calls,usage_metadata}"
    - "Ordered-replay fallback on hash miss + structlog warning (Pitfall §10)"
    - "Async-only convention: _generate raises NotImplementedError"
key-files:
  created:
    - packages/sft-agents/src/sft_agents/llm/mock.py
    - packages/sft-agents/tests/llm/test_factory_mock.py
  modified:
    - packages/sft-agents/src/sft_agents/llm/factory.py
    - packages/sft-agents/src/sft_agents/llm/__init__.py
    - packages/sft-agents/tests/llm/test_mock_backend.py (replaced Wave 0 stub)
decisions:
  - "Mutable replay state (_entries, _index) stored as pydantic PrivateAttr — keeps them out of the LangChain BaseModel schema while remaining mutable across ainvoke calls."
  - "Factory dispatch refactored from implicit 'final fallthrough is vllm' to explicit 'if vllm / else mock' so the third branch reads cleanly without re-ordering pre-existing branches."
  - "Hash-miss fallback raises RuntimeError when the ordered index is exhausted rather than wrapping — silent wrap would hide a fixture deficit from CI."
  - "_llm_type = 'mock-replay' — matches RESEARCH §Pattern 2 exact string for LangSmith/Langfuse trace identification."
metrics:
  duration: ~25 min
  completed: 2026-05-23
  tasks_completed: 2
  files_created: 2
  files_modified: 3
  tests_added: 11
  tests_passing: 23  # 11 new + 12 existing test_llm_factory.py
---

# Phase 06 Plan 03: Mock LLM Backend Factory Branch — Summary

One-liner: Added third LLM factory branch `LLM_BACKEND=mock` backed by `MockReplayChatModel`, a JSONL record/replay `BaseChatModel` keyed on sha256 prompt_hash with graceful ordered-fallback for fixture drift, unlocking deterministic network-free Phase 6 E2E tests.

## What Was Built

### `packages/sft-agents/src/sft_agents/llm/mock.py` (NEW)

```python
class MockReplayChatModel(BaseChatModel):
    fixture_path: pathlib.Path                       # pydantic field
    _entries: list[dict] = PrivateAttr(default_factory=list)
    _index: int = PrivateAttr(default=0)

    def __init__(self, fixture_path: str | pathlib.Path, **kwargs) -> None: ...
    @staticmethod
    def _prompt_hash(messages: list[BaseMessage]) -> str: ...   # sha256(type:content lines)
    def _build_message(self, entry: dict) -> AIMessage: ...
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult: ...
    def _generate(self, *a, **k) -> ChatResult: ...             # raises NotImplementedError
    @property
    def _llm_type(self) -> str:                                  # returns "mock-replay"
```

### Replay semantics

1. Compute `sha256("\n".join(f"{m.type}:{m.content}" for m in messages))`.
2. **Strict path:** if any fixture entry has the matching `prompt_hash`, return its `response` payload as an `AIMessage` (`content`, `tool_calls`, `usage_metadata` propagated verbatim).
3. **Fallback path (Pitfall §10):** if no entry matches, take `_entries[_index]`, increment `_index`, and emit a `structlog.warning("mock_llm_hash_miss_fallback", expected_hash=..., index=..., fallback_hash=..., fixture_path=...)`. CI can grep for this event and fail the PR with "fixture needs refresh."
4. If `_index >= len(_entries)`, raise `RuntimeError` — fail loud rather than silently wrap.

### Factory extension (`factory.py`)

- `LLMBackend = Literal["ollama", "vllm", "mock"]`
- `_VALID_BACKENDS = ("ollama", "vllm", "mock")`
- Whitelist error message now `"LLM_BACKEND must be one of ollama|vllm|mock, got {x!r}"`
- New branch after vllm:
  ```python
  from sft_agents.llm.mock import MockReplayChatModel   # local import
  fixture = os.environ.get("MOCK_LLM_FIXTURE")
  if not fixture:
      raise RuntimeError("LLM_BACKEND=mock requires MOCK_LLM_FIXTURE env var ...")
  logger.info("llm_factory_build", backend="mock", fixture=fixture, temperature=temperature)
  return MockReplayChatModel(fixture_path=pathlib.Path(fixture))
  ```
- Default backend remains `"ollama"` so production deployments never silently flip to mock (T-V6-mock-prod-leak mitigation).

### Public re-export (`llm/__init__.py`)

`MockReplayChatModel` is now importable via `from sft_agents.llm import MockReplayChatModel`.

## Env-var Contract

| Variable             | Required when           | Effect                                                                  |
| -------------------- | ----------------------- | ----------------------------------------------------------------------- |
| `LLM_BACKEND=mock`   | always (to opt in)      | Dispatches `build_chat_model()` to MockReplayChatModel branch           |
| `MOCK_LLM_FIXTURE`   | when `LLM_BACKEND=mock` | Absolute or relative path to JSONL fixture; RuntimeError if absent      |

## Test Coverage

11 new tests, all green; 12 pre-existing `test_llm_factory.py` tests still green (no regressions). Total: 23 pass / 0 fail.

`packages/sft-agents/tests/llm/test_mock_backend.py` (7 tests):
- `test_loads_jsonl_fixture` — `_entries` count after construct.
- `test_llm_type_property` — returns `"mock-replay"`.
- `test_agenerate_returns_aimessage_keyed_by_hash` — strict hash match.
- `test_agenerate_falls_back_to_ordered_when_hash_missing` — two hash misses → two ordered entries + two `mock_llm_hash_miss_fallback` events (verified via `structlog.testing.capture_logs`).
- `test_agenerate_emits_tool_calls` — `tool_calls` payload propagates to `AIMessage.tool_calls`.
- `test_agenerate_includes_usage_metadata` — `usage_metadata` propagates with all token counts.
- `test_sync_generate_raises_not_implemented` — `model._generate(...)` raises NotImplementedError with `"async-only"` in message.

`packages/sft-agents/tests/llm/test_factory_mock.py` (4 tests):
- `test_factory_returns_mock_when_env_set` — env-var dispatch returns MockReplayChatModel.
- `test_factory_raises_when_mock_fixture_env_missing` — RuntimeError mentioning `MOCK_LLM_FIXTURE`.
- `test_factory_validates_backend_whitelist_includes_mock` — RuntimeError message includes `mock`.
- `test_factory_existing_ollama_branch_unchanged` — ollama branch still resolves to ChatOllama.

## Verification

```bash
PYTHONPATH=packages/sft-agents/src pytest \
    packages/sft-agents/tests/llm/test_mock_backend.py \
    packages/sft-agents/tests/llm/test_factory_mock.py \
    packages/sft-agents/tests/test_llm_factory.py -v
# 23 passed in 7.12s
```

Import smoke:
```bash
PYTHONPATH=packages/sft-agents/src python -c \
    "from sft_agents.llm import MockReplayChatModel; print(MockReplayChatModel.__name__)"
# MockReplayChatModel
```

> NB on execution environment: the worktree shares the project `.venv`, whose editable
> install points at the main-repo `packages/sft-agents/src`. To pick up the worktree
> source during local verification, set `PYTHONPATH=packages/sft-agents/src` (or rely
> on pytest run from inside CI where editable install resolves to the checked-out
> worktree path). Both Task 1 (RED) and Task 2 (GREEN) were verified this way.

## Commits

| Task | Type | Hash    | Description                                                                          |
| ---- | ---- | ------- | ------------------------------------------------------------------------------------ |
| 1    | test | 8d7d271 | add failing tests for MockReplayChatModel and factory mock branch (RED)              |
| 2    | feat | 9fca24e | add MockReplayChatModel + LLM_BACKEND=mock factory branch (GREEN — 23 tests pass)   |

## Deviations from Plan

None — plan executed exactly as written. Implementation matches RESEARCH §Pattern 2 sketch (lines 423-467) verbatim modulo the pydantic v2 PrivateAttr adaptation already called out in 06-PATTERNS.md (lines 113-117), and the explicit "if vllm / else mock" restructure inside `build_chat_model` (the original used a comment-only `# resolved == "vllm"` fall-through — turning the vllm path into an `if` block keeps the new mock path symmetrical and unambiguous).

## TDD Gate Compliance

- RED gate: commit 8d7d271 — `test(06-03): add failing tests ...`
- GREEN gate: commit 9fca24e — `feat(06-03): add MockReplayChatModel ...`
- REFACTOR gate: not needed — implementation matches the spec on first GREEN, no cleanup commit warranted.

## Threat Surface

No new threat flags raised. The mock backend introduces only filesystem reads of repo-committed JSONL fixtures (existing `T-V6-secret` and `T-V6-fixture-poisoning` dispositions cover this), and the env-var dispatch keeps `LLM_BACKEND=mock` opt-in (existing `T-V6-mock-prod-leak` mitigation preserved: default remains `ollama`).

## Known Stubs

None.

## Self-Check: PASSED

- File `packages/sft-agents/src/sft_agents/llm/mock.py` — FOUND
- File `packages/sft-agents/tests/llm/test_factory_mock.py` — FOUND
- File `packages/sft-agents/tests/llm/test_mock_backend.py` — FOUND (replaced stub)
- Commit 8d7d271 — FOUND on branch
- Commit 9fca24e — FOUND on branch
- 23/23 tests passing
- `from sft_agents.llm import MockReplayChatModel` — succeeds
