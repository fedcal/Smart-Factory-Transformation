---
phase: 04-core-agentic-runtime-hitl
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - packages/sft-agents/pyproject.toml
  - packages/sft-agents/src/sft_agents/__init__.py
  - packages/sft-agents/src/sft_agents/sdk/__init__.py
  - packages/sft-agents/src/sft_agents/sdk/agent.py
  - packages/sft-agents/src/sft_agents/sdk/tool.py
  - packages/sft-agents/src/sft_agents/sdk/memory.py
  - packages/sft-agents/src/sft_agents/sdk/policy.py
  - packages/sft-agents/src/sft_agents/models/__init__.py
  - packages/sft-agents/src/sft_agents/models/evidence.py
  - packages/sft-agents/src/sft_agents/models/audit.py
  - packages/sft-agents/src/sft_agents/models/approval.py
  - packages/sft-agents/src/sft_agents/models/proposed_action.py
  - packages/sft-agents/src/sft_agents/models/budget.py
  - packages/sft-agents/src/sft_agents/models/memory_record.py
  - packages/sft-agents/src/sft_agents/models/enums.py
  - packages/sft-agents/tests/__init__.py
  - packages/sft-agents/tests/conftest.py
  - packages/sft-agents/tests/test_sdk_interfaces.py
  - packages/sft-agents/tests/test_evidence_panel.py
  - packages/sft-agents/tests/test_audit_record.py
  - packages/sft-agents/tests/test_approval_request.py
  - packages/sft-agents/tests/test_budget_snapshot.py
  - packages/sft-agents/tests/test_migrations.py
  - packages/sft-agents/tests/test_llm_adapter.py
  - packages/sft-agents/tests/test_supervisor.py
  - packages/sft-agents/tests/test_hitl_cycle.py
  - packages/sft-agents/tests/test_escalation.py
  - packages/sft-agents/tests/test_governor.py
  - packages/sft-agents/tests/test_budget.py
  - packages/sft-agents/tests/test_replay.py
  - packages/sft-agents/tests/test_safety_interlock.py
  - packages/sft-agents/tests/test_audit_constraints.py
  - packages/sft-agents/tests/test_rate_limit_audit_query.py
  - packages/sft-agents/tests/test_recursion_limit.py
  - packages/sft-agents/tests/test_tool_registry.py
  - packages/sft-agents/tests/test_llm_factory.py
  - packages/sft-agents/tests/test_public_api.py
autonomous: true
requirements: [CORE-01, CORE-02, HITL-06, HITL-07]
threat_refs: [T-04-Audit-Tamper, T-04-Checkpoint-PII, T-04-LLM-Inject]

must_haves:
  truths:
    - "Public API `from sft_agents import Agent, Tool, Memory, Policy, EvidencePanel, AuditRecord, ApprovalRequest, BudgetSnapshot, ProposedAction, Tier, Decision, ActionType` resolves with no ImportError"
    - "Every Pydantic model frozen + extra=forbid; mutation raises ValidationError"
    - "Every timestamp field rejects naive datetime via field_validator"
    - "EvidencePanel.input_summary max 500 chars with input_truncated flag"
    - "AuditRecord.motivation is required when decision starts with hitl_ (HITL-07)"
    - "All Wave 0 test stub files import target symbols, marked pytest.skip until implementation lands"
  artifacts:
    - path: "packages/sft-agents/src/sft_agents/sdk/agent.py"
      provides: "Agent ABC interface"
      contains: "class Agent(ABC)"
    - path: "packages/sft-agents/src/sft_agents/models/evidence.py"
      provides: "EvidencePanel + ToolCall + RagCitation + TokenUsage"
      contains: "class EvidencePanel(BaseModel)"
    - path: "packages/sft-agents/src/sft_agents/models/audit.py"
      provides: "AuditRecord Pydantic projection"
      contains: "class AuditRecord(BaseModel)"
    - path: "packages/sft-agents/src/sft_agents/models/approval.py"
      provides: "ApprovalRequest, ApprovalDecision, Tier enum"
      contains: "class ApprovalRequest(BaseModel)"
    - path: "packages/sft-agents/src/sft_agents/models/enums.py"
      provides: "Tier, Decision, ActionType enums"
      contains: "class Tier(str, Enum)"
    - path: "packages/sft-agents/tests/conftest.py"
      provides: "shared fixtures: mock_llm, mock_pool, mock_nats, frozen_dt"
      min_lines: 40
  key_links:
    - from: "packages/sft-agents/src/sft_agents/__init__.py"
      to: "sdk + models submodules"
      via: "flat re-export"
      pattern: "from sft_agents.sdk"
    - from: "packages/sft-agents/tests/*"
      to: "production symbols"
      via: "import-then-skip"
      pattern: "from sft_agents import"
