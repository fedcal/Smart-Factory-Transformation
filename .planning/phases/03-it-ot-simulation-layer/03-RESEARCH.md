# Phase 3: IT/OT Simulation Layer — Research

**Researched:** 2026-05-18
**Domain:** OPC-UA simulation + NATS JetStream event bus + TimescaleDB ingestion + dataset replay (LangChain Tools) — textile factory IT/OT data substrate
**Confidence:** HIGH (asyncua / nats-py / asyncpg / TimescaleDB / docker isolation / C-MAPSS — all verified against official docs); MEDIUM (LangChain BaseTool + Pydantic v2 interplay — verified but evolving)

## Summary

Phase 3 monta il substrato eventi sensori che alimenta tutti gli agenti downstream (Phase 4-7). Lo stack è 100% locked da Phase 1 e dal CONTEXT D-44..D-52: `asyncua` 1.1.x come server/client OPC-UA dentro `sim-textile` (singolo processo asyncio con namespace per asset_family, D-50), `nats-py` 2.14.x come publisher in `ot-bridge` con JetStream `WorkQueuePolicy` su subject `sensor.events.<family>.<asset_id>.<tag>` (D-52), `asyncpg` 0.31.x come writer su TimescaleDB hypertable `sensor_events` con compression e retention idiomatici (D-49), `langchain-core` 1.x come base per i 3 Tools in `packages/sft-tools/` (D-46/D-47). L'enforcement del data-diode è 3-layer (D-51): Docker network ACL via `internal: true` semantica + pytest integration test + grep static-analysis.

