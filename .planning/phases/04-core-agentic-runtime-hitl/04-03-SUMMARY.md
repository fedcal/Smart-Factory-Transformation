---
phase: 04-core-agentic-runtime-hitl
plan: 03
subsystem: llm-adapter-tool-registry-langfuse
tags: [llm, adapter, ollama, vllm, langfuse, tool-registry, openai-function-calling, wave-2]
requires:
  - "04-01 (sft-agents SDK foundation: TokenUsage model + ABC Tool)"
provides:
  - "build_chat_model() factory: LLM_BACKEND=ollama|vllm dispatch + RuntimeError on invalid"
  - "BudgetingChatModel: usage_metadata + duration_ms capture wrapper (measurement-only)"
  - "extract_usage_metadata + resolve_model_id helpers (EvidencePanel.model regex compliant)"
  - "get_langfuse_callback + build_invocation_metadata + build_invocation_config (Pitfall §11 v3 API)"
  - "ToolRegistry + export_tool_schemas (OpenAI function-calling JSON via model_json_schema(by_alias=True))"
  - "BUILTIN_TOOLS tuple: 3 Phase 3 tools (ReplayCMAPSSTool, ReplayUCITool, QueryTimescaleTool)"
  - "docs/docs/architecture/llm-serving.md (253 lines, --tool-call-parser hermes documented x4)"
affects:
  - "Unblocks Plan 04-05 (Supervisor + clusters): supervisor.route uses get_llm() + bind_tools"
  - "Unblocks Plan 04-06 (BudgetTracker middleware): BudgetingChatModel is the measurement primitive"
  - "Unblocks Plan 04-08 (replay smoke): Langfuse callback integration testing"
tech_stack:
  added:
    - "langchain-ollama 0.3+ (ChatOllama)"
    - "langchain-openai 0.3+ (ChatOpenAI, OpenAI-compatible vLLM endpoint)"
    - "langfuse 3+ (langfuse.langchain.CallbackHandler — v3 API)"
  patterns:
    - "Env-var dispatch with Literal whitelist + RuntimeError (mirrors ot-bridge/main.py:62-71)"
    - "stream_usage=True on ChatOpenAI for vLLM token-metadata capture (Pitfall §4)"
    - "Pydantic v2 model_json_schema(by_alias=True) for OpenAI function-calling export"
    - "Composition over inheritance for chat-model wrappers (BudgetingChatModel)"
    - "Langfuse v3 metadata via config['metadata'] (NOT constructor — Pitfall §11)"
    - "Local import inside factory branches (mirrors ot-bridge/main.run lazy imports)"
key_files:
  created:
    - "packages/sft-agents/src/sft_agents/llm/__init__.py (9 public symbols)"
    - "packages/sft-agents/src/sft_agents/llm/factory.py (build_chat_model + get_llm)"
    - "packages/sft-agents/src/sft_agents/llm/budgeting.py (BudgetingChatModel)"
    - "packages/sft-agents/src/sft_agents/llm/usage.py (extract_usage_metadata + resolve_model_id)"
    - "packages/sft-agents/src/sft_agents/llm/langfuse_callback.py (v3 callback + invocation config)"
    - "packages/sft-agents/src/sft_agents/tools/__init__.py (BUILTIN_TOOLS + re-exports)"
    - "packages/sft-agents/src/sft_agents/tools/registry.py (ToolRegistry + export_tool_schemas)"
    - "packages/sft-agents/tests/test_langfuse_callback.py (11 tests)"
    - "docs/docs/architecture/llm-serving.md (253 lines)"
  modified:
    - "packages/sft-agents/tests/test_llm_factory.py (Wave 0 stub → 12 real tests)"
    - "packages/sft-agents/tests/test_llm_adapter.py (Wave 0 stub → 9 real tests)"
    - "packages/sft-agents/tests/test_tool_registry.py (Wave 0 stub → 12 real tests)"
    - "docs/mkdocs.yml (nav entry for architecture/llm-serving.md)"