---

<objective>
Foundation Wave 1: build the `sft-agents` SDK skeleton — Pydantic v2 models (EvidencePanel, AuditRecord, ApprovalRequest, BudgetSnapshot, ProposedAction, ToolCall, RagCitation, TokenUsage, MemoryRecord) + Tier/Decision/ActionType enums + Agent/Tool/Memory/Policy ABC interfaces + complete Wave 0 test stub set (12 stub files listed in VALIDATION.md).

Purpose: lock the contracts every downstream plan (02-08) compiles against. No runtime logic — only types, interfaces, and stubs that import target symbols (type-driven scaffolding).

Output: `packages/sft-agents/src/sft_agents/{sdk,models}/` populated; `packages/sft-agents/tests/` Wave 0 stub set in place; pyproject deps added; unit tests for models green.
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
@packages/sft-tools/src/sft_tools/replay/models.py
@services/ot-bridge/src/svc_ot_bridge/models.py
@packages/sft-tools/src/sft_tools/timescale/query.py
@packages/sft-tools/src/sft_tools/__init__.py

<interfaces>
Locked from RESEARCH.md §1 Code Examples + CONTEXT.md D-56/D-57/D-60.

Public API (final) per CONTEXT.md Claude's Discretion:
```python
from sft_agents import (
    Agent, Tool, Memory, Policy,         # ABC
    Supervisor, ClusterSubgraph,         # runtime builders (Plan 04-05 fills)
    BudgetTracker, EvidencePanel,        # middleware + schema
    AuditRecord, ApprovalRequest,        # schema
    ProposedAction, BudgetSnapshot,      # schema
    Tier, Decision, ActionType,          # enums
)
```

EvidencePanel shape (HITL-06, RESEARCH §1 Code Examples):
- input_summary: str max_length=500
- input_truncated: bool = False
- tool_calls: list[ToolCall] default []
- rag_citations: list[RagCitation] default [] (Phase 5 populates)
- confidence: float ge=0 le=1
- model: str pattern r"^[a-z0-9.\-]+@[a-z0-9.\-]+$"
- prompt_hash: str pattern r"^[a-f0-9]{64}$"
- tokens: TokenUsage
- duration_ms: int ge=0

AuditRecord (Pydantic projection of audit.actions DDL, D-56):
- id, ts, action_id (UUID), agent_id, thread_id, cluster, action_type
- evidence_panel: EvidencePanel
- decision: Decision enum
- decision_actor: str | None
- motivation: str | None — validator: required iff decision starts with "hitl_"
- budget_snapshot: BudgetSnapshot
- approval_id: UUID | None (FK to hitl.approvals; required iff hitl_*, NULL for auto)

Tier enum: operator | supervisor | manager | safety_interlock
Decision enum: auto | hitl_operator | hitl_supervisor | hitl_manager | interlock_reject | rolled_back | timed_out | governor_alert | escalated
ActionType enum: WRITE_PLC_SETPOINT | ACTUATOR_COMMAND | FIRMWARE_DEPLOY | NETWORK_ACL_CHANGE | GRAPH_RECURSION_REVIEW | GOVERNOR_ALERT + extensible

