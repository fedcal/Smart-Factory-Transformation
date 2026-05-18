---
phase: 04-core-agentic-runtime-hitl
plan: 03
type: execute
wave: 2
depends_on: ["04-01"]
files_modified:
  - packages/sft-agents/src/sft_agents/llm/__init__.py
  - packages/sft-agents/src/sft_agents/llm/factory.py
  - packages/sft-agents/src/sft_agents/llm/budgeting.py
  - packages/sft-agents/src/sft_agents/llm/langfuse_callback.py
  - packages/sft-agents/src/sft_agents/llm/usage.py
  - packages/sft-agents/tests/test_llm_factory.py
  - packages/sft-agents/tests/test_llm_adapter.py
  - packages/sft-agents/tests/test_tool_registry.py
  - packages/sft-agents/src/sft_agents/tools/__init__.py
  - packages/sft-agents/src/sft_agents/tools/registry.py
  - docs/docs/architecture/llm-serving.md
autonomous: true
requirements: [CORE-05, CORE-06, CORE-07]
threat_refs: [T-04-LLM-Inject, T-04-Budget-Exhaust]

must_haves:
  truths:
    - "`LLM_BACKEND=ollama python -c 'from sft_agents.llm import get_llm; print(type(get_llm()).__name__)'` outputs `ChatOllama`"
    - "`LLM_BACKEND=vllm python -c 'from sft_agents.llm import get_llm; print(type(get_llm()).__name__)'` outputs `ChatOpenAI`"
    - "`LLM_BACKEND=foo` raises `RuntimeError` with message containing both `LLM_BACKEND` and `ollama|vllm`"
    - "Tool registry exports OpenAI-compatible JSON schemas via Pydantic v2 `model_json_schema(by_alias=True)`"
    - "Langfuse callback metadata passed via graph invocation `config['metadata']['langfuse_session_id']`, NOT via constructor (Pitfall §11)"
    - "vLLM tool calling requires `--tool-call-parser hermes` (documented in docs/architecture/llm-serving.md)"
  artifacts:
    - path: "packages/sft-agents/src/sft_agents/llm/factory.py"
      provides: "build_chat_model(backend, **kw) factory + get_llm() default"
      contains: "def build_chat_model"
    - path: "packages/sft-agents/src/sft_agents/llm/budgeting.py"
      provides: "BudgetingChatModel wrapper capturing usage_metadata + duration_ms"
      contains: "class BudgetingChatModel"
    - path: "packages/sft-agents/src/sft_agents/llm/langfuse_callback.py"
      provides: "get_langfuse_callback() — returns CallbackHandler or stub if LANGFUSE_HOST unset"
      contains: "def get_langfuse_callback"
    - path: "packages/sft-agents/src/sft_agents/tools/registry.py"
      provides: "export_tool_schemas + ToolRegistry"
      contains: "def export_tool_schemas"
    - path: "docs/docs/architecture/llm-serving.md"
      provides: "vLLM Qwen2.5 serve command + tool-call-parser hermes documentation"
      min_lines: 30
  key_links:
    - from: "sft_agents.llm.factory"
      to: "langchain_ollama.ChatOllama"
      via: "conditional import on LLM_BACKEND"
      pattern: "from langchain_ollama import ChatOllama"
    - from: "sft_agents.llm.factory"
      to: "langchain_openai.ChatOpenAI"
      via: "conditional import for vLLM"
      pattern: "from langchain_openai import ChatOpenAI"
    - from: "sft_agents.tools.registry"
      to: "Pydantic args_schema"
      via: "model_json_schema(by_alias=True)"
      pattern: "model_json_schema"
---

<objective>
Wave 2 Plan B: provider-agnostic LLM adapter (CORE-05 / CORE-06) + Tool registry with JSON-schema export (CORE-07) + Langfuse v3 callback wiring + vLLM serving documentation.

Purpose: single env var `LLM_BACKEND={ollama|vllm}` switches between dev (Ollama Qwen2.5-7B Q4_K_M) and prod (vLLM Qwen2.5-14B AWQ) with zero agent code changes; Tool registry exports OpenAI function-calling schemas usable by both providers; Langfuse v3 callback is opt-in via `LANGFUSE_HOST` env (otherwise stub, no tracing).

