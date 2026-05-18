---
phase: 4
phase_name: Core Agentic Runtime & HITL
phase_slug: core-agentic-runtime-hitl
mapped_at: "2026-05-18"
requirements: [CORE-01..10, HITL-01..10]
analogs_scope:
  - packages/sft-domain/
  - packages/sft-tools/
  - packages/sft-assets/
  - services/ot-bridge/
  - infra/migrations/timescale/
  - scripts/nats-bootstrap-streams.py
  - tests/conftest.py
  - apps/api-gateway/
language: it
---

# Phase 4 — Pattern Map (Core Agentic Runtime & HITL)

> **Scopo:** assegnare ad ogni nuovo work-area un analogo concreto già presente in repo (Phase 1+3),
> così che il planner produca task `pattern_ref:` puntuali (file + righe) anziché riscrivere idiomi
> da zero. I tre idiomi-cardine (Pydantic v2 frozen, asyncpg `$N` placeholders, idempotent migrations)
> sono **già scolpiti** dalle Phase 2+3. Il dual-write PG-sync + NATS-async esiste 1:1 in `services/ot-bridge/`.

**File mappati:** 16 work-areas
**Analoghi exact-match:** 8 / 16
**Analoghi role-match (riusare 80%+ pattern):** 5 / 16
**Senza analogo (NEW, fallback su RESEARCH.md):** 3 / 16

---

## §1. File Classification

| # | New/Modified Work-Area | Role | Data Flow | Closest Analog | Match |
|---|------------------------|------|-----------|----------------|-------|
| 1 | `packages/sft-agents/src/sft_agents/sdk/` (Agent/Tool/Memory/Policy ABC + Pydantic models) | sdk-base | data-shape | `packages/sft-tools/src/sft_tools/replay/models.py` + `packages/sft-domain/src/sft_domain/glossary/_models.py` | exact |
| 2 | `packages/sft-agents/src/sft_agents/supervisor/` (LangGraph StateGraph + hybrid routing) | runtime-graph | request-response | NEW — no in-repo precedent for LangGraph | none |
| 3 | `packages/sft-agents/src/sft_agents/clusters/{ops,maintenance,knowledge_curation,knowledge_training,supply}/` | runtime-graph | request-response | `apps/agents/{ops,maintenance,knowledge,supply}/*/pyproject.toml` (Phase 1 scaffold layout only) | role-match |
| 4 | `packages/sft-agents/src/sft_agents/checkpointer/` (AsyncPostgresSaver wiring) | persistence | CRUD | `packages/sft-tools/src/sft_tools/timescale/query.py` (asyncpg connect idiom) | role-match |
| 5 | `packages/sft-agents/src/sft_agents/llm/` (LLM_BACKEND={ollama,vllm} factory) | adapter | request-response | `services/ot-bridge/src/svc_ot_bridge/main.py` (env-var dispatch `os.environ.get`) | role-match |
| 6 | `packages/sft-agents/src/sft_agents/hitl/` (interrupt/resume + EvidencePanel + 4-tier escalation + Safety Interlock whitelist) | runtime-middleware | event-driven | `packages/sft-domain/src/sft_domain/glossary/_loader.py` (yaml.safe_load) + `services/ot-bridge/src/svc_ot_bridge/models.py` (Pydantic frozen w/ tz-aware validator) | role-match |
| 7 | `packages/sft-agents/src/sft_agents/audit/` (dual-write PG + NATS + outbox) | persistence | event-driven | **`services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` + `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py`** | **exact** (1:1 replica) |
| 8 | `packages/sft-agents/src/sft_agents/governor/` (1h sliding-window approval-rate alert) | runtime-task | batch / CRUD | `packages/sft-tools/src/sft_tools/timescale/query.py` (parametric SELECT over hypertable) | role-match |
| 9 | `packages/sft-agents/src/sft_agents/budget/` (LangGraph middleware + PG UPSERT) | runtime-middleware | CRUD | `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` (asyncpg `$N` UPSERT idiom) | role-match |
| 10 | `packages/sft-agents/src/sft_agents/replay/` (deterministic replay from checkpoint+audit) | utility | batch | `packages/sft-tools/src/sft_tools/replay/{cmapss,uci}.py` + `packages/sft-tools/src/sft_tools/replay/models.py` | exact |
| 11 | `infra/migrations/timescale/00{2,3,4,5}_*.sql` | migration | DDL | **`infra/migrations/timescale/001_create_sensor_events.sql`** | **exact** (DO $$ idempotent blocks) |
| 12 | `scripts/nats-bootstrap-streams.py` (extend in-place: add `AUDIT_STREAM`) | script | one-shot | **`scripts/nats-bootstrap-streams.py`** (esiste — estendere) | **exact** (in-place edit) |
| 13 | `apps/api-gateway/` (FastAPI `/v1/approvals*` endpoints) | controller | request-response | NEW — scaffold pyproject exists ma `__init__.py` è 2-line stub. Closest FastAPI idiom in repo: nessuno (sim-textile/server.py usa asyncua server, non FastAPI) | none |
| 14 | `packages/sft-agents/tests/` (Wave 0 stubs + unit) | test | unit | `packages/sft-tools/tests/test_query_timescale.py` (mock asyncpg + class-grouped tests) | exact |
| 15 | `tests/e2e/test_hitl_cycle.py` (HITL E2E survives docker compose restart) | test | integration | `tests/integration/test_e2e_sim_to_timescale.py` + `tests/conftest.py::compose_stack` | exact |
| 16 | `.planning/ROADMAP.md` edit (4→5 clusters) | doc | manual | N/A (diff-only edit; conventional commit `docs(04-NN-slug):`) | none |