ApprovalRequest (Pydantic projection of hitl.approvals DDL, D-55):
- id, agent_id, thread_id, tier (Tier), action_type, payload_json (dict)
- status: pending | approved | rejected | escalated | timed_out
- created_at, sla_deadline (datetime tz-aware), decided_at, decided_by, decision_json
- escalated_to_id: UUID | None

ProposedAction:
- id: UUID — deterministic from sha256(thread_id + action_type + canonical_json(args)) per Pitfall 6
- action_type: ActionType
- target_subject: str | None — NATS subject if action publishes
- args: dict

BudgetSnapshot (D-60):
- tokens_input, tokens_output, tokens_total: int ge=0
- cost_usd_simulated: float ge=0
- duration_ms: int ge=0
- limit_tokens, limit_cost_usd, limit_duration_s: int|float
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 04-01-01: pyproject deps + test scaffold conftest</name>
  <files>packages/sft-agents/pyproject.toml, packages/sft-agents/tests/__init__.py, packages/sft-agents/tests/conftest.py, packages/sft-agents/project.json</files>
  <read_first>
    - packages/sft-agents/pyproject.toml (current empty deps list)
    - services/ot-bridge/pyproject.toml (reference layout: hatchling + uv.sources workspace + asyncio_mode auto)
    - packages/sft-tools/tests/test_query_timescale.py (class-grouped tests + AsyncMock + patch idioms)
    - tests/conftest.py (root markers: integration, load — register at package level too)
  </read_first>
  <pattern_ref>services/ot-bridge/pyproject.toml:1-44 (project layout, uv workspace sources, pytest asyncio_mode=auto)</pattern_ref>
  <pattern_ref>packages/sft-tools/tests/test_query_timescale.py:19-95 (class-grouped tests, AsyncMock, patch fixtures)</pattern_ref>
  <threat_ref>T-04-Checkpoint-PII</threat_ref>
  <behavior>
    - `uv sync` in packages/sft-agents resolves without conflicts
    - `pytest packages/sft-agents/tests -k "conftest"` collects without error
    - `import sft_agents` works in test context after dependency add
  </behavior>
  <action>
    Extend `packages/sft-agents/pyproject.toml`: add `[project] dependencies = ["langgraph>=0.4,<0.5", "langgraph-checkpoint-postgres>=3.1,<4", "langchain-core>=0.3,<0.4", "langchain-ollama>=0.3,<0.4", "langchain-openai>=0.3,<0.4", "langfuse>=3,<4", "asyncpg>=0.30,<0.31", "nats-py>=2.7,<2.10", "pydantic>=2.9,<3", "structlog>=24.4", "pyyaml>=6"]`. Add `[project.optional-dependencies] dev = ["pytest>=8", "pytest-asyncio>=0.24", "pytest-mock>=3.14"]`. Add `[tool.uv.sources] sft-tools = {workspace = true}, sft-assets = {workspace = true}, sft-domain = {workspace = true}, sft-contracts = {workspace = true}` plus add those to dependencies. Add `[tool.pytest.ini_options] asyncio_mode = "auto"` + `markers = ["integration: requires docker compose / testcontainers", "load: long-running load test"]`. Create `packages/sft-agents/tests/__init__.py` empty. Create `packages/sft-agents/tests/conftest.py` with fixtures: `frozen_dt()` returns `datetime(2026,5,18, tzinfo=timezone.utc)`; `mock_pool()` returns AsyncMock simulating `asyncpg.Pool` (acquire context manager + fetchrow/execute AsyncMock methods); `mock_nats_js()` returns AsyncMock simulating NATS JetStream context with `publish` AsyncMock; `mock_llm()` returns `FakeListChatModel` from `langchain_core.language_models.fake_chat_models` with default response list; `mock_checkpointer()` returns AsyncMock with `aget_tuple`, `aput`, `setup` AsyncMock methods. Register markers in `project.json` `test` target so `uv run pytest` picks them up.
  </action>
  <verify>
    <automated>cd packages/sft-agents && uv sync --frozen 2>&1 | tail -5 && uv run pytest tests/ --collect-only -q 2>&1 | tail -10</automated>
  </verify>
  <done>uv sync succeeds; pytest --collect-only shows 0 errors; conftest.py contains fixtures `frozen_dt`, `mock_pool`, `mock_nats_js`, `mock_llm`, `mock_checkpointer`</done>
  <commit_scope>feat(04-01-sdk-foundation-01): scaffold sft-agents pyproject deps + tests conftest</commit_scope>