Output: 4 Python modules in `sft_agents/llm/` + Tool registry in `sft_agents/tools/registry.py` + mkdocs page documenting vLLM Qwen2.5 serve command with `--tool-call-parser hermes` (Pitfall §3).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md
@.planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md
@.planning/phases/04-core-agentic-runtime-hitl/04-PATTERNS.md
@.planning/phases/04-core-agentic-runtime-hitl/04-VALIDATION.md
@services/ot-bridge/src/svc_ot_bridge/main.py
@packages/sft-tools/src/sft_tools/timescale/query.py
@packages/sft-tools/src/sft_tools/__init__.py

<interfaces>
LLM factory contract (RESEARCH §4):

```
LLMBackend = Literal["ollama", "vllm"]

def build_chat_model(
    *, backend: LLMBackend | None = None,
    temperature: float = 0.0, seed: int = 42, **kw,
) -> BaseChatModel
```

Env-var defaults:
- `LLM_BACKEND` (default "ollama")
- `OLLAMA_MODEL` (default "qwen2.5:7b-instruct-q4_K_M")
- `OLLAMA_HOST` (default "http://localhost:11434")
- `VLLM_MODEL` (default "Qwen/Qwen2.5-14B-Instruct-AWQ")
- `VLLM_BASE_URL` (default "http://localhost:8000/v1")
- `VLLM_API_KEY` (default "dummy")
- `LANGFUSE_HOST` (default unset → stub callback)
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` (only consumed if LANGFUSE_HOST set)

vLLM-specific:
- `stream_usage=True` MUST be passed to ChatOpenAI (Pitfall §4 — streaming usage_metadata)

BudgetingChatModel:
- Wraps any BaseChatModel
- Captures usage_metadata via UsageMetadataCallbackHandler attached to invocation
- Exposes `.last_token_usage: TokenUsage` and `.last_duration_ms: int`
- Delegates `.ainvoke / .invoke / .bind_tools / .with_structured_output` to the wrapped model
- Does NOT enforce budget limits (that lands in Plan 04-06 BudgetTracker middleware); only measures

Langfuse callback (Pitfall §11 — v3 API):
- Constructor takes NO session_id (v2 API removed)
- Instead, callers pass `config["metadata"]["langfuse_session_id"]` and `config["metadata"]["langfuse_tags"]` at graph.ainvoke time
- If `LANGFUSE_HOST` unset → return None (callers must check); LangGraph accepts None entries in callbacks list

Tool registry:
- `export_tool_schemas(tools: list[BaseTool]) -> list[dict]` — OpenAI function-calling shape `[{"type":"function","function":{"name":..., "description":..., "parameters":...}}]`
- `ToolRegistry` class: `register(name: str, tool: BaseTool)` + `get(name: str) -> BaseTool` + `all() -> list[BaseTool]`
- Re-exports Phase 3 tools: `from sft_tools import ReplayCMAPSSTool, ReplayUCITool, QueryTimescaleTool` via `BUILTIN_TOOLS` constant
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 04-03-01: LLM factory + budgeting wrapper + usage helper</name>
  <files>packages/sft-agents/src/sft_agents/llm/__init__.py, packages/sft-agents/src/sft_agents/llm/factory.py, packages/sft-agents/src/sft_agents/llm/budgeting.py, packages/sft-agents/src/sft_agents/llm/usage.py, packages/sft-agents/tests/test_llm_factory.py, packages/sft-agents/tests/test_llm_adapter.py</files>
  <read_first>
    - services/ot-bridge/src/svc_ot_bridge/main.py (env-var dispatch idiom at lines 62-71 — `os.environ.get(VAR, default)` + `raise RuntimeError` for invalid values)
    - .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md §4 (build_chat_model factory code example lines 386-415; vLLM Hermes parser at 417-431; stream_usage=True Pitfall §4 at 818-821)
    - .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (Claude's Discretion lines 421-429 — model versioning convention `qwen2.5-14b-awq@vllm-0.8`)
    - packages/sft-agents/src/sft_agents/models/evidence.py (TokenUsage model created Plan 04-01)
  </read_first>
  <pattern_ref>services/ot-bridge/src/svc_ot_bridge/main.py:62-71 (env-var dispatch idiom with RuntimeError on invalid)</pattern_ref>
  <pattern_ref>packages/sft-tools/src/sft_tools/timescale/query.py:108 (os.environ.get with default pattern)</pattern_ref>
  <threat_ref>T-04-LLM-Inject, T-04-Budget-Exhaust</threat_ref>
  <behavior>
    - `build_chat_model(backend="ollama")` returns `ChatOllama` instance with `model=qwen2.5:7b-instruct-q4_K_M`, temperature=0.0, seed=42
    - `build_chat_model(backend="vllm")` returns `ChatOpenAI` with base_url=`http://localhost:8000/v1`, model=`Qwen/Qwen2.5-14B-Instruct-AWQ`, stream_usage=True
    - `build_chat_model(backend="foo")` raises `RuntimeError` with message containing "LLM_BACKEND" and "ollama|vllm"
    - `LLM_BACKEND` env var read when `backend` arg is None
    - `get_llm()` is a convenience function returning `build_chat_model()` with default kwargs
    - `BudgetingChatModel(wrapped).ainvoke(messages)` returns the response and populates `.last_token_usage` (TokenUsage with input/output/total ≥ 0) and `.last_duration_ms` (int ≥ 0)
    - BudgetingChatModel.bind_tools delegates to wrapped and returns BudgetingChatModel wrapping the result
    - Resolve model identifier helper `resolve_model_id(backend) -> str` returns e.g. "qwen2.5-7b-q4km@ollama-0.6" or "qwen2.5-14b-awq@vllm-0.8" matching EvidencePanel.model regex
    - LLM_BACKEND mismatch in test asserts via `pytest.raises(RuntimeError, match=r"LLM_BACKEND.*ollama|vllm")`
  </behavior>
  <action>
    Create `llm/usage.py` with `def extract_usage_metadata(response_or_message) -> TokenUsage` reading `usage_metadata` attribute (langchain-core 0.3+ AIMessage shape: `{input_tokens, output_tokens, total_tokens}`) and returning sft_agents.models.TokenUsage; fallback to `(0, 0, 0)` on absence. Add `def resolve_model_id(backend: str) -> str`: backend="ollama" → reads OLLAMA_MODEL env, strips suffix, builds `f"{sanitized_model}@ollama-{ollama_version}"` (use static version "0.6" — Phase 11 may dynamic-query); backend="vllm" → builds `f"{sanitized_model}@vllm-0.8"`. Pattern must match EvidencePanel.model regex `^[a-z0-9.\-]+@[a-z0-9.\-]+$` (lowercase, replace `:` with `-`, replace `/` with `-`). Create `llm/factory.py`: `LLMBackend = Literal["ollama","vllm"]`; `def build_chat_model(*, backend=None, temperature=0.0, seed=42, **kw) -> BaseChatModel`: resolve backend from env if None; if "ollama" import ChatOllama from langchain_ollama and return with model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature, seed, **kw; if "vllm" import ChatOpenAI from langchain_openai and return with model=VLLM_MODEL, base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY, temperature, seed, stream_usage=True (Pitfall §4), **kw; else raise RuntimeError(f"LLM_BACKEND must be one of ollama|vllm, got {backend!r}"). Add `def get_llm(**kw) -> BaseChatModel` convenience returning `build_chat_model(**kw)`. Add module-level logger via structlog. Create `llm/budgeting.py` with `class BudgetingChatModel`: `__init__(self, wrapped: BaseChatModel)`; `async def ainvoke(self, input, config=None, **kw)`: start = time.perf_counter_ns(); resp = await self._wrapped.ainvoke(input, config=config, **kw); self._last_duration_ms = (time.perf_counter_ns() - start) // 1_000_000; self._last_token_usage = extract_usage_metadata(resp); return resp. Properties `last_token_usage` and `last_duration_ms`. `def bind_tools(self, tools)` returns `BudgetingChatModel(self._wrapped.bind_tools(tools))`. `def with_structured_output(self, schema, **kw)` returns `BudgetingChatModel(self._wrapped.with_structured_output(schema, **kw))`. Synchronous `.invoke` delegates similarly. Create `llm/__init__.py` re-exporting `build_chat_model, get_llm, BudgetingChatModel, resolve_model_id, extract_usage_metadata`. Write `test_llm_factory.py` and `test_llm_adapter.py` replacing the Wave 0 stubs: import `from sft_agents.llm import build_chat_model, get_llm, resolve_model_id, BudgetingChatModel`. Test: `monkeypatch.setenv("LLM_BACKEND","ollama")` + `monkeypatch.setenv("OLLAMA_HOST","http://localhost:11434")` + call `build_chat_model()` and assert `type(...).__name__ == "ChatOllama"` and `temperature == 0.0` and `model.startswith("qwen2.5")`. Test: vllm branch with similar pattern asserts ChatOpenAI + stream_usage attribute true (use `.stream_usage` if accessible or `.__dict__`). Test: invalid backend raises RuntimeError matching regex. Test: resolve_model_id("ollama") matches regex `^qwen2\.5\-7b\-q4_k_m@ollama\-0\.6$` (case-insensitive — note: Pydantic regex is lowercase so output must lowercase). Test: BudgetingChatModel with FakeListChatModel from langchain_core captures duration_ms > 0 and TokenUsage with total=0 (FakeListChatModel doesn't populate usage_metadata). Test: BudgetingChatModel.bind_tools returns BudgetingChatModel instance (chain preservation).
  </action>
  <verify>
    <automated>cd packages/sft-agents && LLM_BACKEND=ollama uv run python -c "from sft_agents.llm import get_llm; m = get_llm(); print(type(m).__name__)" && LLM_BACKEND=vllm uv run python -c "from sft_agents.llm import get_llm; m = get_llm(); print(type(m).__name__)" && uv run pytest tests/test_llm_factory.py tests/test_llm_adapter.py -x -v 2>&1 | tail -15</automated>
  </verify>
  <done>LLM_BACKEND=ollama outputs ChatOllama; LLM_BACKEND=vllm outputs ChatOpenAI; both test files green (≥6 assertions covering env switch, invalid backend, resolve_model_id, BudgetingChatModel wrap)</done>
  <commit_scope>feat(04-03-llm-adapter-01): llm factory + budgeting wrapper + usage helper</commit_scope>
