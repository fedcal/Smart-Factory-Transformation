---
phase: 4
phase_name: Core Agentic Runtime & HITL
phase_slug: core-agentic-runtime-hitl
discussed_at: "2026-05-18"
requirements: [CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06, CORE-07, CORE-08, CORE-09, CORE-10, HITL-01, HITL-02, HITL-03, HITL-04, HITL-05, HITL-06, HITL-07, HITL-08, HITL-09, HITL-10]
depends_on_phases: [1, 3]
---

# Phase 4 Context — Core Agentic Runtime & HITL

<domain>
**What this phase delivers:** the orchestrator backbone on which every domain agent (Phase 6-9) will plug in.

Concretely:
- A **`sft-agents` SDK** (`packages/sft-agents/`) with uniform `Agent`, `Tool`, `Memory`, `Policy` interfaces (CORE-01)
- A **LangGraph supervisor + 5 cluster subgraphs** (Ops, Maintenance, Knowledge-Curation, Knowledge-Training, Supply — D-53 deviates from ROADMAP "4 clusters") with hybrid routing (rules + LLM fallback, D-54), each cluster a `StateGraph` skeleton with placeholder child nodes for the 16 agents Phase 1 scaffolded
- A **PostgreSQL checkpointer** wired (CORE-04) with `thread_id` isolation + cross-session resume (success criterion #4: paused HITL survives restart)
- A **provider-agnostic LLM adapter** (`langchain-ollama` for dev / `langchain-openai` for vLLM prod) — single env var `LLM_BACKEND={ollama|vllm}` selects (CORE-05/06)
- A **full HITL `interrupt()`-to-resume loop** (HITL-01): agent proposes → `interrupt()` → state persists PG → NATS notify → human decides → `Command(resume=)` resumes → audit dual-write
- A **4-tier escalation model** (Operator/Supervisor/Manager/Safety Interlock) with auto-escalation timers 2min/15min/1h (D-57), Safety Interlock as manual-only terminal tier with NATS-command whitelist YAML (D-58)
- An **immutable audit trail**: dual-write sync PG `audit.actions` (source-of-truth, 7y retention) + NATS `AUDIT_STREAM` (replica, 90d retention, D-56)
- An **EvidencePanel** Pydantic schema attached to every AI decision (HITL-06): input + tool_calls[] + rag_citations[] (Phase 5 placeholder) + confidence + model + prompt_hash
- A **budget/quota tracker** as LangGraph middleware node + PG storage (D-60), enforced per thread_id + per agent
- A **replay tool** for deterministic re-execution from checkpoint + audit log (CORE-10)
- An **approval rate governor** firing Manager alert when >80% of last-hour approvals were auto-approved (D-58, sliding window)

This phase does NOT build individual agent business logic (deferred Phase 6-9 per cluster), does NOT build Qdrant retrieval (Phase 5), does NOT build the operator UI (Phase 10-11).
</domain>

<canonical_refs>
Files downstream agents (researcher, planner) MUST consult:

- `.planning/ROADMAP.md` — Phase 4 goal + 5 success criteria + 20 requirements (note: ROADMAP says "four cluster subgraph skeletons"; D-53 overrides to 5)
- `.planning/REQUIREMENTS.md` lines for CORE-01..10 + HITL-01..10
- `.planning/PROJECT.md` — core value "ogni decisione AI passa per umano informato"; HITL is the heart of the product
- `.planning/research/STACK.md` — LangGraph 0.4+ locked, langgraph-checkpoint-postgres 3.1.0, langchain-ollama 0.3+, langchain-openai 0.3+ (vLLM OpenAI-compatible), Langfuse v3 self-hosted
- `.planning/research/ARCHITECTURE.md` — C4 supervisor + cluster pattern (see `## Component Diagram`)
- `.planning/phases/01-foundation-monorepo/01-CONTEXT.md` — D-02 packages layout; D-09 docker-compose (PG already up); `apps/agents/{ops,maintenance,knowledge,supply}/` 16 agent scaffolds present
- `.planning/phases/03-it-ot-simulation-layer/03-CONTEXT.md` — D-52 NATS subject hierarchy (`sensor.events.*`, `audit.ot.*`); D-46 ReplayRecord schema (re-used by replay tool in CORE-10); D-49 TimescaleDB hypertable (audit table sibling)
- `.planning/phases/02-domain-modeling-synthetic-corpus/02-CONTEXT.md` — D-21 5 process families (informs Ops cluster); D-25 SOP `status: reviewed` gate (informs Phase 5+ knowledge retrieval; Phase 4 EvidencePanel `rag_citations[]` is the data contract)
- `packages/sft-agents/{pyproject.toml,project.json,src/sft_agents/__init__.py}` — Phase 1 scaffold; Phase 4 fills it
- `packages/sft-tools/src/sft_tools/{replay/*,timescale/query.py}` — Phase 3 — tools sft-agents can import; query_timescale used by audit replay (CORE-10)
- `packages/sft-assets/src/sft_assets/{models.py,loader.py}` — Phase 3 — agents query asset metadata via Asset/Tag
- `services/ot-bridge/src/svc_ot_bridge/` — Phase 3 — audit publisher (`audit.ot.bridge`) is the precedent for `audit.actions.*` ot-bridge-like dual-write
- `infra/migrations/timescale/001_create_sensor_events.sql` — Phase 3 migration pattern (idempotent DO $$ blocks); Phase 4 adds `002_create_hitl_approvals.sql` + `003_create_audit_actions.sql` + `004_create_budget_executions.sql`
- `docs/assumptions/register.yaml` — A-013..A-018 (HITL constraints + GDPR PII boundaries) — already cover Phase 4 invariants

No external SPEC.md or ADR exists for Phase 4 — this CONTEXT.md is source of truth.
</canonical_refs>

<code_context>
**Already exists from Phase 1+3 — reuse, do NOT duplicate:**

- `packages/sft-agents/{pyproject.toml,project.json,src/sft_agents/__init__.py}` — empty scaffold; Phase 4 fills
- `packages/sft-assets/` (Phase 3 v0.1.0) — Asset/Tag models + 30 registry seed
- `packages/sft-tools/` (Phase 3 v0.1.0) — ReplayCMAPSSTool, ReplayUCITool, QueryTimescaleTool — sft-agents imports these
- `packages/sft-domain/` (Phase 2 v0.2.0) — glossary + schemas — agents reference for natural-language explanations
- `apps/agents/{ops,maintenance,knowledge,supply}/*/` — 16 Phase 1 scaffolds; Phase 4 wires them as LangGraph cluster subgraph children (placeholders only — real logic Phase 6-9)
- `services/ot-bridge/` — pattern for NATS+PG dual-write idiom (audit.ot.bridge) — Phase 4 replicates idiom for audit.actions.*
- `infra/compose/core.yml` — Postgres+TimescaleDB already running (Phase 3 used it for sensor_events); Phase 4 reuses same PG instance for checkpointer + audit + budget tables
- `scripts/timescale-migrate.py` — Phase 3 idempotent migration runner — Phase 4 extends with 3 new migrations
- `scripts/nats-bootstrap-streams.py` — Phase 3 — Phase 4 adds `AUDIT_STREAM` declaration (separate from SENSOR_EVENTS; D-58 retention 90d)
- `tests/conftest.py` — Phase 3 fixture compose_stack (with known port-5432 issue documented; Phase 4 fix as bonus or defer Phase 11)

**Naming conventions to honor:**
- Conventional Commits scope `feat(04-NN-slug):` per atomic commit
- Pydantic v2 frozen + extra=forbid (allineato Phase 1+2+3)
- yaml.safe_load mandatory
- asyncpg `$1..$N` placeholders ONLY (no f-string SQL — T-V5-sql Phase 3 threat)
- datetime.now(UTC) mandatory (Pitfall 7 Phase 3)
- structlog JSON logging
- snake_case Python field names + YAML keys
</code_context>

<decisions>

## D-53 — 5 cluster subgraphs (split Knowledge in 2)

**Decision:** LangGraph supervisor routes to 5 cluster subgraphs:
- **Ops** — operator-assistant, production-planner, quality-inspector, anomaly-detector (4 child nodes; SLA strict, real-time factory floor)
- **Maintenance** — predictive-maintenance, rca-specialist, maintenance-coach, downtime-analyzer (4 child nodes; SLA medium, predictive horizon hours-to-days)
- **Knowledge-Curation** — knowledge-curator, documentation-synthesizer (2 child nodes; editorial/governance work, SLA hours, primarily HITL-driven curation)
- **Knowledge-Training** — training-coach, shift-handover (2 child nodes; pedagogical content + handover narration, SLA loose, mostly read-only retrieval)
- **Supply** — inventory-manager, energy-optimizer, cost-analyzer, demand-forecaster (4 child nodes; SLA loose, batch-oriented forecasting)

Total: 16 agent placeholder child nodes split across 5 clusters.

**Why:** Knowledge-Curation and Knowledge-Training have orthogonal SLAs (editorial slow + safety-critical vs training fast + low-stakes). Combining them under a single Knowledge cluster forces a shared supervisor that must arbitrate two very different latency budgets. Splitting allows per-cluster routing policy + per-cluster budget caps (D-60).

**ROADMAP override:** ROADMAP currently says "four cluster subgraph skeletons" — D-53 overrides to 5. Plan 04-NN must include a ROADMAP edit task to align (success criterion #1 needs the count fix).

**Rejected alternatives:**
- 4 clusters (Phase 1 mapping): forces Knowledge cluster compromise SLA.
- 3 clusters (Supply deferred): violates MVP scope.
- 5+ clusters with separate Quality: D-21 Phase 2 settled Quality as cross-cutting `asset_family: quality_grading`, not a process; Ops cluster's quality-inspector already covers.

## D-54 — Hybrid supervisor routing (rules fast-path + LLM fallback)

**Decision:** Supervisor node implements 2-stage routing:
1. **Stage 1 (rule-based, <10ms):** pattern-match intent string against per-cluster rule sets in `sft_agents/policies/routing.yaml`:
   ```yaml
   ops:        keywords: [operator, turno, allarme, produzione, qualita, defetto]
               patterns: ["macchina (\\d+|[A-Z]+-\\d+)", "anomalia"]
   maintenance: keywords: [manutenzione, riparazione, guasto, broken, downtime, RCA]
   knowledge-curation: keywords: [documento, SOP, glossario, aggiorna, taxonomy]
   knowledge-training: keywords: [formazione, training, handover, briefing]
   supply:     keywords: [inventario, ordine, costo, energia, demand]
   ```
   If exactly 1 cluster matches → route directly, log `{route: <cluster>, strategy: rules, confidence: 1.0}` to Langfuse.
2. **Stage 2 (LLM, ~500ms-2s):** if 0 or ≥2 cluster matches at Stage 1, invoke LLM classifier with system prompt + 4-shot examples, structured output `cluster: <enum>` + `confidence: float`. If `confidence < 0.7`, fallback to default `ops` cluster. Log `{route: <cluster>, strategy: llm, confidence: <float>}`.

Tutti i routing tracciati in Langfuse `supervisor.route` span — analytics post-hoc (quale strategia ha quale hit-rate?).

**Why:** Rule-based covers ~80% di intents naturali (factory floor language is repetitive); LLM gestisce ambiguity. Langfuse traccia win-rate per ottimizzare.

**Rejected alternatives:**
- Pure LLM: 500ms+ latency su ogni intent.
- Pure rules: brittle a paraphrasing.
- Embedding similarity: richiede Qdrant (Phase 5 dep).

## D-55 — Approval queue: PG primary + NATS notify + REST UI API

**Decision:** Approval queue is a PG table `hitl.approvals` (append-only audit-style, no UPDATE rows except `status` column transitions). On every new approval request:
1. Insert row PG `hitl.approvals (id, agent_id, thread_id, tier, payload_json, status='pending', created_at, sla_deadline, decided_at, decided_by, decision_json)`.
2. Async publish NATS `hitl.approvals.new.<tier>` event `{id, tier, agent_id, payload_summary}` — UI subscribes for real-time push.
3. UI Phase 11 polls REST `GET /v1/approvals?tier=<tier>&status=pending&limit=50` (FastAPI in `apps/api-gateway/`).
4. Decision via REST `POST /v1/approvals/{id}/decide` body `{decision: approve|reject|escalate, motivation, decided_by}` → updates PG row + publishes NATS `hitl.approvals.resolved.<tier>` + writes AuditRecord (D-56) + returns to LangGraph via `Command(resume=decision)`.

Schema PG:
```sql
CREATE TABLE hitl.approvals (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id        TEXT NOT NULL,
  thread_id       TEXT NOT NULL,
  tier            TEXT NOT NULL CHECK (tier IN ('operator','supervisor','manager','safety_interlock')),
  action_type     TEXT NOT NULL,
  payload_json    JSONB NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','approved','rejected','escalated','timed_out')),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sla_deadline    TIMESTAMPTZ NOT NULL,
  decided_at      TIMESTAMPTZ,
  decided_by      TEXT,
  decision_json   JSONB,
  escalated_to_id UUID REFERENCES hitl.approvals(id)
);
CREATE INDEX idx_approvals_tier_status ON hitl.approvals (tier, status, sla_deadline)
  WHERE status = 'pending';
```

**Why:** PG = ACID + queryable per UI dashboard. NATS notify = push real-time senza WebSocket dedicato. REST API è standard backend, semplice per Phase 11 UI Angular.

**Rejected alternatives:**
- Pure NATS queue: persistence fragile, hard to query complex (es. "give me last 100 approvals by operator X").
- WebSocket-only: duplica transport (NATS già infra).
- Event sourcing: over-engineering Phase 4.

## D-56 — Audit trail: dual-write sync PG primary + NATS replica

**Decision:** Ogni AuditRecord scritto sincrono in PG `audit.actions` (append-only via revoked UPDATE/DELETE on agent role) + async publish NATS `AUDIT_STREAM` subject `audit.actions.<cluster>.<agent_id>`. PG = source of truth (regulatory: 7y retention per A-018), NATS = ops telemetry + replay (90d retention per HITL-05).

AuditRecord schema:
```sql
CREATE TABLE audit.actions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  action_id       UUID NOT NULL,            -- agent's intra-execution id
  agent_id        TEXT NOT NULL,
  thread_id       TEXT NOT NULL,
  cluster         TEXT NOT NULL,
  action_type     TEXT NOT NULL,
  evidence_panel  JSONB NOT NULL,           -- EvidencePanel embedded
  decision        TEXT NOT NULL
                    CHECK (decision IN ('auto','hitl_operator','hitl_supervisor','hitl_manager','interlock_reject','rolled_back')),
  decision_actor  TEXT,                     -- NULL for auto; user_id for HITL
  motivation      TEXT,                     -- mandatory for HITL override (HITL-07)
  budget_snapshot JSONB                     -- {tokens, cost_usd, duration_ms}
);
-- 7y retention via partitioning (TimescaleDB hypertable on ts, chunk=30days)
SELECT create_hypertable('audit.actions', 'ts', chunk_time_interval => INTERVAL '30 days', if_not_exists => TRUE);
-- Revoke mutation on the agent role
REVOKE UPDATE, DELETE ON audit.actions FROM agent_role;
```

EvidencePanel Pydantic schema (`sft_agents.models.EvidencePanel`):
```python
class EvidencePanel(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    input_summary: str                                # ≤500 char dell'intent originale
    tool_calls: list[ToolCall]                        # ordered list
    rag_citations: list[RagCitation] = Field(default_factory=list)  # Phase 5 popola; Phase 4 default []
    confidence: float = Field(ge=0.0, le=1.0)
    model: str                                        # es. "qwen2.5-14b-awq" o "qwen2.5-7b-q4km"
    prompt_hash: str                                  # sha256 del prompt finale + system
    tokens: TokenUsage                                # input/output/total
    duration_ms: int
```

Dual-write order: PG INSERT (sync, blocking) → NATS publish (fire-and-forget async with outbox retry on failure). If PG fails → agent ABORTS (no fake audit). If NATS fails → log warning + outbox replays later.

**Why:** PG-first guarantees audit completeness (regulatory hard requirement). NATS provides reactive telemetry without slowing agent hot path. Outbox pattern documenta nei plan come retry idempotency.

**Rejected alternatives:**
- NATS-first + PG snapshot: replica lag confonde UI.
- Async dual-write: rischio audit loss su crash tra agent ack and PG write.
- Defer EvidencePanel: viola HITL-06.

## D-57 — Escalation SLA: 2m/15m/1h auto-escalate + Safety manual-only

**Decision:** 4-tier escalation con timer auto-escalation:
- **Operator** SLA 2 min — timeout → escalate a Supervisor
- **Supervisor** SLA 15 min — timeout → escalate a Manager
- **Manager** SLA 1 hour — timeout → alert (NATS `hitl.governor.alert` + audit `decision: timed_out`) ma NO escalation ulteriore (Manager è ultimo human tier)
- **Safety Interlock** = special tier, manual-only, NO timeout — un'azione blocked da Safety Interlock richiede esplicito human override; il timer non scade mai

Auto-escalation implementato come background asyncio task in `sft_agents.runtime.escalation_supervisor`: scansiona `hitl.approvals WHERE status='pending' AND sla_deadline < NOW()` ogni 30s; per ogni row scaduta, crea nuova row al tier successivo + segna originale `status='escalated'` + audit record `decision: escalated`. Mantiene FK `escalated_to_id` per traceability.

SLA configurabile via `sft_agents/policies/escalation-sla.yaml`:
```yaml
operator:           {sla_minutes: 2,  next_tier: supervisor}
supervisor:         {sla_minutes: 15, next_tier: manager}
manager:            {sla_minutes: 60, next_tier: null}     # alert only
safety_interlock:   {sla_minutes: null, next_tier: null}   # manual only
```

**Why:** 2/15/60 minutes è il pattern standard factory floor (Operator deve essere reattivo; Manager può prendersi un'ora). Safety Interlock no-timeout perché il blocco DEVE essere consapevole (anti-pattern: agent bypass safety dopo timeout).

**Rejected alternatives:**
- 1/5/30: troppo aggressive su operator (approval fatigue).
- Per-tool SLA configurabile: complessità config esplosa Phase 4 PoC.
- No auto-escalation: blocca workflow se human assente.

## D-58 — Safety Interlock + Governor: NATS-command whitelist + 1h sliding window

**Decision:**

**Safety Interlock scope (HITL-03):** rifiuta a priori azioni che pubblicano su NATS subjects matching whitelist YAML `sft_agents/policies/safety-interlock.yaml`:
```yaml
forbidden_subjects:
  - "cmd.plc.setpoint.>"        # Phase 3 forbids OPC-UA writes; questo è il canale NATS alternativo
  - "cmd.actuator.>"            # comandi attuatori
  - "cmd.firmware.deploy"       # firmware deployment
  - "cmd.network.acl.>"         # network policy mutations
forbidden_action_types:
  - WRITE_PLC_SETPOINT
  - ACTUATOR_COMMAND
  - FIRMWARE_DEPLOY
  - NETWORK_ACL_CHANGE
```
SafetyInterlock check è middleware LangGraph node che si inserisce PRIMA di ogni `ToolNode` invocation. Se action match whitelist → audit `decision: interlock_reject` + raise `SafetyInterlockRejection` (terminates agent thread, ApprovalRequest auto-fails). NESSUN tier ha autorità di override Safety Interlock via UI — required code change + audit trail explicit. **Nota:** Phase 3 data-diode rende `cmd.plc.setpoint.*` non-funzionale (ot-bridge non sottoscrive a `cmd.*`). La whitelist è defense-in-depth: anche se Phase 7+ aggiunge subscriber a `cmd.*`, Safety Interlock blocca a livello agentic.

**Approval rate governor (HITL-09):** background task `sft_agents.runtime.governor` scansiona ogni 60s la window `audit.actions WHERE ts > NOW() - INTERVAL '1 hour'`. Calcola:
```
auto_rate = count(decision='auto') / count(*)
```
Se `auto_rate > 0.80` AND `count(*) >= 20` (minimum sample size), emette alert:
1. Audit row `decision: governor_alert` + payload con rate stats
2. NATS publish `hitl.governor.alert` event `{auto_rate, sample_size, window_start, window_end, top_agents}`
3. Manager-tier ApprovalRequest creato (Manager deve confermare se è OK o se vuole disable governance dell'agent X)

Reset implicito: window è scorrevole; se le azioni successive richiedono più HITL, auto_rate scende sotto 80% naturalmente.

**Why:** Whitelist YAML è auditable Phase 11. 1h sliding window cattura comportamenti emergenti senza false positive su singolo evento. Minimum 20 sample evita alert su agent appena avviati.

**Rejected alternatives:**
- Static enum forbidden: meno flessibile per future categories.
- LLM-based intent classifier per Safety: anti-pattern (trust LLM judgement on safety = pericoloso).
- Adaptive threshold per tier: complessità Phase 11.

## D-59 — Memory layer: short-term + episodic Phase 4; long-term stub (Phase 5)

**Decision:**

**Short-term memory (Phase 4):** LangGraph state via PG checkpointer (`langgraph-checkpoint-postgres` 3.1.0). Configurazione: thread_id = `{cluster}.{agent_id}.{session_uuid}`. Schema PG `langgraph.checkpoints` (creato dal package langgraph-checkpoint-postgres tramite migration tool fornito; Phase 4 ne fa setup script `scripts/langgraph-init.py` idempotente).

**Episodic memory (Phase 4):** NATS replay consumer. SDK class `sft_agents.memory.EpisodicReplay`:
```python
class EpisodicReplay:
    async def replay_thread(self, thread_id: str, since: datetime | None = None) -> list[ActionRecord]:
        """Replays NATS `audit.actions.<cluster>.<agent_id>` filtered by thread_id."""
```
Usa `query_timescale` Tool da sft-tools (Phase 3) per query `SELECT * FROM audit.actions WHERE thread_id=$1 AND ts >= $2`. Bonus: ricostruisce stato deterministico dal checkpoint + audit log.

**Long-term memory (Phase 4 STUB; Phase 5 implementazione):**
- SDK interface `sft_agents.memory.LongTermMemory` (ABC class)
- Phase 4 ships `StubLongTermMemory` che ritorna `[]` per ogni query (no Qdrant client)
- Phase 5 (KNW cluster) sostituisce con `QdrantLongTermMemory` (BGE-M3 embedding + Qdrant search)

Memory interface schema in `sft_agents/memory/base.py`:
```python
class MemoryStore(ABC):
    @abstractmethod
    async def query(self, query: str, k: int = 5, filters: dict | None = None) -> list[MemoryRecord]: ...

    @abstractmethod
    async def store(self, record: MemoryRecord) -> str: ...
```

**Why:** Phase 4 può consegnare HITL fully working senza dependency Phase 5. EvidencePanel `rag_citations[]` resta `[]` finché Phase 5 popola; tutto il resto operativo.

**Rejected alternatives:**
- Phase 4 anche long-term: introduce Qdrant client Phase 4 ma vuoto = overhead inutile.
- Phase 4 SOLO short-term: viola CORE-08 (episodic è deliverable Phase 4).
- Inversione (short-term + long-term, no episodic): episodic è cheap (uses Phase 3 NATS+audit already), inutile differire.

## D-60 — Budget/quota tracker: LangGraph middleware node + PG storage

**Decision:** `BudgetTracker` è un LangGraph node che si inserisce PRIMA di ogni LLM call (via custom `BudgetingChatModel` wrapper around `langchain-openai`/`langchain-ollama`) e ogni `ToolNode` invocation (via middleware decorator). Decora lo state con:
```python
class BudgetSnapshot(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_total: int = 0
    cost_usd_simulated: float = 0.0      # Phase 4 = simulated; Phase 11 può collegare pricing reale
    duration_ms: int = 0
    limit_tokens: int                     # configured per agent
    limit_cost_usd: float                 # configured per agent
    limit_duration_s: int                 # configured per agent
```

Storage row in PG `budget.executions` per `thread_id + agent_id`:
```sql
CREATE TABLE budget.executions (
  thread_id     TEXT NOT NULL,
  agent_id      TEXT NOT NULL,
  tokens_total  INT NOT NULL DEFAULT 0,
  cost_usd      DOUBLE PRECISION NOT NULL DEFAULT 0,
  duration_ms   INT NOT NULL DEFAULT 0,
  step_count    INT NOT NULL DEFAULT 0,
  started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_step_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (thread_id, agent_id)
);
```

Update sync ad ogni step (UPSERT). Quando un limit è superato, agent emette ApprovalRequest:
- `tokens_total > limit_tokens * 0.8` (80% soglia) → operator approval
- `cost_usd_simulated > limit_cost_usd` (hard limit) → supervisor approval
- `duration_ms > limit_duration_s * 1000` → operator approval

Limit configurabili in `sft_agents/policies/budgets.yaml` per cluster + agent_id (override). Default cluster-level:
```yaml
ops:                {tokens: 50000, cost_usd: 1.00, duration_s: 60}
maintenance:        {tokens: 100000, cost_usd: 2.00, duration_s: 300}
knowledge-curation: {tokens: 200000, cost_usd: 5.00, duration_s: 600}
knowledge-training: {tokens: 100000, cost_usd: 2.00, duration_s: 300}
supply:             {tokens: 100000, cost_usd: 2.00, duration_s: 300}
```

Langfuse v3 ALSO traccia indipendentemente (Phase 4 ships Langfuse callback); BudgetTracker fornisce gate enforcement, Langfuse fornisce telemetry analytics.

**Why:** Middleware node = enforced by graph topology, agent non può skipparlo. PG storage = thread state persistente (cross-restart). 80% soft + 100% hard = pattern industry standard (warning before kill).

**Rejected alternatives:**
- Sidecar service: +50-100ms latency per chiamata.
- In-memory: rischio data loss su crash.
- Langfuse-only: Langfuse non blocca, solo traccia.

</decisions>

<scope_boundaries>

**In scope (Phase 4):**
- `packages/sft-agents/` fill-in: SDK base classes (`Agent`, `Tool`, `Memory`, `Policy`), supervisor + 5 cluster subgraph builders, BudgetTracker, EscalationSupervisor, Governor, SafetyInterlock middleware, EvidencePanel/AuditRecord/ApprovalRequest Pydantic models
- LangGraph supervisor + 5 cluster subgraphs + 16 placeholder child nodes (NO agent business logic — Phase 6-9)
- PG checkpointer wiring (setup script + thread_id convention)
- LLM adapter `LLM_BACKEND={ollama|vllm}` env var (Qwen2.5-7B Q4_K_M dev, Qwen2.5-14B AWQ prod)
- Migration files 002_create_hitl_approvals.sql + 003_create_audit_actions.sql + 004_create_budget_executions.sql + 005_create_langgraph_checkpoints.sql (idempotent pattern Phase 3)
- NATS `AUDIT_STREAM` setup + NATS publishers for `hitl.approvals.*` + `hitl.governor.alert`
- `apps/api-gateway/` FastAPI endpoint `POST /v1/approvals/{id}/decide` + `GET /v1/approvals?tier=...` (auth deferred Phase 11 per A-018)
- Tool registry (`sft_agents.tools`) re-export sft-tools (Phase 3) + scaffold per-agent tools placeholder
- Replay tool (CORE-10): `sft_agents.replay.from_checkpoint(thread_id, action_id)` ricostruisce esecuzione
- HITL `interrupt()` round-trip integration test (E2E sim agent → interrupt → API decide → resume → audit verified)
- Langfuse v3 callback wiring (Langfuse server deferred — Phase 11 self-host installation; Phase 4 ships only client config + cloud-or-stub)
- Pytest unit + integration tests (mock NATS, mock LLM, testcontainers PG)
- ROADMAP edit task: 4 → 5 cluster mention

**Explicitly NOT in scope (deferred):**
- **Individual agent business logic** → Phase 6 (Quality+Ops), Phase 7 (Maintenance), Phase 8 (Knowledge), Phase 9 (Supply)
- **Qdrant retrieval pipeline + BGE-M3 embedding** → Phase 5 (Knowledge Layer)
- **Langfuse v3 self-hosted server deployment** (Postgres+ClickHouse+MinIO infra) → Phase 11
- **Operator UI Angular** (consumer of `/v1/approvals` API) → Phase 10-11
- **OAuth/OIDC auth on api-gateway** → Phase 11 (governance)
- **Actual cost pricing per LLM token** (real $$ rates) → Phase 11; Phase 4 usa simulated cost
- **Cross-cluster supervisor patterns** (multi-cluster collaboration) → Phase 7+ (agents that need it)
- **MCP server export of sft-agents** → Phase 12+ (out of MVP)
- **Real PLC NATS command channel** (`cmd.plc.setpoint.*`) → Phase 11 (deployment); Phase 4 Safety Interlock whitelist è defense-in-depth

**Out-of-bounds entirely (mentioned but excluded):**
- Multi-language LLM (Qwen2.5 multilingue but PoC IT-only): A-014 scope-limit
- Custom LLM fine-tuning: Phase 11+
- Auto-scaling vLLM (multi-GPU sharding): Phase 11

</scope_boundaries>

<deferred_ideas>

**Recorded during this discussion but out of Phase 4 scope:**

- **Embedding-based supervisor routing** (Stage 3 fallback): would use Qdrant (Phase 5 dep). Phase 4 ships rules + LLM only. Phase 7+ può aggiungere come 3a strategia se serve.
- **Per-tool SLA configurabile** in escalation-sla.yaml: Phase 11 (governance refinement).
- **Adaptive governor threshold per cluster**: Phase 11.
- **LLM-based safety classifier** in addition to whitelist: Phase 11 — but reject this anti-pattern unless very strong evidence.
- **Real-time pricing per token** (collegamento OpenAI pricing API o Anthropic invoices): Phase 11.
- **Cross-cluster checkpoint sharing** (Maintenance agent reads Ops thread state): Phase 7+.
- **CQRS event sourcing** per AuditRecord: Phase 11 (governance hardening).
- **WebSocket push** per approval queue UI (in alternativa al REST polling + NATS notify): Phase 11.
- **MCP wrapping** di sft-agents (espone agent come MCP servers a IDE Claude/Cursor): Phase 12+.

</deferred_ideas>

<claudes_discretion>

Areas where the user did not request explicit discussion — Claude's PLAN will follow these sensible defaults:

- **sft-agents public API surface:** `from sft_agents import Agent, Tool, Memory, Policy, Supervisor, ClusterSubgraph, BudgetTracker, EvidencePanel, AuditRecord, ApprovalRequest`. ABC classes per `Agent`/`Tool`/`Memory`/`Policy` con `model_config = {"frozen": True, "extra": "forbid"}` per dataclass-style models.
- **LangGraph state schema:** `AgentState(TypedDict)` includes `messages: list[BaseMessage]`, `thread_id: str`, `cluster: str`, `proposed_actions: list[ProposedAction]`, `budget: BudgetSnapshot`, `evidence: EvidencePanel | None`, `pending_approval_id: UUID | None`.
- **Thread ID convention:** `{cluster}.{agent_id}.{session_uuid}` (es. `ops.operator-assistant.7c3a...`). UUID v4 per session.
- **LLM model versioning:** model identifier embedded in `EvidencePanel.model` (es. `qwen2.5-14b-awq@vllm-0.8` o `qwen2.5-7b-q4km@ollama-0.6`). Phase 11 può tagliare retention per model version.
- **NATS subjects Phase 4:** `hitl.approvals.new.<tier>`, `hitl.approvals.resolved.<tier>`, `hitl.governor.alert`, `audit.actions.<cluster>.<agent_id>`. JetStream stream `AUDIT_STREAM` retention 90d (separato da SENSOR_EVENTS Phase 3).
- **API gateway endpoint structure:** REST under `/v1/` prefix; OpenAPI auto-generated; ASGI via Uvicorn; pyproject.toml deps: `fastapi`, `uvicorn`, `langchain-core`, `sft-agents` (workspace), `asyncpg`, `nats-py`.
- **Replay determinism:** Phase 4 ships best-effort (re-execute from checkpoint con stesso `seed` LLM dove supportato; tool calls deterministici from audit log). Full determinism (frozen tool outputs) defer Phase 11.
- **Test strategy:** unit tests (mock LLM/NATS/PG) per ogni SDK class; integration test (real testcontainers PG + NATS + mock LLM via langchain-fake) per HITL E2E loop; load test deferred.
- **Migration ordering:** 002 (hitl.approvals) → 003 (audit.actions) → 004 (budget.executions) → 005 (langgraph.checkpoints via langgraph-checkpoint-postgres setup tool); migrate.py Phase 3 estende numbered convention.
- **EvidencePanel rag_citations Phase 4 stub:** Empty list di `RagCitation` Pydantic models; Phase 5 popola. Shape `RagCitation = {source_uri, snippet, score, retrieved_at}` definita Phase 4 per stabilizzare contract.
- **Conventional commit scope:** `feat(04-NN-slug):` per atomic commit.
- **Pyproject deps additions:** `langgraph>=0.4`, `langgraph-checkpoint-postgres>=3.1`, `langchain-core>=0.3`, `langchain-ollama>=0.3`, `langchain-openai>=0.3` (vLLM), `langfuse>=3` (callback), `fastapi>=0.115` (api-gateway).
- **Dev-only LLM provider:** Phase 4 dev = `langchain-ollama` mock (real Ollama daemon not required for unit tests); load `OLLAMA_HOST=http://localhost:11434` only if integration test marker active.
- **Audit write FK to approval:** se `decision IN ('hitl_*')`, `audit.actions` row include `approval_id UUID REFERENCES hitl.approvals(id)`. Decision `auto` ha `approval_id = NULL`.

</claudes_discretion>

<downstream_guidance>

**For gsd-phase-researcher (Phase 4):**

Research focus areas (high → low priority):
1. **LangGraph 0.4+ supervisor + cluster subgraph pattern** — multi-level routing, `StateGraph` composition, `add_subgraph()` API. Best practices for 5+ cluster supervisor scalability.
2. **`langgraph-checkpoint-postgres` 3.1.0 setup** — initialization API, thread_id schema, table layout (`langgraph.checkpoints` table or schema-prefixed), migration tool, cross-restart resume verification.
3. **LangGraph `interrupt()` + `Command(resume=)` end-to-end** — full HITL cycle with PG persistence + reactivation; edge cases (timeout during interrupt, concurrent decide calls, malformed resume payload).
4. **LangChain provider-agnostic adapter** — `ChatOllama` + `ChatOpenAI` (vLLM-compatible) shared signature; env var switching pattern; structured output Pydantic v2 binding; streaming compatibility (vLLM vs Ollama).
5. **Langfuse v3 callback** for LangGraph — `LangfuseCallbackHandler`, span hierarchy (supervisor → cluster → agent → LLM/tool), instrumentation overhead (target <50ms/call).
6. **HITL escalation pattern** in LangGraph — background asyncio supervisor that monitors PG queue + triggers `Command(resume=)` for timed-out approvals (vs polling pattern).
7. **Tool registry typing + JSON schema export** (CORE-07) — LangChain `BaseTool` + Pydantic v2 `args_schema` + `model_json_schema(by_alias=True)` for OpenAI function calling export.
8. **NATS JetStream `AUDIT_STREAM` config** — retention 90d, consumer durability, ack policy, ordering guarantees (per-thread_id partitioning).
9. **PG append-only enforcement** — REVOKE UPDATE/DELETE on agent_role, row-level security alternatives, post-insert immutability via trigger.
10. **Replay determinism** — LLM seed control across Ollama/vLLM; tool call replay from audit log; fixture seed strategy in tests.

NOT research (already decided in CONTEXT.md):
- Cluster split (D-53)
- Routing strategy (D-54)
- Approval queue transport (D-55)
- Audit dual-write semantics (D-56)
- Escalation SLA (D-57)
- Safety + Governor (D-58)
- Memory split (D-59)
- Budget tracker (D-60)

**Output a Validation Architecture section** (Nyquist applies — HITL E2E test, budget enforcement gate, safety interlock gate, replay determinism check).

**For gsd-planner (Phase 4):**

Expected plan count: **6-8 plans** with clear wave structure:

- **Wave 1 (foundation):** Plan 04-01 — sft-agents SDK base (Pydantic models: EvidencePanel, AuditRecord, ApprovalRequest, BudgetSnapshot, ProposedAction; ABC: Agent/Tool/Memory/Policy; tests)
- **Wave 2 (parallel):** Plan 04-02 PG migrations (002+003+004+005 idempotent + extend migrate.py from Phase 3); Plan 04-03 LLM adapter + Langfuse callback + env switching; Plan 04-04 NATS AUDIT_STREAM setup + nats-bootstrap extension
- **Wave 3 (parallel):** Plan 04-05 — LangGraph supervisor + 5 cluster subgraphs + 16 placeholder child nodes + PG checkpointer wiring; Plan 04-06 — HITL middleware (SafetyInterlock + BudgetTracker + EvidencePanel attachment) + EscalationSupervisor + Governor background tasks
- **Wave 4 (integration):** Plan 04-07 — `apps/api-gateway/` FastAPI endpoints (/v1/approvals*) + integration test HITL E2E (real PG + NATS via testcontainers + mock LLM); Plan 04-08 — Replay tool + audit verification + Langfuse manual smoke + ROADMAP edit (5 cluster correction)

Each plan must have:
- Atomic commit boundaries `feat(04-NN-slug):`
- Frontmatter validation step before code
- `depends_on` short-form (e.g., `["01"]` foundation, `["04-01"]` for things using SDK)

**Sizing constraints:**
- 1 plan = sft-agents SDK foundation
- 1 plan = ALL PG migrations bundled (idempotent run = single artifact)
- 1 plan = LLM adapter + Langfuse callback (tightly coupled)
- 1 plan = supervisor + cluster subgraphs (cohesive)
- 1 plan = HITL middleware + escalation + governor (cohesive runtime concerns)
- 1 plan = api-gateway + HITL E2E test
- 1 plan = replay + ROADMAP edit + Langfuse smoke

</downstream_guidance>

<next_steps>

Run `/clear` to free context, then:

```
/gsd-plan-phase 4
```

This will:
1. Spawn `gsd-phase-researcher` → produces `04-RESEARCH.md`
2. Spawn `gsd-pattern-mapper` → produces `04-PATTERNS.md` (analogs from Phase 1/2/3)
3. Spawn `gsd-planner` → produces 6-8 `04-NN-slug-PLAN.md` files
4. Spawn `gsd-plan-checker` → verification loop

Only after planning approved: `/gsd-execute-phase 4`.

</next_steps>