</task>

<task type="auto" tdd="true">
  <name>Task 04-01-02: Pydantic models (evidence, audit, approval, budget, proposed_action, enums)</name>
  <files>packages/sft-agents/src/sft_agents/models/__init__.py, packages/sft-agents/src/sft_agents/models/enums.py, packages/sft-agents/src/sft_agents/models/evidence.py, packages/sft-agents/src/sft_agents/models/audit.py, packages/sft-agents/src/sft_agents/models/approval.py, packages/sft-agents/src/sft_agents/models/proposed_action.py, packages/sft-agents/src/sft_agents/models/budget.py, packages/sft-agents/src/sft_agents/models/memory_record.py, packages/sft-agents/tests/test_evidence_panel.py, packages/sft-agents/tests/test_audit_record.py, packages/sft-agents/tests/test_approval_request.py, packages/sft-agents/tests/test_budget_snapshot.py, packages/sft-agents/tests/test_audit_constraints.py</files>
  <read_first>
    - packages/sft-tools/src/sft_tools/replay/models.py (frozen + extra=forbid + tz-aware validator pattern)
    - services/ot-bridge/src/svc_ot_bridge/models.py (Literal source enum + dual tz validator at lines 22-72)
    - .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md lines 130-200 (D-55 hitl.approvals DDL, D-56 audit.actions DDL, EvidencePanel definition)
    - .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md §1 Code Examples (EvidencePanel illustrative — lines 957-1007)
  </read_first>
  <pattern_ref>packages/sft-tools/src/sft_tools/replay/models.py:25-63 (ReplayRecord — exact analog for Pydantic frozen+tz-aware)</pattern_ref>
  <pattern_ref>services/ot-bridge/src/svc_ot_bridge/models.py:22-72 (SensorEvent — Literal enum + tz validator)</pattern_ref>
  <threat_ref>T-04-Checkpoint-PII, T-04-Audit-Tamper, T-04-LLM-Inject</threat_ref>
  <behavior>
    - EvidencePanel rejects naive datetime in ToolCall.ts, RagCitation.retrieved_at (raises ValidationError)
    - EvidencePanel.input_summary length > 500 raises ValidationError; input_truncated bool defaults False
    - EvidencePanel.model rejects pattern not matching `name@runtime` (e.g. "raw-model" without @ fails)
    - EvidencePanel.prompt_hash rejects non-sha256 (must be 64 hex chars)
    - AuditRecord validator: decision in {hitl_operator, hitl_supervisor, hitl_manager} requires non-empty motivation (HITL-07)
    - AuditRecord validator: decision in hitl_* requires approval_id not None
    - AuditRecord validator: decision == "auto" requires approval_id is None
    - ApprovalRequest sla_deadline must be tz-aware (raises ValidationError on naive)
    - ApprovalRequest status default "pending"; transitions to {approved, rejected, escalated, timed_out} allowed
    - ProposedAction.id is deterministic: same (thread_id, action_type, args) produces same UUID (sha256-hash-based) per Pitfall 6
    - BudgetSnapshot tokens_total ≥ tokens_input + tokens_output - 1 (consistency check, allow rounding)
    - All models reject `extra` fields (ValidationError on unknown key)
    - All models reject mutation (ValidationError on setattr after construct)
  </behavior>
  <action>
    Create `packages/sft-agents/src/sft_agents/models/enums.py` with `Tier(str, Enum) = {OPERATOR=operator, SUPERVISOR=supervisor, MANAGER=manager, SAFETY_INTERLOCK=safety_interlock}`, `Decision(str, Enum) = {AUTO=auto, HITL_OPERATOR=hitl_operator, HITL_SUPERVISOR=hitl_supervisor, HITL_MANAGER=hitl_manager, INTERLOCK_REJECT=interlock_reject, ROLLED_BACK=rolled_back, TIMED_OUT=timed_out, GOVERNOR_ALERT=governor_alert, ESCALATED=escalated}`, `ApprovalStatus(str, Enum) = {PENDING, APPROVED, REJECTED, ESCALATED, TIMED_OUT}`, `ActionType(str, Enum)` containing WRITE_PLC_SETPOINT, ACTUATOR_COMMAND, FIRMWARE_DEPLOY, NETWORK_ACL_CHANGE, GRAPH_RECURSION_REVIEW, GOVERNOR_ALERT (extensible — leave room for cluster-specific via str values). Create `evidence.py` with classes ToolCall(name, args:dict, result:dict|None, duration_ms ge=0, ts:datetime), RagCitation(source_uri, snippet max_length=2000, score ge=0 le=1, retrieved_at:datetime), TokenUsage(input, output, total: int ge=0), EvidencePanel(input_summary max_length=500, input_truncated:bool=False, tool_calls=[], rag_citations=[], confidence ge=0 le=1, model pattern r"^[a-z0-9.\-]+@[a-z0-9.\-]+$", prompt_hash pattern r"^[a-f0-9]{64}$", tokens:TokenUsage, duration_ms ge=0). Each model frozen+extra=forbid with `_tz_aware` field_validator on all datetime fields. Create `audit.py` AuditRecord matching D-56 DDL columns (id:UUID, ts:datetime, action_id:UUID, agent_id, thread_id, cluster, action_type, evidence_panel:EvidencePanel, decision:Decision, decision_actor:str|None, motivation:str|None, budget_snapshot:BudgetSnapshot, approval_id:UUID|None) with `model_validator(mode="after")` enforcing: decision.value.startswith("hitl_") implies motivation truthy AND approval_id not None; decision == AUTO implies approval_id is None (per CONTEXT.md Claude's Discretion line 431). Create `approval.py` ApprovalRequest(id, agent_id, thread_id, tier:Tier, action_type, payload_json:dict, status:ApprovalStatus=PENDING, created_at:datetime, sla_deadline:datetime, decided_at:datetime|None, decided_by:str|None, decision_json:dict|None, escalated_to_id:UUID|None) + ApprovalDecision(decision:Literal["approve","reject","escalate"], motivation:str min_length=1, decided_by:str). Create `proposed_action.py` ProposedAction with classmethod `from_payload(cls, thread_id, action_type, args, target_subject=None)` deriving `id = UUID(sha256_hex(thread_id + action_type + json.dumps(args, sort_keys=True))[:32])` for idempotency (Pitfall 6). Create `budget.py` BudgetSnapshot + BudgetLimits per D-60. Create `memory_record.py` MemoryRecord with source_uri, content, score, ts. Re-export from `models/__init__.py`. Write test files `test_evidence_panel.py` (10+ assertions: tz-aware reject, length cap, pattern match, frozen, extra=forbid), `test_audit_record.py` (motivation-required validator, approval_id matrix), `test_approval_request.py` (status enum, tz-aware), `test_budget_snapshot.py` (limits, ge=0), `test_audit_constraints.py` (HITL-07 motivation matrix). All tests use Pydantic ValidationError import via `from pydantic import ValidationError`.
  </action>
  <verify>
    <automated>cd packages/sft-agents && uv run pytest tests/test_evidence_panel.py tests/test_audit_record.py tests/test_approval_request.py tests/test_budget_snapshot.py tests/test_audit_constraints.py -x -v 2>&1 | tail -20</automated>
  </verify>
  <done>5 model test files green; 25+ assertions covering frozen/extra=forbid/tz-aware/pattern/motivation-required; ProposedAction.from_payload returns identical UUID for identical input on 2 calls</done>
  <commit_scope>feat(04-01-sdk-foundation-02): pydantic v2 models (evidence, audit, approval, budget, proposed_action, enums) + tests</commit_scope>
</task>

<task type="auto" tdd="true">
  <name>Task 04-01-03: ABC interfaces (Agent/Tool/Memory/Policy) + public API + Wave 0 stub set</name>
  <files>packages/sft-agents/src/sft_agents/sdk/__init__.py, packages/sft-agents/src/sft_agents/sdk/agent.py, packages/sft-agents/src/sft_agents/sdk/tool.py, packages/sft-agents/src/sft_agents/sdk/memory.py, packages/sft-agents/src/sft_agents/sdk/policy.py, packages/sft-agents/src/sft_agents/__init__.py, packages/sft-agents/tests/test_sdk_interfaces.py, packages/sft-agents/tests/test_public_api.py, packages/sft-agents/tests/test_migrations.py, packages/sft-agents/tests/test_llm_adapter.py, packages/sft-agents/tests/test_llm_factory.py, packages/sft-agents/tests/test_supervisor.py, packages/sft-agents/tests/test_hitl_cycle.py, packages/sft-agents/tests/test_escalation.py, packages/sft-agents/tests/test_governor.py, packages/sft-agents/tests/test_budget.py, packages/sft-agents/tests/test_replay.py, packages/sft-agents/tests/test_safety_interlock.py, packages/sft-agents/tests/test_rate_limit_audit_query.py, packages/sft-agents/tests/test_recursion_limit.py, packages/sft-agents/tests/test_tool_registry.py</files>
  <read_first>
    - packages/sft-tools/src/sft_tools/timescale/query.py (BaseTool subclass + async-first NotImplementedError pattern lines 46-84)
    - packages/sft-tools/src/sft_tools/__init__.py (re-export idiom)
    - .planning/phases/04-core-agentic-runtime-hitl/04-VALIDATION.md (Wave 0 stubs list — 12 stub files required before any Wave 2+ implementation)
    - .planning/phases/04-core-agentic-runtime-hitl/04-RESEARCH.md §1 SDK skeleton layout
  </read_first>
  <pattern_ref>packages/sft-tools/src/sft_tools/timescale/query.py:46-84 (BaseTool subclass; _run raises NotImplementedError to force _arun)</pattern_ref>
  <pattern_ref>packages/sft-tools/src/sft_tools/__init__.py (flat re-export — replica for sft_agents/__init__.py)</pattern_ref>
  <threat_ref>T-04-LLM-Inject</threat_ref>
  <behavior>
    - `from sft_agents import Agent, Tool, Memory, Policy, EvidencePanel, AuditRecord, ApprovalRequest, BudgetSnapshot, ProposedAction, Tier, Decision, ActionType, ApprovalStatus, ApprovalDecision` works without ImportError
    - Agent ABC has abstract methods `async def step(self, state) -> dict` and properties `name: str`, `cluster: str`
    - Tool ABC extends langchain_core.tools.BaseTool with `_run` raising NotImplementedError + abstract `async def _arun`
    - Memory ABC has abstract `async def query(query, k=5, filters=None) -> list[MemoryRecord]` + `async def store(record) -> str`
    - Policy ABC has abstract `async def pre_tool_check(action: ProposedAction) -> None` + `async def post_decision_check(record: AuditRecord) -> None`
    - Concrete subclass that omits abstract method raises TypeError on instantiation
    - All 16 Wave 0 stub test files exist; each imports the symbol it will test and contains 1+ `pytest.mark.skip(reason="W0 stub — Plan 04-XX implements")` test stub
  </behavior>
  <action>
    Create `sdk/agent.py` with `class Agent(ABC)` having `name`, `cluster`, `tools`, `memory`, `policy` instance attributes (no Pydantic — runtime composition class) + `@abstractmethod async def step(self, state: dict) -> dict` + concrete helper `async def execute(self, state) -> dict` calling `step`. Create `sdk/tool.py` with `class Tool(BaseTool, ABC)` from langchain_core.tools.BaseTool subclassing and overriding `_run` to `raise NotImplementedError("Tool requires async; use _arun")` and declaring `@abstractmethod async def _arun(self, *args, **kwargs)`. Create `sdk/memory.py` with `class Memory(ABC)` + `@abstractmethod async def query(self, query: str, k: int = 5, filters: dict | None = None) -> list[MemoryRecord]` + `@abstractmethod async def store(self, record: MemoryRecord) -> str`. Create `sdk/policy.py` with `class Policy(ABC)` + abstract `async def pre_tool_check(self, action: ProposedAction) -> None` + `async def post_decision_check(self, record: AuditRecord) -> None` (default no-op `pass`). `sdk/__init__.py` re-exports Agent, Tool, Memory, Policy. Update `packages/sft-agents/src/sft_agents/__init__.py` to flat re-export: from sft_agents.sdk import Agent, Tool, Memory, Policy; from sft_agents.models import EvidencePanel, AuditRecord, ApprovalRequest, ApprovalDecision, ApprovalStatus, BudgetSnapshot, BudgetLimits, ProposedAction, ToolCall, RagCitation, TokenUsage, MemoryRecord, Tier, Decision, ActionType. `__version__ = "0.1.0"` exported. Write `test_sdk_interfaces.py` with assertions: Agent ABC; instantiating subclass missing `step` raises TypeError; Tool subclass with only `_arun` is concrete; Memory subclass with `query+store` is concrete; Policy default `post_decision_check` returns None. Write `test_public_api.py` containing `assert hasattr(sft_agents, name)` for all 14 names listed; plus `assert sft_agents.__version__ == "0.1.0"`. Create the 12 Wave 0 stub files per VALIDATION.md list (test_migrations.py, test_llm_adapter.py, test_llm_factory.py, test_supervisor.py, test_hitl_cycle.py, test_escalation.py, test_governor.py, test_budget.py, test_replay.py, test_safety_interlock.py, test_rate_limit_audit_query.py, test_recursion_limit.py, test_tool_registry.py). Each stub file: (1) imports the target symbol it will test (e.g. test_llm_factory.py: `from sft_agents.llm.factory import build_chat_model`), and (2) contains a single test function `def test_<name>_stub(): pytest.skip(reason="Wave 0 stub — Plan 04-XX implements")`. For test_recursion_limit.py and test_tool_registry.py, mark `pytest.importorskip("langgraph")` then skip — the target modules don't exist yet but `pytest.skip` body shouldn't import-error at collection time; resolve via top-level `pytest.importorskip("sft_agents.runtime.supervisor", reason="Plan 04-05")` followed by skip body. **Stub-file template clarification (W2):** The Wave 0 stub files listed above (test_migrations.py through test_tool_registry.py) are GENERATED FROM A SINGLE TEMPLATE-DRIVEN LOOP — not hand-written 13-by-13. The executor writes ONE template helper (e.g. `_make_stub(target_module: str, target_symbol: str, owner_plan: str) -> str` returning the file body), then iterates over a list of `(filename, target_module, target_symbol, owner_plan)` tuples writing each file. Body shell is identical across stubs: shebang + `from __future__ import annotations` + `import pytest` + module-level `pytest.importorskip(target_module, reason=f'W0 stub — {owner_plan} implements')` + single `def test_<slug>_stub(): pytest.skip(reason=f'Wave 0 stub — {owner_plan} implements')`. Only the 4 tuple values differ per file. This is mechanically uniform, not 13 independent designs — read the files_modified list as 'N entries × 1 template' rather than N hand-written stubs.

    Cross-cutting acceptance: every new file has `from __future__ import annotations` at top; pre-commit hooks (ruff, mypy strict) pass.
  </action>
  <verify>
    <automated>cd packages/sft-agents && uv run python -c "from sft_agents import Agent, Tool, Memory, Policy, EvidencePanel, AuditRecord, ApprovalRequest, ApprovalDecision, ApprovalStatus, BudgetSnapshot, BudgetLimits, ProposedAction, ToolCall, RagCitation, TokenUsage, MemoryRecord, Tier, Decision, ActionType; print('OK', len([Agent, Tool, Memory, Policy, EvidencePanel, AuditRecord, ApprovalRequest, ApprovalDecision, ApprovalStatus, BudgetSnapshot, BudgetLimits, ProposedAction, ToolCall, RagCitation, TokenUsage, MemoryRecord, Tier, Decision, ActionType]))" && uv run pytest tests/ -x --tb=short 2>&1 | tail -15</automated>
  </verify>
  <done>Public API imports 19+ symbols; test_sdk_interfaces + test_public_api green; all 12 Wave 0 stub files exist with pytest.skip body; `find packages/sft-agents/tests -name "test_*.py" | wc -l` >= 17</done>
  <commit_scope>feat(04-01-sdk-foundation-03): abc interfaces (Agent/Tool/Memory/Policy) + public api + wave 0 stubs</commit_scope>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM-text → AuditRecord.evidence_panel | Untrusted LLM output crosses into PG-persisted audit (sanitization via Pydantic length caps + regex patterns) |
| Caller-args → ProposedAction.args | Caller-supplied dict crosses into deterministic UUID derivation (idempotency hinge) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-Checkpoint-PII | Info Disclosure | EvidencePanel.input_summary | mitigate | max_length=500 + truncate flag; Phase 11 adds redactor middleware (deferred per CONTEXT.md scope_boundaries) |
| T-04-LLM-Inject | Tampering | EvidencePanel.model regex + EvidencePanel.prompt_hash regex | mitigate | Pydantic pattern validator rejects malformed model identifiers and non-sha256 hashes; freezes the audit record |
| T-04-Audit-Tamper | Tampering/Repudiation | AuditRecord (Pydantic projection) | mitigate | frozen=True + extra=forbid + motivation-required model_validator for hitl_* decisions (HITL-07); DB-side enforcement lands in Plan 04-02 (REVOKE) |
| T-04-Audit-Tamper (FK) | Tampering | AuditRecord.approval_id consistency | mitigate | model_validator: hitl_* implies approval_id NOT NULL; auto implies approval_id NULL (Claude's Discretion line 431) |
</threat_model>

<verification>
- All Wave 0 stub files in `packages/sft-agents/tests/` exist and import their target symbol
- `uv run pytest packages/sft-agents/tests -x` green (model tests run; stub tests skip cleanly)
- `uv run python -c "import sft_agents; print(sft_agents.__version__)"` outputs `0.1.0`
- `ruff check packages/sft-agents/src` exit 0
- `find packages/sft-agents/tests -name 'test_*.py' | wc -l` >= 17
</verification>

<success_criteria>
- Foundation Wave 1 unblocks Waves 2-4: every downstream plan can `from sft_agents import <X>` without scaffolding gaps
- 4 ABC interfaces (Agent, Tool, Memory, Policy) instantiable from concrete subclasses; abstract enforcement validated via TypeError
- 9 Pydantic v2 models (EvidencePanel, AuditRecord, ApprovalRequest, ApprovalDecision, BudgetSnapshot, BudgetLimits, ProposedAction, ToolCall, RagCitation, TokenUsage, MemoryRecord) with frozen+extra=forbid+tz-aware on every datetime
- HITL-06 contract stable: EvidencePanel shape locked for Phase 5 RAG to populate `rag_citations[]`
- HITL-07 mechanically enforced: motivation field required on hitl_* decisions via model_validator
- Wave 0 stubs cover all 11 implementation-pending requirements (CORE-03..10, HITL-01..05, HITL-08..10)
</success_criteria>

<output>
Create `.planning/phases/04-core-agentic-runtime-hitl/04-01-SUMMARY.md` documenting:
- Final public API symbol count
- Pydantic model count and field validators added
- Wave 0 stub files created
- Any deviation from D-56 schema (should be none)
</output>