---

## §2. Cross-Cutting Idioms (apply to ALL new files)

Convenzioni ereditate Phase 1+2+3 — il planner DEVE annotarle come acceptance criteria di OGNI plan:

| Idiom | Source-of-Truth | One-Liner |
|-------|-----------------|-----------|
| **Pydantic v2 frozen + extra=forbid** | `packages/sft-tools/src/sft_tools/replay/models.py:33` + `services/ot-bridge/src/svc_ot_bridge/models.py:32` | `model_config = {"frozen": True, "extra": "forbid"}` su OGNI `BaseModel` |
| **asyncpg `$1..$N` placeholders ONLY** | `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:30-34` + `packages/sft-tools/src/sft_tools/timescale/query.py:35-43` | SQL come COSTANTE modulo. **MAI f-string SQL** (T-V5-sql). `tag_id = ANY($4)` per liste |
| **asyncpg statement_cache_size=0** | `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:82-88` + `infra/migrations/timescale/migrate.py:67-72` | Obbligatorio per TimescaleDB dynamic plan optimization (Pitfall 6) |
| **datetime.now(UTC) tz-aware** | `services/ot-bridge/src/svc_ot_bridge/models.py:59-72` + `packages/sft-tools/src/sft_tools/replay/models.py:49-63` | `@field_validator(...)` rifiuta `tzinfo is None`. `UTC = timezone.utc` constante modulo |
| **yaml.safe_load mandatory** | `packages/sft-domain/src/sft_domain/glossary/_loader.py:52` | MAI `yaml.load`. Per OGNI YAML config (routing.yaml, escalation-sla.yaml, safety-interlock.yaml, budgets.yaml) |
| **structlog JSON logging** | `services/ot-bridge/src/svc_ot_bridge/main.py:30-40` + `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:22-26` | `logger = structlog.get_logger(__name__)`. JSONRenderer + iso TimeStamper |
| **Env-var fail-fast** | `services/ot-bridge/src/svc_ot_bridge/main.py:64-69` + `packages/sft-tools/src/sft_tools/timescale/query.py:108` | `os.environ["VAR"]` (KeyError) per required; `os.environ.get("VAR", default)` per optional. Mai hardcode DSN |
| **Conventional Commits + atomic** | `git log` Phase 3: `feat(03-NN-slug):` | Scope `feat(04-NN-slug):` per ogni atomic commit; un plan = N commits monotematici |
| **`@nxlv/python` uv-project layout** | `packages/sft-agents/pyproject.toml` + `services/ot-bridge/pyproject.toml` | `[project]` → `requires-python = ">=3.12,<3.13"`; `[tool.hatch.build.targets.wheel] packages = ["src/<pkg>"]`; `[tool.uv.sources] <dep> = { workspace = true }` |
| **pytest layout + markers** | `tests/conftest.py:53-71` (markers) + `services/ot-bridge/pyproject.toml:36-38` (`asyncio_mode = "auto"`) | Register `@pytest.mark.integration` (compose stack required) + `@pytest.mark.load` |
| **Path-traversal-safe paths** | `tests/conftest.py:11-12` (`pathlib.Path` only, no `os.path` / string-concat) | T-02-10 mitigation; usa `pathlib.Path(__file__).parent` per relative lookup |
| **Idempotent DDL/scripts** | `infra/migrations/timescale/001_create_sensor_events.sql:36-48` (DO $$ guards) + `scripts/nats-bootstrap-streams.py:148-167` (try add → except → update) | `IF NOT EXISTS`, `DO $$ ... END $$`, `if_not_exists => TRUE`. Per NATS: try `add_stream` → except `BadRequestError` → `update_stream` |