</task>

<task type="auto" tdd="true">
  <name>Task 04-03-02: Langfuse v3 callback + Tool registry + vLLM serving docs</name>
  <files>packages/sft-agents/src/sft_agents/llm/langfuse_callback.py, packages/sft-agents/src/sft_agents/tools/__init__.py, packages/sft-agents/src/sft_agents/tools/registry.py, packages/sft-agents/tests/test_tool_registry.py, docs/docs/architecture/llm-serving.md</files>
  <read_first>
    - .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md Pitfall §11 (Langfuse v3 SDK breaking change — session_id in metadata not constructor)
    - .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md §5 (Tool registry code example lines 437-455 — model_json_schema(by_alias=True))
    - .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md §4 vLLM serve block (lines 419-431 — --tool-call-parser hermes)
    - packages/sft-tools/src/sft_tools/__init__.py (re-export idiom for BUILTIN_TOOLS)
    - packages/sft-tools/src/sft_tools/timescale/query.py:46-84 (BaseTool subclass with args_schema — example of tool whose schema must be exported)
    - docs/ (find existing mkdocs structure for architecture section)
  </read_first>
  <pattern_ref>packages/sft-tools/src/sft_tools/__init__.py (re-export pattern for sft_agents.tools.__init__)</pattern_ref>
  <pattern_ref>packages/sft-tools/src/sft_tools/timescale/query.py:46-84 (BaseTool with Pydantic args_schema — target of export_tool_schemas)</pattern_ref>
  <threat_ref>T-04-LLM-Inject</threat_ref>
  <behavior>
    - `get_langfuse_callback()` returns None when LANGFUSE_HOST unset (no exception)
    - `get_langfuse_callback()` returns langfuse.callback.CallbackHandler instance when LANGFUSE_HOST + LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY all set
    - Module-level helper `build_invocation_metadata(thread_id, user_id=None, tags=None) -> dict` returns `{"langfuse_session_id": thread_id, "langfuse_user_id": user_id, "langfuse_tags": ["phase4"] + (tags or [])}` (Pitfall §11)
    - `export_tool_schemas([tool])` returns list with element `{"type":"function","function":{"name":..., "description":..., "parameters": <JSON schema>}}`
    - `ToolRegistry().register(name, tool)` stores; `.get(name)` retrieves; `.all()` returns list; duplicate register raises ValueError
    - `BUILTIN_TOOLS` constant from `sft_agents.tools` contains 3 Phase 3 tools: ReplayCMAPSSTool, ReplayUCITool, QueryTimescaleTool (instances, NOT classes — for schema export)
    - `docs/docs/architecture/llm-serving.md` contains vLLM serve command with `--tool-call-parser hermes` + `--enable-auto-tool-choice` + Pitfall §3 explanation
  </behavior>
  <action>
    Create `llm/langfuse_callback.py`: `def get_langfuse_callback() -> Any | None`: read env LANGFUSE_HOST; if unset return None and log info "langfuse_disabled"; else `from langfuse.callback import CallbackHandler` (langfuse v3 path; may differ — check Pitfall §11 reference); return `CallbackHandler(host=LANGFUSE_HOST, public_key=os.environ["LANGFUSE_PUBLIC_KEY"], secret_key=os.environ["LANGFUSE_SECRET_KEY"])`. Add `def build_invocation_metadata(thread_id: str, user_id: str | None = None, tags: list[str] | None = None) -> dict`: returns dict with langfuse_session_id, langfuse_user_id (if provided), langfuse_tags=["phase4"]+tags. Add `def build_invocation_config(thread_id, user_id=None, tags=None, recursion_limit=25) -> dict` returning the full LangGraph config dict per Pitfall §11 code block (configurable, callbacks=[langfuse_handler if any], metadata, recursion_limit). Wire into llm/__init__.py exports. Create `tools/registry.py`: `def export_tool_schemas(tools: list[BaseTool]) -> list[dict]` iterating tools and building OpenAI function-calling format: each entry `{"type":"function","function":{"name":tool.name,"description":tool.description,"parameters":tool.args_schema.model_json_schema(by_alias=True)}}`. Handle case where `tool.args_schema is None` by emitting empty `parameters={"type":"object","properties":{}}`. `class ToolRegistry`: `__init__(self)`: `self._tools: dict[str, BaseTool] = {}`; `register(self, name, tool)`: raise ValueError on duplicate name; `get(self, name)`: KeyError if missing; `all(self)`: return list; `export_schemas(self)`: return `export_tool_schemas(self.all())`. Create `tools/__init__.py` importing Phase 3 tools: `from sft_tools import ...` (check actual export names via sft-tools/__init__.py) — likely `from sft_tools.replay.cmapss import ReplayCMAPSSTool, from sft_tools.replay.uci import ReplayUCITool, from sft_tools.timescale.query import QueryTimescaleTool`; instantiate them: `BUILTIN_TOOLS = (ReplayCMAPSSTool(), ReplayUCITool(), QueryTimescaleTool())` (or use a `def get_builtin_tools()` factory if instantiation requires config); re-export ToolRegistry + export_tool_schemas. Write `test_tool_registry.py` replacing Wave 0 stub: import ToolRegistry + export_tool_schemas + BUILTIN_TOOLS. Test: registry.register("foo", FakeTool()) then registry.get("foo") returns it; duplicate register raises ValueError. Test: export_tool_schemas(BUILTIN_TOOLS) returns list of length 3; each entry has keys {"type","function"} and `entry["function"]["name"]` non-empty and `entry["function"]["parameters"]["type"] == "object"`. Test: schema entries valid JSON via `json.dumps(schema)` round-trip. Create `docs/docs/architecture/llm-serving.md` with sections: "## Overview" (provider-agnostic adapter overview + env vars table), "## Ollama (dev)" (qwen2.5:7b-instruct-q4_K_M install command via `ollama pull`, env vars), "## vLLM (prod) - Qwen2.5-14B AWQ" (exact serve command with `--tool-call-parser hermes` flag MANDATORY for Qwen2.5 tool calling per Pitfall §3), "## Tool Calling Notes" (Hermes-style tokens, langchain-openai response shape, FakeListChatModel for unit tests not real LLM per Pitfall §5), "## Determinism Caveats" (temperature=0+seed=42 are not sufficient cross-hardware per Pitfall §5; use FakeListChatModel for unit tests). Add references to vLLM docs URLs from RESEARCH.md Sources section. Front-matter `title: LLM Serving (Ollama dev / vLLM prod)` + `tags: [architecture, phase-04]`.
  </action>
  <verify>
    <automated>cd packages/sft-agents && uv run python -c "from sft_agents.tools import BUILTIN_TOOLS, export_tool_schemas; schemas = export_tool_schemas(list(BUILTIN_TOOLS)); print(len(schemas), [s['function']['name'] for s in schemas])" && uv run python -c "from sft_agents.llm.langfuse_callback import get_langfuse_callback, build_invocation_metadata; print(get_langfuse_callback() is None, build_invocation_metadata('t1')['langfuse_session_id'])" && uv run pytest tests/test_tool_registry.py -x -v 2>&1 | tail -10 && grep -c "tool-call-parser hermes" docs/docs/architecture/llm-serving.md</automated>
  </verify>
  <done>BUILTIN_TOOLS exports 3 schemas with valid OpenAI shape; langfuse callback returns None when LANGFUSE_HOST unset; build_invocation_metadata produces correct dict; docs/docs/architecture/llm-serving.md contains `--tool-call-parser hermes`</done>
  <commit_scope>feat(04-03-llm-adapter-02): langfuse v3 callback + tool registry + vllm serving docs</commit_scope>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM_BACKEND env var → factory dispatch | Env var (deployment input) selects code path; invalid values rejected with RuntimeError |