decisions:
  - "BudgetingChatModel uses composition (not subclass of BaseChatModel) to keep contract narrow + avoid Pydantic v2 BaseChatModel field surface"
  - "Static runtime tags (ollama-0.6 / vllm-0.8) in resolve_model_id — Phase 11 may dynamic-query"
  - "BUILTIN_TOOLS is a tuple (not list) — instances are reused across registries, frozen at module load"
  - "get_langfuse_callback() returns None on missing langchain peer dep (soft failure) — tracing fully opt-in"
  - "Default model identifiers lowercased + ':'/'/'/'_' → '-' to match EvidencePanel.model regex"
metrics:
  duration: "single session"
  completed_date: "2026-05-18"
  tasks_completed: 2
  files_created: 9
  files_modified: 4
  tests_passing: 128
  tests_skipped: 10
  public_api_symbols_added: 9
---

# Phase 4 Plan 03: LLM Adapter + Tool Registry + Langfuse v3 Summary

Plan 04-03 ships a provider-agnostic LLM adapter (`LLM_BACKEND={ollama|vllm}`) with a single switch point, a measurement-only `BudgetingChatModel` wrapper that captures `usage_metadata` + wall-clock duration for downstream BudgetTracker (Plan 04-06), a name-keyed `ToolRegistry` that exports OpenAI function-calling JSON via Pydantic v2 `model_json_schema(by_alias=True)`, and the Langfuse v3 invocation-config helper that puts `session_id` in `config['metadata']` (Pitfall §11). vLLM Qwen2.5 tool-calling requires `--tool-call-parser hermes` — that deploy blocker is documented 4x in `docs/docs/architecture/llm-serving.md` (Pitfall §3).

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 RED  | failing tests for LLM factory + budgeting wrapper | `baf00d5` | tests/test_llm_factory.py, tests/test_llm_adapter.py |
| 1 GREEN | LLM factory + budgeting wrapper + usage helper | `87ecf9f` | llm/__init__.py, llm/factory.py, llm/budgeting.py, llm/usage.py, tests/test_llm_adapter.py |
| 2 RED  | failing tests for tool registry + langfuse callback | `42f3668` | tests/test_tool_registry.py, tests/test_langfuse_callback.py |
| 2 GREEN | langfuse v3 callback + tool registry + vllm serving docs | `0c4dba2` | llm/__init__.py, llm/langfuse_callback.py, tools/__init__.py, tools/registry.py, docs/docs/architecture/llm-serving.md, docs/mkdocs.yml |

## LLM Factory + env-var matrix

| Variable | Default | Branch | Notes |
| --- | --- | --- | --- |
| `LLM_BACKEND` | `ollama` | both | Selector (RuntimeError on invalid) |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct-q4_K_M` | ollama | Phase 4 lock (D-CONTEXT line 421) |
| `OLLAMA_HOST` | `http://localhost:11434` | ollama | Ollama daemon endpoint |
| `VLLM_MODEL` | `Qwen/Qwen2.5-14B-Instruct-AWQ` | vllm | HF model id |
| `VLLM_BASE_URL` | `http://localhost:8000/v1` | vllm | OpenAI-compatible endpoint |
| `VLLM_API_KEY` | `dummy` | vllm | vLLM doesn't validate in dev |
| `LANGFUSE_HOST` | unset | both | Unset → callback returns None |

## BudgetingChatModel behaviour

| Property | Behavior |
| --- | --- |
| `last_token_usage: TokenUsage` | Populated post-ainvoke via `extract_usage_metadata(response)`; zero-fallback when `usage_metadata` absent |
| `last_duration_ms: int` | `(perf_counter_ns() - start) // 1_000_000`, clamped at 0 |
| `bind_tools(tools)` | Delegates to wrapped, returns **new** `BudgetingChatModel` wrapping the bound result (chain preservation) |
| `with_structured_output(schema)` | Same delegation + rewrap pattern |
| `invoke / ainvoke` | Sync + async forms; both capture duration_ms + token_usage post-call |

**Scope:** measurement only. Budget enforcement (80% soft + 100% hard caps per HITL-09) lands in Plan 04-06 BudgetTracker middleware that reads `last_token_usage` + `last_duration_ms` after each call.