---

## §3. Pattern Assignments (per work-area)

### §3.1 — `packages/sft-agents/src/sft_agents/sdk/` (SDK base — CORE-01, CORE-02)

**Pydantic models** (`EvidencePanel`, `AuditRecord`, `ApprovalRequest`, `BudgetSnapshot`, `ProposedAction`, `RagCitation`, `ToolCall`, `TokenUsage`, `MemoryRecord`):

- **Analog (exact):** `packages/sft-tools/src/sft_tools/replay/models.py` (ReplayRecord pattern)
- **Pattern:** `model_config = {"frozen": True, "extra": "forbid"}` + `@field_validator` per tz-aware su CORE timestamp fields (Pitfall 7)
- **Pattern ref:** `packages/sft-tools/src/sft_tools/replay/models.py:25-63` (ReplayRecord + timestamp validator)
- **Pattern ref:** `services/ot-bridge/src/svc_ot_bridge/models.py:22-72` (SensorEvent w/ Literal source + dual tz validator)

**ABC interfaces** (`Agent`, `Tool`, `Memory`, `Policy`):

- **Analog (role-match):** `packages/sft-tools/src/sft_tools/timescale/query.py` (LangChain `BaseTool` subclass — già pattern noto)
- **Pattern:** `from abc import ABC, abstractmethod`; async-first (`async def query(...)`, `async def store(...)`). `_run` solleva `NotImplementedError` per forzare `_arun`.
- **Pattern ref:** `packages/sft-tools/src/sft_tools/timescale/query.py:46-84` (BaseTool subclass + async-first NotImplementedError pattern)

**Public API export** (`packages/sft-agents/src/sft_agents/__init__.py`):

- **Pattern:** flat re-export ABCs + models. Idiom: `from sft_agents.sdk.models import EvidencePanel, AuditRecord, ...`
- **Pattern ref:** `packages/sft-tools/src/sft_tools/__init__.py` (re-export pattern Phase 3) — leggere per replica

---

### §3.2 — `packages/sft-agents/src/sft_agents/supervisor/` (CORE-02, D-54)

**Analog:** NESSUNO — LangGraph è nuovo in repo. Fallback su RESEARCH.md §3.1 (StateGraph composition) + §3.4 (hybrid routing).

**Patterns da rispettare (cross-cutting):**
- `yaml.safe_load` per `routing.yaml` → ref §2 `_loader.py:52`
- `structlog` per ogni `supervisor.route` log → ref §2 `main.py:30-40`
- Pydantic v2 frozen per `RoutingDecision` model

---

### §3.3 — `packages/sft-agents/src/sft_agents/clusters/{ops,maintenance,knowledge_curation,knowledge_training,supply}/` (D-53)

**Analog (role-match — solo per layout):** `apps/agents/{ops,maintenance,knowledge,supply}/*/pyproject.toml` (Phase 1 scaffolds 16 agenti).

- **Pattern (riuso):** lista child-node IDs allineata ai 16 agent slug Phase 1:
  - `ops/`: `operator-assistant`, `production-planner`, `quality-inspector`, `anomaly-detector`
  - `maintenance/`: `predictive-maintenance`, `rca-specialist`, `maintenance-coach`, `downtime-analyzer`
  - `knowledge_curation/`: `knowledge-curator`, `documentation-synthesizer`
  - `knowledge_training/`: `training-coach`, `shift-handover`
  - `supply/`: `inventory-manager`, `energy-optimizer`, `cost-analyzer`, `demand-forecaster`
- **Pattern ref:** `find apps/agents -name pyproject.toml | sort` (16 file enumera lo split — il planner DEVE allinearsi a questi slug exact)