| LLM response → BudgetingChatModel.last_token_usage | LLM-reported token counts cross into budget enforcement; underreporting is a DoS vector |
| Tool args_schema → exported JSON schema | Pydantic model emitted to LLM as function-calling spec; structured-output validation is enforced client-side |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-LLM-Inject | Tampering | factory.py env dispatch | mitigate | RuntimeError on unrecognized LLM_BACKEND prevents arbitrary provider injection; whitelist `Literal["ollama","vllm"]` |
| T-04-LLM-Inject (tool schema poisoning) | Tampering | tools/registry.py | mitigate | export_tool_schemas reads only Pydantic args_schema (model-internal); tool definitions are first-party code; no user-supplied schemas |
| T-04-Budget-Exhaust | DoS | BudgetingChatModel | mitigate | BudgetingChatModel captures usage_metadata via stream_usage=True (Pitfall §4); enforcement by BudgetTracker middleware in Plan 04-06 |
| T-04-Budget-Exhaust (streaming usage drop) | DoS | langchain-openai streaming | mitigate | vLLM branch passes `stream_usage=True` to ChatOpenAI per Pitfall §4 |
| T-04-LLM-Inject (Langfuse session leak) | Info Disclosure | langfuse_callback metadata | mitigate | Pitfall §11 — pass session_id only via invocation config (per-call), never via global handler; if LANGFUSE_HOST unset, no tracing emitted |
</threat_model>