## Tool Registry export shape

Sample schema entry for `query_timescale`:

```json
{
  "type": "function",
  "function": {
    "name": "query_timescale",
    "description": "Query TimescaleDB sensor_events hypertable for historical sensor data...",
    "parameters": {
      "type": "object",
      "properties": {
        "asset_id": { "type": "string", "description": "..." },
        "time_range": { "...": "..." },
        "tags": { "anyOf": [{"type": "array"}, {"type": "null"}], "default": null }
      },
      "required": ["asset_id", "time_range"]
    }
  }
}
```

`by_alias=True` (mandatory) prevents leaking Pydantic internal field names.

`BUILTIN_TOOLS = (ReplayCMAPSSTool(), ReplayUCITool(), QueryTimescaleTool())` — 3 instances created at module import time, reused across registries.

## Langfuse v3 vs v2 API delta (Pitfall §11)

| Aspect | v2 (deprecated) | v3 (current) |
| --- | --- | --- |
| `session_id` | Constructor arg: `CallbackHandler(session_id=...)` | Invocation config: `config["metadata"]["langfuse_session_id"]` |
| `user_id` | Constructor arg | `config["metadata"]["langfuse_user_id"]` |
| `tags` | Constructor arg | `config["metadata"]["langfuse_tags"]` |
| Import path | `langfuse.callback.CallbackHandler` | `langfuse.langchain.CallbackHandler` |

`build_invocation_config(thread_id, ...)` emits the full LangGraph config shape:

```python
{
  "configurable":    {"thread_id": "thread-abc"},
  "callbacks":       [<handler or empty>],
  "metadata":        {"langfuse_session_id": "thread-abc", "langfuse_tags": ["phase4"]},
  "recursion_limit": 25,
}
```

When `LANGFUSE_HOST` is unset, `callbacks` is `[]` and the runtime carries on without tracing.

## Verification

```bash
$ LLM_BACKEND=ollama uv run python -c "from sft_agents.llm import get_llm; print(type(get_llm()).__name__)"
ChatOllama

$ LLM_BACKEND=vllm  uv run python -c "from sft_agents.llm import get_llm; print(type(get_llm()).__name__)"
ChatOpenAI

$ LLM_BACKEND=foo   uv run python -c "from sft_agents.llm import get_llm; get_llm()"
RuntimeError: LLM_BACKEND must be one of ollama|vllm, got 'foo'

$ uv run python -c "from sft_agents.tools import BUILTIN_TOOLS, export_tool_schemas; \
  schemas = export_tool_schemas(list(BUILTIN_TOOLS)); \
  print(len(schemas), [s['function']['name'] for s in schemas])"
3 ['replay_cmapss', 'replay_uci', 'query_timescale']

$ uv run python -c "from sft_agents.llm.langfuse_callback import get_langfuse_callback, build_invocation_metadata; \
  print(get_langfuse_callback() is None, build_invocation_metadata('t1')['langfuse_session_id'])"
True t1

$ grep -c "tool-call-parser hermes" docs/docs/architecture/llm-serving.md
4

$ uv run pytest tests/
128 passed, 10 skipped in 1.23s
```

## Success Criteria

- [x] **CORE-05**: single env var `LLM_BACKEND` switches Ollama ↔ vLLM with zero agent code change — verified by `LLM_BACKEND=ollama|vllm` smoke commands above
- [x] **CORE-06**: default models locked (Qwen2.5-7B Q4_K_M for ollama, Qwen2.5-14B AWQ for vllm) + `stream_usage=True` on vLLM branch — verified by `test_vllm_branch_stream_usage_true`
- [x] **CORE-07**: Tool registry exports OpenAI function-calling JSON via Pydantic v2 `model_json_schema(by_alias=True)` for all 3 Phase 3 builtin tools — verified by `test_export_schemas_for_builtins` + `test_builtins_json_round_trip`
- [x] **Pitfall §11 avoided**: Langfuse v3 metadata passed via `config["metadata"]`, NOT constructor — verified by `test_has_metadata_with_session_id`
- [x] **Pitfall §3 documented**: `--tool-call-parser hermes` documented 4x in llm-serving.md — verified by `grep -c "tool-call-parser hermes" = 4`