I quattro rischi-pilastro che il planner deve materializzare in task espliciti sono: **(1)** asyncpg pool tuning su carico 5k msg/s sostenuto (`statement_cache_size=0` + batch `executemany` vs binary `COPY` — quest'ultimo wins di ~10x ma richiede formattazione manuale); **(2)** TimescaleDB compression API: dalla 2.18.0 segnata "Old API" ma ancora supportata, NON migriamo a `add_columnstore_policy()` (rischio di lock su API non-LTS); **(3)** Docker `internal: true` ferma il routing L3, ma il container con due interfacce (`ot-bridge` su ot+it network) può sempre bridge: l'enforcement è "ot-bridge non APRE socket inbound dal lato it-network", garantito a livello applicativo + verificato da pytest; **(4)** LangChain `BaseTool` async pattern richiede Pydantic v2 fields-only schema, niente mix con v1.

**Primary recommendation:** Stick con stack già locked (asyncua 1.1.8, nats-py 2.14.0, asyncpg 0.31.0, langchain-core 1.x, prometheus-client 0.25.0, pydantic 2.13.x). Wave-1 priorità è `packages/sft-assets/` + `packages/sft-tools/` (foundation). Wave-2 parallelizza sim-textile + ot-bridge + Timescale migration. Wave-3 è docker-compose extension + pytest data-diode test + smoke load test in CI. Wave-4 è full load test 5k×60s + IOT-09 ingest schema docs.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-44 — Fault injection: per-asset YAML profiles + 5 calibrated defaults**
- Profile files in `simulators/sim-textile/profiles/{loom,spinning,warping,dyeing,finishing}.yaml`
- Schema: `asset_family`, `sample_rate_hz`, `fault_injection: {nan_probability, drift, jitter, burst_noise, alarm_storm}`, `default_baseline`
- CLI: `uv run sim-textile --profile loom` o env `SIM_PROFILES=loom,dyeing`

**D-45 — Asset registry: nuovo package `packages/sft-assets/`**
- Layout: `registry.yaml` + `models.py` (Pydantic Asset, Tag frozen+extra=forbid) + `loader.py` (lru_cache) + `schemas/asset.schema.json`
- Seed: ~30 asset reali (12 LOOM + 8 SPIN + 4 WARP + 4 DYE + 2 STEN), ~50 tag distribuiti per family

**D-46 — Replay loaders: LangChain Tool registry**
- 2 Tools: `replay_cmapss(unit_id, time_range, sensor_subset) -> pd.DataFrame`, `replay_uci(dataset, asset_id, time_range) -> pd.DataFrame`
- Schema unificato `ReplayRecord` (asset_id, timestamp, sensor_id, value, unit, source_dataset, source_unit)
- `BaseTool` con `args_schema` Pydantic + async-first (`_arun` priorizzato)

**D-47 — Tool registry location: nuovo `packages/sft-tools/`**
- Phase 3 ships: `replay_cmapss`, `replay_uci` + `query_timescale(asset_id, time_range, tags)`
- Layout: `src/sft_tools/{replay/{cmapss,uci,models}.py, timescale/query.py}`
- Exports `REPLAY_TOOLS`, `TIMESCALE_TOOLS`

**D-48 — Load test scenario: steady-state 60s + realistic asset mix**
- Mix asset ~5,000 msg/s totali (60% loom, 20% spinning, 10% dyeing/finishing, 10% warping)
- Payload 256-512 byte JSON `{asset_id, tag_id, timestamp_utc, value, unit, quality_code}`
- Durata: 60s steady-state, NO ramp-up
- Tool: custom asyncio harness `tests/load/harness.py` con `asyncpg.Pool(min=10, max=20)`, NO Locust/k6
- Target: p99 < 200ms (IOT-10)
- Smoke in CI 1k×10s, full 5k×60s PR-label gated

**D-49 — TimescaleDB retention: chunk=1d / compress=7d / drop=90d**
- Hypertable `sensor_events(asset_id TEXT, tag_id TEXT, timestamp_utc TIMESTAMPTZ, value DOUBLE PRECISION, unit TEXT, quality_code SMALLINT, source TEXT)`
- `chunk_time_interval => INTERVAL '1 day'`
- `compress_segmentby='asset_id, tag_id'`, `compress_orderby='timestamp_utc DESC'`
- `add_compression_policy('sensor_events', INTERVAL '7 days')`
- `add_retention_policy('sensor_events', INTERVAL '90 days')`
- Continuous aggregates DEFERRED a Phase 4-5

**D-50 — Simulator orchestration: docker-compose service + YAML profile**
- Singolo container long-running `sim-textile` su `ot-network` only
- Singolo processo asyncio in `sim_textile.main:run()` con `asyncio.create_task(asset_emitter(profile))` per profile abilitato
- OPC-UA server `opc.tcp://sim-textile:4840` (anonymous policy in PoC per A-018)
- Prometheus `/metrics` su porta 8080: `sim_events_emitted_total{asset_family,asset_id,tag_id}`, `sim_fault_injected_total{type,asset_family}`, `sim_message_rate_per_second`
- CLI: `uv run --project simulators/sim-textile sim-textile --profile loom --time-scale 2.0`

**D-51 — OT Bridge data-diode enforcement: 3-layer**
- Layer 1: docker-compose networks `ot-network` + `it-network`, `sim-textile` su SOLO ot, `nats`/`timescaledb` su SOLO it, `ot-bridge` su entrambe (unico bridge)
- Layer 2: pytest `tests/integration/test_data_diode.py` — un container fake-agent su it-network NON può aprire socket OPC-UA verso sim-textile (assert `ConnectionRefusedError | TimeoutError | OSError`)
- Layer 3: grep static-analysis `grep -E 'set_value|write_attribute' src/svc_ot_bridge/` deve dare 0 match

**D-52 — NATS subject hierarchy**
- `sensor.events.<asset_family>.<asset_id>.<tag_id>` — es. `sensor.events.loom.LOOM-01.warp_tension`
- `sensor.alarms.<asset_family>.<asset_id>` — alarm storm aggregate
- `audit.ot.<service>` — log strutturato Phase 11 governance
- JetStream stream `SENSOR_EVENTS` con `WorkQueuePolicy` retention + maxAge `7d`

### Claude's Discretion

- **OPC-UA namespace pattern:** `urn:mantis:<asset_family>:<asset_id>` (freeform), documentato in `docs/docs/it-ot/opcua-schema.md`
- **OPC-UA endpoint:** `opc.tcp://sim-textile:4840`, anonymous policy (A-018)
- **asyncpg connection pool:** `min_size=10, max_size=20`, `statement_cache_size=0`, DSN da env `TIMESCALE_DSN`
- **Pydantic models:** v2 frozen + extra=forbid
- **Logging:** structlog JSON con `service`, `asset_id`, `tag_id`, `event_type`, output stderr
- **Metrics:** prometheus-client in sim-textile + ot-bridge, endpoint `/metrics`, NO Grafana dashboards (Phase 11)
- **Replay dataset paths:** `simulators/sim-textile/replay-data/` (gitignored). Download script `scripts/download-replay-datasets.py` con SHA256 verify in `replay-data/CHECKSUMS.txt`
- **CI:** estende `.github/workflows/ci.yml` con step "Run IT/OT integration tests" + step "Run IT/OT load test (smoke)" 1k×10s
- **Time skew:** simulator emits `datetime.now(UTC)` come `timestamp_utc`; ot-bridge ri-stampa `server_received_ts` ma NON modifica `timestamp_utc` (A-004 invariante)
- **Quality codes:** OPC-UA StatusCode integer pass-through (Good=0, BadOutOfService=0x80AF0000, etc.)
- **Asset registry seed:** 12 LOOM-01..12, 8 SPIN-01..08, 4 WARP-01..04, 4 DYE-01..04, 2 STEN-01..02

### Deferred Ideas (OUT OF SCOPE)

- OPC-UA tag naming standard ISA-95 / AAS → Phase 7+ industrial integration
- Continuous aggregates OEE/MTBF → Phase 4-5
- K8s NetworkPolicy + Helm extension per data-diode prod → Phase 11
- MCP wrapping di sft-tools → Phase 7+
- Simulator burst test 10k msg/s capacity headroom → Phase 11
- Hot/warm/cold tier storage (S3 archive after 90d) → Phase 11
- Asset registry DB-backed → Phase 11
- PredictiveMaintenance training pipeline su replay data → Phase 7
- OPC-UA write commands path (HITL_REQUIRED) → never in PoC scope
- Real PLC integration → A-013 scope-limit
- Multi-tenant simulator → A-012 scope-limit
- ERP integration → A-014 scope-limit

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IOT-01 | Simulatore Python custom della linea tessile (telai, filatoi, orditoi, finissaggio, tintoria) | asyncua server multi-namespace pattern (§Standard Stack, §Pattern 1); D-44 fault profiles |
| IOT-02 | Mock OPC-UA server (asyncua) con nodi browsabili e sottoscrizione eventi | asyncua 1.1.8 verified PyPI; `register_namespace` + `add_object` + `add_variable` pattern |
| IOT-03 | Fault injection nel simulatore: NaN, drift, jitter, burst noise, alarm storm | D-44 YAML profile schema; fault engine pattern §Pattern 2 |
| IOT-04 | Bus eventi NATS JetStream con subject hierarchy `sensor.events.*`, `agent.actions.*`, `audit.*` | nats-py 2.14.0 verified; D-52 subject schema; idempotent stream creation §Pattern 3 |
| IOT-05 | OT Bridge separato (microservizio): legge OPC-UA → pubblica su NATS, nessun path inverso | D-51 3-layer enforcement; docker-compose `internal: true` semantics §Common Pitfalls #4 |
| IOT-06 | TimescaleDB per ingest time-series sensori (hypertable con compression policy) | D-49 SQL idiomatic; compression API 2.18 Old API still supported §State of the Art |
| IOT-07 | Replay loader per dataset NASA C-MAPSS integrato come tool | C-MAPSS schema 21 sensors §Pattern 6; LangChain BaseTool async §Pattern 5 |
| IOT-08 | Replay loader per dataset UCI Manufacturing integrato come tool | Stesso pattern di IOT-07 |
| IOT-09 | Ingest schema documentato con esempi (asset registry, tag dictionary, units of measure) | D-45 asset registry layout + JSON Schema validation |
| IOT-10 | Test di carico simulato fino a 5K msg/s con assert di latency p99 < 200ms | D-48 harness; asyncpg COPY vs executemany trade-off §Pattern 4; load test in `tests/load/` |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Generazione eventi sensori (fault injection) | OT Simulator (Level 1/0 mock) | — | Per ISA-95 (§ARCHITECTURE.md), Level 0/1 è dove vivono i sensori; sim-textile occupa questo strato in PoC |
| Esposizione OPC-UA browseable | OT Simulator (Level 2 mock) | — | Server `asyncua.Server` espone l'address space; client OPC-UA solo da ot-bridge (data-diode) |
| Subscribe OPC-UA + normalize | DMZ Bridge (Level 3.5) | — | ot-bridge è l'unico componente sulla DMZ; legge OPC-UA, produce `SensorEvent` Pydantic |
| Publish NATS JetStream | IT Backbone (Level 3) | — | Stream `SENSOR_EVENTS` su it-network; nessun agent ha credenziali publish (audit-only di lettura) |
| Time-series ingestion | IT Storage (Level 3) | — | TimescaleDB hypertable; ot-bridge è writer, agents/tools sono reader-only |
| Replay loader (C-MAPSS/UCI) | IT Tools | — | LangChain Tools standalone — NESSUN path verso OPC-UA/NATS-publish; output diretto come DataFrame al chiamante (Phase 4 agent) |
| Asset registry lookup | Shared metadata (sft-assets) | — | Pydantic models import-only; consumato da sim-textile (gen OPC-UA nodes), ot-bridge (routing), Phase 4+ agents (filter eventi) |
| Tool registry | Shared library (sft-tools) | — | Importato da Phase 4+ agent packages; nessuna istanza runtime in Phase 3 |
| Prometheus metrics scrape | Observability (cross-tier) | — | sim-textile + ot-bridge espongono `/metrics`; Grafana scrape è Phase 11 |

**Tier ownership rule violations to flag during plan-check:**
- Se un task mette logica di fault-injection in ot-bridge → SBAGLIATO (fault è OT-side property)
- Se un task fa subscribe NATS da sim-textile → SBAGLIATO (sim non vede it-network)
- Se un task fa OPC-UA write call da ot-bridge → CRITICAL (viola data-diode)

## Project Constraints (from CLAUDE.md)

Nessun `./CLAUDE.md` esiste a root del repo (verificato con ls). Le sole constraint applicabili sono i rules globali utente caricati via `~/.claude/rules/common/*.md`:

| Source | Constraint | Phase 3 Impact |
|--------|------------|----------------|
| coding-style.md | Immutability — niente mutate, sempre new copy | Pydantic models frozen=True (già D-44 lock); fault injection state via dataclass replace |
| coding-style.md | File 200-400 lines typical, 800 max | sim-textile.main split per fault type, ot-bridge split publisher/normalizer/writer |
| coding-style.md | Error handling explicit, no silent swallow | OPC-UA disconnect, NATS publish failure, asyncpg pool exhaustion — tutti devono logged + alerted |
| coding-style.md | Input validation at boundaries | YAML profile → Pydantic validate; OPC-UA tag → registry lookup; NATS payload → schema validate |
| testing.md | 80% coverage min; TDD red-green-refactor | Wave 0 (Nyquist) crea test scaffolding prima dell'implementation |
| security.md | No hardcoded secrets, env vars only | `TIMESCALE_DSN`, `NATS_URL`, OPC-UA password (Phase 11 hardening) via env |
| security.md | SQL injection prevention (parameterized queries) | asyncpg `$1, $2` placeholders, no f-string SQL — applicato in tutti i writer/query |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncua | 1.1.8 [VERIFIED: PyPI 2026-05-18] | OPC-UA async client+server per sim-textile e ot-bridge | Async nativo (asyncio), maintainer attivo FreeOpcUa, ~35k downloads/week, LGPL; deprecato `python-opcua` sincrono |
| nats-py | 2.14.0 [VERIFIED: PyPI 2026-05-18] | NATS JetStream client async per ot-bridge publisher | Client ufficiale nats.io Python; JetStream API native (`js.add_stream`, `js.publish`, `js.subscribe`) |
| asyncpg | 0.31.0 [VERIFIED: PyPI 2026-05-18] | Postgres/TimescaleDB driver async per writer/load test | Driver Python più veloce per Postgres (binary protocol nativo); pool built-in; raccomandato da Tiger Data per ingest [CITED: tigerdata.com] |
| langchain-core | 1.4.0 [VERIFIED: PyPI 2026-05-18] | `BaseTool` base class per i 3 Tools in sft-tools | Phase 4 LangGraph supervisor consuma `BaseTool` via `langgraph.prebuilt.ToolNode` standard |
| pydantic | 2.13.x [VERIFIED: PyPI 2026-05-18] | Modelli frozen+extra=forbid per `SensorEvent`, `Asset`, `Tag`, `ReplayRecord`, fault profile schemas | Già in stack Phase 1+2; v2 frozen pattern matches sft-domain convention |
| pyyaml | 6.0.3 [VERIFIED: PyPI 2026-05-18] | Loader per fault profiles + asset registry YAML | `yaml.safe_load` ONLY (mai `yaml.load`) — pattern Phase 2 |
| jsonschema | 4.26.0 [VERIFIED: PyPI 2026-05-18] | JSON Schema validation per asset registry + fault profile in CI | Già Phase 2 pattern per glossary/assumption schemas |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| prometheus-client | 0.25.0 [VERIFIED: PyPI 2026-05-18] | Esporre `/metrics` da sim-textile + ot-bridge | Counter per `sim_events_emitted_total`, Histogram per `ingest_latency_seconds`, Gauge per `nats_pending_acks` |
| structlog | 25.5.0 [VERIFIED: PyPI 2026-05-18] | Logging JSON strutturato | Field-bound logger per ogni service; `bind(asset_id=..., tag_id=...)` pattern |
| pandas | 2.3.x [VERIFIED: PyPI 2026-05-18] | DataFrame output dei replay Tools | `replay_cmapss` / `replay_uci` ritornano `pd.DataFrame`; pandas 2.x non 3.x (sft-tools deps PIN minor) |
| pytest + pytest-asyncio | 8.x / 0.24+ | Test framework | Già Phase 1; aggiungere `tests/integration/`, `tests/load/` directory |
| testcontainers | 4.14.2 [VERIFIED: PyPI 2026-05-18] | TimescaleDB + NATS ephemeral container per integration tests | Alternativa a docker-compose `up` durante pytest (più rapido e isolato) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncua server | open62541 + python binding | open62541 è C-native (più veloce); ma asyncio integration non-native = costo dev > benefit; rejected |
| nats-py | aiokafka | Stack già locked NATS (Phase 1); Kafka è overkill (<10k msg/s); rejected già in STACK.md |
| asyncpg | psycopg3 async | psycopg3 supporta async ma protocollo testuale; asyncpg binary è ~2x più veloce su INSERT pesante [CITED: tigerdata.com benchmarks] |
| Alembic migrations | Raw SQL files | Alembic è overhead per 1 hypertable + 2 policy SQL statements; raw SQL `migrations/001_create_sensor_events.sql` (idempotent `CREATE TABLE IF NOT EXISTS`) basta per Phase 3. Alembic deferred Phase 4+ quando arriveranno migrations correlate (orchestrator state, audit) |
| `executemany` per insert batch | `COPY` binary protocol | COPY è ~10x più veloce ma richiede formattazione manuale del payload binario asyncpg. **Raccomandato:** `executemany` con batch_size 500-1000 per load test 5k msg/s (sostenibile e più semplice da debug). COPY come fallback se p99 > 200ms in misurazione [CITED: jacopofarina.eu] |
| Locust / k6 load test | Custom asyncio harness | Già locked D-48 — Locust HTTP overhead non riflette OPC-UA→NATS path |

**Installation (Phase 3 totale):**
```bash
# packages/sft-assets/
uv add pydantic pyyaml jsonschema
uv add --dev pytest pytest-asyncio

# packages/sft-tools/
uv add langchain-core pydantic pandas asyncpg
uv add --dev pytest pytest-asyncio

# simulators/sim-textile/
uv add asyncua pydantic pyyaml structlog prometheus-client
uv add --dev pytest pytest-asyncio

# services/ot-bridge/
uv add asyncua nats-py asyncpg pydantic structlog prometheus-client
uv add --dev pytest pytest-asyncio testcontainers

# tests/load/ (workspace root)
uv add --dev asyncpg nats-py pytest pytest-asyncio
```

**Version verification (eseguito 2026-05-18):**
```
asyncua 1.1.8 (latest 1.1.x; Python >=3.10)
nats-py 2.14.0 (latest stable)
asyncpg 0.31.0 (latest stable)
prometheus-client 0.25.0 (latest stable)
structlog 25.5.0 (latest stable)
langchain-core 1.4.0 (1.x LTS line; Pydantic v2 native)
pydantic 2.13.4 (Phase 1+2 align)
pyyaml 6.0.3 (latest stable; CVE-fixed)
jsonschema 4.26.0
pandas 2.3.x (PIN minor — pandas 3.x might break DataFrame API surface for Tools)
testcontainers 4.14.2
```

## Package Legitimacy Audit

> Eseguito con `slopcheck scan --pkg pypi <name>` su tutti i pacchetti recommended. slopcheck v0.0.4 installato via `pip install slopcheck --break-system-packages`.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| asyncua | pypi | 5+ yrs | ~35k/wk | github.com/FreeOpcUa/opcua-asyncio | [OK] | Approved |
| nats-py | pypi | 5+ yrs | high | github.com/nats-io/nats.py | [OK] | Approved |
| asyncpg | pypi | 7+ yrs | very high | github.com/MagicStack/asyncpg | [OK] | Approved |
| prometheus-client | pypi | 8+ yrs | very high | github.com/prometheus/client_python | [WARN: naming pattern flag — "ends with -client"] but slopcheck confirms established | Approved |
| structlog | pypi | 9+ yrs | very high | github.com/hynek/structlog | [OK] | Approved |
| langchain-core | pypi | 2+ yrs | very high | github.com/langchain-ai/langchain | [WARN: naming pattern flag — "starts with langchain-"] but slopcheck confirms established | Approved |
| pydantic | pypi | 8+ yrs | very high | github.com/pydantic/pydantic | [OK] | Approved |
| pyyaml | pypi | 14+ yrs | very high | github.com/yaml/pyyaml | [OK] | Approved |
| jsonschema | pypi | 12+ yrs | very high | github.com/python-jsonschema/jsonschema | [OK] | Approved |
| pandas | pypi | 16+ yrs | very high | github.com/pandas-dev/pandas | [OK] | Approved |
| python-frontmatter | pypi | 10+ yrs | high | github.com/eyeseast/python-frontmatter | [WARN: naming pattern flag — "starts with python-"] but slopcheck confirms established | Approved (solo se serve in sft-assets per SOP references; opzionale) |
| testcontainers | pypi | 6+ yrs | high | github.com/testcontainers/testcontainers-python | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none (i 3 WARN sono pattern-naming hints, non SUS — slopcheck dichiara esplicitamente "established")

## Architecture Patterns

### System Architecture Diagram

```mermaid
flowchart LR
    subgraph OT[ot-network — Level 1/0 + 2 mock]
        SIM[sim-textile<br/>asyncua.Server :4840<br/>5 namespace per asset_family]
    end

    subgraph DMZ[Level 3.5 — DMZ Bridge]
        BR[ot-bridge<br/>asyncua.Client → Pydantic normalize → publish/write]
    end

    subgraph IT[it-network — Level 3]
        NATS[(NATS JetStream<br/>stream SENSOR_EVENTS<br/>subject sensor.events.*)]
        TS[(TimescaleDB<br/>hypertable sensor_events<br/>chunk=1d compress=7d drop=90d)]
        TOOLS[sft-tools<br/>BaseTool<br/>replay_cmapss<br/>replay_uci<br/>query_timescale]
    end

    subgraph META[Shared metadata]
        ASSETS[sft-assets<br/>registry.yaml<br/>30 asset · 50 tag]
    end

    SIM -->|OPC-UA subscribe| BR
    BR -->|publish sensor.events.&lt;family&gt;.&lt;asset_id&gt;.&lt;tag&gt;| NATS
    BR -->|asyncpg executemany batch| TS
    ASSETS -.import models.-> SIM
    ASSETS -.import models.-> BR
    ASSETS -.import models.-> TOOLS
    TOOLS -.async query.-> TS

    REPLAY[(replay-data/<br/>NASA C-MAPSS<br/>UCI Manufacturing)]
    REPLAY -.csv read.-> TOOLS

    AGENT[Phase 4+ Agents<br/>LangGraph nodes]
    AGENT -->|subscribe consumer.agent.*| NATS
    AGENT -->|invoke BaseTool| TOOLS

    classDef otStyle fill:#ffe4e1,stroke:#c00
    classDef dmzStyle fill:#fff4e1,stroke:#c80
    classDef itStyle fill:#e1f5e1,stroke:#080
    class SIM otStyle
    class BR dmzStyle
    class NATS,TS,TOOLS itStyle
```

**Data flow:** sim-textile genera (fault injection) → OPC-UA server → ot-bridge subscribe → normalize a `SensorEvent` Pydantic → fan-out a NATS (per agents) e TimescaleDB (per replay/historical query). Agents Phase 4+ leggono SOLO via NATS subscribe o tool invocation — mai diretto verso OPC-UA. Replay tools leggono CSV statici, non transitano per OPC-UA/NATS.

### Recommended Project Structure

```
packages/sft-assets/
├── pyproject.toml
├── project.json                      # Nx target: test, validate-registry
├── src/sft_assets/
│   ├── __init__.py                  # exports Asset, Tag, load_assets, load_tag_dict
│   ├── models.py                    # Pydantic Asset, Tag (frozen+extra=forbid)
│   ├── loader.py                    # load_assets(), load_tag_dict() con lru_cache
│   ├── registry.yaml                # ~30 asset seed
│   └── schemas/
│       └── asset.schema.json        # JSON Schema Draft 2020-12
└── tests/
    ├── test_models.py
    ├── test_loader.py
    └── test_registry_validation.py

packages/sft-tools/
├── pyproject.toml
├── project.json                      # Nx target: test
├── src/sft_tools/
│   ├── __init__.py                  # exports REPLAY_TOOLS, TIMESCALE_TOOLS
│   ├── replay/
│   │   ├── __init__.py
│   │   ├── models.py                # ReplayRecord Pydantic
│   │   ├── cmapss.py                # ReplayCMAPSSTool(BaseTool)
│   │   └── uci.py                   # ReplayUCITool(BaseTool)
│   └── timescale/
│       ├── __init__.py
│       └── query.py                 # QueryTimescaleTool(BaseTool)
└── tests/
    ├── test_replay_cmapss.py
    ├── test_replay_uci.py
    └── test_query_timescale.py

simulators/sim-textile/
├── pyproject.toml                    # asyncua, pydantic, pyyaml, structlog, prometheus-client
├── project.json
├── profiles/
│   ├── loom.yaml
│   ├── spinning.yaml
│   ├── warping.yaml
│   ├── dyeing.yaml
│   └── finishing.yaml
├── src/sim_textile/
│   ├── __init__.py
│   ├── main.py                      # entry: asyncio.run(run())
│   ├── server.py                    # asyncua.Server setup, register_namespace per family
│   ├── emitter.py                   # asset_emitter(profile): asyncio.create_task loop
│   ├── faults/
│   │   ├── __init__.py
│   │   ├── nan.py                   # NaN injection
│   │   ├── drift.py                 # incremental drift
│   │   ├── jitter.py                # ±band_pct jitter
│   │   ├── burst.py                 # burst noise
│   │   └── alarm_storm.py           # threshold-based storm
│   ├── models.py                    # FaultProfile Pydantic (frozen)
│   ├── metrics.py                   # prometheus Counter/Gauge/Histogram
│   └── cli.py                       # argparse: --profile, --time-scale
└── tests/
    ├── test_faults.py
    ├── test_emitter.py
    └── test_profile_validation.py

services/ot-bridge/
├── pyproject.toml                    # asyncua, nats-py, asyncpg, pydantic, structlog
├── project.json
├── src/svc_ot_bridge/
│   ├── __init__.py
│   ├── main.py                      # entry: asyncio.run(run())
│   ├── opcua_client.py              # asyncua.Client + subscribe handler
│   ├── normalizer.py                # OPC-UA data → SensorEvent Pydantic
│   ├── nats_publisher.py            # nats-py JetStream publish con subject derivation
│   ├── timescale_writer.py          # asyncpg Pool batch INSERT (executemany batch=500)
│   ├── models.py                    # SensorEvent Pydantic frozen
│   └── metrics.py                   # ingest_latency_seconds Histogram, etc.
└── tests/
    ├── test_normalizer.py
    ├── test_subject_derivation.py
    ├── test_publisher.py
    └── test_writer.py

infra/migrations/timescale/
└── 001_create_sensor_events.sql     # CREATE TABLE + create_hypertable + ALTER + add_compression_policy + add_retention_policy (idempotent)

infra/compose/
├── core.yml                         # già esistente Phase 1 — non toccare
├── obs.yml                          # già esistente
└── sim.yml                          # ESTENDERE: aggiungere sim-textile + ot-bridge services + ot-network/it-network

scripts/
├── download-replay-datasets.py      # NASA C-MAPSS + UCI download con SHA256 verify
├── nats-bootstrap-streams.py        # idempotent JetStream stream creation
└── timescale-migrate.py             # apply 001_*.sql idempotent

tests/
├── integration/
│   ├── test_data_diode.py           # D-51 Layer 2 enforcement
│   └── test_e2e_sim_to_timescale.py # sim-textile → ot-bridge → NATS → TimescaleDB roundtrip
└── load/
    ├── harness.py                   # custom asyncio publisher 5k msg/s
    ├── test_ingestion_smoke.py      # 1k×10s gate CI
    └── test_ingestion_throughput.py # 5k×60s full load (PR label)

docs/docs/it-ot/
├── ingest-schema.md                 # IT — IOT-09 documentation
└── opcua-schema.md                  # IT — namespace pattern
docs/docs/en/it-ot/
├── ingest-schema.md
└── opcua-schema.md
```

### Pattern 1: asyncua Server multi-namespace per asset_family

**What:** Singolo `asyncua.Server` con un namespace OPC-UA per ogni `asset_family`. Ogni asset (LOOM-01, SPIN-03, ecc.) è un Object node sotto il namespace appropriato, con Variable nodes per ogni `tag_id` definito in registry.

**When to use:** D-50 single-process design. Tutti i 30 asset condividono un solo processo asyncio + un solo server `:4840`.

**Example:**
```python
# Source: https://opcua-asyncio.readthedocs.io/en/latest/usage/get-started/minimal-server.html
# Adapted for D-50 multi-namespace single-process design
import asyncio
from asyncua import Server, ua
from sft_assets import load_assets, load_tag_dict

async def setup_server() -> Server:
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/sft-textile/")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])  # A-018 anonymous PoC

    assets = load_assets()                    # list[Asset] from sft-assets registry
    tag_dict = load_tag_dict()                # dict[str, Tag]

    family_to_ns_idx: dict[str, int] = {}
    family_root_nodes: dict[str, "Node"] = {}

    # one namespace per asset_family
    for family in sorted({a.asset_family for a in assets}):
        uri = f"urn:mantis:{family}"
        idx = await server.register_namespace(uri)
        family_to_ns_idx[family] = idx
        family_root = await server.nodes.objects.add_folder(idx, family)
        family_root_nodes[family] = family_root

    # add an Object per asset, Variables per tag
    asset_variables: dict[tuple[str, str], "Node"] = {}
    for asset in assets:
        idx = family_to_ns_idx[asset.asset_family]
        root = family_root_nodes[asset.asset_family]
        asset_obj = await root.add_object(idx, asset.asset_id)
        for tag_ref in asset.tags:
            tag = tag_dict[tag_ref.tag_id]
            var = await asset_obj.add_variable(
                idx, tag.tag_id, 0.0, varianttype=ua.VariantType.Double
            )
            await var.set_writable(False)  # data-diode at protocol level
            asset_variables[(asset.asset_id, tag.tag_id)] = var
    return server, asset_variables

async def run():
    server, vars_map = await setup_server()
    async with server:
        while True:
            # emitter loop populates vars_map via var.write_value(new_value)
            await asyncio.sleep(0.1)
```

### Pattern 2: Fault injection state machine (per-asset)

**What:** Ogni `asset_emitter` task mantiene uno stato `EmitterState` (dataclass frozen, replace-based mutation) che traccia: baseline value corrente per tag, drift accumulato, contatore eventi recenti per alarm storm threshold. Fault è applicato come funzione pura `apply_fault(state, profile, t) -> (new_state, new_value)`.

**When to use:** Tutti gli emitter task in sim-textile. Pattern testabile (puro), composable (chained fault types), e auditabile (state diff visibile).

**Example:**
```python
# Source: internal pattern; aligned with coding-style.md immutability rule
from dataclasses import dataclass, replace
from datetime import datetime, UTC
import random
import math

@dataclass(frozen=True)
class EmitterState:
    drift_accumulated: float
    recent_alarms: tuple[datetime, ...]   # immutable tuple, not list

def apply_drift(state: EmitterState, rate_per_hour: float, dt_seconds: float) -> tuple[EmitterState, float]:
    delta = rate_per_hour * (dt_seconds / 3600.0)
    new_state = replace(state, drift_accumulated=state.drift_accumulated + delta)
    return new_state, new_state.drift_accumulated

def apply_jitter(value: float, band_pct: float) -> float:
    return value * (1.0 + random.uniform(-band_pct/100.0, band_pct/100.0))

def maybe_nan(value: float, nan_probability: float) -> float:
    return float("nan") if random.random() < nan_probability else value

def check_alarm_storm(state: EmitterState, now: datetime, threshold: int, window_s: int = 30) -> tuple[EmitterState, bool]:
    cutoff = now.timestamp() - window_s
    pruned = tuple(t for t in state.recent_alarms if t.timestamp() >= cutoff)
    storm = len(pruned) >= threshold
    new_state = replace(state, recent_alarms=pruned + (now,))
    return new_state, storm
```

### Pattern 3: NATS JetStream idempotent stream + durable consumer setup

**What:** Bootstrap script `scripts/nats-bootstrap-streams.py` chiama `js.add_stream(config=...)` con configurazione completa. Idempotency: aggiungere uno stream con stessi parametri è no-op; aggiungere con parametri diversi solleva error → l'operatore deve `js.update_stream`.

**When to use:** Eseguito una volta dopo `docker compose up`, prima di lanciare ot-bridge. Documentato in `infra/compose/README.md` come step di setup.

**Example:**
```python
# Source: docs.nats.io/using-nats/developer/develop_jetstream/streams (idempotent semantics)
import asyncio
import nats
from nats.js.api import StreamConfig, RetentionPolicy, StorageType

async def bootstrap():
    nc = await nats.connect("nats://nats:4222")
    js = nc.jetstream()
    cfg = StreamConfig(
        name="SENSOR_EVENTS",
        subjects=["sensor.events.>", "sensor.alarms.>"],
        retention=RetentionPolicy.WORK_QUEUE,
        max_age=7 * 24 * 3600 * 1_000_000_000,   # 7d in nanoseconds
        storage=StorageType.FILE,
        max_msgs_per_subject=-1,
        discard="old",
    )
    try:
        await js.add_stream(config=cfg)
    except nats.js.errors.BadRequestError as e:
        # stream exists with different config — update
        await js.update_stream(config=cfg)
    await nc.close()

if __name__ == "__main__":
    asyncio.run(bootstrap())
```

Per i consumer (lato agent Phase 4+), pattern raccomandato:
```python
# Durable consumer per agent — explicit ack
from nats.js.api import ConsumerConfig, AckPolicy, DeliverPolicy

await js.subscribe(
    "sensor.events.loom.>",
    durable="anomaly_detector_loom",      # durable name = resume on reconnect
    manual_ack=True,                       # explicit ack
    config=ConsumerConfig(
        ack_policy=AckPolicy.EXPLICIT,
        deliver_policy=DeliverPolicy.NEW,  # only events from now (no replay backlog)
        max_ack_pending=1000,
    ),
    cb=handler,
)
```

### Pattern 4: asyncpg batch INSERT con executemany (recommended) + COPY fallback

**What:** ot-bridge accumula `SensorEvent` in buffer (size=500 o flush ogni 100ms — whichever first), poi `pool.acquire() -> conn.executemany(stmt, rows)` con statement precompilato.

**When to use:** Default per IOT-10 (5k msg/s target). Se p99 > 200ms misurato, fallback a `conn.copy_records_to_table` (binary COPY).

**Example:**
```python
# Source: https://www.tigerdata.com/blog/how-to-build-applications-with-asyncpg-and-postgresql
# Adapted for Phase 3 D-49 schema + D-48 load target
import asyncpg
from contextlib import asynccontextmanager

INSERT_STMT = """
INSERT INTO sensor_events
  (asset_id, tag_id, timestamp_utc, value, unit, quality_code, source)
VALUES ($1, $2, $3, $4, $5, $6, $7)
"""

class TimescaleWriter:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def start(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=10,
            max_size=20,
            statement_cache_size=0,   # TimescaleDB dynamic plan: skip prepared cache
            command_timeout=10.0,
        )

    async def write_batch(self, events: list[SensorEvent]) -> None:
        rows = [
            (e.asset_id, e.tag_id, e.timestamp_utc, e.value, e.unit, e.quality_code, e.source)
            for e in events
        ]
        async with self._pool.acquire() as conn:
            await conn.executemany(INSERT_STMT, rows)

    async def write_batch_copy(self, events: list[SensorEvent]) -> None:
        # Fallback path: ~10x faster but more rigid
        rows = [
            (e.asset_id, e.tag_id, e.timestamp_utc, e.value, e.unit, e.quality_code, e.source)
            for e in events
        ]
        async with self._pool.acquire() as conn:
            await conn.copy_records_to_table(
                "sensor_events",
                records=rows,
                columns=("asset_id","tag_id","timestamp_utc","value","unit","quality_code","source"),
            )
```

### Pattern 5: LangChain BaseTool async pattern Pydantic v2

**What:** `class XxxTool(BaseTool)` con `name`, `description`, `args_schema: type[BaseModel]`, e implementazione `_arun` async (raise NotImplementedError su `_run` per forzare async usage).

**When to use:** Tutti e 3 i tools in sft-tools (`replay_cmapss`, `replay_uci`, `query_timescale`).

**Example:**
```python
# Source: https://python.langchain.com/api_reference/core/tools/langchain_core.tools.base.BaseTool.html
# langchain-core 1.x is Pydantic v2 native (1.0+ migration complete)
from datetime import datetime
from typing import Literal
import pandas as pd
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

class ReplayCMAPSSArgs(BaseModel):
    unit_id: int = Field(..., description="C-MAPSS engine unit identifier (1-260)")
    time_range: tuple[datetime, datetime] | None = Field(
        None, description="Optional UTC time range; None = full trajectory"
    )
    sensor_subset: list[str] | None = Field(
        None, description="Subset of 21 sensor IDs (sensor_1..sensor_21); None = all"
    )
    dataset: Literal["FD001", "FD002", "FD003", "FD004"] = Field("FD001")

class ReplayCMAPSSTool(BaseTool):
    name: str = "replay_cmapss"
    description: str = (
        "Replay NASA C-MAPSS turbofan run-to-failure data, mapped to a textile asset "
        "via sft-assets registry. Returns DataFrame with columns: "
        "asset_id, timestamp, sensor_id, value, unit, source_dataset, source_unit."
    )
    args_schema: type[BaseModel] = ReplayCMAPSSArgs

    def _run(self, *args, **kwargs):
        raise NotImplementedError("Use async _arun")

    async def _arun(
        self,
        unit_id: int,
        time_range: tuple[datetime, datetime] | None = None,
        sensor_subset: list[str] | None = None,
        dataset: str = "FD001",
    ) -> pd.DataFrame:
        # implementation: read CSV from replay-data/, filter, map to ReplayRecord, return DataFrame
        ...
```

### Pattern 6: NASA C-MAPSS data loader concettuale (textile mapping)

**What:** C-MAPSS è run-to-failure di motori turbofan (NASA Ames). Schema: 26 columns per row → `(unit_id, cycle, op_setting_1, op_setting_2, op_setting_3, sensor_1, ..., sensor_21)`. Mapping concettuale **M:1**: ogni `unit_id` C-MAPSS è mappato a un nostro asset Mantis tramite registry (es. `unit_id=1 → LOOM-01`). I 21 sensori sono mappati a tag generici "stress proxy" (es. `sensor_2 → vibration_proxy`, `sensor_7 → temperature_proxy`).

**When to use:** `replay_cmapss` Tool consuma CSV `train_FD001.txt`, applica mapping, emette ReplayRecord per ogni (asset_id, tag_id, timestep).

**Sub-dataset reference [CITED: deepwiki.com/barryib1603/NASA-Turbofan-Jet-Engine-RUL-prediction-C-MAPSS]:**
- FD001: 100 train / 100 test trajectories — 1 condition (Sea Level), 1 fault mode (HPC Degradation)
- FD002: 260 train / 259 test — 6 conditions, 1 fault mode (HPC Degradation)
- FD003: 100 train / 100 test — 1 condition, 2 fault modes (HPC + Fan Degradation)
- FD004: 248 train / 249 test — 6 conditions, 2 fault modes (HPC + Fan Degradation)

**Phase 3 ships:** FD001 only (semplificazione PoC). FD002-FD004 deferred a Phase 7 (PredictiveMaintenance training).

**UCI Manufacturing variants:** 3 dataset disponibili:
- "Air Quality" — temporal sensor data, mapped a `dyeing` ambient sensors
- "Energy Efficiency" — building energy benchmark, mapped a `finishing` energy proxy
- "Production" — manufacturing process, mapped a `loom` throughput proxy

### Anti-Patterns to Avoid

- **Multi-process sim-textile (one process per asset):** Violates D-50 — overhead docker 5x, debug cross-container difficile. Single asyncio process con `asyncio.create_task` per asset.
- **Mutating SensorEvent in normalizer:** Violates immutability. Pydantic frozen + new model.
- **f-string SQL nei query Timescale tool:** Violates security.md (SQL injection). Sempre `$1, $2` placeholders.
- **Catch-all `except Exception` nei publisher loop:** Silenzia errori NATS publish. Log+re-raise+pause su backoff.
- **Stato globale fault counters:** Pattern 2 lock pure-function + immutable state.
- **Continuous aggregates day-one:** Phase 3 over-engineering. Solo raw hypertable.
- **Alembic per 1 sola migration:** Overhead non-giustificato. Raw SQL idempotent.
- **Locust HTTP overhead nel load test:** D-48 lock. Asyncio harness diretto.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OPC-UA server + address space management | Custom socket server con binary protocol parsing | asyncua | Maturo, async-native, decine di edge case (subscription throttling, server diagnostics, security policies); 5+ anni di production hardening |
| OPC-UA → struct deserialization | Manual `ua.VariantType` decoding | asyncua `node.read_value()` / DataChangeNotification | asyncua gestisce type-coercion + array dims + status code propagation automaticamente |
| NATS stream + consumer setup | TCP-level NATS protocol | nats-py JetStream high-level API | Idempotent stream creation, ack semantics, durable consumer state — tutti edge case già coperti |
| Postgres connection pool | Manual psycopg connection management | asyncpg built-in `create_pool` | Pool lifecycle, prepared statement cache, connection recycling, dead connection detection |
| Time-series chunking | Custom partition tables + cron | TimescaleDB `create_hypertable` | Automatic chunk routing, distributed query planning, compression transparent |
| Compression columnar | Custom dump-and-compact job | TimescaleDB `add_compression_policy` | Background worker triggered by schedule; rollback supportato |
| Retention drop | Custom DELETE+VACUUM | TimescaleDB `add_retention_policy` | Drops chunk metadata + storage atomically; no VACUUM bloat |
| JSON Schema validation | hand-written field-by-field checks | jsonschema library | Draft 2020-12 compliance, format validators, error messages |
| Fault injection (NaN/drift/jitter) primitives | Manual numpy noise generators | Pattern 2 above + standard library `random` | Phase 3 fault is event-domain not signal-domain; numpy is overkill; explicit state machine is auditable |
| LangChain Tool wiring | Custom function-calling adapter | `langchain_core.tools.BaseTool` | Phase 4 LangGraph `ToolNode` consuma BaseTool standard; rolling-your-own = breaking later |
| Prometheus exposition format | Manual text export | prometheus-client | Buckets, exemplars, multiprocess mode, OpenMetrics compat |
| pytest fixtures for testcontainer Postgres | Custom Docker subprocess management | testcontainers-python | Lifecycle, network isolation, port mapping, cleanup |

**Key insight:** Ogni componente del Phase 3 ha un peer library che ha 5+ anni di edge-case hardening. Hand-rolling è un anti-pattern documentato in ARCHITECTURE.md (§15) e nei rules globali (testing.md "Use existing libraries before custom").

## Runtime State Inventory

> **N/A — Phase 3 è greenfield.** Non c'è rename/refactor/migration involved. Tutti i nuovi file sono creati ex-novo; gli unici file modificati sono:
> - `infra/compose/sim.yml` (estensione, non rename)
> - `.github/workflows/ci.yml` (aggiunta step, non rename)
> - `Makefile` (aggiunta target, non rename)
> - `simulators/sim-textile/{pyproject.toml,src/}` (riempimento scaffold Phase 1)
> - `services/ot-bridge/{pyproject.toml,src/}` (riempimento scaffold Phase 1)
>
> Sezione omessa per Phase 3. La sezione tornerà in Phase 4+ quando saranno toccati modelli persistenti (langgraph_checkpoints, agent_actions) o in Phase 11 quando il rename `sim-textile` → `textile-factory-sim` venisse considerato.

## Common Pitfalls

### Pitfall 1: asyncua subscription throttling under high message rate

**What goes wrong:** Sotto 1k+ msg/s di DataChangeNotification, asyncua client può accodare notifiche con backpressure su asyncio queue interna; alcune callback vengono ritardate, asincronia perde fairness.

**Why it happens:** asyncua `Subscription` ha publishing interval di default 100ms; client deve ack ogni notification batch. Se la callback del bridge fa work pesante (es. sync `pool.execute`), il loop si congestionа.

**How to avoid:**
- Imposta `publishing_interval=50` (ms) e `samples_per_publish=10` per batching
- Nella callback `datachange_notification`, fai solo `asyncio.create_task(handle_event(...))` o `queue.put_nowait(event)` → handler async separato
- Misura `nats_pending_acks` Gauge: se cresce, applica backpressure (rate-limit emitter side)

**Warning signs:**
- `asyncua.common.subscription` warning "subscription overflow"
- Latency simulator-to-NATS > 1s

### Pitfall 2: TimescaleDB compression API "Old" status in 2.18

**What goes wrong:** Da TimescaleDB 2.18.0, `add_compression_policy` + `ALTER TABLE … SET (timescaledb.compress)` sono marcati "Old API" in favore di `add_columnstore_policy()` (hypercore).

**Why it happens:** Hypercore (lanciato 2024-2025) è il nuovo storage engine columnar; "Old API" still **supportata** [CITED: docs.timescale.com/api/latest/compression] ma terminology shift verso "columnstore".

**How to avoid:**
- Phase 3 USA "Old API" deliberatamente: D-49 lock e codice esempi industria sono allineati
- Documenta in `infra/migrations/timescale/001_create_sensor_events.sql` un commento: `-- Using legacy compression API (TimescaleDB 2.18.x); migration to columnstore deferred to Phase 11 if/when hypercore semantic settles`
- Pin TimescaleDB image alla versione 2.18.x in compose (già `timescale/timescaledb:2.18.0-pg16` da Phase 1 SUMMARY)

**Warning signs:**
- TimescaleDB log warning "compression policy is deprecated, use add_columnstore_policy"
- Upgrade TimescaleDB a 3.x in Phase 11 → migration script richiesto

### Pitfall 3: nats-py JetStream stream config drift fails idempotently

**What goes wrong:** Se ot-bridge è ricreato con `subjects=["sensor.events.>"]` ma il bootstrap script l'ha già creato con `subjects=["sensor.events.>", "sensor.alarms.>"]`, `js.add_stream` solleva `BadRequestError` "stream name already in use with different config".

**Why it happens:** JetStream `add_stream` è idempotent SOLO se la config matches esattamente [CITED: docs.nats.io/using-nats/developer/develop_jetstream/streams].

**How to avoid:**
- Bootstrap script TRY add_stream → ON BadRequestError DO update_stream (Pattern 3)
- Documentare config sorgente di verità: `scripts/nats-bootstrap-streams.py` è la sola source of truth, mai modificare config in compose/env
- Test integration: tear down + bootstrap + verify config matches

**Warning signs:**
- ot-bridge fail-to-start con NATS error "stream config mismatch"
- nats-server log "stream update rejected"

### Pitfall 4: docker-compose `internal: true` does NOT enforce L4 isolation through bridge container

**What goes wrong:** `ot-network` con `internal: true` impedisce route verso il default-gateway, MA un container con **due** interfacce (ot+it network, come ot-bridge) può sempre forwardare traffico se applicazione lo facesse. Internal flag opera a livello L3 routing, non L4 application.

**Why it happens:** Docker bridge `internal: true` = nessun NAT verso host external; non è un application firewall [CITED: docs.docker.com/reference/compose-file/networks/].

**How to avoid (D-51 3-layer):**
- Layer 1 (network ACL): isola sim-textile da it-network, nats/timescale da ot-network — i container NON dotati di doppia interfaccia non si vedono mai
- Layer 2 (pytest enforcement): un fake-agent container su SOLO it-network tenta `opc.tcp://sim-textile:4840` e DEVE failure (sim-textile non risolve DNS dal lato it)
- Layer 3 (application): ot-bridge codice ha 0 chiamate `set_value` / `write_attribute` verso OPC-UA; verificato da grep CI

**Warning signs:**
- Test data-diode fallisce silenziosamente perché DNS resolution lato it-network risolve comunque (caso edge: se Docker embedded DNS è shared)
- ot-bridge logs mostrano OPC-UA write tentati (regression bug)

### Pitfall 5: pydantic v1/v2 mix in langchain BaseTool

**What goes wrong:** Vecchi tutorial mostravano `from langchain.pydantic_v1 import BaseModel` per workaround durante langchain<0.3. Con langchain-core 1.x questo è **errore**: Pydantic v2 è native, mix v1/v2 causa `args_schema` validation crash.

**Why it happens:** Migration LangChain → Pydantic v2 completa in langchain-core 0.3+, full v2 in 1.x. Vecchi snippet importano `pydantic.v1`.

**How to avoid:**
- SOLO `from pydantic import BaseModel, Field` (v2 native)
- Verifica in CI: `grep -E "pydantic\.v1|from langchain.pydantic_v1" packages/sft-tools/` deve dare 0 match
- Pin `langchain-core>=1.0,<2.0` in pyproject.toml

**Warning signs:**
- `TypeError: Schema is not valid Pydantic v2 schema`
- LangGraph ToolNode init failure

### Pitfall 6: asyncpg `statement_cache_size=0` necessary on TimescaleDB but slow on plain Postgres

**What goes wrong:** asyncpg di default usa prepared statement cache (1024 entries) → grande speedup. Su TimescaleDB con planner dinamico per chunk routing, cached plan può diventare stale → query degradate / errori "cached plan must not change result type".

**Why it happens:** TimescaleDB ha planner adaptation per chunk constraints; plan cache asyncpg conflicts.

**How to avoid:**
- Set `statement_cache_size=0` SOLO sul pool che parla a TimescaleDB
- Mantieni cache abilitata su pool che parla a Postgres puro (se in futuro il bridge avrà dual-DB)
- Documenta in `ot-bridge/src/svc_ot_bridge/timescale_writer.py` con comment

**Warning signs:**
- asyncpg error `cached plan must not change result type`
- Performance regression dopo aggiunta hypertable chunks

### Pitfall 7: Datetime tz-naive in TimescaleDB inserts

**What goes wrong:** sim-textile emette `datetime.now()` (tz-naive); TimescaleDB column è `TIMESTAMPTZ`; asyncpg converte tz-naive come "local time of server" → drift di ore.

**Why it happens:** Python `datetime.now()` ritorna tz-naive; asyncpg non auto-coerce a UTC.

**How to avoid:**
- Pattern obbligatorio: `datetime.now(UTC)` ovunque (A-004 lock)
- Pydantic field validator: `@field_validator("timestamp_utc") def _aware(cls, v): assert v.tzinfo is not None`
- CI grep: `grep -rE "datetime\.now\(\)" simulators/ services/` deve dare 0 match

**Warning signs:**
- Time skew tra event_time e ingest_time
- TimescaleDB chunks misallineati

## Code Examples

### Asset registry loader con lru_cache

```python
# Source: pattern Phase 2 sft-domain glossary loader (verified working)
from functools import lru_cache
from pathlib import Path
import yaml
from pydantic import BaseModel, ConfigDict, Field

class Tag(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    tag_id: str
    unit: str
    sample_rate_hz: float
    semantic_type: str

class Asset(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    asset_id: str
    asset_family: str
    line_id: str
    opcua_namespace: str
    tags: tuple[Tag, ...] = Field(default_factory=tuple)
    status: str = "active"

_REGISTRY_PATH = Path(__file__).parent / "registry.yaml"

@lru_cache(maxsize=1)
def load_assets() -> tuple[Asset, ...]:
    with _REGISTRY_PATH.open() as f:
        raw = yaml.safe_load(f)  # SAFE_LOAD mandatory (security.md)
    return tuple(Asset.model_validate(item) for item in raw)

@lru_cache(maxsize=1)
def load_tag_dict() -> dict[str, Tag]:
    out: dict[str, Tag] = {}
    for asset in load_assets():
        for tag in asset.tags:
            if tag.tag_id in out:
                # cross-asset tag definitions must be consistent
                assert out[tag.tag_id] == tag, f"Tag {tag.tag_id} inconsistent"
            out[tag.tag_id] = tag
    return out
```

### TimescaleDB migration SQL idempotente

```sql
-- Source: D-49 + docs.timescale.com/api/latest/compression/
-- File: infra/migrations/timescale/001_create_sensor_events.sql
-- Idempotent: safe to run multiple times

CREATE TABLE IF NOT EXISTS sensor_events (
  asset_id      TEXT NOT NULL,
  tag_id        TEXT NOT NULL,
  timestamp_utc TIMESTAMPTZ NOT NULL,
  value         DOUBLE PRECISION,
  unit          TEXT,
  quality_code  SMALLINT,
  source        TEXT NOT NULL DEFAULT 'live'  -- 'live' | 'replay_cmapss' | 'replay_uci'
);

SELECT create_hypertable(
  'sensor_events',
  'timestamp_utc',
  chunk_time_interval => INTERVAL '1 day',
  if_not_exists => TRUE
);

-- Compression config: idempotent via re-run-safe ALTER + DO block
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM timescaledb_information.hypertables
    WHERE hypertable_name = 'sensor_events' AND compression_enabled = true
  ) THEN
    ALTER TABLE sensor_events SET (
      timescaledb.compress,
      timescaledb.compress_segmentby = 'asset_id, tag_id',
      timescaledb.compress_orderby = 'timestamp_utc DESC'
    );
  END IF;
END $$;

-- Compression policy (7 days)
SELECT add_compression_policy(
  'sensor_events',
  compress_after => INTERVAL '7 days',
  if_not_exists => TRUE
);

-- Retention policy (90 days)
SELECT add_retention_policy(
  'sensor_events',
  drop_after => INTERVAL '90 days',
  if_not_exists => TRUE
);

-- Useful indexes for typical agent queries
CREATE INDEX IF NOT EXISTS idx_sensor_events_asset_time
  ON sensor_events (asset_id, timestamp_utc DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_events_tag_time
  ON sensor_events (tag_id, timestamp_utc DESC);
```

### docker-compose dual-network excerpt

```yaml
# Source: D-51 Layer 1 + docs.docker.com/reference/compose-file/networks/
# File: infra/compose/sim.yml (EXTEND existing)

networks:
  sft-ot:
    driver: bridge
    internal: false   # OPC-UA può exit (clients opcua external); ingress inbound limitato a containers su questa rete
  sft-it:
    driver: bridge

services:
  sim-textile:
    build:
      context: ../../simulators/sim-textile
    container_name: sft-sim-textile
    environment:
      - SIM_PROFILES=loom,spinning,warping,dyeing,finishing
      - SIM_TIME_SCALE=1.0
      - OPCUA_BIND=0.0.0.0:4840
      - METRICS_PORT=8080
    networks:
      - sft-ot                          # ONLY ot-network
    ports:
      - "4840:4840"
      - "8080:8080"

  ot-bridge:
    build:
      context: ../../services/ot-bridge
    container_name: sft-ot-bridge
    environment:
      - OPCUA_URL=opc.tcp://sim-textile:4840
      - NATS_URL=nats://nats:4222
      - TIMESCALE_DSN=postgresql://sft:sft_dev_pass@timescaledb:5432/sft
    networks:
      - sft-ot                          # both networks — unique bridge container
      - sft-it
    depends_on:
      sim-textile:
        condition: service_started
      nats:
        condition: service_healthy
      timescaledb:
        condition: service_healthy

  nats:
    networks:
      - sft-it                          # nats SOLO it-network

  timescaledb:
    networks:
      - sft-it                          # timescaledb SOLO it-network
```

### pytest data-diode integration test (D-51 Layer 2)

```python
# Source: D-51 lock — pattern test enforcement; uses testcontainers-python network isolation
# File: tests/integration/test_data_diode.py
import asyncio
import pytest
import asyncua

@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_cannot_reach_sim_textile_via_it_network():
    """A container on sft-it network MUST NOT be able to open an OPC-UA socket to sim-textile (which is on sft-ot only).

    Expected: ConnectionRefusedError, TimeoutError, or OSError 'Network is unreachable' within 5s.
    """
    # Test assumption: docker-compose up has been performed with networks sft-ot and sft-it.
    # This test runs from within a temp container on sft-it network (CI orchestration).

    client = asyncua.Client(url="opc.tcp://sft-sim-textile:4840", timeout=5)
    with pytest.raises((ConnectionRefusedError, asyncio.TimeoutError, OSError)):
        async with asyncio.timeout(5):
            async with client:
                await client.get_root_node()


@pytest.mark.integration
def test_ot_bridge_has_no_opcua_write_calls():
    """Layer 3: static analysis — ot-bridge code MUST NOT call any OPC-UA write API."""
    import subprocess
    result = subprocess.run(
        ["grep", "-rE", r"set_value|write_attribute|write_value", "services/ot-bridge/src/"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1, (    # 1 = no match (good); 0 = match (bad)
        f"OT bridge contains OPC-UA write calls — violates D-51 Layer 3:\n{result.stdout}"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `python-opcua` synchronous | `asyncua` (opcua-asyncio) | 2022 deprecation | Phase 3 USA asyncua; old library not maintained |
| TimescaleDB `ALTER TABLE … SET (compress)` | `add_columnstore_policy` (hypercore) | 2.18.0 (2024) Old API marked | Phase 3 stays on Old API (still supported); migration to hypercore deferred to Phase 11 |
| LangChain BaseTool with `pydantic.v1` | langchain-core 1.x + Pydantic v2 native | langchain 0.3+ (2024), full in 1.0 (2025) | Phase 3 uses v2 only; pin langchain-core>=1.0,<2.0 |
| nats.py 2.7.x with asynchronous JetStream stream creation hand-rolled | nats-py 2.14.x with native `js.add_stream(StreamConfig)` API | nats-py 2.10+ | Phase 3 uses StreamConfig; idempotent via try/except update |
| Manual `executemany` per row | asyncpg `pool.executemany(stmt, rows)` batch | asyncpg 0.25+ | Phase 3 default; COPY as fallback |
| RAGAS for ML eval (irrelevant for Phase 3) | n/a | — | Not applicable Phase 3 |
| C-MAPSS as ad-hoc CSV reader | Standardized via LangChain Tool | Phase 3 ships | Agents Phase 4+ consume via ToolNode |

**Deprecated/outdated:**
- `python-opcua` (sync) — non maintained, blocking IO
- LangChain agents API legacy (AgentExecutor) — Phase 4 uses LangGraph `create_react_agent` / supervisor pattern
- Pre-JetStream Core NATS for persistent streams — Phase 3 uses JetStream for `WorkQueue` + `Limits`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `executemany` batch=500 sostiene 5k msg/s p99<200ms su TimescaleDB single-node con `min_size=10, max_size=20` pool | §Standard Stack Alternatives + Pattern 4 | LOW — se misurazione fallisce, fallback documentato a `copy_records_to_table` (10x faster); load test in Wave 4 misura empiricamente |
| A2 | TimescaleDB 2.18.x "Old API" compression rimane supportata fino a Phase 11 (almeno 18 mesi) | §Pitfall 2 + State of the Art | LOW — TimescaleDB ha track record di backward compat 3+ anni; mitigato da pin di versione `2.18.0-pg16` in Phase 1 docker-compose |
| A3 | NASA C-MAPSS FD001 (100 trajectories, 21 sensors) è sufficiente per `replay_cmapss` Tool in Phase 3 | §Pattern 6 | LOW — agenti Phase 7 (PredictiveMaintenance) potranno aggiungere FD002-FD004 senza schema change |
| A4 | UCI Manufacturing dataset variants (air_quality, energy, production) sono disponibili pubblicamente e replicabili | §Pattern 6 | MEDIUM — URL UCI possono cambiare; mitigare con SHA256 verify + checkpoint locale `replay-data/CHECKSUMS.txt` (D Claude discretion) |
| A5 | Docker bridge `internal: true` + dual-interface ot-bridge pattern è enforced sufficientemente da Layer 1+2+3 combinato | §Pitfall 4 + D-51 | MEDIUM — runtime enforcement testato in pytest, ma se la rete CI usa Docker DNS shared, test può false-pass; mitigation richiede `--network` flag esplicito |
| A6 | `statement_cache_size=0` non degrada throughput TimescaleDB più di 20% rispetto a cache abilitata | §Pitfall 6 + Pattern 4 | LOW — confermato da Tiger Data benchmark [CITED: tigerdata.com]; alternative path = `prepared_statement_cache_size=0` solo per writer pool |
| A7 | nats-py 2.14.0 `StreamConfig.retention=WorkQueuePolicy` ack-explicit pattern è stabile in 2.14.x line | §Pattern 3 | LOW — verified contro docs.nats.io 2026-05-18 |
| A8 | LangChain BaseTool con `_arun` async + Pydantic v2 `args_schema` funziona transparente con `langgraph.prebuilt.ToolNode` | §Pattern 5 | LOW — langchain-core 1.x e langgraph 0.4+ sono coordinate; mitigare con integration test in sft-tools |
| A9 | asyncua server con singolo processo asyncio sostiene ~5k var-write/s (sim-textile emission rate) senza degradare publishing interval | §Pattern 1 + D-50 | MEDIUM — non verified empirically in research; smoke test Wave 4 misurerà. Fallback: split per-asset-family in N processi se single fails |
| A10 | NASA C-MAPSS dataset license è compatibile con redistribuzione in repo (oppure download-on-demand pattern è sufficiente) | §Claude's Discretion replay-data | MEDIUM — C-MAPSS è open dataset NASA (US gov work, public domain), UCI è BSD-style; **verify before redistributing in repo**; pattern download-on-demand (script `scripts/download-replay-datasets.py` gitignored data dir) is the safe default |
| A11 | `prometheus-client` esposizione `/metrics` su porta 8080 in entrambi sim-textile + ot-bridge non crea collisione con Phase 11 osservabilità | §Standard Stack | LOW — port 8080 esposta solo via docker-compose; Phase 11 può espandere a sidecar pattern |
| A12 | Asset registry (~30 asset, ~50 tag) ha schema YAML stabile per Phase 3-11 senza breaking change | §Pattern Asset loader | MEDIUM — additive changes via versioned schema OK; breaking rename richiederebbe data migration in Phase 11 |

**Confirmation needed before plan execution:**
- **A4** (UCI dataset URLs): planner deve aggiungere task verifica URLs in Wave-1 (download script test)
- **A5** (network enforcement edge): planner deve aggiungere CI test su CI runner reale (GitHub Actions docker-in-docker) + documentare in `tests/integration/README.md`
- **A10** (C-MAPSS license redistribution): default = download-on-demand (NO redistribute); planner conferma con utente o mette CHECKSUMS-only in repo

## Open Questions (RESOLVED)

1. **NATS JetStream replicas in docker-compose dev**
   - What we know: ARCHITECTURE.md menziona `replicas=1 (dev) / 3 (prod)`; D-52 non lock replicas count
   - What's unclear: Phase 3 dev compose deve usare replicas=1 (sufficient per smoke test) o configurare cluster (3 nats container)?
   - **RESOLVED:** Phase 3 ships `replicas=1` (single nats container, già nel Phase 1 compose). Cluster (3 nats container) è deferred a Phase 11 prod hardening. Implementato in **Plan 03-06 Task 1** (docker-compose extension); documentato in `infra/compose/README.md`.

2. **TimescaleDB chunk_time_interval per replay data**
   - What we know: D-49 lock chunk=1d per `sensor_events`; replay data può essere injected con timestamp passati (es. C-MAPSS cycle 1 → 2014-01-01)
   - What's unclear: Replay insertion crea N chunk storici per asset → bloat? Strategy: separato hypertable `sensor_events_replay`?
   - **RESOLVED:** Phase 3 usa UNA hypertable `sensor_events` con colonna `source` (`'live' | 'replay_cmapss' | 'replay_uci'`); chunk creation è automatico, retention 90d copre replay storici. Se PredictiveMaintenance Phase 7 avrà bisogno retention diversa per replay → separate hypertable in Phase 7. Implementato in **Plan 03-05 Task 1** (migration SQL).

3. **NATS subject `audit.ot.<service>` content scope**
   - What we know: D-52 lock subject `audit.ot.<service>` ma scope content non definito
   - What's unclear: ot-bridge logga audit eventi (connection open, publish failure)? Sim-textile logga (fault injected timeline)?
   - **RESOLVED:** Solo ot-bridge pubblica `audit.ot.bridge` con eventi `{ts, level, event_type, details}` (Pydantic-validated). Sim-textile NON pubblica audit (livello OT; audit è IT-side concern). Schema governance dettagliato → Phase 11. Implementato in **Plan 03-04 Task 1** (ot-bridge publisher).

4. **Asset registry CI validation: where to put the validator?**
   - What we know: D-45 dichiara `schemas/asset.schema.json` Draft 2020-12
   - What's unclear: Validation script lives in `packages/sft-assets/tests/test_registry_validation.py` (pytest) o `scripts/validate-asset-registry.py` (standalone CI)?
   - **RESOLVED:** Entrambi. Pytest `packages/sft-assets/tests/test_registry_validation.py` per local fast feedback + standalone CLI `scripts/validate-asset-registry.py` per CI integration (allinea pattern Phase 2 `validate-glossary-coverage.py`). Implementato in **Plan 03-01 Task 1** (pytest) + **Plan 03-01 Task 2** (script CLI).

5. **`replay_cmapss` mapping policy per `unit_id` → asset_id**
   - What we know: D-46 dice "M:1 mapping registry-driven"
   - What's unclear: Mapping è statico (esempio: unit_id 1..12 → LOOM-01..12) o dinamico (parametro `target_asset_id` nel Tool args)?
   - **RESOLVED:** Tool accetta `target_asset_id: str` opzionale (default: deterministic hash `unit_id` → asset list filtrata per asset_family compatibile); documentato in tool description. Permette test riproducibile + flessibilità per agents. Implementato in **Plan 03-02 Task 1** (replay_cmapss Tool).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Docker Engine | docker-compose stack + testcontainers | ✓ | 29.3.0 | — |
| PostgreSQL client (psql) | Migration apply + debug | ✓ | 17.9 | container-only |
| Python | sim-textile, ot-bridge, sft-tools, sft-assets | ✓ | 3.13.7 (target 3.12 per Phase 1 lock) | pin 3.12 via uv |
| uv | Python package manager | ✓ | 0.11.13 | — |
| NATS server | Event bus | ✓ (via docker-compose Phase 1 sim.yml) | 2.10-alpine | — |
| TimescaleDB | Time-series storage | ✓ (via docker-compose Phase 1 core.yml) | 2.18.0-pg16 | — |
| NASA C-MAPSS dataset CSV | replay_cmapss Tool | ✗ (download required) | — | Script `download-replay-datasets.py` + manual fallback documented in README |
| UCI Manufacturing dataset CSV | replay_uci Tool | ✗ (download required) | — | Same script |
| GitHub Actions docker-in-docker | CI integration test D-51 Layer 2 | ✓ (services context standard) | latest | testcontainers-python local alternative |

**Missing dependencies with no fallback:** none

**Missing dependencies with fallback:**
- NASA C-MAPSS dataset CSV — download-on-demand pattern (script + SHA256 verify, gitignored data dir). Planner adds Wave-2 task.
- UCI Manufacturing dataset CSV — same pattern.

**Python version note:** Working machine has 3.13.7 but Phase 1 locked 3.12. Tutti i pyproject.toml hanno già `requires-python = ">=3.12,<3.13"` (verified). uv risolve 3.12 via toolchain auto-download — nessun action required.

## Validation Architecture

> `workflow.nyquist_validation: true` confirmed in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24+ (Phase 1 lock) |
| Config file | `pyproject.toml` per ogni Nx project (`[tool.pytest.ini_options]`) + workspace-root `tests/conftest.py` (Wave 0) |
| Quick run command | `nx test sft-assets sim-textile ot-bridge sft-tools` (Nx affected pipeline) |
| Full suite command | `nx run-many --target=test --all && pytest tests/integration tests/load -m "not load_full"` |
| Phase gate | `pytest tests/load/test_ingestion_throughput.py --full-load-test` (PR-label gated) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IOT-01 | Simulator emette eventi per 5 asset_family | unit | `pytest simulators/sim-textile/tests/test_emitter.py -k "test_all_families_emit" -x` | ❌ Wave 0 |
| IOT-02 | OPC-UA server browseable + subscribe | integration | `pytest tests/integration/test_opcua_browseable.py -x` | ❌ Wave 0 |
| IOT-03 | Fault injection NaN/drift/jitter/burst/alarm produce eventi corretti | unit | `pytest simulators/sim-textile/tests/test_faults.py -x` | ❌ Wave 0 |
| IOT-04 | NATS pubblica su `sensor.events.<family>.<asset_id>.<tag>` | integration | `pytest tests/integration/test_nats_subjects.py -x` | ❌ Wave 0 |
| IOT-05 | OT Bridge data-diode enforced (3-layer) | integration | `pytest tests/integration/test_data_diode.py -x` | ❌ Wave 0 |
| IOT-06 | TimescaleDB hypertable + compression + retention created | unit | `pytest infra/migrations/timescale/tests/test_migration_idempotent.py -x` | ❌ Wave 0 |
| IOT-07 | replay_cmapss Tool ritorna DataFrame schema-valid | unit | `pytest packages/sft-tools/tests/test_replay_cmapss.py -x` | ❌ Wave 0 |
| IOT-08 | replay_uci Tool ritorna DataFrame schema-valid | unit | `pytest packages/sft-tools/tests/test_replay_uci.py -x` | ❌ Wave 0 |
| IOT-09 | Ingest schema docs + asset registry schema validate | unit | `pytest packages/sft-assets/tests/test_registry_validation.py -x && mkdocs build --strict` | ❌ Wave 0 |
| IOT-10 | Load test 5k msg/s × 60s p99<200ms | load | `pytest tests/load/test_ingestion_throughput.py::test_5k_60s --full-load-test` (PR-label) + `tests/load/test_ingestion_smoke.py` (1k×10s, CI default) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `nx affected --target=test` (auto-scope a project modificato)
- **Per wave merge:** `nx run-many --target=test --all && pytest tests/integration -m "not slow"`
- **Phase gate:** Full suite green + smoke load test + manual full load test via PR label before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `packages/sft-assets/tests/conftest.py` — shared Pydantic fixture (Asset, Tag)
- [ ] `packages/sft-tools/tests/conftest.py` — shared fixture mock TimescaleDB pool + replay data
- [ ] `simulators/sim-textile/tests/conftest.py` — fault profile fixture + frozen time
- [ ] `services/ot-bridge/tests/conftest.py` — testcontainers fixture (TimescaleDB + NATS)
- [ ] `tests/conftest.py` workspace-root — docker-compose lifecycle fixture per integration tests
- [ ] `tests/integration/test_data_diode.py` — D-51 Layer 2 enforcement (sample inline §Pattern + Pattern test_ot_bridge_has_no_opcua_write_calls)
- [ ] `tests/integration/test_e2e_sim_to_timescale.py` — sim → ot-bridge → NATS → Timescale roundtrip (<5s)
- [ ] `tests/load/harness.py` + `test_ingestion_smoke.py` + `test_ingestion_throughput.py` — D-48 harness
- [ ] Framework install: `uv add --dev pytest pytest-asyncio testcontainers` in tutti i 4 new Nx projects + workspace root

*(Wave 0 gap is broad: all test infrastructure is new — Phase 1 has minimal pytest scaffolds, Phase 2 ships content-validation tests but no integration/load.)*

## Security Domain

> `security_enforcement` non disabilitato in config (mode: yolo non affects security), implicit enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (limited) | OPC-UA anonymous in PoC (A-018 documented); NATS no-auth dev (Phase 11 NKey hardening). TimescaleDB password via env (`TIMESCALE_DSN` env). |
| V3 Session Management | no | Stateless services; nessuna user session in Phase 3 |
| V4 Access Control | yes | Docker network ACL (D-51 Layer 1); NATS subject ACL deferred Phase 11 |
| V5 Input Validation | yes | Pydantic frozen+extra=forbid su tutti i model boundaries; `yaml.safe_load`; JSON Schema validate asset registry in CI |
| V6 Cryptography | no (PoC) | Nessun crypto custom; OPC-UA `NoSecurity` policy in PoC (A-018 documented). TLS termination deferred Phase 11 |
| V7 Error Handling | yes | structlog JSON logs senza secret values; exception handling explicit (no silent swallow per coding-style.md) |
| V8 Data Protection | yes (limited) | TimescaleDB credentials via env (no hardcoded); replay data gitignored |
| V14 Configuration | yes | docker-compose `internal: true` semantic + secrets via SealedSecrets (Phase 11) / env (Phase 3 dev) |

### Threat ID Convention (Phase 3 canonical)

The 7 plans in Phase 3 reference threats with short IDs in their `<threat_model>` blocks. These IDs are Phase-3-scoped and map to the threat patterns + ASVS categories below:

| Threat ID | Maps to | Description |
|-----------|---------|-------------|
| `T-V5-yaml` | ASVS V5 + Pattern "YAML unsafe deserialization" | `yaml.safe_load` mandatory; `yaml.load` raw forbidden (CWE-502) |
| `T-V5-pydantic` | ASVS V5 + Pattern "Pydantic boundary validation" | Pydantic v2 frozen + `extra=forbid` on all model boundaries (SensorEvent, Asset, Tag, ReplayRecord, FaultProfile) |
| `T-V5-sql` | ASVS V5 + Pattern "SQL injection in TimescaleDB writer/reader" | asyncpg `$1, $2` placeholders; no f-string SQL; CI grep gate |
| `T-DATA-DIODE` | D-51 + Pattern "OPC-UA write command from agent" | 3-layer enforcement: docker network ACL (Layer 1) + pytest write-attempt fails (Layer 2) + grep static analysis no `set_value/write_attribute/write_value` (Layer 3) |
| `T-NATS-subject` | Pattern "NATS subject explosion (DoS)" | JetStream `max_msgs_per_subject` config; ot-bridge rate limiter `max_ack_pending=1000` |
| `T-V12-asset` | ASVS V12 + Pattern "Asset registry tampering" | JSON Schema Draft 2020-12 validation in CI; gitleaks gate on registry YAML |
| `T-PERF` | IOT-10 + Pattern "asyncpg pool exhaustion under burst" | pool `max_size=20` + `command_timeout=10s`; Prometheus alert on `asyncpg_pool_size_used`; load test gate |

Plans reference these IDs in their `<threat_model>` sections; readers map back here for the canonical definition.

### Known Threat Patterns for {asyncua + nats-py + asyncpg + langchain-core + docker compose stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| OPC-UA write command from agent | Tampering | D-51 3-layer: network ACL + pytest + grep (no `set_value` calls in ot-bridge) |
| YAML unsafe deserialization | Tampering / RCE | `yaml.safe_load` mandatory; grep CI: `grep -rE "yaml\.load\(" packages/ simulators/ services/` deve dare 0 match |
| SQL injection in TimescaleDB writer/reader | Injection | asyncpg `$1, $2` placeholders; CI grep `grep -rE 'f"INSERT|f"SELECT|\.format\(.*INSERT' src/` 0 match |
| NATS subject explosion (DoS) | DoS | NATS JetStream `max_msgs_per_subject` config; ot-bridge rate limiter `max_ack_pending=1000` |
| asyncpg pool exhaustion under burst | DoS | `max_size=20` + `command_timeout=10s`; alert su Prometheus `asyncpg_pool_size_used` |
| Replay data tampering (modified CSV) | Tampering | SHA256 verify via `replay-data/CHECKSUMS.txt`; download script verifies before use |
| Supply chain (compromised package) | Tampering | slopcheck verified (§Package Legitimacy Audit); pin exact versions in pyproject.toml; Syft+Grype scan in CI (Phase 1 license-scan.yml extends to Phase 3 packages) |
| Container escape via dual-network ot-bridge | Elevation of Privilege | `runAsNonRoot: true` already in Phase 1 Helm; container drops capabilities |
| Sensitive log leak (PII / credentials) | Information Disclosure | structlog field redaction processor; never log `TIMESCALE_DSN` raw |
| Datetime tz-naive Information Disclosure (time-skew exploit) | Tampering | Pydantic validator forces `tzinfo is not None` (Pitfall 7 mitigation) |
| OPC-UA endpoint discoverable from external | Information Disclosure | docker-compose port `4840` exposed solo a ot-network; host port mapping only for dev — disable in prod via Phase 11 |

### Phase 3-specific security checks (planner must include)

1. **CI grep gates:**
   - `grep -rE "yaml\.load\(" packages/sft-assets packages/sft-tools simulators/sim-textile services/ot-bridge` → 0 match
   - `grep -rE 'f"(INSERT|SELECT|UPDATE|DELETE)' services/ot-bridge packages/sft-tools` → 0 match
   - `grep -rE "(set_value|write_attribute|write_value)" services/ot-bridge/src/` → 0 match (D-51 Layer 3)
   - `grep -rE "datetime\.now\(\)" simulators/sim-textile services/ot-bridge` → 0 match (must be `datetime.now(UTC)`)
   - `grep -rE "pydantic\.v1|from langchain.pydantic_v1" packages/sft-tools` → 0 match (Pitfall 5)

2. **Pydantic validators on boundaries:**
   - `SensorEvent.timestamp_utc` validator: `tzinfo is not None`
   - `Asset.opcua_namespace` validator: starts with `urn:mantis:`
   - `FaultProfile.fault_injection.nan_probability` validator: `0 <= v <= 1`

3. **Secrets management:** All credentials via env (`.env.example` documented), never in code; planner ensures `.env` already in `.gitignore` from Phase 1.

## Sources

### Primary (HIGH confidence)

- [opcua-asyncio official docs — minimal server](https://opcua-asyncio.readthedocs.io/en/latest/usage/get-started/minimal-server.html) — namespace register pattern, `add_object` / `add_variable`
- [opcua-asyncio GitHub — FreeOpcUa](https://github.com/FreeOpcUa/opcua-asyncio) — version 1.1.x line confirmed, LGPL license, active maintenance
- [NATS docs — Streams (idempotency)](https://docs.nats.io/using-nats/developer/develop_jetstream/streams) — `add_stream` idempotent semantics
- [NATS docs — Consumers (durable + explicit ack)](https://docs.nats.io/using-nats/developer/develop_jetstream/consumers) — durable + AckExplicit reference
- [NATS docs — Consumer Details](https://docs.nats.io/nats-concepts/jetstream/consumers) — AckPolicy reference
- [asyncpg official docs](https://magicstack.github.io/asyncpg/current/usage.html) — pool, `executemany`, `copy_records_to_table`
- [Tiger Data — asyncpg performance](https://www.tigerdata.com/blog/how-to-build-applications-with-asyncpg-and-postgresql) — pool + statement_cache tradeoffs on TimescaleDB
- [Tiger Data — INSERT vs Batch INSERT vs COPY](https://www.tigerdata.com/learn/testing-postgres-ingest-insert-vs-batch-insert-vs-copy) — performance comparison COPY > executemany > execute
- [Tiger Data Documentation — add_compression_policy](https://docs.timescale.com/api/latest/compression/add_compression_policy/) — Old API still supported 2.18+
- [TimescaleDB compression API root](https://docs.timescale.com/api/latest/compression/) — confirms "Old API" status + migration path
- [Docker Compose — Networks reference](https://docs.docker.com/reference/compose-file/networks/) — `internal: true` semantics
- [Docker Compose — Networking how-to](https://docs.docker.com/compose/how-tos/networking/) — bridge driver isolation
- [LangChain BaseTool API reference](https://python.langchain.com/api_reference/core/tools/langchain_core.tools.base.BaseTool.html) — `args_schema`, `_run`/`_arun`
- [PyPI asyncua 1.1.8](https://pypi.org/project/asyncua/) — version confirmed
- [PyPI nats-py 2.14.0](https://pypi.org/project/nats-py/) — version confirmed
- [PyPI asyncpg 0.31.0](https://pypi.org/project/asyncpg/) — version confirmed

### Secondary (MEDIUM confidence)

- [DeepWiki C-MAPSS FD001-FD004 sub-datasets](https://deepwiki.com/barryib1603/NASA-Turbofan-Jet-Engine-RUL-prediction-C-MAPSS/2.2-fd001-fd004-sub-datasets) — train/test trajectory counts, fault modes per sub-dataset (cross-verified)
- [NASA Open Data Portal — CMAPSS Jet Engine](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data) — dataset origin authoritative
- [LangChain blog — Structured Tools](https://blog.langchain.com/structured-tools/) — args_schema pattern
- [Build OPC UA Server in Python tutorial](https://iotdigitaltwinplm.com/opc-ua-server-python-asyncua-tutorial-production-ready/) — production patterns reference
- [OneUptime — Docker isolated network for testing](https://oneuptime.com/blog/post/2026-02-08-how-to-create-an-isolated-docker-network-for-testing/view) — internal flag testing patterns
- [Jacopo Farina — Ingest data into Postgres fast](https://jacopofarina.eu/posts/ingest-data-into-postgres-fast/) — prepared statement performance 3700 rows/s baseline
- [Medium — NATS JetStream playbook exactly-once](https://medium.com/@hadiyolworld007/nats-jetstream-playbook-exactly-once-minus-the-bloat-02fd9d5a051c) — durable+ack pattern

### Tertiary (LOW confidence — needs verification before use)

- [Ignition forum — OPC UA namespace best practice](https://forum.inductiveautomation.com/t/opc-ua-namespace-best-practice/105848) — namespace URI patterns (community thread; verified against asyncua docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all 12 packages verified on PyPI (2026-05-18), versions latest stable, slopcheck cleared
- Architecture: HIGH — patterns matched against asyncua/nats-py/asyncpg/langchain-core/TimescaleDB official docs; D-49 SQL syntax verified live in TimescaleDB 2.18 docs
- Pitfalls: HIGH — 7 pitfalls identified, all with documented mitigation steps + warning signs
- LangChain v1.x Pydantic v2 native: MEDIUM — verified through official BaseTool reference; some old tutorials still show v1 mix (Pitfall 5 explicit warning)
- Docker network enforcement: MEDIUM — `internal: true` semantics confirmed; CI-context edge cases (DNS shared) flagged as Open Question #1 and Assumption A5

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (30 days for stack like asyncua/nats-py/asyncpg/TimescaleDB — stable; flag LangChain core ecosystem at 14 days due to fast-moving major version line)