<verification>
- `LLM_BACKEND=ollama uv run python -c "from sft_agents.llm import get_llm; print(type(get_llm()).__name__)"` → `ChatOllama`
- `LLM_BACKEND=vllm uv run python -c "..."` → `ChatOpenAI`
- `LLM_BACKEND=foo uv run python -c "..."` → exits non-zero with RuntimeError
- `uv run pytest packages/sft-agents/tests/test_llm_factory.py tests/test_llm_adapter.py tests/test_tool_registry.py -x` green
- `grep -c "tool-call-parser hermes" docs/docs/architecture/llm-serving.md` ≥ 1
- `grep -E "langfuse_session_id" packages/sft-agents/src/sft_agents/llm/langfuse_callback.py | grep -v '^#' | wc -l` ≥ 1
</verification>

<success_criteria>
- CORE-05: single env var `LLM_BACKEND` switches between Ollama and vLLM with zero agent code changes (success criterion #3)
- CORE-06: default models locked (Qwen2.5-7B Q4_K_M for ollama, Qwen2.5-14B AWQ for vllm) with `stream_usage=True` for vLLM token capture
- CORE-07: Tool registry exports OpenAI function-calling JSON schemas via Pydantic v2 `model_json_schema(by_alias=True)` for all Phase 3 tools
- Langfuse v3 callback wired correctly (metadata via config, not constructor) — pitfall avoided
- vLLM Qwen2.5 Hermes tool parser documented (deploy-blocker prevention)
</success_criteria>

<output>
Create `.planning/phases/04-core-agentic-runtime-hitl/04-03-SUMMARY.md` documenting:
- LLM factory + env var matrix
- BudgetingChatModel wrapper behavior
- Tool registry export shape (sample schema)
- Langfuse v3 vs v2 API delta (Pitfall §11)
</output>