## Pattern References Honored

- `services/ot-bridge/src/svc_ot_bridge/main.py:62-71` — env-var dispatch idiom + RuntimeError on invalid (used in `factory._resolve_backend`)
- `packages/sft-tools/src/sft_tools/__init__.py` — flat re-export pattern (mirrored in `sft_agents.tools.__init__`)
- `packages/sft-tools/src/sft_tools/timescale/query.py:46-84` — BaseTool subclass with Pydantic args_schema (the target of `export_tool_schemas`)
- RESEARCH §4 — ChatOllama / ChatOpenAI signature parity
- RESEARCH §5 / Pitfall §11 — Langfuse v3 LangChain integration via `langfuse.langchain`

## Deviations from Plan

### [Rule 1 - Bug] FakeListChatModel.bind_tools raises NotImplementedError

- **Found during:** Task 1 GREEN test run
- **Issue:** `langchain_core.language_models.fake_chat_models.FakeListChatModel.bind_tools` raises `NotImplementedError` (the base BaseChatModel default), so the unit test exercising `BudgetingChatModel.bind_tools` chain preservation could not use the fake directly.
- **Fix:** Introduced `_BindableFakeChatModel(FakeListChatModel)` inside `tests/test_llm_adapter.py` that overrides `bind_tools` and `with_structured_output` to return a fresh fake. The wrapper itself (`BudgetingChatModel.bind_tools`) was unchanged — it delegates to the wrapped model verbatim. This is a test-only shim, not a production code change.
- **Files modified:** `packages/sft-agents/tests/test_llm_adapter.py`
- **Commit:** `87ecf9f`

### [Rule 2 - Missing critical functionality] Langfuse import-failure fallback

- **Found during:** Task 2 implementation (probing langfuse package surface)
- **Issue:** Plan referenced `from langfuse.callback import CallbackHandler` (v2 path). In langfuse v3, the LangChain integration lives at `langfuse.langchain.CallbackHandler` and requires the `langchain` peer dependency. Our pyproject.toml installs only `langchain-core` (Phase 4 stack lock per CONTEXT line 37) — so the import would fail at runtime.
- **Fix:** `get_langfuse_callback()` wraps the import in try/except, logs `langfuse_import_failed`, returns `None`. Tracing remains fully opt-in: callers ship into a `callbacks` list and filter `None`. Documented this soft-failure behavior in `llm-serving.md`.
- **Files modified:** `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py`
- **Commit:** `0c4dba2`

## Deferred Issues

| Issue | File(s) | Plan to address |
| ----- | ------- | --------------- |
| Live Langfuse tracing smoke test | n/a (would require running Langfuse server) | Plan 04-08 (Langfuse manual smoke) |
| Per-tool budget caps in BudgetingChatModel | `llm/budgeting.py` | Plan 04-06 (BudgetTracker enforcement layer) |
| `with_structured_output` for the runtime tool registry (e.g. classifier schema in supervisor) | `llm/budgeting.py` | Plan 04-05 (supervisor LLM classifier) |

## Self-Check: PASSED

- `packages/sft-agents/src/sft_agents/llm/__init__.py` — FOUND
- `packages/sft-agents/src/sft_agents/llm/factory.py` — FOUND
- `packages/sft-agents/src/sft_agents/llm/budgeting.py` — FOUND
- `packages/sft-agents/src/sft_agents/llm/usage.py` — FOUND
- `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py` — FOUND
- `packages/sft-agents/src/sft_agents/tools/__init__.py` — FOUND
- `packages/sft-agents/src/sft_agents/tools/registry.py` — FOUND
- `docs/docs/architecture/llm-serving.md` — FOUND (253 lines; grep "tool-call-parser hermes" = 4)
- Commits `baf00d5`, `87ecf9f`, `42f3668`, `0c4dba2` — verified via `git log`
- Full test suite: 128 passed, 10 skipped (remaining Wave 0 stubs for plans 04-04..04-08)