**ATTENZIONE:** Knowledge Phase 1 = `apps/agents/knowledge/{knowledge-curator,documentation-synthesizer,training-coach,shift-handover}` (4 sotto un'unica directory). D-53 splitta a 2 cluster a livello SDK ma NON rinomina Phase 1 paths. Il cluster mapping è metadata, non filesystem move.

---

### §3.4 — `packages/sft-agents/src/sft_agents/checkpointer/` (CORE-04)

**Analog (role-match):** `packages/sft-tools/src/sft_tools/timescale/query.py` (asyncpg connect lifecycle).

**Pattern:**
- `dsn = os.environ["TIMESCALE_DSN"]` (fail-fast, no hardcode)
- `asyncpg.connect(dsn, statement_cache_size=0, command_timeout=...)` (Pitfall 6)
- Async lifecycle `start()/close()` come in `TimescaleWriter`
- **Pattern ref:** `packages/sft-tools/src/sft_tools/timescale/query.py:108-126` (DSN + connect + try/finally close)
- **Pattern ref:** `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:74-91` (pool start lifecycle)

**Setup script:** `scripts/langgraph-init.py` idempotente. **Pattern ref:** `infra/migrations/timescale/migrate.py` (intero file 132 righe — replica struttura argparse + asyncio.run + dry-run flag).

---

### §3.5 — `packages/sft-agents/src/sft_agents/llm/` (CORE-05, CORE-06)

**Analog:** NESSUNO (provider-agnostic LangChain è nuovo). Fallback RESEARCH.md §4 (ChatOllama + ChatOpenAI signature).

**Patterns (cross-cutting):**
- Env-var dispatch idiom: `services/ot-bridge/src/svc_ot_bridge/main.py:62-71`
  ```python
  llm_backend = os.environ.get("LLM_BACKEND", "ollama")
  if llm_backend not in {"ollama", "vllm"}:
      raise RuntimeError(f"LLM_BACKEND must be ollama|vllm, got {llm_backend!r}")
  ```
- Factory function (no class wrapper se non necessario) — segue stile `derive_event_subject` in `nats_publisher.py:31-38`.

---

### §3.6 — `packages/sft-agents/src/sft_agents/hitl/` (HITL-01..06)

**Sub-areas:**

| Sub-area | Analog | Idiom |
|----------|--------|-------|
| `interrupt/resume` middleware | NEW (LangGraph specific) | Fallback RESEARCH.md §6 (Command resume) |
| `EvidencePanel` Pydantic | `services/ot-bridge/src/svc_ot_bridge/models.py:22-72` | `frozen=True` + `extra=forbid` + `Literal` enums |
| `escalation-sla.yaml` loader | `packages/sft-domain/src/sft_domain/glossary/_loader.py:21-60` | `yaml.safe_load` + `pathlib.Path(__file__).parent` + `lru_cache(maxsize=N)` |
| `safety-interlock.yaml` whitelist | idem (`_loader.py:52`) | yaml.safe_load + Pydantic validation post-load |
| EscalationSupervisor background task | `services/ot-bridge/src/svc_ot_bridge/main.py:114-168` (worker loop with `asyncio.wait_for` + `shutdown_event`) | Async background scan every 30s, cancellable via `shutdown_event` |
| ApprovalRequest INSERT idiom | `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:103-144` | `_INSERT_SQL` costante modulo + `$N` placeholders + try/except + structlog |

**Pattern ref CRITICAL:** `services/ot-bridge/src/svc_ot_bridge/main.py:114-168` — riusare 1:1 per `EscalationSupervisor.run()` (worker pattern con queue, shutdown_event, asyncio.wait_for timeout).

---

### §3.7 — `packages/sft-agents/src/sft_agents/audit/` (CORE-08, HITL-05, D-56) — **DUAL-WRITE EXACT REPLICA**

**Questo è l'analogo più puntuale del fase 4.** Il dual-write `PG-sync + NATS-async` esiste **1:1** in `services/ot-bridge/`.

**Files target & analog 1:1:**

| New file | Direct analog (1:1) | Idiom |
|----------|---------------------|-------|
| `sft_agents/audit/pg_writer.py` (AuditPgWriter) | `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` (TUTTO il file) | asyncpg pool + executemany + `_INSERT_SQL` costante + `$N` + structlog + try/finally pool close |
| `sft_agents/audit/nats_publisher.py` (AuditNatsPublisher) | `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py` (TUTTO) | nats.connect → jetstream() → `publish(subject, payload)` con `model_dump_json().encode("utf-8")` |
| `sft_agents/audit/writer.py` (AuditWriter — orchestrator) | RESEARCH.md §12 (snippet 627-672) + `services/ot-bridge/src/svc_ot_bridge/main.py:158-159` (`publisher.publish_event + writer.push`) | PG sync FIRST (blocking; agent ABORTS on failure) → NATS fire-and-forget con outbox retry |
| `sft_agents/audit/outbox.py` (OutboxRetry background task) | `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:146-158` (`_flush_loop`) | `asyncio.create_task` background loop every 30s, CancelledError-safe |

**Pattern ref dettagliato (READ THESE LINES per ogni plan audit-related):**
- `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:30-34` — `_INSERT_SQL` costante con `$1..$7`
- `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:82-91` — `create_pool(min_size=10, max_size=20, statement_cache_size=0, command_timeout=10.0)`
- `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:108-144` — `_flush_locked` con executemany + try/except + structlog error
- `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:146-158` — `_flush_loop` async background pattern
- `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:60-118` — `NatsPublisher` class lifecycle (connect → jetstream → publish → drain)
- `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:120-132` — `publish_audit(AuditEvent)` con `model_dump_json().encode("utf-8")`

**REVOKE UPDATE/DELETE pattern (HITL-05):** NEW — non esiste in repo. Embed nel migration SQL `003_create_audit_actions.sql`:
```sql
REVOKE UPDATE, DELETE ON audit.actions FROM agent_role;
```
(Pattern di SQL grants segue Postgres standard — nessun analogo in-repo.)

---

### §3.8 — `packages/sft-agents/src/sft_agents/governor/` (HITL-09)

**Analog (role-match):** `packages/sft-tools/src/sft_tools/timescale/query.py` (SELECT con $N + asyncpg + statement_cache_size=0).

**Pattern:** background task 60s che esegue:
```python
# Query con $N — MAI f-string SQL
sql = (
    "SELECT count(*) FILTER (WHERE decision='auto') AS auto_count, "
    "       count(*) AS total "
    "FROM audit.actions WHERE ts > NOW() - INTERVAL '1 hour'"
)
```
- **Pattern ref:** `packages/sft-tools/src/sft_tools/timescale/query.py:35-43` (SQL costante)
- **Pattern ref (background loop):** `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:146-158` (`_flush_loop`)

NATS alert publish: replica `nats_publisher.py:120-132` (`publish_audit` rinominato `publish_alert`).

---

### §3.9 — `packages/sft-agents/src/sft_agents/budget/` (HITL-09, CORE-09, D-60)

**Analog (role-match):** `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` (asyncpg UPSERT pattern; sostituire INSERT con `INSERT ... ON CONFLICT (thread_id, agent_id) DO UPDATE SET tokens_total = tokens_total + EXCLUDED.tokens_total, ...`).

- **Pattern ref:** `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:30-34` (SQL costante) + `:108-135` (executemany style → adattare a single-row execute con UPSERT)

**LangGraph middleware decorator** — NEW pattern (RESEARCH.md §3.5).

---

### §3.10 — `packages/sft-agents/src/sft_agents/replay/` (CORE-10)

**Analog (exact):** `packages/sft-tools/src/sft_tools/replay/{cmapss.py,uci.py,models.py}` (Phase 3 ReplayCMAPSSTool/ReplayUCITool).

- **Pattern:** `ReplayRecord`-like Pydantic schema per `ReplayedAgentStep`
- **Pattern ref:** `packages/sft-tools/src/sft_tools/replay/models.py:25-63` (D-46 ReplayRecord — già definito Phase 3)
- **Riuso:** importare `query_timescale` (Phase 3) per leggere `audit.actions WHERE thread_id=$1 AND ts >= $2` (D-59 episodic memory).
- **Pattern ref:** `packages/sft-tools/src/sft_tools/timescale/query.py` (intero file — riferimento per query custom su `audit.actions`)

---

### §3.11 — `infra/migrations/timescale/00{2,3,4,5}_*.sql` — **IDEMPOTENT EXACT REPLICA**

**Analog 1:1:** `infra/migrations/timescale/001_create_sensor_events.sql` (75 righe; replicare struttura per ognuna delle 4 nuove migration).

**Pattern critico (DO $$ idempotent block):**
- **Pattern ref:** `infra/migrations/timescale/001_create_sensor_events.sql:36-48` (DO $$ + IF NOT EXISTS guards)
- **Pattern ref:** `:14-22` (CREATE TABLE IF NOT EXISTS + tipi)
- **Pattern ref:** `:26-31` (`create_hypertable(..., if_not_exists => TRUE)`)
- **Pattern ref:** `:52-65` (`add_compression_policy` + `add_retention_policy` con `if_not_exists => TRUE`)

**Migrations Phase 4:**
| File | Schema | Hypertable? | Retention |
|------|--------|-------------|-----------|
| `002_create_hitl_approvals.sql` | `hitl.approvals` (D-55 schema CONTEXT.md:131-150) | NO (transactional, OLTP) | nessuna (lifecycle gestito da app) |
| `003_create_audit_actions.sql` | `audit.actions` (D-56 schema CONTEXT.md:165-184) + `audit.outbox` | YES (chunk 30d, D-56) | 7y partitioning (RESEARCH §12) + `REVOKE UPDATE, DELETE ... FROM agent_role` |
| `004_create_budget_executions.sql` | `budget.executions` (D-60 schema CONTEXT.md:324-336) | NO | nessuna |
| `005_create_langgraph_checkpoints.sql` | `langgraph.checkpoints` (delegato a package `langgraph-checkpoint-postgres` setup tool — file 005 invoca solo `CREATE SCHEMA IF NOT EXISTS langgraph` + chiama setup-Python in `scripts/langgraph-init.py`) | NO | nessuna |

**Migration runner:** già pronto in `infra/migrations/timescale/migrate.py` (pattern discover-via-glob `[0-9][0-9][0-9]_*.sql`). I 4 nuovi file vengono auto-scoperti — nessuna modifica al runner richiesta.

---

### §3.12 — `scripts/nats-bootstrap-streams.py` (extend in-place)

**Analog (exact):** **lo stesso file** — esiste già da Phase 3 e contiene `SENSOR_EVENTS` + `AUDIT_OT`. Phase 4 aggiunge `AUDIT_STREAM` (D-56, 90d retention).

**Pattern di estensione:**
- **Pattern ref:** `scripts/nats-bootstrap-streams.py:85-92` (config dict `audit_ot_cfg`) — copiare struttura per `audit_actions_cfg`:
  ```python
  audit_actions_cfg = {
      "name": "AUDIT_STREAM",
      "subjects": ["audit.actions.>", "hitl.approvals.>", "hitl.governor.>"],
      "retention": "LimitsPolicy",
      "max_age_days": 90,  # D-56 + HITL-05
      "storage": "FileStorage",
  }
  ```
- **Pattern ref:** `scripts/nats-bootstrap-streams.py:129-135` (StreamConfig per AUDIT_OT) — replica con `max_age = 90 * 24 * 3600 * 1_000_000_000`
- **Pattern ref:** `scripts/nats-bootstrap-streams.py:148-167` (try add_stream → except BadRequestError → update_stream — Pitfall 3 idempotency)

---

### §3.13 — `apps/api-gateway/` (FastAPI scaffold — POST /v1/approvals/{id}/decide + GET /v1/approvals)

**Analog:** NESSUNO — il package esiste come scaffold `0.1.0` con solo `__init__.py` di 2 righe e `pyproject.toml` con `dependencies = []`. Fallback su RESEARCH.md §8 + best-practices FastAPI standard.

**Patterns cross-cutting da applicare:**
- pyproject layout: replicare `services/ot-bridge/pyproject.toml:1-44` (hatchling + `[tool.uv.sources] sft-agents = { workspace = true }` + `[tool.pytest.ini_options] asyncio_mode = "auto"`)
- structlog wiring: replicare `services/ot-bridge/src/svc_ot_bridge/main.py:30-40` (JSON renderer + iso TimeStamper)
- Env-var fail-fast: `os.environ["TIMESCALE_DSN"]` + `os.environ.get("NATS_URL", "nats://localhost:4222")`
- asyncpg per query approvals: replicare `packages/sft-tools/src/sft_tools/timescale/query.py` (intero file)
- Pydantic v2 request/response models: replicare idiom `replay/models.py:25-63`

**NB:** auth (OAuth/OIDC) **deferred Phase 11** (CONTEXT.md scope_boundaries riga 385). Plan 04-07 NON deve scaffoldare auth.

---

### §3.14 — `packages/sft-agents/tests/` (unit tests)

**Analog (exact):** `packages/sft-tools/tests/test_query_timescale.py` (320 righe — class-grouped tests + mock asyncpg).

**Pattern:**
- **Pattern ref:** `packages/sft-tools/tests/test_query_timescale.py:19-44` (class `TestQueryTimescaleToolMetadata` — group tests by concern)
- **Pattern ref:** `packages/sft-tools/tests/test_query_timescale.py:67-95` (`@pytest.mark.asyncio` + `AsyncMock` + `patch("module.asyncpg")` + `patch.dict("os.environ", ...)`)
- **Pattern ref:** `services/ot-bridge/tests/test_writer.py:21-36` (`_make_event` helper factory per fixture Pydantic models)

**Local conftest:** segue `tests/conftest.py:50-71` (markers registration) ma a livello package (`packages/sft-agents/tests/conftest.py`).

---

### §3.15 — `tests/e2e/test_hitl_cycle.py` (E2E full HITL cycle survives docker restart)

**Analog (exact):** `tests/integration/test_e2e_sim_to_timescale.py` (60 righe — pattern E2E con `compose_stack` fixture).

**Pattern:**
- **Pattern ref:** `tests/integration/test_e2e_sim_to_timescale.py:17-62` (intero test — `@pytest.mark.integration` + `@pytest.mark.asyncio` + `compose_stack: dict` + `asyncpg.connect(dsn, statement_cache_size=0)` + try/finally close + fetchrow con `$N`)
- **Pattern ref:** `tests/conftest.py:84-147` (`compose_stack` fixture — yield endpoints + teardown `docker compose down -v`)

**Per success criterion #4 (paused HITL survives restart):** estendere `compose_stack` fixture con metodo `restart_service(name)` — o usare `subprocess.run(["docker", "compose", "restart", "<service>"])` inline al test. RESEARCH.md §11 (no precedent specifico — pattern nuovo ma costruito su fixture esistente).

**Known issue port-5432 (RESEARCH OQ8):** se il test fallisce con port-conflict (host Postgres locale), il planner DEVE accodare task di fix in Plan 04-08 oppure rimandare con marker `@pytest.mark.skip(reason="port-5432 conflict; tracked in OQ8")`.

---

### §3.16 — `.planning/ROADMAP.md` edit (4→5 clusters per D-53)

**Analog:** nessuno (è una doc-edit minima). Conventional commit: `docs(04-NN-slug): align ROADMAP cluster count 4→5 (D-53)`.

**Verifica manuale:** dopo edit, eseguire `grep -n "four cluster\|4 cluster" .planning/ROADMAP.md` deve restituire 0 hit (oppure solo riferimenti storici esplicitamente annotati).

---

## §4. Shared Patterns (referenced by multiple plans)

### §4.1 — Audit Dual-Write Idiom (used by: Plan §3.7, indirectly §3.6, §3.8, §3.9)

**Source:** `services/ot-bridge/src/svc_ot_bridge/{timescale_writer.py,nats_publisher.py,main.py}` (3-file pattern).

**Apply to:** ogni write path che genera audit row + NATS notify (audit.actions, hitl.approvals.new/resolved, hitl.governor.alert).

**Order invariant (D-56):** PG sync blocking FIRST → NATS fire-and-forget. PG failure = agent ABORT. NATS failure = log warning + outbox enqueue.

### §4.2 — Background asyncio Loop (used by: Plan §3.6 EscalationSupervisor, §3.7 OutboxRetry, §3.8 Governor)

**Source:** `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py:146-158` (`_flush_loop`).

**Pattern:**
```python
async def _loop(self) -> None:
    try:
        while not self._shutdown.is_set():
            await asyncio.sleep(self._interval_s)
            await self._scan_once()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.error("loop_error", error=str(exc))
```

### §4.3 — YAML Policy Loader (used by: Plan §3.6 escalation-sla + safety-interlock, §3.2 routing, §3.9 budgets)

**Source:** `packages/sft-domain/src/sft_domain/glossary/_loader.py:21-80`.

**Apply to:** ogni file YAML in `packages/sft-agents/src/sft_agents/policies/` (routing.yaml, escalation-sla.yaml, safety-interlock.yaml, budgets.yaml).

**Pattern:** `yaml.safe_load(path.read_text(encoding="utf-8"))` → `pydantic.BaseModel.model_validate(entry)` → `lru_cache(maxsize=N)` per cold-start performance. `invalidate_cache()` utility per test.

### §4.4 — Idempotent Migration (used by: Plan §3.11 — 4 files)

**Source:** `infra/migrations/timescale/001_create_sensor_events.sql` (intero file).

**Apply to:** 002 + 003 + 004 + 005 nuove migrations.

**Pattern primitives:**
- `CREATE TABLE IF NOT EXISTS`
- `CREATE SCHEMA IF NOT EXISTS`
- `CREATE INDEX IF NOT EXISTS`
- `DO $$ BEGIN IF NOT EXISTS (...) THEN ... END IF; END $$;` per ALTER TABLE
- `create_hypertable(..., if_not_exists => TRUE)`
- `add_compression_policy(..., if_not_exists => TRUE)`
- `add_retention_policy(..., if_not_exists => TRUE)`

### §4.5 — Pydantic v2 Frozen Model (used by: tutti i model nuovi — §3.1, §3.6, §3.9, §3.10)

**Source:** `services/ot-bridge/src/svc_ot_bridge/models.py:22-72` + `packages/sft-tools/src/sft_tools/replay/models.py:25-63`.

**Boilerplate canonico:**
```python
from __future__ import annotations
from datetime import datetime
from typing import Annotated, Literal
from pydantic import BaseModel, Field, field_validator

class XyzModel(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    some_field: Annotated[str, Field(min_length=1, description="...")]
    ts: Annotated[datetime, Field(description="UTC tz-aware")]

    @field_validator("ts")
    @classmethod
    def _tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError(f"Field must be tz-aware, got naive: {v!r}")
        return v
```

---

## §5. No Analog Found (planner uses RESEARCH.md instead)

| Work-area | Reason | RESEARCH.md fallback |
|-----------|--------|----------------------|
| `sft_agents/supervisor/` (LangGraph StateGraph + hybrid routing) | LangGraph è nuovo in repo Phase 4 | RESEARCH §3.1 + §3.4 (StateGraph composition + rules+LLM routing) |
| `sft_agents/llm/` (provider-agnostic LLM factory) | langchain-ollama/openai entrambi nuovi | RESEARCH §4 (ChatOllama + ChatOpenAI signature parity) |
| `apps/api-gateway/` (FastAPI app) | scaffold vuoto Phase 1; FastAPI assente nel resto | RESEARCH §8 (api-gateway endpoint structure); standard FastAPI patterns |
| `sft_agents/hitl/interrupt-resume` (LangGraph Command resume) | LangGraph specific | RESEARCH §6 (full HITL cycle) |
| LangGraph middleware decorator (`sft_agents/budget/`) | LangGraph specific | RESEARCH §3.5 (middleware node insertion before LLM/Tool) |
| Langfuse v3 callback wiring (CORE-06) | Langfuse è nuovo | RESEARCH §5 (LangfuseCallbackHandler) |

**Per ognuno di questi:** il planner mette comunque le acceptance criteria cross-cutting di §2 (Pydantic frozen, asyncpg $N, yaml.safe_load, datetime.now(UTC), structlog JSON, env-var fail-fast, conventional-commits scope).

---

## §6. Wave Mapping (allineato CONTEXT.md downstream_guidance + RESEARCH §wave structure)

| Wave | Plans | Pattern groups | Primary analog files |
|------|-------|----------------|----------------------|
| **Wave 1 (foundation)** | 04-01 SDK base | §3.1 (Pydantic models + ABC) | `sft-tools/replay/models.py`, `sft-domain/glossary/_loader.py` |
| **Wave 2 (3 parallel)** | 04-02 PG migrations / 04-03 LLM adapter+Langfuse / 04-04 NATS AUDIT_STREAM | §3.11 migrations / §3.5 LLM / §3.12 nats bootstrap | `001_create_sensor_events.sql`, `ot-bridge/main.py:62-71`, `scripts/nats-bootstrap-streams.py:85-167` |
| **Wave 3 (2 parallel)** | 04-05 Supervisor+clusters+checkpointer / 04-06 HITL middleware+escalation+governor | §3.2-§3.4 supervisor/clusters/checkpointer / §3.6-§3.8 HITL/escalation/governor | `sft-tools/timescale/query.py`, `ot-bridge/timescale_writer.py:146-158`, `glossary/_loader.py` |
| **Wave 4 (integration sequential)** | 04-07 api-gateway+HITL E2E / 04-08 replay+ROADMAP edit+Langfuse smoke | §3.13 api-gateway / §3.15 E2E test / §3.10 replay / §3.16 ROADMAP | `tests/integration/test_e2e_sim_to_timescale.py`, `sft-tools/replay/cmapss.py`, `tests/conftest.py:84-147` |

---

## §7. Metadata

- **Analog search scope:** `packages/sft-{domain,tools,assets,agents,contracts}/`, `services/ot-bridge/`, `infra/migrations/timescale/`, `scripts/`, `tests/`, `apps/api-gateway/`, `apps/agents/` (Phase 1 scaffolds)
- **Files scanned:** ~35 (Python source) + 4 (SQL/YAML) + 8 (pyproject.toml)
- **Files Read (analog extraction):** 14
- **Patterns extraction date:** 2026-05-18
- **Coverage:** 13/16 work-areas con analogo concreto in-repo (81%); 3/16 (supervisor/LLM/api-gateway) richiedono fallback RESEARCH.md per pattern primario, ma TUTTI applicano i 12 cross-cutting idioms §2.

---

## PATTERNS COMPLETE

**Coverage 13/16 (81%) con analoghi in-repo concreti; 3/16 (supervisor LangGraph, LLM adapter, api-gateway FastAPI) richiedono fallback RESEARCH.md per pattern primario.**

**Idioma cardine identificato:** il dual-write `PG-sync + NATS-async` di `services/ot-bridge/{timescale_writer.py, nats_publisher.py, main.py}` è il template 1:1 per `sft_agents/audit/` (CORE-08, HITL-05, D-56) — il planner deve istruire la replica letterale di quei file con due delta soli: REVOKE UPDATE/DELETE su `audit.actions` (DDL-side) + outbox table per retry NATS (vs Phase 3 che logga-e-droppa).

**Garanzie cross-cutting:** ogni plan Phase 4 deve esibire le 12 convenzioni §2 (Pydantic v2 frozen+extra=forbid, asyncpg `$N` placeholders only, statement_cache_size=0, datetime.now(UTC) tz-aware, yaml.safe_load, structlog JSON, env-var fail-fast, conventional commit scope `feat(04-NN-slug):`, @nxlv/python uv-project layout, pytest @markers + asyncio_mode=auto, pathlib paths, idempotent DDL/scripts).
